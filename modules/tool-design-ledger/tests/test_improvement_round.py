"""Keep, undo and budget receipts survive the real ledger boundary."""
from copy import deepcopy
import base64
import hashlib
import json
import re
from pathlib import Path
import subprocess
import sys

import jsonschema
import pytest

from amplifier_module_tool_design_ledger import DesignLedgerTool
from amplifier_module_tool_design_ledger.improvement_round import validate_round
from amplifier_module_tool_render_report.template import ship_verdict
from amplifier_module_tool_render_report.template import render

ROOT=Path(__file__).resolve().parents[3]
FIXTURES=ROOT/'fixtures/improvement-round'


def fixture(name='keep'):
    return json.loads((FIXTURES/(name+'.json')).read_text())


@pytest.mark.parametrize('name,adoption,can_continue',[
    ('keep','recorded_keep',False),('undo','recorded_undo',False),('budget','pending',False)])
def test_canonical_schema_and_runtime_adapter_agree(name,adoption,can_continue):
    value=fixture(name)
    schema=json.loads((ROOT/'contracts/taste-improvement-round.v1.schema.json').read_text())
    jsonschema.Draft202012Validator(schema).validate(value)
    result=validate_round(value)
    assert result['adoption_status']==adoption
    assert result['can_continue']is can_continue
    assert result['runtime_authorization']=='not established by this record'
    for key in ['baseline','candidate']:
        assert hashlib.sha256((ROOT/value[key]['artifact_ref']).read_bytes()).hexdigest()==value[key]['sha256']


@pytest.mark.parametrize('status',['fail','unknown'])
def test_high_score_cannot_bypass_a_critical_gate(status):
    value=fixture();value['gates'][0]['status']=status
    with pytest.raises(ValueError,match='block keep'):validate_round(value)


def test_baseline_candidate_and_brief_cannot_shift_under_a_recorded_decision():
    before=fixture()
    for key in ['baseline','candidate']:
        value=deepcopy(before);value[key]['sha256']='f'*64
        with pytest.raises(ValueError,match='changed within'):validate_round(value,before)
    value=deepcopy(before);value['comparison']['brief_ref']='different-brief'
    with pytest.raises(ValueError,match='same brief'):validate_round(value)


def test_unverified_proposals_count_and_exhausted_budget_stops():
    value=fixture();value['budget']['rounds_used']=0
    with pytest.raises(ValueError,match='including proposed rounds'):validate_round(value)
    value=fixture('budget');value['budget']['stop_reason']='continue'
    with pytest.raises(ValueError,match='exhausted'):validate_round(value)


def test_keep_needs_a_recorded_authority_source_but_does_not_authenticate_it():
    value=fixture();value['decision']['authority']='none'
    with pytest.raises(ValueError,match='decision source'):validate_round(value)
    assert ship_verdict(32,converged=True)=='Ready for review'


def test_app_payload_keeps_review_readiness_separate_from_shipping():
    from app.results import build_result_payload
    result=build_result_payload({'records':[],'champion':{'scores':{'clarity':4},'total':32},'gate':{'reason':'bar_met'},'converged':True})
    assert result['review_ready']is True and result['ship']is False
    assert result['ship_label']=='Ready for review'
    assert result['adoption_status']=='not established by score or convergence'


async def test_real_ledger_rejects_invalid_round_without_writing(tmp_path):
    value=fixture();value['gates'][0]['status']='unknown'
    result=await DesignLedgerTool(tmp_path).execute({'op':'append','record':{
        'run_id':'fictional','task_class':'note','pass':1,'outcome':'accepted',
        'scores':{'clarity':4},'improvement_round':value}})
    assert not result.success and 'block keep'in result.error['message']
    assert not tmp_path.joinpath('note.jsonl').exists()


async def test_real_ledger_keeps_receipts_but_never_promotes_undone_candidate(tmp_path):
    tool=DesignLedgerTool(tmp_path)
    for name in ['keep','undo','budget']:
        result=await tool.execute({'op':'append','record':{'run_id':name,'task_class':'note',
          'pass':1,'outcome':'accepted','scores':{'clarity':4},'improvement_round':fixture(name)}})
        assert result.success,result.error
    queried=await tool.execute({'op':'query','task_class':'note'})
    assert [r['improvement_round_status']['adoption_status']for r in queried.output]==['recorded_keep','recorded_undo','pending']
    best=await tool.execute({'op':'best','task_class':'note'})
    assert best.output['improvement_round_status']['adoption_status']!='recorded_undo'
    changed=fixture();changed['baseline']['sha256']='f'*64
    result=await tool.execute({'op':'append','record':{'run_id':'keep','task_class':'note',
       'pass':2,'outcome':'accepted','improvement_round':changed}})
    assert not result.success
    assert len((tmp_path/'note.jsonl').read_text().splitlines())==3


async def test_new_round_cannot_reset_or_silently_raise_the_recorded_run_budget(tmp_path):
    tool=DesignLedgerTool(tmp_path)
    base={'run_id':'one-run','task_class':'note','pass':1,'outcome':'accepted'}
    assert (await tool.execute({'op':'append','record':{**base,'improvement_round':fixture('keep')}})).success
    value=fixture('undo')
    result=await tool.execute({'op':'append','record':{**base,'improvement_round':value}})
    assert not result.success and 'increment'in result.error['message']
    value['budget'].update(rounds_used=2,rounds_limit=3)
    result=await tool.execute({'op':'append','record':{**base,'improvement_round':value}})
    assert not result.success and 'silently change'in result.error['message']
    value=fixture('budget')
    assert (await tool.execute({'op':'append','record':{**base,'improvement_round':value}})).success
    assert len((tmp_path/'note.jsonl').read_text().splitlines())==2


def test_dlx_threads_supplied_round_into_a_real_pass_record(tmp_path):
    (tmp_path/'improvement_round.json').write_text(json.dumps(fixture()))
    command=[sys.executable,str(ROOT/'recipes/dlx.py'),'passrec',str(tmp_path),'run','note','sig','v1','accepted','','NEW_BEST']
    result=subprocess.run(command,text=True,capture_output=True)
    assert result.returncode==0,result.stderr
    assert json.loads(result.stdout)['improvement_round']==fixture()
    (tmp_path/'improvement_round.json').write_text('broken')
    result=subprocess.run(command,text=True,capture_output=True)
    assert result.returncode!=0 and 'invalid_improvement_round'in result.stdout


def test_embedded_recipe_helpers_match_the_canonical_script():
    expected=(ROOT/'recipes/dlx.py').read_bytes()
    for name in ['design-pass.yaml','design-converge.yaml']:
        encoded=re.search(r"echo '([A-Za-z0-9+/=]+)' \| base64 -d > \"\$(?:W|WD)/dlx\.py\"",(ROOT/'recipes'/name).read_text())
        assert encoded and base64.b64decode(encoded[1])==expected


def test_report_shows_recorded_decision_without_shipping_claim_and_escapes_it(tmp_path):
    value=fixture();value['decision']['reason']='<script>bad</script>'
    artifact=str(FIXTURES/'candidate.html')
    dims=['clarity','elegance','restraint','empowerment','agency','ease','character','point']
    state={'records':[{'pass':0,'task_class':'fictional','artifact_ref':artifact,'scores':dict.fromkeys(dims,4),'improvement_round':value}],
           'champion':{'artifact_ref':artifact,'scores':dict.fromkeys(dims,4),'total':32},
           'gate':{'action':'DONE','reason':'bar_met'},'converged':True}
    result=render(state,out_dir=str(tmp_path))
    report=Path(result['report_html']).read_text()
    assert 'Ready for review'in report and 'Ready to ship'not in report
    assert 'Ship it'not in report and 'Worth it'not in report
    assert 'Recorded decision: keep'in report and '&lt;script&gt;bad&lt;/script&gt;'in report
    assert 'do not authenticate a person or grant runtime permission'in report
