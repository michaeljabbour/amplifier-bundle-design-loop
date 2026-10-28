"""Pure improvement-round/v1 consumer validation; no model, I/O or authorization.

Taste owns the portable schema/method. This adapter owns Design Loop validation.
It records a claimed human decision without authenticating or executing it.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys


def _object(value, keys, label):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError(f'{label}: expected exactly {", ".join(keys)}')


def _text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{label}: non-empty text required')


def _choice(value, choices, label):
    if value not in choices:
        raise ValueError(f'{label}: expected one of {", ".join(choices)}')


def _artifact(value, label):
    _object(value, ['artifact_ref', 'sha256'], label)
    _text(value['artifact_ref'], label + '.artifact_ref')
    if not isinstance(value['sha256'], str) or not re.fullmatch('[a-f0-9]{64}', value['sha256']):
        raise ValueError(f'{label}: sha256 must be 64 lower-case hex characters')


def validate_round(record, previous=None):
    """Validate a comparison record and return technical/recorded-adoption states.

    Artifact hashes are checked for format and consistency across the same round,
    not recomputed from arbitrary filesystem paths. The caller owns actual file
    capture and permission enforcement. Invalid input raises ValueError.
    """
    _object(record, ['schema_version', 'round_id', 'brief', 'baseline', 'candidate',
                     'change', 'gates', 'comparison', 'decision', 'budget'], 'round')
    if record['schema_version'] != 'improvement-round/v1':
        raise ValueError('Unsupported improvement-round version')
    _text(record['round_id'], 'round_id')
    brief=record['brief']
    _object(brief, ['intent','audience','source_ref','lens_status','must_preserve'], 'brief')
    for key in ['intent','audience','source_ref']:_text(brief[key], 'brief.'+key)
    _choice(brief['lens_status'], ['stated','assumed'], 'brief.lens_status')
    if not isinstance(brief['must_preserve'], list):raise ValueError('must_preserve must be a list')
    for item in brief['must_preserve']:_text(item,'must_preserve item')
    for key in ['baseline','candidate']:_artifact(record[key],key)
    if previous is not None and previous.get('round_id')==record['round_id']:
        for key in ['brief','baseline','candidate','change']:
            if previous.get(key)!=record[key]:raise ValueError(f'{key} changed within the same round; use a new round ID')
    change=record['change']
    _object(change, ['mode','hypothesis','predicted_benefit','regression_risk'], 'change')
    _choice(change['mode'], ['hillclimb','jump'], 'change.mode')
    for key in ['hypothesis','predicted_benefit','regression_risk']:_text(change[key],'change.'+key)
    gates=record['gates']
    if not isinstance(gates,list) or not gates:raise ValueError('At least one gate is required')
    gate_ids=[];blocked=[]
    for gate in gates:
        _object(gate,['id','critical','status','evidence_ref','reason'],'gate')
        for key in ['id','evidence_ref','reason']:_text(gate[key],'gate.'+key)
        if type(gate['critical'])is not bool:raise ValueError('gate.critical must be boolean')
        _choice(gate['status'],['pass','fail','unknown','not-applicable'],'gate.status')
        gate_ids.append(gate['id'])
        if gate['critical'] and gate['status']in['fail','unknown']:blocked.append(gate['id'])
    if len(set(gate_ids))!=len(gate_ids):raise ValueError('Gate IDs must be unique')
    comparison=record['comparison']
    _object(comparison,['brief_ref','observations','taste','elegance'],'comparison')
    if comparison['brief_ref']!=brief['source_ref']:raise ValueError('Comparison must use the same brief')
    if not isinstance(comparison['observations'],list):raise ValueError('observations must be a list')
    for item in comparison['observations']:_text(item,'comparison observation')
    for axis in ['taste','elegance']:
        _object(comparison[axis],['status','reason'],axis)
        _choice(comparison[axis]['status'],['hypothesis','observed','unknown'],axis+'.status')
        _text(comparison[axis]['reason'],axis+'.reason')
    decision=record['decision']
    _object(decision,['action','authority','source_ref','reason','rollback_ref'],'decision')
    _choice(decision['action'],['proposed','keep','undo','defer'],'decision.action')
    _choice(decision['authority'],['human','delegated','none'],'decision.authority')
    for key in ['source_ref','reason','rollback_ref']:_text(decision[key],'decision.'+key)
    if decision['action']in['keep','undo'] and decision['authority']=='none':raise ValueError('Keep/undo needs a recorded human or delegated decision source')
    if decision['action']=='keep' and blocked:raise ValueError('Critical failed/unknown gates block keep: '+', '.join(blocked))
    budget=record['budget']
    _object(budget,['rounds_limit','rounds_used','stop_reason'],'budget')
    if any(type(budget[k])is not int or budget[k]<1 for k in ['rounds_limit','rounds_used']):raise ValueError('Budget counts must be positive integers, including proposed rounds')
    _choice(budget['stop_reason'],['continue','success','no-meaningful-gain','budget-exhausted','gate-blocked','owner-stop'],'budget.stop_reason')
    if budget['rounds_used']>budget['rounds_limit']:raise ValueError('Round budget exceeded')
    if budget['rounds_used']==budget['rounds_limit'] and budget['stop_reason']=='continue':raise ValueError('Round budget exhausted; a stop reason is required')
    if budget['stop_reason']=='budget-exhausted' and budget['rounds_used']<budget['rounds_limit']:raise ValueError('Budget-exhausted reason disagrees with the round count')
    action=decision['action']
    return {'technical_valid':not blocked,'blocked_gates':blocked,
            'adoption_status':'recorded_'+action if action in ['keep','undo'] else'pending',
            'runtime_authorization':'not established by this record',
            'can_continue':budget['rounds_used']<budget['rounds_limit'] and budget['stop_reason']=='continue',
            'stop_reason':budget['stop_reason']}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('record',type=Path)
    args=parser.parse_args()
    try:result=validate_round(json.loads(args.record.read_text()))
    except (ValueError,TypeError,KeyError,OSError)as error:
        print(json.dumps({'valid':False,'error':str(error)}),file=sys.stderr);return 2
    print(json.dumps({'valid':True,**result}));return 0


if __name__=='__main__':sys.exit(main())
