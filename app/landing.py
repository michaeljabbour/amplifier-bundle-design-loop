"""Builds the Landing page HTML: vendored Page_Worth CSS + a REAL drag-and-drop /
click-to-browse / paste-image upload zone, a URL input, and an HTML paste/upload
panel (vanilla JS, no framework) -- plus the in-app Working and Results panes
and a Past-verdicts history list.

Reuses the same CSS custom properties and small markup helpers that
amplifier_module_tool_render_report.template uses for the generated
report.html, so the Landing page (served by this app) and the Results pane
(the report.html this app now embeds inline, rather than navigating to) look
like one continuous journey -- exactly the effect the bundle's own
`_pw_journey_nav` / `data-pw-view` convention is designed for.
"""

from __future__ import annotations

from amplifier_module_tool_render_report import template as t

_EXTRA_CSS = """
.dl-dropzone{max-width:640px;margin:0 auto;border:2px dashed var(--border-1);border-radius:8px;
  background:var(--bg-card);padding:46px 24px;text-align:center;cursor:pointer;transition:border-color .15s,background .15s}
.dl-dropzone.dl-drag{border-color:var(--slp-amber);background:var(--band-soft)}
.dl-dropzone h3{font-family:var(--font-display);font-weight:500;font-size:22px;color:var(--fg-1);margin:0 0 8px}
.dl-dropzone p{font-family:var(--font-body);font-size:14px;color:var(--fg-3);margin:0}
.dl-dropzone .dl-icon{font-size:34px;margin-bottom:10px;color:var(--fg-accent)}
.dl-preview{max-width:640px;margin:18px auto 0;display:none}
.dl-preview img{max-width:100%;max-height:220px;border-radius:6px;border:1px solid var(--border-1);display:block;margin:0 auto}
.dl-status{font-family:var(--font-ui);font-size:12px;color:var(--fg-3);text-align:center;margin-top:10px}
.dl-error{color:#a4392a}
[data-pw-tab][disabled]{opacity:.35;cursor:default;pointer-events:none}
.dl-mode-row{display:flex;justify-content:center;margin-bottom:22px}
.dl-mode-row-inner{display:inline-flex;border:1px solid var(--border-1);border-radius:3px;
  background:var(--bg-card);padding:4px;gap:4px;box-shadow:var(--shadow-card)}
.dl-mode-btn{font-family:var(--font-ui);font-weight:500;font-size:13px;border:none;background:none;
  border-radius:3px;padding:9px 18px;color:var(--fg-3);cursor:pointer}
.dl-mode-btn.dl-mode-active{background:var(--slp-amber);color:#fff}
.dl-panel{display:none}
.dl-panel.dl-panel-active{display:block}
.dl-field-label{display:block;font-family:var(--font-ui);font-weight:500;font-size:12px;
  letter-spacing:.06em;text-transform:uppercase;color:var(--fg-3);margin-bottom:8px}
.dl-url-input,.dl-html-textarea{width:100%;font-family:var(--font-ui);font-size:14px;color:var(--fg-1);
  background:var(--bg-card);border:1px solid var(--border-1);border-radius:6px;padding:12px 14px;
  box-sizing:border-box}
.dl-html-textarea{min-height:160px;resize:vertical;font-family:'Courier New',Courier,monospace;font-size:12.5px}
.dl-html-filerow{margin:10px 0;font-family:var(--font-ui);font-size:12px;color:var(--fg-3)}
.dl-analyze-btn{margin-top:12px;font-family:var(--font-ui);font-weight:600;font-size:13px;color:#fff;
  background:var(--slp-amber);border:none;border-radius:4px;padding:10px 20px;cursor:pointer}
.dl-analyze-btn:disabled{opacity:.5;cursor:default}
.dl-result-link{font-family:var(--font-ui);font-weight:600;font-size:13px;color:var(--fg-accent);
  text-decoration:underline;text-underline-offset:3px}
.dl-history-empty{font-family:var(--font-ui);font-size:13px;color:var(--fg-3);font-style:italic}
.dl-history-grid{display:grid;gap:14px;grid-template-columns:repeat(auto-fill,minmax(220px,1fr))}
.dl-history-card{background:var(--bg-card);border:1px solid var(--border-1);border-radius:6px;
  padding:14px 16px;display:flex;flex-direction:column;gap:6px;box-shadow:var(--shadow-card);
  text-decoration:none;color:inherit}
"""


def _dropzone_card() -> str:
    return (
        '<div class="dl-dropzone" id="dl-dropzone" tabindex="0" role="button" '
        'aria-label="Upload a screenshot to critique">'
        '<div class="dl-icon">&#8681;</div>'
        "<h3>Drop a screenshot here</h3>"
        "<p>...or click to browse, or paste an image (Cmd/Ctrl+V)</p>"
        '<input id="dl-file-input" type="file" accept="image/*" style="display:none" />'
        "</div>"
        '<div class="dl-preview" id="dl-preview"><img id="dl-preview-img" alt="Upload preview" /></div>'
        '<div class="dl-status" id="dl-status"></div>'
    )


def _image_panel() -> str:
    return (
        '<div class="dl-panel dl-panel-active" data-dl-panel="image">'
        + _dropzone_card()
        + "</div>"
    )


def _url_panel() -> str:
    return (
        '<div class="dl-panel" data-dl-panel="url" style="max-width:640px;margin:0 auto">'
        '<label class="dl-field-label" for="dl-url-input">Paste a URL to critique</label>'
        '<input type="text" id="dl-url-input" class="dl-url-input" placeholder="https://example.com" />'
        '<div><button type="button" id="dl-url-analyze" class="dl-analyze-btn">Analyze &rarr;</button></div>'
        '<div class="dl-status" id="dl-url-status"></div>'
        "</div>"
    )


def _html_panel() -> str:
    return (
        '<div class="dl-panel" data-dl-panel="html" style="max-width:640px;margin:0 auto">'
        '<label class="dl-field-label" for="dl-html-textarea">Paste raw HTML to critique</label>'
        '<textarea id="dl-html-textarea" class="dl-html-textarea" '
        'placeholder="&lt;!DOCTYPE html&gt;..."></textarea>'
        '<div class="dl-html-filerow">...or drop / choose an .html file: '
        '<input id="dl-html-file-input" type="file" accept=".html,.htm" /></div>'
        '<div><button type="button" id="dl-html-analyze" class="dl-analyze-btn">Analyze &rarr;</button></div>'
        '<div class="dl-status" id="dl-html-status"></div>'
        "</div>"
    )


def _mode_tabs_row() -> str:
    """Functional Image | URL | HTML segmented control (replaces the dead
    t._pw_mode_tabs() demo buttons from the generated report's Landing
    section -- these actually switch input panels below)."""
    return (
        '<div class="dl-mode-row"><div class="dl-mode-row-inner" role="tablist">'
        '<button type="button" class="dl-mode-btn dl-mode-active" data-dl-mode="image">Image</button>'
        '<button type="button" class="dl-mode-btn" data-dl-mode="url">URL</button>'
        '<button type="button" class="dl-mode-btn" data-dl-mode="html">HTML</button>'
        "</div></div>"
    )


def _input_modes_section() -> str:
    return _mode_tabs_row() + _image_panel() + _url_panel() + _html_panel()


def _dims_grid() -> str:
    return "".join(
        '<div style="background:var(--bg-card);padding:14px 16px">'
        f'<div style="font-family:var(--font-ui);font-weight:600;font-size:12px;letter-spacing:.06em;'
        f'text-transform:uppercase;color:var(--fg-accent);margin-bottom:3px">{t._esc(d["label"])}</div>'
        f'<div style="font-family:var(--font-body);font-size:13.5px;line-height:1.45;color:var(--fg-2)">'
        f"{t._esc(d['q'])}</div>"
        "</div>"
        for d in t.PW_DIMS
    )


def _history_section() -> str:
    """Container for the 'Past verdicts' list; populated client-side from
    GET /api/history on load and refreshed after each run completes."""
    return (
        '<div style="max-width:640px;margin:46px auto 0">'
        '<div style="display:flex;align-items:center;justify-content:center;gap:10px;margin-bottom:18px">'
        '<span style="display:block;width:30px;height:1px;background:var(--slp-amber)"></span>'
        '<span style="font-family:var(--font-ui);font-weight:500;font-size:11px;letter-spacing:.24em;'
        'text-transform:uppercase;color:var(--fg-3)">Past verdicts</span>'
        '<span style="display:block;width:30px;height:1px;background:var(--slp-amber)"></span>'
        "</div>"
        '<div id="dl-history-list" class="dl-history-empty" style="text-align:center">Loading&hellip;</div>'
        "</div>"
    )


def _journey_nav() -> str:
    """1/2/3 tab strip plus an always-available 'Start over' reset control.

    The Landing tab is never given a `disabled` attribute, so it stays
    clickable at every stage of the journey (per spec).
    """
    return (
        '<div class="pw-journey-nav">'
        '<button type="button" data-pw-tab="landing" class="pw-tab-active">1 &middot; Landing</button>'
        '<button type="button" data-pw-tab="working" disabled>2 &middot; Working</button>'
        '<button type="button" data-pw-tab="results" disabled>3 &middot; Results</button>'
        '<button type="button" id="dl-reset-btn" style="margin-left:auto;font-family:var(--font-ui);'
        "font-weight:500;font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--fg-3);"
        "background:none;border:1px solid var(--border-1);border-radius:4px;padding:6px 14px;"
        'cursor:pointer;align-self:center">&#8635; Start over</button>'
        "</div>"
    )


def _working_view() -> str:
    """Live transaction-log pane -- rows are appended by JS as stream_events
    arrive -- plus an animated 'Running...' status header (B1) that flips to
    a done/escalated label once the `result` message arrives."""
    header = (
        '<div style="display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:12px">'
        '<div style="display:flex;align-items:center;gap:10px">'
        '<span style="display:block;width:26px;height:1px;background:var(--slp-amber)"></span>'
        '<span style="font-family:var(--font-ui);font-weight:500;font-size:11px;letter-spacing:.2em;'
        'text-transform:uppercase;color:var(--fg-3)">Working &middot; live transaction log</span>'
        "</div>"
        '<div id="dl-run-status" style="display:flex;align-items:center;gap:8px">'
        '<span id="dl-run-spinner" style="display:inline-block;width:8px;height:8px;border-radius:50%;'
        'background:var(--slp-amber);animation:pw-pulse 1s ease-in-out infinite"></span>'
        '<span id="dl-run-status-text" style="font-family:var(--font-ui);font-weight:600;font-size:12px;'
        'letter-spacing:.04em;color:var(--fg-accent)">Running&hellip;</span>'
        "</div>"
        "</div>"
    )
    return (
        '<div data-pw-view="working" hidden>'
        + header
        + '<div id="dl-log" style="background:var(--bg-card);border:1px solid var(--border-1);'
        'border-radius:6px;padding:14px 20px;box-shadow:var(--shadow-card);min-height:120px"></div>'
        "</div>"
    )


def _script() -> str:
    """Vanilla JS: tab switching + real DnD/click/paste image upload + URL/HTML
    input modes + WS streaming client + in-app results rendering + reset +
    history list. No template literals or backticks are used (string
    concatenation only) so this stays trivially embeddable regardless of how
    the surrounding Python string is quoted.
    """
    lines = [
        "(function(){",
        "var tabs=document.querySelectorAll('[data-pw-tab]');",
        "var views=document.querySelectorAll('[data-pw-view]');",
        "function showView(name){",
        "  views.forEach(function(v){v.hidden=v.getAttribute('data-pw-view')!==name;});",
        "  tabs.forEach(function(tb){tb.classList.toggle('pw-tab-active',tb.getAttribute('data-pw-tab')===name);});",
        "}",
        "tabs.forEach(function(tb){tb.addEventListener('click',function(){",
        "  if(tb.hasAttribute('disabled')){return;}",
        "  showView(tb.getAttribute('data-pw-tab'));",
        "});});",
        "",
        "function escHtml(s){",
        "  if(s===null||s===undefined){s='';}",
        "  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\"/g,'&quot;');",
        "}",
        "",
        "var dropzone=document.getElementById('dl-dropzone');",
        "var fileInput=document.getElementById('dl-file-input');",
        "var preview=document.getElementById('dl-preview');",
        "var previewImg=document.getElementById('dl-preview-img');",
        "var statusEl=document.getElementById('dl-status');",
        "var logEl=document.getElementById('dl-log');",
        "var workingTab=document.querySelector('[data-pw-tab=\"working\"]');",
        "var resultsTab=document.querySelector('[data-pw-tab=\"results\"]');",
        "var resultsView=document.querySelector('[data-pw-view=\"results\"]');",
        "var runStatusText=document.getElementById('dl-run-status-text');",
        "var runSpinner=document.getElementById('dl-run-spinner');",
        "var resetBtn=document.getElementById('dl-reset-btn');",
        "var currentSocket=null;",
        "var activeStatusEl=statusEl;",
        "",
        "function setStatusFor(el,msg,isError){",
        "  if(!el){return;}",
        "  el.textContent=msg;",
        "  el.className='dl-status'+(isError?' dl-error':'');",
        "}",
        "function setStatus(msg,isError){setStatusFor(statusEl,msg,isError);}",
        "",
        "function setRunStatus(state,label){",
        "  if(state==='running'){",
        "    runStatusText.textContent='Running\\u2026';",
        "    runStatusText.style.color='var(--fg-accent)';",
        "    runSpinner.style.display='inline-block';",
        "  } else if(state==='done'){",
        "    runStatusText.textContent=label||'\\u2713 Done';",
        "    runStatusText.style.color='var(--slp-sage-dark)';",
        "    runSpinner.style.display='none';",
        "  } else {",
        "    runStatusText.textContent=label||'Error';",
        "    runStatusText.style.color='#a4392a';",
        "    runSpinner.style.display='none';",
        "  }",
        "}",
        "",
        "function showPreview(file){",
        "  var reader=new FileReader();",
        "  reader.onload=function(e){previewImg.src=e.target.result;preview.style.display='block';};",
        "  reader.readAsDataURL(file);",
        "}",
        "",
        "function appendLogRow(label,text,active){",
        "  var row=document.createElement('div');",
        "  row.className='pw-log-line'+(active?' pw-row-active':'');",
        "  row.setAttribute('data-pw-logrow','');",
        "  var b=document.createElement('b');",
        "  b.textContent=label;",
        "  row.appendChild(b);",
        "  row.appendChild(document.createTextNode(text));",
        "  var prevActive=logEl.querySelector('.pw-row-active');",
        "  if(prevActive){prevActive.classList.remove('pw-row-active');}",
        "  logEl.appendChild(row);",
        "  logEl.scrollTop=logEl.scrollHeight;",
        "}",
        "",
        "function finalizeLog(total,verdict){",
        "  var prevActive=logEl.querySelector('.pw-row-active');",
        "  if(prevActive){prevActive.classList.remove('pw-row-active');}",
        "  var row=document.createElement('div');",
        "  row.className='pw-log-line';",
        "  row.setAttribute('data-pw-logrow','');",
        "  var b=document.createElement('b');",
        "  b.textContent='\\u2713 DONE';",
        "  row.appendChild(b);",
        "  var totalText=(total===null||total===undefined)?'?':String(total);",
        "  row.appendChild(document.createTextNode(' \\u2014 champion '+totalText+'/32 ('+(verdict||'unknown')+')'));",
        "  logEl.appendChild(row);",
        "  logEl.scrollTop=logEl.scrollHeight;",
        "}",
        "",
        "var toolRows={};",
        "function handleStreamEvent(evtType,data){",
        "  data=data||{};",
        "  if(evtType==='display'){",
        "    var source=(data.metadata&&data.metadata.source)||'loop';",
        "    appendLogRow(source.toUpperCase(),' '+(data.message||''),true);",
        "  } else if(evtType==='tool:pre'){",
        "    var name=data.tool_name||'tool';",
        "    appendLogRow('TOOL',' using '+name+'...',true);",
        "    toolRows[name]=logEl.querySelector('[data-pw-logrow]:last-child');",
        "  } else if(evtType==='tool:post'){",
        "    var tname=data.tool_name||'tool';",
        "    var resp=data.tool_response||{};",
        "    var ok=resp.success!==false;",
        "    var row=toolRows[tname];",
        "    var mark=ok?String.fromCharCode(0x2705):String.fromCharCode(0x274C);",
        "    if(row){",
        "      row.lastChild.textContent=' '+mark+' '+tname+(resp.summary?(' -- '+resp.summary):'');",
        "      row.classList.remove('pw-row-active');",
        "    } else {",
        "      appendLogRow('TOOL',' '+mark+' '+tname,false);",
        "    }",
        "  }",
        "}",
        "",
        "function renderResults(msg){",
        "  var reportUrl=msg.report_url||'';",
        "  var upgradedUrl=msg.upgraded_url||'';",
        "  var baselineUrl=msg.baseline_url||'';",
        "  var html='';",
        "  html+='<div style=\"display:flex;align-items:center;gap:10px;margin-bottom:12px\">';",
        "  html+='<span style=\"display:block;width:26px;height:1px;background:var(--slp-amber)\"></span>';",
        "  html+='<span style=\"font-family:var(--font-ui);font-weight:500;font-size:11px;letter-spacing:.2em;';",
        "  html+='text-transform:uppercase;color:var(--fg-3)\">Results</span>';",
        "  html+='</div>';",
        '  html+=\'<iframe id="dl-report-iframe" src="\'+reportUrl+\'" title="Design loop report" \';',
        "  html+='style=\"width:100%;height:640px;border:1px solid var(--border-1);border-radius:6px;';",
        "  html+='box-shadow:var(--shadow-card);background:var(--bg-2);display:block\"></iframe>';",
        "  html+='<div style=\"display:flex;gap:18px;flex-wrap:wrap;margin-top:14px\">';",
        '  html+=\'<a class="dl-result-link" href="\'+reportUrl+\'" target="_blank" rel="noopener">Open full report \\u2197</a>\';',
        '  html+=\'<a class="dl-result-link" href="\'+upgradedUrl+\'" target="_blank" rel="noopener">Upgraded page \\u2197</a>\';',
        '  html+=\'<a class="dl-result-link" href="\'+baselineUrl+\'" target="_blank" rel="noopener">Baseline page \\u2197</a>\';',
        "  html+='</div>';",
        "  resultsView.innerHTML=html;",
        "}",
        "",
        "function loadHistory(){",
        "  var listEl=document.getElementById('dl-history-list');",
        "  if(!listEl){return;}",
        "  fetch('/api/history').then(function(res){return res.json();}).then(function(data){",
        "    var entries=data.entries||[];",
        "    if(entries.length===0){",
        "      listEl.className='dl-history-empty';",
        "      listEl.style.textAlign='center';",
        "      listEl.textContent='No past runs yet.';",
        "      return;",
        "    }",
        "    listEl.className='dl-history-grid';",
        "    listEl.style.textAlign='';",
        "    var html='';",
        "    for(var i=0;i<entries.length;i++){",
        "      var e=entries[i];",
        "      var dateStr=escHtml((e.ts||'').slice(0,10));",
        "      var statusLabel=e.converged?'Converged':('Escalated'+(e.reason?(' ('+escHtml(e.reason)+')'):''));",
        "      var totalStr=(e.total===null||e.total===undefined)?'?':escHtml(e.total);",
        "      var tc=escHtml(e.task_class||'\\u2014');",
        "      var reportUrl=e.report_url||'#';",
        '      html+=\'<a class="dl-history-card" href="\'+reportUrl+\'" target="_blank" rel="noopener">\';',
        "      html+='<div style=\"display:flex;align-items:center;justify-content:space-between;gap:8px\">';",
        "      html+='<span style=\"font-family:var(--font-ui);font-weight:600;font-size:11px;letter-spacing:.1em;'+",
        "        'text-transform:uppercase;color:var(--fg-accent)\">'+statusLabel+'</span>';",
        "      html+='<span style=\"font-family:var(--font-display);font-weight:600;font-size:16px;'+",
        "        'color:var(--fg-1)\">'+totalStr+'/32</span>';",
        "      html+='</div>';",
        "      html+='<div style=\"font-family:var(--font-body);font-size:13px;color:var(--fg-2)\">'+tc+'</div>';",
        "      html+='<div style=\"font-family:var(--font-ui);font-size:11px;color:var(--fg-3)\">'+dateStr+'</div>';",
        "      html+='</a>';",
        "    }",
        "    listEl.innerHTML=html;",
        "  }).catch(function(){",
        "    listEl.className='dl-history-empty';",
        "    listEl.style.textAlign='center';",
        "    listEl.textContent='Could not load history.';",
        "  });",
        "}",
        "",
        "function openSocket(runId){",
        "  var proto=(window.location.protocol==='https:')?'wss:':'ws:';",
        "  var ws=new WebSocket(proto+'//'+window.location.host+'/ws');",
        "  currentSocket=ws;",
        "  ws.onopen=function(){ws.send(JSON.stringify({type:'start',run_id:runId}));};",
        "  ws.onerror=function(){setRunStatus('error','Error');setStatusFor(activeStatusEl,'WebSocket error -- see server console.',true);};",
        "  ws.onmessage=function(evt){",
        "    var msg=JSON.parse(evt.data);",
        "    if(msg.type==='stream_event'){",
        "      handleStreamEvent(msg.event_type,msg.data);",
        "    } else if(msg.type==='result'){",
        "      finalizeLog(msg.total,msg.verdict);",
        "      if(msg.converged){",
        "        setRunStatus('done','\\u2713 Done \\u2014 converged');",
        "      } else {",
        "        setRunStatus('done','\\u26a0 Done \\u2014 escalated ('+escHtml(msg.verdict||'unknown')+')');",
        "      }",
        "      setStatusFor(activeStatusEl,'Done. See the Results tab.',false);",
        "      renderResults(msg);",
        "      resultsTab.removeAttribute('disabled');",
        "      showView('results');",
        "      loadHistory();",
        "    } else if(msg.type==='error'){",
        "      setRunStatus('error','Error');",
        "      setStatusFor(activeStatusEl,'Error: '+(msg.message||'unknown'),true);",
        "    }",
        "  };",
        "}",
        "",
        "function startRun(runId,originStatusEl){",
        "  activeStatusEl=originStatusEl||statusEl;",
        "  workingTab.removeAttribute('disabled');",
        "  showView('working');",
        "  logEl.innerHTML='';",
        "  setRunStatus('running');",
        "  openSocket(runId);",
        "}",
        "",
        "function uploadFile(file){",
        "  if(!file||file.type.indexOf('image/')!==0){",
        "    setStatus('Please provide an image file.',true);",
        "    return;",
        "  }",
        "  showPreview(file);",
        "  setStatus('Uploading...',false);",
        "  var form=new FormData();",
        "  form.append('file',file,file.name||'upload.png');",
        "  fetch('/api/upload',{method:'POST',body:form})",
        "    .then(function(res){",
        "      if(!res.ok){throw new Error('upload failed: '+res.status);}",
        "      return res.json();",
        "    })",
        "    .then(function(data){",
        "      setStatus('Uploaded. Starting design loop (run '+data.run_id+')...',false);",
        "      startRun(data.run_id,statusEl);",
        "    })",
        "    .catch(function(err){setStatus(String(err),true);});",
        "}",
        "",
        "function startFromSource(kind,value,statusElForKind){",
        "  if(!value||!value.trim()){",
        "    setStatusFor(statusElForKind,'Please provide a value.',true);",
        "    return;",
        "  }",
        "  setStatusFor(statusElForKind,'Submitting...',false);",
        "  fetch('/api/source',{",
        "    method:'POST',",
        "    headers:{'Content-Type':'application/json'},",
        "    body:JSON.stringify({kind:kind,value:value})",
        "  })",
        "    .then(function(res){",
        "      if(!res.ok){throw new Error('request failed: '+res.status);}",
        "      return res.json();",
        "    })",
        "    .then(function(data){",
        "      setStatusFor(statusElForKind,'Started run '+data.run_id+'...',false);",
        "      startRun(data.run_id,statusElForKind);",
        "    })",
        "    .catch(function(err){setStatusFor(statusElForKind,String(err),true);});",
        "}",
        "",
        "dropzone.addEventListener('click',function(){fileInput.click();});",
        "dropzone.addEventListener('keydown',function(e){",
        "  if(e.key==='Enter'||e.key===' '){fileInput.click();}",
        "});",
        "fileInput.addEventListener('change',function(e){",
        "  if(e.target.files&&e.target.files[0]){uploadFile(e.target.files[0]);}",
        "});",
        "['dragenter','dragover'].forEach(function(ev){",
        "  dropzone.addEventListener(ev,function(e){",
        "    e.preventDefault();e.stopPropagation();dropzone.classList.add('dl-drag');",
        "  });",
        "});",
        "['dragleave','drop'].forEach(function(ev){",
        "  dropzone.addEventListener(ev,function(e){",
        "    e.preventDefault();e.stopPropagation();dropzone.classList.remove('dl-drag');",
        "  });",
        "});",
        "dropzone.addEventListener('drop',function(e){",
        "  var files=e.dataTransfer&&e.dataTransfer.files;",
        "  if(files&&files[0]){uploadFile(files[0]);}",
        "});",
        "document.addEventListener('paste',function(e){",
        "  var items=(e.clipboardData||window.clipboardData).items;",
        "  if(!items){return;}",
        "  for(var i=0;i<items.length;i++){",
        "    if(items[i].type.indexOf('image')!==-1){",
        "      uploadFile(items[i].getAsFile());",
        "      break;",
        "    }",
        "  }",
        "});",
        "",
        "var modeButtons=document.querySelectorAll('[data-dl-mode]');",
        "var modePanels=document.querySelectorAll('[data-dl-panel]');",
        "function setMode(mode){",
        "  modeButtons.forEach(function(b){b.classList.toggle('dl-mode-active',b.getAttribute('data-dl-mode')===mode);});",
        "  modePanels.forEach(function(p){p.classList.toggle('dl-panel-active',p.getAttribute('data-dl-panel')===mode);});",
        "}",
        "modeButtons.forEach(function(b){b.addEventListener('click',function(){setMode(b.getAttribute('data-dl-mode'));});});",
        "",
        "var urlAnalyzeBtn=document.getElementById('dl-url-analyze');",
        "var urlInputEl=document.getElementById('dl-url-input');",
        "var urlStatusEl=document.getElementById('dl-url-status');",
        "if(urlAnalyzeBtn){",
        "  urlAnalyzeBtn.addEventListener('click',function(){",
        "    startFromSource('url',urlInputEl.value,urlStatusEl);",
        "  });",
        "}",
        "",
        "var htmlAnalyzeBtn=document.getElementById('dl-html-analyze');",
        "var htmlTextareaEl=document.getElementById('dl-html-textarea');",
        "var htmlFileInputEl=document.getElementById('dl-html-file-input');",
        "var htmlStatusEl=document.getElementById('dl-html-status');",
        "if(htmlAnalyzeBtn){",
        "  htmlAnalyzeBtn.addEventListener('click',function(){",
        "    startFromSource('html',htmlTextareaEl.value,htmlStatusEl);",
        "  });",
        "}",
        "function loadHtmlFile(file){",
        "  if(!file){return;}",
        "  var reader=new FileReader();",
        "  reader.onload=function(e){",
        "    htmlTextareaEl.value=e.target.result;",
        "    setStatusFor(htmlStatusEl,'Loaded '+(file.name||'file')+'. Click Analyze to continue.',false);",
        "  };",
        "  reader.readAsText(file);",
        "}",
        "if(htmlFileInputEl){",
        "  htmlFileInputEl.addEventListener('change',function(e){",
        "    if(e.target.files&&e.target.files[0]){loadHtmlFile(e.target.files[0]);}",
        "  });",
        "}",
        "var htmlPanel=document.querySelector('[data-dl-panel=\"html\"]');",
        "if(htmlPanel){",
        "  ['dragenter','dragover'].forEach(function(ev){",
        "    htmlPanel.addEventListener(ev,function(e){e.preventDefault();e.stopPropagation();});",
        "  });",
        "  htmlPanel.addEventListener('drop',function(e){",
        "    e.preventDefault();e.stopPropagation();",
        "    var files=e.dataTransfer&&e.dataTransfer.files;",
        "    if(files&&files[0]){loadHtmlFile(files[0]);}",
        "  });",
        "}",
        "",
        "function resetApp(){",
        "  if(currentSocket){",
        "    try{currentSocket.close();}catch(e){}",
        "    currentSocket=null;",
        "  }",
        "  logEl.innerHTML='';",
        "  preview.style.display='none';",
        "  previewImg.src='';",
        "  fileInput.value='';",
        "  setStatus('',false);",
        "  if(urlInputEl){urlInputEl.value='';}",
        "  setStatusFor(urlStatusEl,'',false);",
        "  if(htmlTextareaEl){htmlTextareaEl.value='';}",
        "  if(htmlFileInputEl){htmlFileInputEl.value='';}",
        "  setStatusFor(htmlStatusEl,'',false);",
        "  setMode('image');",
        "  workingTab.setAttribute('disabled','');",
        "  resultsTab.setAttribute('disabled','');",
        "  resultsView.innerHTML='';",
        "  setRunStatus('running');",
        "  showView('landing');",
        "}",
        "if(resetBtn){resetBtn.addEventListener('click',resetApp);}",
        "",
        "showView('landing');",
        "loadHistory();",
        "})();",
    ]
    return "<script>" + "\n".join(lines) + "</script>"


def build_landing_html() -> str:
    """Return the full Landing page HTML (Page_Worth chrome + real upload UI)."""
    hero = (
        '<div style="text-align:center;margin:34px 0 24px">'
        + t._pw_eyebrow("Design intelligence", "var(--fg-accent)")
        + '<h1 style="font-family:var(--font-display);font-weight:300;font-size:46px;line-height:1.06;'
        'letter-spacing:-.015em;margin:16px 0 16px">Drop a screen.<br>Know what to '
        '<em style="font-style:italic;color:var(--fg-accent)">fix</em> first.</h1>'
        '<p style="font-family:var(--font-body);color:var(--fg-2);max-width:50ch;margin:0 auto;'
        'font-size:17px;line-height:1.6">Upload a screenshot, paste a URL, or paste/upload raw HTML and '
        "the design loop will render it, score it across eight dimensions, and iterate a better version -- "
        "streaming every MAKER &rarr; LINTS &rarr; CRITIC &rarr; GATE step live.</p>"
        "</div>"
    )
    dims_section = (
        '<div style="max-width:640px;margin:46px auto 0">'
        '<div style="display:flex;align-items:center;justify-content:center;gap:10px;margin-bottom:18px">'
        '<span style="display:block;width:30px;height:1px;background:var(--slp-amber)"></span>'
        '<span style="font-family:var(--font-ui);font-weight:500;font-size:11px;letter-spacing:.24em;'
        'text-transform:uppercase;color:var(--fg-3)">Judged on eight things</span>'
        '<span style="display:block;width:30px;height:1px;background:var(--slp-amber)"></span>'
        "</div>"
        '<div style="display:grid;grid-template-columns:1fr 1fr;gap:1px;background:var(--border-1);'
        'border:1px solid var(--border-1);border-radius:6px;overflow:hidden">'
        + _dims_grid()
        + "</div>"
        "</div>"
    )
    landing_view = (
        '<div data-pw-view="landing">'
        "<section>"
        + hero
        + _input_modes_section()
        + dims_section
        + _history_section()
        + "</section>"
        "</div>"
    )

    page_open = (
        '<div style="font-family:var(--font-body);color:var(--fg-1);max-width:920px;'
        'margin:0 auto;padding:26px 22px 110px;min-height:100vh">'
    )

    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8" />\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1" />\n'
        "<title>Page Worth &middot; Design Loop</title>\n"
        "<style>\n" + t._PW_REAL_CSS + t._PW_JOURNEY_CSS + _EXTRA_CSS + "</style>\n"
        "</head>\n"
        "<body>\n"
        + page_open
        + t._pw_header()
        + _journey_nav()
        + landing_view
        + _working_view()
        + '<div data-pw-view="results" hidden></div>'
        + t._pw_footer()
        + _script()
        + "</div>\n"
        "</body>\n"
        "</html>"
    )
