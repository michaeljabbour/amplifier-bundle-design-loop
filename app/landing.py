"""Builds the Landing page HTML: vendored Page_Worth CSS + a single smart-input
zone (type/paste a URL or raw HTML, or drop / paste / click a screenshot or
.html file -- the input kind is auto-detected), plus the in-app Working and
Results panes and a Past-verdicts history list (vanilla JS, no framework).

Reuses the same CSS custom properties and small markup helpers that
amplifier_module_tool_render_report.template uses for the generated
report.html, so the Landing page (served by this app) and the Results pane
look like one continuous journey -- exactly the effect the bundle's own
`_pw_journey_nav` / `data-pw-view` convention is designed for.

The Results pane deliberately does NOT embed the full journey report.html any
more (that felt recursive). It shows a concise verdict + a real before/after
of the baseline and upgraded pages, with the full report one click away.
"""

from __future__ import annotations

from amplifier_module_tool_render_report import template as t

_EXTRA_CSS = """
html{background:var(--bg-2)}
@media(max-width:640px){
  .pw-journey-nav{display:grid!important;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}
  .pw-journey-nav>[data-pw-tab]{padding:10px 0;font-size:11px}
  #dl-mode-badge{grid-column:1 / 3;margin-left:0!important;justify-self:start}
  #dl-reset-btn{margin-left:0!important;padding:6px!important;font-size:10px!important}
}
.dl-context-row input{min-width:0}
.dl-smart{max-width:660px;margin:0 auto;border:2px dashed var(--border-1);border-radius:10px;
  background:var(--bg-card);padding:8px 8px 0;transition:border-color .15s,background .15s;box-shadow:var(--shadow-card)}
.dl-smart.dl-drag{border-color:var(--slp-amber);background:var(--band-soft)}
.dl-smart.dl-focus{border-style:solid;border-color:var(--slp-amber)}
.dl-input{width:100%;box-sizing:border-box;border:none;background:transparent;resize:none;outline:none;
  font-family:var(--font-ui);font-size:15px;line-height:1.5;color:var(--fg-1);padding:16px 14px 8px;min-height:96px}
.dl-input::placeholder{color:var(--fg-3)}
.dl-smart-foot{display:flex;align-items:center;gap:12px;padding:10px 12px;border-top:1px solid var(--border-1);
  flex-wrap:wrap}
.dl-detect{font-family:var(--font-ui);font-size:11px;letter-spacing:.06em;text-transform:uppercase;
  color:var(--fg-3);display:inline-flex;align-items:center;gap:6px}
.dl-detect b{color:var(--fg-accent);font-weight:600}
.dl-detect-dot{width:7px;height:7px;border-radius:50%;background:var(--border-1);display:inline-block}
.dl-detect.dl-on .dl-detect-dot{background:var(--slp-amber)}
.dl-browse{font-family:var(--font-ui);font-size:12px;color:var(--fg-accent);text-decoration:underline;
  text-underline-offset:3px;cursor:pointer;background:none;border:none;padding:0}
.dl-spacer{flex:1 1 auto}
.dl-analyze-btn{font-family:var(--font-ui);font-weight:600;font-size:13px;color:#fff;
  background:var(--slp-amber);border:none;border-radius:5px;padding:9px 20px;cursor:pointer;
  display:inline-flex;align-items:center;gap:6px}
.dl-analyze-btn:disabled{opacity:.45;cursor:default}
.dl-analyze-btn:not(:disabled):hover{background:var(--slp-amber-dark)}
.dl-hint{max-width:660px;margin:10px auto 0;font-family:var(--font-ui);font-size:11.5px;color:var(--fg-3);
  text-align:center}
.dl-preview{max-width:660px;margin:14px auto 0;display:none}
.dl-preview img{max-width:100%;max-height:220px;border-radius:6px;border:1px solid var(--border-1);display:block;margin:0 auto}
.dl-status{font-family:var(--font-ui);font-size:12px;color:var(--fg-3);text-align:center;margin-top:10px;min-height:16px}
.dl-error{color:#a4392a}
[data-pw-tab][disabled]{opacity:.35;cursor:default;pointer-events:none}
.dl-step-ico{display:inline-flex;align-items:center;justify-content:center;width:17px;height:17px;
  border-radius:50%;border:1px solid var(--border-1);font-size:10px;font-weight:600;margin-right:7px;
  color:var(--fg-3);vertical-align:middle;transition:all .15s}
.pw-tab-active .dl-step-ico{border-color:var(--slp-amber);color:var(--slp-amber)}
.dl-step-done .dl-step-ico{background:var(--slp-sage-dark);border-color:var(--slp-sage-dark);color:#fff}
/* progress */
.dl-progress-wrap{margin:2px 0 16px}
.dl-progress-track{height:5px;border-radius:3px;background:var(--border-1);overflow:hidden}
.dl-progress-bar{height:100%;width:0;background:var(--slp-amber);border-radius:3px;transition:width .4s ease}
.dl-progress-bar.dl-done{background:var(--slp-sage-dark)}
.dl-progress-bar.dl-esc{background:#a4392a}
.dl-progress-label{font-family:var(--font-ui);font-size:11px;letter-spacing:.06em;text-transform:uppercase;
  color:var(--fg-3);margin-bottom:6px;display:flex;justify-content:space-between}
.dl-stop-btn{font-family:var(--font-ui);font-weight:500;font-size:11px;letter-spacing:.06em;text-transform:uppercase;
  color:#a4392a;background:none;border:1px solid var(--border-1);border-radius:4px;padding:6px 14px;cursor:pointer}
.dl-stop-btn:hover{border-color:#a4392a}
/* results verdict */
.dl-verdict{border:1px solid var(--border-1);border-radius:10px;background:var(--bg-card);
  box-shadow:var(--shadow-card);padding:22px 24px;display:flex;align-items:center;gap:22px;flex-wrap:wrap}
.dl-verdict-score{font-family:var(--font-display);font-weight:300;font-size:52px;line-height:1;color:var(--fg-1)}
.dl-verdict-score small{font-size:22px;color:var(--fg-3)}
.dl-badge{display:inline-block;font-family:var(--font-ui);font-weight:600;font-size:11px;letter-spacing:.1em;
  text-transform:uppercase;padding:5px 12px;border-radius:20px}
.dl-badge-ok{background:var(--band-soft);color:var(--slp-sage-dark);border:1px solid var(--slp-sage-dark)}
.dl-badge-esc{background:#f6e9e6;color:#a4392a;border:1px solid #a4392a}
.dl-verdict-copy{flex:1 1 260px}
.dl-verdict-copy p{font-family:var(--font-body);font-size:15px;line-height:1.55;color:var(--fg-2);margin:8px 0 0}
.dl-ba-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:20px}
@media(max-width:640px){.dl-ba-grid{grid-template-columns:1fr}}
.dl-ba-col h4{font-family:var(--font-ui);font-weight:600;font-size:11px;letter-spacing:.1em;text-transform:uppercase;
  color:var(--fg-3);margin:0 0 8px;display:flex;align-items:center;gap:8px}
.dl-ba-col h4 .dl-ba-tag{font-weight:600}
.dl-ba-note{font-family:var(--font-ui);font-size:12.5px;color:#a4392a;margin:2px 0 10px}
/* Before/after thumbnails: render the whole page at 50% so the hero is
   visible, not just the top 300px sliver. Wrapper clips; iframe is 2x wide
   and scaled down. */
.dl-ba-shot{position:relative;width:100%;height:320px;border:1px solid var(--border-1);border-radius:8px;
  background:#fff;box-shadow:var(--shadow-card);overflow:hidden}
.dl-ba-frame{position:absolute;top:0;left:0;width:200%;height:640px;border:0;
  transform:scale(.5);transform-origin:top left;pointer-events:none}
.dl-result-links{display:flex;gap:18px;flex-wrap:wrap;align-items:center;margin-top:18px}
.dl-result-link{font-family:var(--font-ui);font-weight:600;font-size:13px;color:var(--fg-accent);
  text-decoration:underline;text-underline-offset:3px}
.dl-rerun-btn{font-family:var(--font-ui);font-weight:600;font-size:13px;color:#fff;background:var(--slp-amber);
  border:none;border-radius:5px;padding:9px 18px;cursor:pointer}
.dl-rerun-btn:hover{background:var(--slp-amber-dark)}
.dl-history-empty{font-family:var(--font-ui);font-size:13px;color:var(--fg-3);font-style:italic}
.dl-history-grid{display:grid;gap:14px;grid-template-columns:repeat(auto-fill,minmax(220px,1fr))}
.dl-history-card{background:var(--bg-card);border:1px solid var(--border-1);border-radius:6px;
  padding:14px 16px;display:flex;flex-direction:column;gap:6px;box-shadow:var(--shadow-card);
  text-decoration:none;color:inherit}
.dl-hist-clear{font-family:var(--font-ui);font-weight:500;font-size:11px;letter-spacing:.06em;text-transform:uppercase;
  color:#a4392a;background:none;border:1px solid var(--border-1);border-radius:4px;padding:5px 12px;cursor:pointer}
.dl-hist-clear:hover{border-color:#a4392a}
.dl-hist-kind{font-family:var(--font-ui);font-size:10px;letter-spacing:.06em;text-transform:uppercase;
  color:var(--fg-3);border:1px solid var(--border-1);border-radius:10px;padding:1px 8px}
.dl-hist-actions{display:flex;align-items:center;gap:10px;margin-top:8px;padding-top:8px;border-top:1px solid var(--border-1)}
.dl-hist-open{font-family:var(--font-ui);font-weight:600;font-size:12px;color:#fff;background:var(--slp-amber);
  border:none;border-radius:4px;padding:6px 14px;cursor:pointer}
.dl-hist-open:hover{background:var(--slp-amber-dark)}
.dl-hist-link{font-family:var(--font-ui);font-weight:600;font-size:12px;color:var(--fg-accent);
  text-decoration:underline;text-underline-offset:2px}
.dl-hist-del{margin-left:auto;font-family:var(--font-ui);font-size:13px;color:var(--fg-3);background:none;
  border:1px solid var(--border-1);border-radius:4px;padding:4px 9px;cursor:pointer;line-height:1}
.dl-hist-del:hover{color:#a4392a;border-color:#a4392a}
/* mode badge */
.dl-mode-badge{align-self:center;font-family:var(--font-ui);font-weight:600;font-size:10px;letter-spacing:.08em;
  text-transform:uppercase;padding:4px 10px;border-radius:12px;border:1px solid var(--border-1);color:var(--fg-3)}
.dl-mode-badge.dl-mode-dry{color:var(--slp-sage-dark);border-color:var(--slp-sage-dark);background:var(--band-soft)}
.dl-mode-badge.dl-mode-live{color:#fff;border-color:var(--slp-amber);background:var(--slp-amber)}
.dl-mode-badge.dl-mode-warn{color:#a4392a;border-color:#a4392a;background:#f6e9e6}
/* goal-context field on landing */
.dl-context-row{max-width:660px;margin:12px auto 0;display:flex;align-items:center;gap:10px}
.dl-context-row input{flex:1;font-family:var(--font-ui);font-size:13px;color:var(--fg-1);
  background:var(--bg-card);border:1px solid var(--border-1);border-radius:6px;padding:9px 12px}
.dl-context-row label{font-family:var(--font-ui);font-size:11px;letter-spacing:.06em;
  text-transform:uppercase;color:var(--fg-3);white-space:nowrap}
/* ship banner */
.dl-ship{display:flex;align-items:center;gap:20px;flex-wrap:wrap;border-radius:12px;padding:20px 24px;
  border:1px solid var(--border-1);box-shadow:var(--shadow-card)}
.dl-ship-ok{background:var(--band-soft)}
.dl-ship-esc{background:#f6e9e6}
.dl-ship-verdict{font-family:var(--font-display);font-weight:500;font-size:26px;line-height:1.05}
.dl-ship-ok .dl-ship-verdict{color:var(--slp-sage-dark)}
.dl-ship-esc .dl-ship-verdict{color:#a4392a}
.dl-ship-sub{font-family:var(--font-ui);font-size:12.5px;color:var(--fg-2);margin-top:4px}
.dl-ship-score{margin-left:auto;text-align:right;font-family:var(--font-display);font-weight:300;
  font-size:44px;line-height:1;color:var(--fg-1)}
.dl-ship-score small{font-size:18px;color:var(--fg-3)}
.dl-delta{display:inline-block;font-family:var(--font-ui);font-weight:600;font-size:12px;
  padding:2px 8px;border-radius:12px;margin-left:8px;vertical-align:middle}
.dl-delta-up{background:var(--band-soft);color:var(--slp-sage-dark)}
.dl-delta-down{background:#f6e9e6;color:#a4392a}
.dl-goal-chip{display:inline-block;font-family:var(--font-ui);font-size:11px;letter-spacing:.04em;
  color:var(--fg-3);border:1px solid var(--border-1);border-radius:12px;padding:3px 10px;margin-top:8px}
/* punch list */
.dl-sec-head{font-family:var(--font-ui);font-weight:600;font-size:12px;letter-spacing:.08em;
  text-transform:uppercase;color:var(--fg-accent);margin:26px 0 12px}
.dl-punch{display:flex;flex-direction:column;gap:12px}
.dl-punch-card{display:flex;gap:14px;border:1px solid var(--border-1);border-radius:10px;
  background:var(--bg-card);box-shadow:var(--shadow-card);padding:16px 18px}
.dl-punch-rank{font-family:var(--font-display);font-weight:300;font-size:30px;color:var(--fg-3);
  line-height:1;min-width:26px}
.dl-punch-body{flex:1}
.dl-punch-title{display:flex;align-items:center;gap:10px;margin-bottom:6px}
.dl-punch-title b{font-family:var(--font-ui);font-weight:600;font-size:14px;color:var(--fg-1)}
.dl-sev{font-family:var(--font-ui);font-weight:600;font-size:10px;letter-spacing:.08em;text-transform:uppercase;
  padding:2px 8px;border-radius:10px}
.dl-sev-critical{background:#f6e9e6;color:#a4392a}
.dl-sev-high{background:#faf0e2;color:#8a5a1f}
.dl-sev-medium{background:var(--band-soft);color:var(--slp-sage-dark)}
.dl-punch-issue{font-family:var(--font-body);font-size:14px;line-height:1.5;color:var(--fg-2);margin:0 0 6px}
.dl-punch-fix{font-family:var(--font-body);font-size:14px;line-height:1.5;color:var(--fg-1)}
.dl-punch-fix b{color:var(--fg-accent);font-weight:600}
/* deliverable actions */
.dl-actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:16px}
.dl-act-btn{font-family:var(--font-ui);font-weight:600;font-size:12.5px;cursor:pointer;
  border-radius:6px;padding:9px 14px;border:1px solid var(--border-1);background:var(--bg-card);color:var(--fg-1)}
.dl-act-btn:hover{border-color:var(--slp-amber)}
.dl-act-primary{background:var(--slp-amber);border-color:var(--slp-amber);color:#fff}
.dl-act-primary:hover{background:var(--slp-amber-dark)}
/* what changed + scorecard */
.dl-chip-row{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px}
.dl-chip{font-family:var(--font-ui);font-size:11.5px;padding:3px 10px;border-radius:12px}
.dl-chip-imp{background:var(--band-soft);color:var(--slp-sage-dark)}
.dl-chip-reg{background:#f6e9e6;color:#a4392a}
.dl-score-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px 22px;margin-top:6px}
@media(max-width:640px){.dl-score-grid{grid-template-columns:1fr}}
.dl-score-row{display:flex;align-items:center;gap:10px;font-family:var(--font-ui);font-size:12.5px}
.dl-score-name{width:96px;color:var(--fg-2)}
.dl-score-track{flex:1;height:6px;border-radius:3px;background:var(--border-1);position:relative;overflow:hidden}
.dl-score-a{position:absolute;left:0;top:0;height:100%;background:var(--fg-3);opacity:.5;border-radius:3px}
.dl-score-b{position:absolute;left:0;top:0;height:100%;background:var(--slp-amber);border-radius:3px}
.dl-score-num{width:52px;text-align:right;color:var(--fg-3)}
.dl-score-num b{color:var(--fg-1)}
/* steer */
.dl-steer{margin-top:22px;padding:16px 18px;border:1px dashed var(--border-1);border-radius:10px}
.dl-steer-label{font-family:var(--font-ui);font-size:12px;color:var(--fg-2);margin-bottom:10px}
.dl-focus-btn{font-family:var(--font-ui);font-weight:600;font-size:12.5px;cursor:pointer;margin:0 8px 8px 0;
  border-radius:20px;padding:7px 14px;border:1px solid var(--slp-amber);background:var(--bg-card);color:var(--fg-accent)}
.dl-focus-btn:hover{background:var(--band-soft)}
/* root cause + audience chip */
.dl-root{font-family:var(--font-body);font-size:13.5px;line-height:1.5;color:var(--fg-2);margin-top:10px}
.dl-root b{color:var(--fg-1);font-weight:600}
.dl-aud-chip{display:inline-block;font-family:var(--font-ui);font-size:11px;letter-spacing:.04em;
  color:var(--fg-3);border:1px solid var(--border-1);border-radius:12px;padding:3px 10px;margin:8px 0 0 6px}
.dl-goal-note{font-family:var(--font-ui);font-size:12px;color:var(--fg-accent);margin-top:8px;font-weight:600}
/* strengths */
.dl-strength-row{display:flex;gap:10px;flex-wrap:wrap}
.dl-strength{flex:1 1 220px;border:1px solid var(--border-1);border-left:3px solid var(--slp-sage-dark);
  border-radius:8px;background:var(--bg-card);padding:12px 14px}
.dl-strength b{font-family:var(--font-ui);font-weight:600;font-size:13px;color:var(--fg-1)}
.dl-strength span{font-family:var(--font-body);font-size:13px;color:var(--fg-2)}
/* impact/effort + do-this-first */
.dl-io{display:inline-flex;gap:6px;align-items:center;margin-left:2px}
.dl-io-tag{font-family:var(--font-ui);font-weight:600;font-size:10px;letter-spacing:.05em;text-transform:uppercase;
  padding:2px 7px;border-radius:10px;border:1px solid var(--border-1);color:var(--fg-3)}
.dl-punch-card.dl-first{border-color:var(--slp-amber);box-shadow:0 0 0 1px var(--slp-amber),var(--shadow-card)}
.dl-first-ribbon{display:inline-block;font-family:var(--font-ui);font-weight:700;font-size:10px;letter-spacing:.08em;
  text-transform:uppercase;color:#fff;background:var(--slp-amber);border-radius:10px;padding:2px 9px;margin-bottom:8px}
/* ground truth */
.dl-gt{display:grid;grid-template-columns:1fr 1fr;gap:8px 22px;margin-top:6px}
@media(max-width:640px){.dl-gt{grid-template-columns:1fr}}
.dl-gt-row{display:flex;align-items:flex-start;gap:10px;font-family:var(--font-ui);font-size:12.5px}
.dl-gt-dot{flex:none;width:9px;height:9px;border-radius:50%;margin-top:4px}
.dl-gt-pass{background:var(--slp-sage-dark)}
.dl-gt-warn{background:#c98a2b}
.dl-gt-fail{background:#a4392a}
.dl-gt-name{font-weight:600;color:var(--fg-1)}
.dl-gt-detail{color:var(--fg-3)}
.dl-gt-summary{font-family:var(--font-ui);font-size:12px;color:var(--fg-3);margin-bottom:8px}
.dl-gt-na{font-family:var(--font-body);font-size:13px;color:var(--fg-3);font-style:italic}
/* annotated page + benchmark */
.dl-annot-frame{width:100%;height:460px;border:1px solid var(--border-1);border-radius:8px;background:#fff;
  box-shadow:var(--shadow-card);display:block;margin-top:4px}
.dl-bm-summary{font-family:var(--font-ui);font-size:13px;color:var(--fg-1);font-weight:600;margin-bottom:10px}
.dl-bm-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px 22px;margin-bottom:8px}
@media(max-width:640px){.dl-bm-grid{grid-template-columns:1fr}}
.dl-bm-row{display:flex;align-items:center;gap:8px;font-family:var(--font-ui);font-size:12.5px}
.dl-bm-name{flex:1;color:var(--fg-2)}
.dl-bm-vs{font-size:10px;color:var(--fg-3);letter-spacing:.05em}
.dl-bm-head{display:flex;gap:8px;font-family:var(--font-ui);font-weight:600;font-size:10px;letter-spacing:.05em;
  text-transform:uppercase;color:var(--fg-3);justify-content:flex-end;margin-bottom:2px}
/* agent-log cards (real backend firehose, de-noised) */
.dl-agent-card{border:1px solid var(--border-1);border-left:3px solid var(--fg-3);border-radius:8px;
  background:var(--bg-card);margin:8px 0;padding:9px 12px}
.dl-agent-card.role-critic{border-left-color:var(--slp-amber)}
.dl-agent-card.role-planner{border-left-color:#a4392a}
.dl-agent-card.role-maker{border-left-color:var(--slp-sage-dark)}
.dl-agent-card.role-judge{border-left-color:var(--fg-accent)}
.dl-agent-head{display:flex;align-items:center;gap:8px;font-family:var(--font-ui);font-size:12px}
.dl-agent-dot{width:9px;height:9px;border-radius:50%;background:var(--fg-3);flex:none}
.role-critic .dl-agent-dot{background:var(--slp-amber)}
.role-planner .dl-agent-dot{background:#a4392a}
.role-maker .dl-agent-dot{background:var(--slp-sage-dark)}
.role-judge .dl-agent-dot{background:var(--fg-accent)}
.dl-agent-name{font-weight:600;color:var(--fg-1);text-transform:capitalize}
.dl-agent-cost{color:var(--fg-3);font-size:11px}
.dl-agent-think{margin-left:auto;color:var(--slp-amber);font-size:11px;letter-spacing:.04em;display:none}
.dl-card-active .dl-agent-think{display:inline}
.dl-agent-tools{display:flex;flex-direction:column;gap:2px;margin-top:5px}
.dl-tool-row{font-family:var(--font-ui);font-size:12.5px;color:var(--fg-2);display:flex;align-items:baseline;gap:7px}
.dl-tool-ico{flex:none}
.dl-tool-name{color:var(--fg-1);font-weight:600}
.dl-tool-arg{color:var(--fg-3);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.dl-tool-status{margin-left:auto;flex:none}
.dl-tool-row.fail .dl-tool-name{color:#a4392a}
.dl-agent-reason{margin-top:6px}
.dl-agent-reason summary{font-family:var(--font-ui);font-size:11px;color:var(--fg-3);cursor:pointer;
  letter-spacing:.05em;text-transform:uppercase}
.dl-agent-reason .dl-reason-body{font-family:var(--font-body);font-size:12.5px;color:var(--fg-3);line-height:1.5;
  margin-top:6px;max-height:200px;overflow:auto;white-space:pre-wrap}
/* milestone cards -- the CLEAN, ordered PRIMARY view (replaces the raw
   firehose, which now lives inside the collapsed "Show raw agent log"
   <details> below). One card per real pipeline phase: render, baseline,
   plan, make, score, decide. */
.dl-phase-indicator{font-family:var(--font-ui);font-size:12px;color:var(--fg-accent);font-weight:600;
  letter-spacing:.03em;margin:2px 0 12px}
.dl-milestones{display:flex;flex-direction:column;gap:10px;margin-bottom:14px}
.dl-ms-card{border:1px solid var(--border-1);border-left:3px solid var(--slp-amber);border-radius:8px;
  background:var(--bg-card);box-shadow:var(--shadow-card);padding:12px 16px;opacity:.55;transition:opacity .2s}
.dl-ms-card.ms-active{opacity:1;border-left-color:var(--slp-sage-dark)}
.dl-ms-card.ms-decide{border-left-color:var(--slp-sage-dark)}
.dl-ms-head{display:flex;align-items:center;gap:9px}
.dl-ms-ico{flex:none;font-size:14px;color:var(--fg-accent)}
.dl-ms-title{font-family:var(--font-ui);font-weight:600;font-size:13.5px;color:var(--fg-1)}
.dl-ms-detail{font-family:var(--font-body);font-size:12.5px;color:var(--fg-3);margin-top:4px;line-height:1.45}
.dl-ms-items{margin:8px 0 0;padding-left:18px;font-family:var(--font-body);font-size:12.5px;color:var(--fg-2)}
.dl-ms-items li{margin-bottom:3px}
.dl-ms-scores{display:grid;grid-template-columns:1fr 1fr;gap:4px 18px;margin-top:8px}
@media(max-width:640px){.dl-ms-scores{grid-template-columns:1fr}}
.dl-ms-score-row{display:flex;align-items:center;gap:8px;font-family:var(--font-ui);font-size:11.5px}
.dl-ms-score-name{width:88px;color:var(--fg-2)}
.dl-ms-score-track{flex:1;height:5px;border-radius:3px;background:var(--border-1);position:relative;overflow:hidden}
.dl-ms-score-b{position:absolute;left:0;top:0;height:100%;background:var(--slp-amber);border-radius:3px}
.dl-ms-score-num{width:56px;text-align:right;color:var(--fg-3)}
.dl-ms-score-num b{color:var(--fg-1)}
/* collapsible raw agent log (was the primary Working view; demoted here) */
.dl-rawlog-details{margin-top:6px}
.dl-rawlog-summary{font-family:var(--font-ui);font-weight:500;font-size:11px;letter-spacing:.08em;
  text-transform:uppercase;color:var(--fg-3);cursor:pointer;padding:6px 2px;user-select:none}
.dl-rawlog-summary:hover{color:var(--fg-accent)}
/* results top bar: non-destructive back-to-home + run identity (id + when) */
.dl-result-topbar{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin:0 0 20px}
.dl-back-btn{font-family:var(--font-ui);font-weight:600;font-size:12px;letter-spacing:.03em;color:var(--fg-accent);
  background:var(--bg-card);border:1px solid var(--border-1);border-radius:6px;padding:7px 14px;cursor:pointer}
.dl-back-btn:hover{border-color:var(--slp-amber)}
.dl-run-ident{font-family:var(--font-ui);font-size:11.5px;letter-spacing:.03em;color:var(--fg-3);
  display:inline-flex;align-items:center;gap:8px}
.dl-run-ident b{font-weight:600;color:var(--fg-2)}
.dl-run-dot{width:3px;height:3px;border-radius:50%;background:var(--fg-3);display:inline-block}
/* runs dashboard: search + status filters over the history grid */
.dl-dash-tools{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:16px}
.dl-dash-search{flex:1 1 200px;min-width:150px;font-family:var(--font-ui);font-size:13px;color:var(--fg-1);
  background:var(--bg-card);border:1px solid var(--border-1);border-radius:6px;padding:9px 12px;outline:none}
.dl-dash-search:focus{border-color:var(--slp-amber)}
.dl-dash-search::placeholder{color:var(--fg-3)}
.dl-dash-filters{display:inline-flex;gap:6px}
.dl-fchip{font-family:var(--font-ui);font-weight:600;font-size:11px;letter-spacing:.03em;color:var(--fg-3);
  background:var(--bg-card);border:1px solid var(--border-1);border-radius:20px;padding:6px 13px;cursor:pointer}
.dl-fchip:hover{border-color:var(--slp-amber)}
.dl-fchip-on{color:#fff;background:var(--slp-amber);border-color:var(--slp-amber)}
.dl-dash-count{font-family:var(--font-ui);font-size:11px;letter-spacing:.03em;color:var(--fg-3)}
.dl-hist-when{font-family:var(--font-ui);font-size:11px;color:var(--fg-3)}
/* collapsed "judged on eight things" explainer -- tucked, not a wall of tiles */
.dl-dims-disclosure{max-width:660px;margin:30px auto 0;border:1px solid var(--border-1);border-radius:8px;
  background:var(--bg-card);overflow:hidden}
.dl-dims-summary{font-family:var(--font-ui);font-weight:500;font-size:11px;letter-spacing:.18em;text-transform:uppercase;
  color:var(--fg-3);cursor:pointer;padding:13px 16px;user-select:none;list-style:none;display:flex;align-items:center;gap:9px}
.dl-dims-summary::-webkit-details-marker{display:none}
.dl-dims-summary::before{content:"\\25B8";color:var(--slp-amber);font-size:10px;transition:transform .15s;display:inline-block}
.dl-dims-disclosure[open] .dl-dims-summary::before{transform:rotate(90deg)}
.dl-dims-summary:hover{color:var(--fg-accent)}
.dl-dims-body{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:var(--border-1);border-top:1px solid var(--border-1)}
@media(max-width:640px){.dl-dims-body{grid-template-columns:1fr}}
"""


def _smart_input_section() -> str:
    """One smart input: a textarea for URL/HTML that is also a drop / paste /
    click target for a screenshot or .html file. Kind is auto-detected and
    shown in a live chip; a single Analyze button (or Enter / Cmd-Enter)
    starts the run."""
    return (
        '<div class="dl-smart" id="dl-smart" tabindex="-1">'
        '<textarea id="dl-input" class="dl-input" rows="3" '
        'placeholder="Paste a URL, paste raw HTML, or drop / paste / click to add a screenshot…">'
        "</textarea>"
        '<div class="dl-smart-foot">'
        '<span class="dl-detect" id="dl-detect"><span class="dl-detect-dot"></span>'
        '<span id="dl-detect-text">Detects URL, HTML or image</span></span>'
        '<button type="button" class="dl-browse" id="dl-browse">Browse…</button>'
        '<span class="dl-spacer"></span>'
        '<button type="button" class="dl-analyze-btn" id="dl-analyze" disabled>'
        "Analyze &rarr;</button>"
        "</div>"
        '<input id="dl-file-input" type="file" accept="image/*,.html,.htm" style="display:none" />'
        "</div>"
        '<div class="dl-hint">Enter to analyze a URL &middot; Cmd/Ctrl+Enter for HTML &middot; '
        "Cmd/Ctrl+V to paste a screenshot</div>"
        '<div class="dl-context-row">'
        '<label for="dl-brief">Goal / Brief</label>'
        '<input type="text" id="dl-brief" maxlength="300" '
        'placeholder="Optional: e.g. make a version for veterinary scientists" />'
        "</div>"
        '<div class="dl-context-row">'
        '<label for="dl-context">Goal</label>'
        '<input type="text" id="dl-context" maxlength="120" '
        'placeholder="Optional: what is this page for? e.g. B2B pricing page, app download" />'
        "</div>"
        '<div class="dl-context-row">'
        '<label for="dl-audience">Audience</label>'
        '<input type="text" id="dl-audience" maxlength="120" '
        'placeholder="Optional: who is it for? e.g. solo founders, enterprise buyers" />'
        "</div>"
        '<div class="dl-context-row">'
        '<label for="dl-compare">Compare</label>'
        '<input type="text" id="dl-compare" maxlength="300" '
        'placeholder="Optional: a competitor URL to benchmark ground-truth checks against" />'
        "</div>"
        '<div class="dl-preview" id="dl-preview"><img id="dl-preview-img" alt="Upload preview" /></div>'
        '<div class="dl-status" id="dl-status"></div>'
    )


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
    """The runs dashboard: a searchable, status-filterable list of past runs.
    Populated client-side from GET /api/history on load and refreshed after
    each run completes. Replaces the old flat 'Past verdicts' tile strip."""
    return (
        '<div style="max-width:660px;margin:44px auto 0">'
        '<div style="display:flex;align-items:baseline;justify-content:space-between;gap:10px;margin-bottom:16px">'
        '<span style="font-family:var(--font-display);font-weight:400;font-size:20px;color:var(--fg-1)">Your runs</span>'
        '<span id="dl-dash-count" class="dl-dash-count"></span>'
        "</div>"
        '<div class="dl-dash-tools">'
        '<input id="dl-dash-search" class="dl-dash-search" type="text" placeholder="Search by goal\u2026" autocomplete="off" />'
        '<div class="dl-dash-filters">'
        '<button type="button" class="dl-fchip dl-fchip-on" data-filter="all">All</button>'
        '<button type="button" class="dl-fchip" data-filter="converged">\u2713 Converged</button>'
        '<button type="button" class="dl-fchip" data-filter="escalated">\u26a0 Escalated</button>'
        "</div>"
        '<button type="button" id="dl-history-clear" class="dl-hist-clear">Clear</button>'
        "</div>"
        '<div id="dl-history-list" class="dl-history-empty" style="text-align:center">Loading&hellip;</div>'
        "</div>"
    )


def _journey_nav() -> str:
    """1/2/3 step strip plus an always-available 'Start over' reset control.

    Each step carries a status glyph (number -> check when complete) so the
    three tabs read as connected steps of one flow rather than three separate
    pages. Landing is never `disabled`, so it stays clickable at every stage.
    """
    def _step(name: str, num: str, label: str, active: bool, disabled: bool) -> str:
        cls = "pw-tab-active" if active else ""
        dis = " disabled" if disabled else ""
        return (
            f'<button type="button" data-pw-tab="{name}" class="{cls}"{dis}>'
            f'<span class="dl-step-ico">{num}</span><span>{label}</span></button>'
        )

    return (
        '<div class="pw-journey-nav">'
        + _step("landing", "1", "Landing", True, False)
        + _step("working", "2", "Working", False, True)
        + _step("results", "3", "Results", False, True)
        + '<span id="dl-mode-badge" class="dl-mode-badge" style="margin-left:auto" title=""></span>'
        + '<button type="button" id="dl-reset-btn" style="font-family:var(--font-ui);'
        "font-weight:500;font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--fg-3);"
        "background:none;border:1px solid var(--border-1);border-radius:4px;padding:6px 14px;margin-left:10px;"
        'cursor:pointer;align-self:center">&#8635; Start over</button>'
        "</div>"
    )


def _working_view() -> str:
    """Live transaction-log pane with a Pass N/N counter + determinate
    progress bar (driven by the streamed 'Pass N/M' maker lines) and a Stop
    control, above the streamed rows."""
    header = (
        '<div style="display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:12px">'
        '<div style="display:flex;align-items:center;gap:10px">'
        '<span style="display:block;width:26px;height:1px;background:var(--slp-amber)"></span>'
        '<span style="font-family:var(--font-ui);font-weight:500;font-size:11px;letter-spacing:.2em;'
        'text-transform:uppercase;color:var(--fg-3)">Working &middot; live transaction log</span>'
        "</div>"
        '<div style="display:flex;align-items:center;gap:12px">'
        '<div id="dl-run-status" style="display:flex;align-items:center;gap:8px">'
        '<span id="dl-run-spinner" style="display:inline-block;width:8px;height:8px;border-radius:50%;'
        'background:var(--slp-amber);animation:pw-pulse 1s ease-in-out infinite"></span>'
        '<span id="dl-run-status-text" style="font-family:var(--font-ui);font-weight:600;font-size:12px;'
        'letter-spacing:.04em;color:var(--fg-accent)">Running&hellip;</span>'
        "</div>"
        '<button type="button" id="dl-home-btn" class="dl-back-btn" '
        'title="Go home \u2014 your run keeps running; return via the Working tab">\u2190 Home</button>'
        '<button type="button" id="dl-stop-btn" class="dl-stop-btn">&#9632; Stop</button>'
        "</div>"
        "</div>"
    )
    progress = (
        '<div class="dl-progress-wrap">'
        '<div class="dl-progress-label"><span id="dl-progress-text">Starting&hellip;</span>'
        '<span id="dl-progress-pct"></span></div>'
        '<div class="dl-progress-track"><div class="dl-progress-bar" id="dl-progress-bar"></div></div>'
        "</div>"
    )
    # PRIMARY: current-phase indicator + ordered milestone cards, derived from
    # the recipe's own structured outputs (see real_runner._watch_milestones /
    # dry_runner.run_dry, which emit "milestone" stream events). The raw
    # per-line CLI transcript (source=agent/agent-stderr display events) still
    # arrives on the SAME socket, but is now demoted to a collapsed <details>
    # -- available on demand, no longer the primary view.
    phase_indicator = (
        '<div id="dl-phase-indicator" class="dl-phase-indicator">Starting&hellip;</div>'
    )
    milestones = '<div id="dl-milestones" class="dl-milestones"></div>'
    raw_log = (
        '<details id="dl-rawlog" class="dl-rawlog-details">'
        '<summary class="dl-rawlog-summary">Show raw agent log</summary>'
        '<div id="dl-log" style="background:var(--bg-card);border:1px solid var(--border-1);'
        'border-radius:6px;padding:14px 20px;box-shadow:var(--shadow-card);min-height:120px;'
        'margin-top:10px"></div>'
        "</details>"
    )
    return (
        '<div data-pw-view="working" hidden>'
        + header
        + progress
        + phase_indicator
        + milestones
        + raw_log
        + "</div>"
    )


def _script() -> str:
    """Vanilla JS: smart-input auto-detect + real DnD/click/paste upload +
    WS streaming client with progress + in-app concise Results (verdict +
    before/after) + stop/re-run + reset + history. No template literals or
    backticks (string concatenation only)."""
    lines = [
        "(function(){",
        "var STEPS=['landing','working','results'];",
        "var tabs=document.querySelectorAll('[data-pw-tab]');",
        "var views=document.querySelectorAll('[data-pw-view]');",
        "function setStepStates(name){",
        "  var idx=STEPS.indexOf(name);",
        "  tabs.forEach(function(tb){",
        "    var s=tb.getAttribute('data-pw-tab');var si=STEPS.indexOf(s);",
        "    tb.classList.toggle('pw-tab-active',s===name);",
        "    var ico=tb.querySelector('.dl-step-ico');",
        "    if(si<idx){tb.classList.add('dl-step-done');if(ico){ico.innerHTML='\\u2713';}}",
        "    else{tb.classList.remove('dl-step-done');if(ico){ico.textContent=String(si+1);}}",
        "  });",
        "}",
        "function showView(name){",
        "  views.forEach(function(v){v.hidden=v.getAttribute('data-pw-view')!==name;});",
        "  setStepStates(name);",
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
        "var smart=document.getElementById('dl-smart');",
        "var inputEl=document.getElementById('dl-input');",
        "var fileInput=document.getElementById('dl-file-input');",
        "var browseBtn=document.getElementById('dl-browse');",
        "var analyzeBtn=document.getElementById('dl-analyze');",
        "var detectEl=document.getElementById('dl-detect');",
        "var detectText=document.getElementById('dl-detect-text');",
        "var preview=document.getElementById('dl-preview');",
        "var previewImg=document.getElementById('dl-preview-img');",
        "var statusEl=document.getElementById('dl-status');",
        "var logEl=document.getElementById('dl-log');",
        "var milestonesEl=document.getElementById('dl-milestones');",
        "var phaseIndicatorEl=document.getElementById('dl-phase-indicator');",
        "var workingTab=document.querySelector('[data-pw-tab=\"working\"]');",
        "var resultsTab=document.querySelector('[data-pw-tab=\"results\"]');",
        "var resultsView=document.querySelector('[data-pw-view=\"results\"]');",
        "var runStatusText=document.getElementById('dl-run-status-text');",
        "var runSpinner=document.getElementById('dl-run-spinner');",
        "var stopBtn=document.getElementById('dl-stop-btn');",
        "var resetBtn=document.getElementById('dl-reset-btn');",
        "var progBar=document.getElementById('dl-progress-bar');",
        "var progText=document.getElementById('dl-progress-text');",
        "var progPct=document.getElementById('dl-progress-pct');",
        "var goalEl=document.getElementById('dl-brief');",
        "var contextEl=document.getElementById('dl-context');",
        "var audienceEl=document.getElementById('dl-audience');",
        "var compareEl=document.getElementById('dl-compare');",
        "var currentSocket=null;",
        "var currentRunId=null;",
        "var pendingImage=null;",
        "var lastResult=null;",
        "var currentOpts={};",
        "var prevTotal=null;",
        "",
        "function setStatus(msg,isError){",
        "  statusEl.textContent=msg||'';",
        "  statusEl.className='dl-status'+(isError?' dl-error':'');",
        "}",
        "",
        "function setRunStatus(state,label){",
        "  if(state==='running'){",
        "    runStatusText.textContent='Running\\u2026';",
        "    runStatusText.style.color='var(--fg-accent)';",
        "    runSpinner.style.display='inline-block';",
        "    if(stopBtn){stopBtn.style.display='inline-block';}",
        "  } else if(state==='done'){",
        "    runStatusText.textContent=label||'\\u2713 Done';",
        "    runStatusText.style.color='var(--slp-sage-dark)';",
        "    runSpinner.style.display='none';",
        "    if(stopBtn){stopBtn.style.display='none';}",
        "  } else {",
        "    runStatusText.textContent=label||'Error';",
        "    runStatusText.style.color='#a4392a';",
        "    runSpinner.style.display='none';",
        "    if(stopBtn){stopBtn.style.display='none';}",
        "  }",
        "}",
        "",
        "function setProgress(cur,total,label){",
        "  var pct=total?Math.round((cur/total)*100):0;",
        "  progBar.style.width=pct+'%';",
        "  if(label){progText.textContent=label;}",
        "  progPct.textContent=total?('Pass '+cur+' / '+total):'';",
        "}",
        "",
        "function detectKind(text){",
        "  var tt=(text||'').trim();",
        "  if(!tt){return '';}",
        "  if(/^https?:\\/\\//i.test(tt)){return 'url';}",
        "  if(!/\\s/.test(tt)&&tt.indexOf('<')===-1&&/^[\\w-]+(\\.[\\w-]+)+(\\/[^\\s]*)?$/.test(tt)){return 'url';}",
        "  if(/<[a-z!\\/][\\s\\S]*>/i.test(tt)){return 'html';}",
        "  return (tt.indexOf('<')!==-1)?'html':'url';",
        "}",
        "",
        "var KIND_LABEL={url:'URL',html:'HTML',image:'Image'};",
        "function refreshDetect(){",
        "  var kind;",
        "  if(pendingImage){kind='image';}",
        "  else{kind=detectKind(inputEl.value);}",
        "  if(kind){",
        "    detectEl.classList.add('dl-on');",
        "    detectText.innerHTML='Will analyze as <b>'+KIND_LABEL[kind]+'</b>';",
        "    analyzeBtn.disabled=false;",
        "  } else {",
        "    detectEl.classList.remove('dl-on');",
        "    detectText.textContent='Detects URL, HTML or image';",
        "    analyzeBtn.disabled=true;",
        "  }",
        "  return kind;",
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
        "// ---- agent-log de-noiser: fold the real backend's console firehose",
        "// (source 'agent'/'agent-stderr' display lines: thinking blocks, token",
        "// boxes, tree-drawn tool dumps, giant JSON) into clean per-agent cards.",
        "var curCard=null,curName=null,lastTool=null,reasonMode=false,skipDump=false;",
        "function clearAgentState(){curCard=null;curName=null;lastTool=null;reasonMode=false;skipDump=false;}",
        "function stripTree(s){return s.replace(/^[\\s\\u2502\\u250c\\u2514\\u251c\\u2500|]+/,'').trim();}",
        "function isRule(s){return s===''||/^[=_\\-\\u2500\\u2550\\s]+$/.test(s);}",
        "function baseName(p){p=(p||'').replace(/\\/+$/,'');var i=p.lastIndexOf('/');return i>=0?p.slice(i+1):p;}",
        "function agentTag(msg){var m=msg.match(/\\[(design-loop-design-\\w+|foundation:[\\w.-]+)\\]/);return m?m[1]:null;}",
        "function shortAgent(tag){var m=tag.match(/design-(\\w+)$/);if(m){return m[1];}var i=tag.indexOf(':');return i>=0?tag.slice(i+1):tag;}",
        "function roleClass(short){var r=['critic','planner','maker','judge'];return r.indexOf(short)>=0?('role-'+short):'role-other';}",
        "function ensureCard(short){",
        "  if(curCard&&curName===short){return curCard;}",
        "  if(curCard){curCard.classList.remove('dl-card-active');}",
        "  var card=document.createElement('div');card.className='dl-agent-card '+roleClass(short)+' dl-card-active';",
        "  card._cost=0;card._calls=0;",
        "  var head=document.createElement('div');head.className='dl-agent-head';",
        "  head.innerHTML='<span class=\"dl-agent-dot\"></span><span class=\"dl-agent-name\">'+escHtml(short)+'</span>'+",
        "    '<span class=\"dl-agent-cost\"></span><span class=\"dl-agent-think\">\\u2026 thinking</span>';",
        "  var tools=document.createElement('div');tools.className='dl-agent-tools';",
        "  card.appendChild(head);card.appendChild(tools);",
        "  card._head=head;card._tools=tools;card._costEl=head.querySelector('.dl-agent-cost');",
        "  card._thinkEl=head.querySelector('.dl-agent-think');card._reason=null;",
        "  logEl.appendChild(card);logEl.scrollTop=logEl.scrollHeight;",
        "  curCard=card;curName=short;lastTool=null;reasonMode=false;skipDump=false;",
        "  return card;",
        "}",
        "function setThink(card,on){if(card&&card._thinkEl){card._thinkEl.style.display=on?'inline':'none';}}",
        "function addCost(card,amt){if(!card){return;}card._cost+=amt;card._costEl.textContent='$'+card._cost.toFixed(2)+' \\u00b7 '+card._calls+' calls';}",
        "function addTool(card,name){",
        "  card._calls++;var row=document.createElement('div');row.className='dl-tool-row';row.setAttribute('data-tool',name);",
        "  row.innerHTML='<span class=\"dl-tool-ico\">\\u1f527</span><span class=\"dl-tool-name\">'+escHtml(name)+'</span>'+",
        "    '<span class=\"dl-tool-arg\"></span><span class=\"dl-tool-status\">\\u00b7\\u00b7\\u00b7</span>';",
        "  row.querySelector('.dl-tool-ico').textContent='\\ud83d\\udd27';",
        "  card._tools.appendChild(row);addCost(card,0);logEl.scrollTop=logEl.scrollHeight;return row;",
        "}",
        "function findTool(card,name){var rows=card._tools.querySelectorAll('[data-tool=\"'+name+'\"]');return rows.length?rows[rows.length-1]:lastTool;}",
        "function setToolArg(row,arg){if(row&&!row._arg){row._arg=1;row.querySelector('.dl-tool-arg').textContent=arg;}}",
        "function setToolResult(row,ok,extra){if(!row){return;}row.classList.toggle('fail',!ok);",
        "  var s=row.querySelector('.dl-tool-status');s.textContent=(ok?'\\u2705':'\\u274c')+(extra?(' '+extra):'');}",
        "function addReason(card,text){if(!card){return;}",
        "  if(!card._reason){var d=document.createElement('details');d.className='dl-agent-reason';",
        "    d.innerHTML='<summary>reasoning</summary><div class=\"dl-reason-body\"></div>';",
        "    card.appendChild(d);card._reason=d.querySelector('.dl-reason-body');}",
        "  card._reason.textContent+=(card._reason.textContent?' ':'')+text;}",
        "function agentLine(src,msg){",
        "  var tag=agentTag(msg);if(tag){ensureCard(shortAgent(tag));}",
        "  var card=curCard;var core=stripTree(msg);",
        "  if(/Thinking(\\.\\.\\.|:)?\\s*$/.test(core)){if(card){setThink(card,true);}reasonMode=true;skipDump=false;return;}",
        "  if(isRule(core)){if(reasonMode){reasonMode=false;}return;}",
        "  if(/Token Usage/.test(core)){return;}",
        "  var cm=core.match(/Cost:\\s*\\$([0-9.]+)/);if(cm){addCost(card,parseFloat(cm[1]));reasonMode=false;return;}",
        "  var um=core.match(/Using tool:\\s*([A-Za-z0-9_]+)/);",
        "  if(um){if(card){setThink(card,false);lastTool=addTool(card,um[1]);}reasonMode=false;skipDump=false;return;}",
        "  var rm=msg.match(/(\\u2705|\\u274c)\\s*\\[[^\\]]*\\]\\s*Tool result:\\s*([A-Za-z0-9_]+)/);",
        "  if(rm){var ok=rm[1]==='\\u2705';if(card){setToolResult(findTool(card,rm[2]),ok,'');}skipDump=false;return;}",
        "  var am=core.match(/^(file_path|source|url|path|command|skill_name):\\s*(.+)$/);",
        "  if(am&&lastTool){setToolArg(lastTool,am[1]==='command'?String(am[2]).slice(0,40):baseName(am[2]));return;}",
        "  if(/^(content|improved_html|body):/.test(core)){skipDump=true;return;}",
        "  var bm=core.match(/^bytes:\\s*(\\d+)/);if(bm&&lastTool){setToolResult(lastTool,true,'('+bm[1]+' bytes)');return;}",
        "  if(/^(screenshot_path|target_html_path|target_screenshot_path|file_path|lines_read|offset|total_lines):/.test(core)){return;}",
        "  if(/Cannot read file|No such file|timed out|UnicodeDecodeError|\\[stderr\\]/.test(core)){if(lastTool){setToolResult(lastTool,false,'failed');}else{addReason(card,'\\u26a0 '+core.slice(0,120));}return;}",
        "  if(skipDump){return;}",
        "  if(/^[\\{\\[\\\"]/.test(core)||core.indexOf('\"scores\"')>=0||core.slice(0,3)==='...'){return;}",
        "  if(reasonMode||card){addReason(card,core);return;}",
        "}",
        "// ---- milestone cards: the CLEAN, ordered PRIMARY view -----------------",
        "// One card per real pipeline phase (render/baseline/plan/make/score/",
        "// decide), built from the structured `milestone` stream event -- see",
        "// real_runner._watch_milestones / dry_runner.run_dry (producers) and",
        "// protocols.WebStreamingHook.milestone() (wire shape).",
        "var MS_LABELS={clarity:'Clarity',elegance:'Elegance',restraint:'Restraint',empowerment:'Empowerment',",
        "  agency:'Agency',ease:'Ease',character:'Character',point:'Point'};",
        "var MS_ORDER=['clarity','elegance','restraint','empowerment','agency','ease','character','point'];",
        "var MS_ICON={render:'\u25A1',baseline:'\u25CF',plan:'\u2699',make:'\u2692',score:'\u2605',decide:'\u2713'};",
        "var MS_PHASE_LABEL={render:'Rendering your input',baseline:'Scoring the baseline',",
        "  plan:'Planning the next fix',make:'Building the candidate',score:'Re-scoring the candidate',",
        "  decide:'Wrapping up'};",
        "var msSeen={};",
        "function msScoreRowsHtml(scores,prevScores){",
        "  if(!scores){return '';}",
        "  var html='<div class=\"dl-ms-scores\">';",
        "  for(var i=0;i<MS_ORDER.length;i++){",
        "    var dim=MS_ORDER[i];var b=scores[dim];",
        "    if(b===undefined||b===null){continue;}",
        "    var a=(prevScores&&prevScores[dim]!==undefined&&prevScores[dim]!==null)?prevScores[dim]:null;",
        "    html+='<div class=\"dl-ms-score-row\"><span class=\"dl-ms-score-name\">'+MS_LABELS[dim]+'</span>';",
        "    html+='<span class=\"dl-ms-score-track\"><span class=\"dl-ms-score-b\" style=\"width:'+(b/4*100)+'%\"></span></span>';",
        "    html+='<span class=\"dl-ms-score-num\">'+(a!==null?(a+' \u2192 '):'')+'<b>'+b+'</b></span></div>';",
        "  }",
        "  return html+'</div>';",
        "}",
        "function msItemsHtml(items){",
        "  if(!items||!items.length){return '';}",
        "  var html='<ul class=\"dl-ms-items\">';",
        "  for(var i=0;i<items.length;i++){html+='<li>'+escHtml(items[i])+'</li>';}",
        "  return html+'</ul>';",
        "}",
        "function setPhaseIndicator(phase,isFinal){",
        "  if(!phaseIndicatorEl){return;}",
        "  phaseIndicatorEl.textContent=isFinal?'Finished':('Currently: '+(MS_PHASE_LABEL[phase]||phase));",
        "}",
        "function renderMilestone(data){",
        "  data=data||{};var phase=data.phase||'';",
        "  if(!phase||msSeen[phase]){return;}",
        "  msSeen[phase]=true;",
        "  if(milestonesEl){",
        "    var prevActive=milestonesEl.querySelector('.dl-ms-card.ms-active');",
        "    if(prevActive){prevActive.classList.remove('ms-active');}",
        "    var card=document.createElement('div');",
        "    card.className='dl-ms-card ms-'+phase+' ms-active';",
        "    var html='<div class=\"dl-ms-head\"><span class=\"dl-ms-ico\">'+(MS_ICON[phase]||'\u2022')+'</span>';",
        "    html+='<span class=\"dl-ms-title\">'+escHtml(data.title||phase)+'</span></div>';",
        "    if(data.detail){html+='<div class=\"dl-ms-detail\">'+escHtml(data.detail)+'</div>';}",
        "    html+=msItemsHtml(data.items);",
        "    html+=msScoreRowsHtml(data.scores,data.prev_scores);",
        "    card.innerHTML=html;",
        "    milestonesEl.appendChild(card);",
        "    milestonesEl.scrollTop=milestonesEl.scrollHeight;",
        "  }",
        "  setPhaseIndicator(phase,phase==='decide');",
        "}",
        "function resetMilestones(){",
        "  msSeen={};if(milestonesEl){milestonesEl.innerHTML='';}",
        "  if(phaseIndicatorEl){phaseIndicatorEl.textContent='Starting\\u2026';}",
        "}",
        "",
        "function handleStreamEvent(evtType,data){",
        "  data=data||{};",
        "  if(evtType==='milestone'){renderMilestone(data);return;}",
        "  if(evtType==='display'){",
        "    var source=(data.metadata&&data.metadata.source)||'loop';",
        "    var message=data.message||'';",
        "    var m=message.match(/Pass\\s+(\\d+)\\s*\\/\\s*(\\d+)/);",
        "    if(m){setProgress(parseInt(m[1],10),parseInt(m[2],10),'Pass '+m[1]+' of '+m[2]);}",
        "    if(source==='agent'||source==='agent-stderr'||source==='stderr'){agentLine(source,message);return;}",
        "    var core=stripTree(message);if(isRule(core)){return;}",
        "    if(curCard){curCard.classList.remove('dl-card-active');setThink(curCard,false);}clearAgentState();",
        "    appendLogRow(source.toUpperCase(),' '+message,true);",
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
        "window.__dlFeed=function(arr){arr.forEach(function(e){handleStreamEvent(e.event_type,e.data);});};",
        "",
        "function fallbackCopy(text){",
        "  var ta=document.createElement('textarea');ta.value=text;ta.style.position='fixed';ta.style.left='-9999px';",
        "  document.body.appendChild(ta);ta.select();try{document.execCommand('copy');}catch(e){}document.body.removeChild(ta);",
        "}",
        "function copyText(text,btn){",
        "  function done(){if(btn){var o=btn.getAttribute('data-label')||btn.textContent;btn.setAttribute('data-label',o);",
        "    btn.textContent='Copied \\u2713';setTimeout(function(){btn.textContent=o;},1400);}}",
        "  if(navigator.clipboard&&navigator.clipboard.writeText){",
        "    navigator.clipboard.writeText(text).then(done,function(){fallbackCopy(text);done();});",
        "  } else {fallbackCopy(text);done();}",
        "}",
        "function buildPrompt(payload,context){",
        "  var probs=(payload&&payload.problems)||[];",
        "  var out='You are a senior product designer improving a landing page.';",
        "  if(context){out+=' The page\\u2019s goal: '+context+'.';}",
        "  out+='\\n\\nApply these fixes, in priority order:\\n';",
        "  for(var i=0;i<probs.length;i++){",
        "    out+='\\n'+(i+1)+'. ['+probs[i].label+'] '+probs[i].issue+'\\n   Fix: '+probs[i].fix+'\\n';",
        "  }",
        "  out+='\\nKeep the copy honest and specific; do not add generic filler.';",
        "  return out;",
        "}",
        "window.__dlBuildPrompt=buildPrompt;",
        "function downloadUrl(url,name){",
        "  var a=document.createElement('a');a.href=url;a.download=name||'upgraded.html';",
        "  document.body.appendChild(a);a.click();document.body.removeChild(a);",
        "}",
        "function sevLabel(s){return s==='critical'?'Critical':(s==='high'?'High':'Medium');}",
        "function fmtWhen(iso){",
        "  if(!iso){return '';}",
        "  var d=new Date(iso);",
        "  if(isNaN(d.getTime())){return String(iso).slice(0,16).replace('T',' ');}",
        "  try{return d.toLocaleString(undefined,{month:'short',day:'numeric',year:'numeric',hour:'numeric',minute:'2-digit'});}",
        "  catch(e){return d.toISOString().slice(0,16).replace('T',' ');}",
        "}",
        "var histEntries=[],histById={},histFilter='all',histQuery='';",
        "",
        "function renderResults(msg){",
        "  var p=msg.payload||{};",
        "  var converged=!!msg.converged;",
        "  var total=(p.total===null||p.total===undefined)?msg.total:p.total;",
        "  var totalStr=(total===null||total===undefined)?'?':escHtml(total);",
        "  var bar=p.bar||26;",
        "  var ship=!!p.ship;",
        "  var shipCls=ship?'dl-ship-ok':'dl-ship-esc';",
        "  var shipVerdict=p.ship_label||(ship?'Ready to ship':'Not ready yet');",
        "  var shipSub;",
        "  if(p.blockers){shipSub='Ground-truth checks found '+p.blockers+' blocking issue'+(p.blockers!=1?'s':'')+' on your real page \\u2014 these gate shipping regardless of the '+bar+'/32 score. Fix them first.';}",
        "  else if(ship){shipSub='Cleared the bar of '+bar+'/32. Apply the punch list below to push it further, or ship as-is.';}",
        "  else {shipSub='Best-effort upgrade below the bar of '+bar+'/32'+(p.reason_text?(' ('+escHtml(p.reason_text)+')'):'')+'. Start with the punch list \\u2014 these are the highest-impact fixes.';}",
        "  var delta='';",
        "  if(prevTotal!==null&&total!==null&&total!==undefined){",
        "    var d=total-prevTotal;",
        "    if(d!==0){delta='<span class=\"dl-delta '+(d>0?'dl-delta-up':'dl-delta-down')+'\">'+(d>0?'+':'')+d+' vs last</span>';}",
        "  }",
        "  var goalChip=p.context?('<span class=\"dl-goal-chip\">Goal: '+escHtml(p.context)+'</span>'):'';",
        "  var audChip=p.audience?('<span class=\"dl-aud-chip\">Audience: '+escHtml(p.audience)+'</span>'):'';",
        "  var goalNote=p.goal_note?('<div class=\"dl-goal-note\">'+escHtml(p.goal_note)+'</div>'):'';",
        "  var rootCause=p.root_cause?('<div class=\"dl-root\"><b>Root cause \\u2014</b> '+escHtml(p.root_cause)+'.</div>'):'';",
        "  var html='';",
        "  var runId=msg.run_id||currentRunId||'';",
        "  var ts=msg.ts||(histById[runId]||{}).ts||(new Date()).toISOString();",
        "  var whenStr=fmtWhen(ts);",
        "  html+='<div class=\"dl-result-topbar\">';",
        "  html+='<button type=\"button\" class=\"dl-back-btn\" id=\"dl-back-home\">\\u2190 All runs</button>';",
        "  html+='<span class=\"dl-run-ident\">'+(runId?('<b>Run '+escHtml(String(runId).slice(0,8))+'</b>'):'')+(whenStr?('<span class=\"dl-run-dot\"></span>'+escHtml(whenStr)):'')+'</span>';",
        "  html+='</div>';",
        "  html+='<div style=\"display:flex;align-items:center;gap:10px;margin-bottom:14px\">';",
        "  html+='<span style=\"display:block;width:26px;height:1px;background:var(--slp-amber)\"></span>';",
        "  html+='<span style=\"font-family:var(--font-ui);font-weight:500;font-size:11px;letter-spacing:.2em;';",
        "  html+='text-transform:uppercase;color:var(--fg-3)\">Verdict</span></div>';",
        "  html+='<div class=\"dl-ship '+shipCls+'\">';",
        "  html+='<div><div class=\"dl-ship-verdict\">'+shipVerdict+delta+'</div><div class=\"dl-ship-sub\">'+shipSub+'</div>'+goalNote+'<div>'+goalChip+audChip+'</div></div>';",
        "  html+='<div class=\"dl-ship-score\">'+totalStr+'<small>/32</small></div>';",
        "  html+='</div>';",
        "  html+=rootCause;",
        "  // what's working",
        "  var strs=p.strengths||[];",
        "  if(strs.length){",
        "    html+='<div class=\"dl-sec-head\">What\\u2019s working</div><div class=\"dl-strength-row\">';",
        "    for(var st=0;st<strs.length;st++){",
        "      html+='<div class=\"dl-strength\"><b>'+escHtml(strs[st].label)+'</b> <span>\\u00b7 '+escHtml(strs[st].note)+' ('+strs[st].a+'/4)</span></div>';",
        "    }",
        "    html+='</div>';",
        "  } else if(p.strengths_note){",
        "    html+='<div class=\"dl-sec-head\">What\\u2019s working</div><div class=\"dl-root\">'+escHtml(p.strengths_note)+'</div>';",
        "  }",
        "  // punch list",
        "  var probs=p.problems||[];",
        "  if(probs.length){",
        "    html+='<div class=\"dl-sec-head\">Fix these first \\u00b7 ranked by impact \\u00d7 effort</div><div class=\"dl-punch\">';",
        "    for(var i=0;i<probs.length;i++){var pr=probs[i];",
        "      html+='<div class=\"dl-punch-card'+(pr.first?' dl-first':'')+'\"><div class=\"dl-punch-rank\">'+(i+1)+'</div><div class=\"dl-punch-body\">';",
        "      if(pr.first){html+='<div class=\"dl-first-ribbon\">Do this first</div>';}",
        "      html+='<div class=\"dl-punch-title\"><b>'+escHtml(pr.label)+'</b>';",
        "      html+='<span class=\"dl-sev dl-sev-'+pr.severity+'\">'+sevLabel(pr.severity)+'</span>';",
        "      html+='<span class=\"dl-io\"><span class=\"dl-io-tag\">'+escHtml(pr.impact)+' impact</span><span class=\"dl-io-tag\">'+escHtml(pr.effort)+' effort</span></span></div>';",
        "      html+='<p class=\"dl-punch-issue\">'+escHtml(pr.issue)+'</p>';",
        "      html+='<div class=\"dl-punch-fix\"><b>Fix \\u2192</b> '+escHtml(pr.fix)+'</div>';",
        "      html+='</div></div>';",
        "    }",
        "    html+='</div>';",
        "  }",
        "  // deliverable actions",
        "  html+='<div class=\"dl-actions\">';",
        "  html+='<button type=\"button\" class=\"dl-act-btn dl-act-primary\" id=\"dl-copy-prompt\">Copy fixes as prompt</button>';",
        "  html+='<button type=\"button\" class=\"dl-act-btn\" id=\"dl-copy-html\">Copy improved HTML</button>';",
        "  html+='<button type=\"button\" class=\"dl-act-btn\" id=\"dl-dl-html\">Download HTML</button>';",
        "  html+='<button type=\"button\" class=\"dl-act-btn\" id=\"dl-copy-link\">Copy share link</button>';",
        "  html+='<a class=\"dl-result-link\" style=\"align-self:center\" href=\"'+escHtml(msg.report_url||'')+'\" target=\"_blank\" rel=\"noopener\">Open full report \\u2197</a>';",
        "  html+='</div>';",
        "  // accessibility & ground truth",
        "  var gt=p.ground_truth||{};",
        "  html+='<div class=\"dl-sec-head\">Accessibility &amp; ground truth</div>';",
        "  if(gt.available&&gt.findings&&gt.findings.length){",
        "    var sm=gt.summary||{};",
        "    html+='<div class=\"dl-gt-summary\">Checked on your real markup \\u2014 '+(sm.pass||0)+' pass, '+(sm.warn||0)+' warn, '+(sm.fail||0)+' fail'+(gt.note?(' \\u00b7 '+escHtml(gt.note)):'')+'</div>';",
        "    html+='<div class=\"dl-gt\">';",
        "    for(var g=0;g<gt.findings.length;g++){var fnd=gt.findings[g];",
        "      html+='<div class=\"dl-gt-row\"><span class=\"dl-gt-dot dl-gt-'+fnd.status+'\"></span>';",
        "      html+='<span><span class=\"dl-gt-name\">'+escHtml(fnd.label)+'</span> \\u2014 <span class=\"dl-gt-detail\">'+escHtml(fnd.detail)+'</span></span></div>';",
        "    }",
        "    html+='</div>';",
        "  } else {",
        "    html+='<div class=\"dl-gt-na\">'+escHtml(gt.note||'Paste HTML or a URL to get a real accessibility audit of your page.')+'</div>';",
        "  }",
        "  // benchmark vs competitor URL",
        "  var bm=p.benchmark;",
        "  if(bm&&bm.available){",
        "    var you=bm.you||{},them=bm.them||{};",
        "    html+='<div class=\"dl-sec-head\">Benchmark vs '+escHtml(bm.url)+'</div>';",
        "    html+='<div class=\"dl-bm-summary\">You: '+(you.pass||0)+' pass / '+(you.warn||0)+' warn / '+(you.fail||0)+' fail &nbsp;\\u00b7&nbsp; Them: '+(them.pass||0)+' pass / '+(them.warn||0)+' warn / '+(them.fail||0)+' fail</div>';",
        "    var tm={};(bm.them_findings||[]).forEach(function(f){tm[f.label]=f;});",
        "    html+='<div class=\"dl-bm-head\"><span>You</span><span>Them</span></div><div class=\"dl-bm-grid\">';",
        "    (bm.you_findings||[]).forEach(function(f){var tf=tm[f.label];if(!tf){return;}",
        "      html+='<div class=\"dl-bm-row\"><span class=\"dl-bm-name\">'+escHtml(f.label)+'</span>';",
        "      html+='<span class=\"dl-gt-dot dl-gt-'+f.status+'\"></span><span class=\"dl-bm-vs\">vs</span><span class=\"dl-gt-dot dl-gt-'+tf.status+'\"></span></div>';",
        "    });",
        "    html+='</div><div class=\"dl-gt-summary\">'+escHtml(bm.note||'')+'</div>';",
        "  }",
        "  // your page, annotated",
        "  if(p.has_annotated&&msg.annotated_url){",
        "    html+='<div class=\"dl-sec-head\">Your page, annotated</div>';",
        "    html+='<div class=\"dl-gt-summary\">Redline markers on your actual markup \\u2014 numbered issues with a legend, bottom-right.</div>';",
        "    html+='<iframe class=\"dl-annot-frame\" src=\"'+escHtml(msg.annotated_url)+'\" title=\"Annotated page\"></iframe>';",
        "  }",
        "  // what changed",
        "  var imp=(p.improved||[]),reg=(p.regressed||[]);",
        "  if(imp.length||reg.length){",
        "    html+='<div class=\"dl-sec-head\">What changed</div><div class=\"dl-chip-row\">';",
        "    for(var a=0;a<imp.length;a++){html+='<span class=\"dl-chip dl-chip-imp\">\\u2191 '+escHtml(imp[a])+'</span>';}",
        "    for(var r=0;r<reg.length;r++){html+='<span class=\"dl-chip dl-chip-reg\">\\u2193 '+escHtml(reg[r])+'</span>';}",
        "    html+='</div>';",
        "  }",
        "  // before / after",
        "  // Before/after only makes sense when a DISTINCT upgraded candidate exists.",
        "  // When a run escalates before producing one (common on real runs), show the",
        "  // baseline screenshot solo with an honest note instead of a blank 'After' pane.",
        "  var _hasAfter=!!(msg.upgraded_url&&msg.upgraded_url!==msg.baseline_url);",
        "  if(_hasAfter){",
        "    html+='<div class=\"dl-sec-head\">Before &amp; after</div><div class=\"dl-ba-grid\">';",
        "    html+='<div class=\"dl-ba-col\"><h4><span class=\"dl-ba-tag\">Before</span> \\u00b7 baseline</h4>';",
        "    html+='<div class=\"dl-ba-shot\"><iframe class=\"dl-ba-frame\" scrolling=\"no\" src=\"'+escHtml(msg.baseline_url||'')+'\" title=\"Baseline\" loading=\"lazy\"></iframe></div></div>';",
        "    html+='<div class=\"dl-ba-col\"><h4><span class=\"dl-ba-tag\" style=\"color:var(--slp-sage-dark)\">After</span> \\u00b7 upgraded</h4>';",
        "    html+='<div class=\"dl-ba-shot\"><iframe class=\"dl-ba-frame\" scrolling=\"no\" src=\"'+escHtml(msg.upgraded_url||'')+'\" title=\"Upgraded\" loading=\"lazy\"></iframe></div></div>';",
        "    html+='</div>';",
        "  } else if(msg.baseline_url){",
        "    html+='<div class=\"dl-sec-head\">Your screenshot</div>';",
        "    html+='<div class=\"dl-ba-note\">No improved version was produced \\u2014 the loop escalated before it converged. Use the punch list above, then re-run.</div>';",
        "    html+='<div class=\"dl-ba-shot\"><iframe class=\"dl-ba-frame\" scrolling=\"no\" src=\"'+escHtml(msg.baseline_url)+'\" title=\"Baseline\" loading=\"lazy\"></iframe></div>';",
        "  }",
        "  // compact scorecard",
        "  var sc=p.scores||[];",
        "  if(sc.length){",
        "    html+='<div class=\"dl-sec-head\">Scorecard \\u00b7 before \\u2192 after</div><div class=\"dl-score-grid\">';",
        "    for(var s=0;s<sc.length;s++){var row=sc[s];",
        "      html+='<div class=\"dl-score-row\"><span class=\"dl-score-name\">'+escHtml(row.label)+'</span>';",
        "      html+='<span class=\"dl-score-track\"><span class=\"dl-score-a\" style=\"width:'+(row.a/4*100)+'%\"></span>';",
        "      html+='<span class=\"dl-score-b\" style=\"width:'+(row.b/4*100)+'%\"></span></span>';",
        "      html+='<span class=\"dl-score-num\">'+row.a+' \\u2192 <b>'+row.b+'</b></span></div>';",
        "    }",
        "    html+='</div>';",
        "  }",
        "  // steer",
        "  html+='<div class=\"dl-steer\"><div class=\"dl-steer-label\">Not satisfied? Re-run this input, or push one dimension harder:</div>';",
        "  html+='<button type=\"button\" class=\"dl-focus-btn\" data-focus=\"\">\\u21bb Re-run</button>';",
        "  for(var w=0;w<probs.length;w++){",
        "    html+='<button type=\"button\" class=\"dl-focus-btn\" data-focus=\"'+escHtml(probs[w].criterion)+'\">Focus: '+escHtml(probs[w].label)+'</button>';",
        "  }",
        "  html+='</div>';",
        "  resultsView.innerHTML=html;",
        "  window.__dlPayload=p;",
        "  var bh=document.getElementById('dl-back-home');",
        "  if(bh){bh.addEventListener('click',function(){showView('landing');loadHistory();});}",
        "  // wire actions",
        "  var cp=document.getElementById('dl-copy-prompt');",
        "  if(cp){cp.addEventListener('click',function(){copyText(buildPrompt(p,p.context||''),cp);});}",
        "  var ch=document.getElementById('dl-copy-html');",
        "  if(ch){ch.addEventListener('click',function(){",
        "    fetch(msg.upgraded_url).then(function(r){return r.text();}).then(function(t){copyText(t,ch);}).catch(function(){});",
        "  });}",
        "  var dh=document.getElementById('dl-dl-html');",
        "  if(dh){dh.addEventListener('click',function(){downloadUrl(msg.upgraded_url,'upgraded.html');});}",
        "  var cl=document.getElementById('dl-copy-link');",
        "  if(cl){cl.addEventListener('click',function(){copyText(window.location.origin+(msg.report_url||''),cl);});}",
        "  var fbtns=resultsView.querySelectorAll('.dl-focus-btn');",
        "  fbtns.forEach(function(fb){fb.addEventListener('click',function(){",
        "    if(!currentRunId){return;}",
        "    var f=fb.getAttribute('data-focus');",
        "    var opts={context:(currentOpts&&currentOpts.context)||'',audience:(currentOpts&&currentOpts.audience)||'',compare_url:(currentOpts&&currentOpts.compare_url)||''};",
        "    if(f){opts.focus=f;}",
        "    fb.disabled=true;",
        "    fetch('/api/run/'+encodeURIComponent(currentRunId)+'/rerun',{method:'POST'})",
        "      .then(function(r){if(!r.ok){throw new Error('Could not prepare a new run.');}return r.json();})",
        "      .then(function(data){startRun(data.run_id,opts);})",
        "      .catch(function(e){setStatus(e.message,true);fb.disabled=false;});",
        "  });});",
        "}",
        "",
        "function openPastRun(runId){",
        "  fetch('/api/run/'+encodeURIComponent(runId)).then(function(r){return r.json();}).then(function(msg){",
        "    if(!msg||msg.error){setStatus('Could not open that run.',true);return;}",
        "    if(!msg.payload||msg.payload.total===undefined){if(msg.report_url){window.location.assign(msg.report_url);}else{setStatus('No saved report is available for that run.',true);}return;}",
        "    prevTotal=null;currentRunId=msg.run_id||runId;",
        "    currentOpts={context:msg.payload.context||'',audience:msg.payload.audience||''};",
        "    lastResult=msg;renderResults(msg);",
        "    workingTab.setAttribute('disabled','');",
        "    resultsTab.removeAttribute('disabled');showView('results');",
        "  }).catch(function(){setStatus('Could not open that run.',true);});",
        "}",
        "function deleteRun(runId){",
        "  fetch('/api/run/'+encodeURIComponent(runId),{method:'DELETE'}).then(function(r){return r.json();})",
        "    .then(function(data){if(data.error){setStatus(data.error,true);return;}loadHistory();})",
        "    .catch(function(){setStatus('Could not update history. Please try again.',true);});",
        "}",
        "function clearHistory(){",
        "  fetch('/api/history/clear',{method:'POST'}).then(function(r){return r.json();})",
        "    .then(function(data){if(data.error){setStatus(data.error,true);return;}loadHistory();})",
        "    .catch(function(){setStatus('Could not update history. Please try again.',true);});",
        "}",
        "function loadHistory(){",
        "  var listEl=document.getElementById('dl-history-list');",
        "  if(!listEl){return;}",
        "  wireDashboardOnce();",
        "  fetch('/api/history').then(function(res){return res.json();}).then(function(data){",
        "    histEntries=data.entries||[];",
        "    histById={};",
        "    for(var h=0;h<histEntries.length;h++){histById[histEntries[h].run_id]=histEntries[h];}",
        "    renderHistory();",
        "  }).catch(function(){",
        "    listEl.className='dl-history-empty';listEl.style.textAlign='center';",
        "    listEl.textContent='Could not load history.';",
        "  });",
        "}",
        "function wireDashboardOnce(){",
        "  if(window.__dlDashWired){return;}",
        "  window.__dlDashWired=true;",
        "  var s=document.getElementById('dl-dash-search');",
        "  if(s){s.addEventListener('input',function(){histQuery=(s.value||'').toLowerCase().trim();renderHistory();});}",
        "  var chips=document.querySelectorAll('.dl-fchip');",
        "  chips.forEach(function(c){c.addEventListener('click',function(){",
        "    histFilter=c.getAttribute('data-filter')||'all';",
        "    chips.forEach(function(x){x.classList.remove('dl-fchip-on');});",
        "    c.classList.add('dl-fchip-on');renderHistory();",
        "  });});",
        "  var cl=document.getElementById('dl-history-clear');",
        "  if(cl){cl.addEventListener('click',function(){if(window.confirm('Clear the runs list? Run files are kept on disk.')){clearHistory();}});}",
        "}",
        "function renderHistory(){",
        "  var listEl=document.getElementById('dl-history-list');",
        "  var countEl=document.getElementById('dl-dash-count');",
        "  if(!listEl){return;}",
        "  var total=histEntries.length;",
        "  var entries=histEntries.filter(function(e){",
        "    if(histFilter==='converged'&&!e.converged){return false;}",
        "    if(histFilter==='escalated'&&e.converged){return false;}",
        "    if(histQuery){var hay=((e.goal||'')+' '+(e.task_class||'')+' '+(e.kind||'')+' '+(e.run_id||'')).toLowerCase();if(hay.indexOf(histQuery)===-1){return false;}}",
        "    return true;",
        "  });",
        "  if(countEl){countEl.textContent=total?(entries.length===total?(total+' run'+(total!==1?'s':'')):(entries.length+' of '+total)):'';}",
        "  if(total===0){listEl.className='dl-history-empty';listEl.style.textAlign='center';listEl.textContent='No past runs yet.';return;}",
        "  if(entries.length===0){listEl.className='dl-history-empty';listEl.style.textAlign='center';listEl.textContent='No runs match this filter.';return;}",
        "  listEl.className='dl-history-grid';listEl.style.textAlign='';",
        "  var html='';",
        "  for(var i=0;i<entries.length;i++){",
        "      var e=entries[i];",
        "      var dateStr=escHtml(fmtWhen(e.ts));",
        "      var statusLabel=e.converged?'Converged':('Escalated'+(e.reason?(' ('+escHtml(e.reason)+')'):''));",
        "      var totalStr=(e.total===null||e.total===undefined)?'?':escHtml(e.total);",
        "      var meta=escHtml(e.goal||e.task_class||'\\u2014');",
        "      var kindStr=e.kind?('<span class=\"dl-hist-kind\">'+escHtml(e.kind)+'</span>'):'';",
        "      var col=e.converged?'var(--slp-sage-dark)':'#a4392a';",
        "      var rid=escHtml(e.run_id);",
        "      var reportUrl=e.report_url||'';",
        "      html+='<div class=\"dl-history-card\" data-run=\"'+rid+'\">';",
        "      html+='<div style=\"display:flex;align-items:center;justify-content:space-between;gap:8px\">';",
        "      html+='<span style=\"font-family:var(--font-ui);font-weight:600;font-size:11px;letter-spacing:.1em;'+",
        "        'text-transform:uppercase;color:'+col+'\">'+statusLabel+'</span>';",
        "      html+='<span style=\"font-family:var(--font-display);font-weight:600;font-size:16px;'+",
        "        'color:var(--fg-1)\">'+totalStr+'/32</span></div>';",
        "      html+='<div style=\"font-family:var(--font-body);font-size:13px;color:var(--fg-2)\">'+meta+'</div>';",
        "      html+='<div style=\"display:flex;align-items:center;gap:8px\"><span style=\"font-family:var(--font-ui);font-size:11px;color:var(--fg-3)\">'+dateStr+'</span>'+kindStr+'</div>';",
        "      html+='<div class=\"dl-hist-actions\">';",
        "      html+='<button type=\"button\" class=\"dl-hist-open\" data-run=\"'+rid+'\">Open</button>';",
        "      if(reportUrl){html+='<a class=\"dl-hist-link\" href=\"'+reportUrl+'\" target=\"_blank\" rel=\"noopener\">Report \\u2197</a>';}",
        "      html+='<button type=\"button\" class=\"dl-hist-del\" data-run=\"'+rid+'\" title=\"Delete run + files\">\\u2715</button>';",
        "      html+='</div></div>';",
        "    }",
        "  listEl.innerHTML=html;",
        "  listEl.querySelectorAll('.dl-hist-open').forEach(function(b){b.addEventListener('click',function(){openPastRun(b.getAttribute('data-run'));});});",
        "  listEl.querySelectorAll('.dl-hist-del').forEach(function(b){b.addEventListener('click',function(){",
        "    if(window.confirm('Delete this run and its files? This cannot be undone.')){deleteRun(b.getAttribute('data-run'));}});});",
        "}",
        "",
        "function openSocket(runId,opts){",
        "  var proto=(window.location.protocol==='https:')?'wss:':'ws:';",
        "  var ws=new WebSocket(proto+'//'+window.location.host+'/ws');",
        "  currentSocket=ws;",
        "  ws.onopen=function(){ws.send(JSON.stringify({type:'start',run_id:runId,options:opts||{}}));};",
        "  ws.onerror=function(){setRunStatus('error','Error');setStatus('WebSocket error -- see server console.',true);};",
        "  ws.onmessage=function(evt){",
        "    var msg=JSON.parse(evt.data);",
        "    if(msg.type==='stream_event'){",
        "      handleStreamEvent(msg.event_type,msg.data);",
        "    } else if(msg.type==='result'){",
        "      lastResult=msg;",
        "      setProgress(1,1,'Complete');",
        "      progBar.className='dl-progress-bar '+(msg.converged?'dl-done':'dl-esc');",
        "      finalizeLog(msg.total,msg.verdict);",
        "      var _doneTotal=(msg.total===null||msg.total===undefined)?'?':escHtml(msg.total);",
        "      var _doneLabel='\\u2713 Done \\u2014 best '+_doneTotal+'/32'+(msg.verdict?(' ('+escHtml(msg.verdict)+')'):'');",
        "      setRunStatus('done',_doneLabel);",
        "      setStatus('',false);",
        "      renderResults(msg);",
        "      var _t=(msg.payload&&msg.payload.total!==undefined&&msg.payload.total!==null)?msg.payload.total:msg.total;",
        "      prevTotal=_t;",
        "      resultsTab.removeAttribute('disabled');",
        "      var _wv=document.querySelector('[data-pw-view=\"working\"]');",
        "      if(_wv&&!_wv.hidden){showView('results');}else{setStatus('Run finished \\u2014 open the Results tab to see the verdict.',false);}",
        "      loadHistory();",
        "    } else if(msg.type==='cancelled'){",
        "      setRunStatus('error','\\u25a0 Stopped');",
        "      appendLogRow('STOPPED',' run cancelled by user',false);",
        "      progText.textContent='Stopped';",
        "    } else if(msg.type==='error'){",
        "      setRunStatus('error','Error');",
        "      setStatus('Error: '+(msg.message||'unknown'),true);",
        "    }",
        "  };",
        "}",
        "",
        "function startRun(runId,opts){",
        "  currentRunId=runId;",
        "  currentOpts=opts||{};",
        "  workingTab.removeAttribute('disabled');",
        "  resultsTab.setAttribute('disabled','');",
        "  showView('working');",
        "  logEl.innerHTML='';toolRows={};clearAgentState();resetMilestones();",
        "  progBar.className='dl-progress-bar';progBar.style.width='0%';",
        "  progText.textContent='Starting\\u2026';progPct.textContent='';",
        "  setRunStatus('running');",
        "  openSocket(runId,currentOpts);",
        "}",
        "",
        "function stopRun(){",
        "  if(currentSocket&&currentSocket.readyState===1){",
        "    currentSocket.send(JSON.stringify({type:'cancel',run_id:currentRunId}));",
        "  } else {",
        "    setRunStatus('error','\\u25a0 Stopped');",
        "  }",
        "}",
        "if(stopBtn){stopBtn.addEventListener('click',stopRun);}",
        "var homeBtn=document.getElementById('dl-home-btn');",
        "if(homeBtn){homeBtn.addEventListener('click',function(){showView('landing');loadHistory();});}",
        "",
        "function uploadFile(file){",
        "  var isHtml=/\\.html?$/i.test(file.name||'');",
        "  if(isHtml){loadHtmlFile(file);return;}",
        "  if(file.type.indexOf('image/')!==0){setStatus('Please provide an image or .html file.',true);return;}",
        "  pendingImage=file;showPreview(file);refreshDetect();",
        "  setStatus('Uploading '+(file.name||'screenshot')+'\\u2026',false);",
        "  var form=new FormData();form.append('file',file,file.name||'upload.png');",
        "  form.append('goal',getGoal());",
        "  fetch('/api/upload',{method:'POST',body:form})",
        "    .then(function(res){if(!res.ok){throw new Error('upload failed: '+res.status);}return res.json();})",
        "    .then(function(data){setStatus('',false);startRun(data.run_id,baseOpts());})",
        "    .catch(function(err){setStatus(String(err),true);});",
        "}",
        "",
        "// Drop/paste/browse STAGE the input (preview + enable Analyze); they do NOT",
        "// auto-start. The run begins only when the user presses Analyze -- so a goal",
        "// added after dropping is captured, and an accidental drop never spends a run.",
        "function stageImage(file){",
        "  if(!file){return;}",
        "  var isHtml=/\\.html?$/i.test(file.name||'');",
        "  if(isHtml){loadHtmlFile(file);return;}",
        "  if(file.type.indexOf('image/')!==0){setStatus('Please provide an image or .html file.',true);return;}",
        "  pendingImage=file;showPreview(file);refreshDetect();",
        "  setStatus('Screenshot ready \\u2014 add a goal (optional), then press Analyze.',false);",
        "}",
        "",
        "function getGoal(){return goalEl?goalEl.value.trim():'';}",
        "function getContext(){return contextEl?contextEl.value.trim():'';}",
        "function getAudience(){return audienceEl?audienceEl.value.trim():'';}",
        "function getCompare(){return compareEl?compareEl.value.trim():'';}",
        "function baseOpts(){return {context:getContext(),audience:getAudience(),compare_url:getCompare()};}",
        "",
        "function loadHtmlFile(file){",
        "  var reader=new FileReader();",
        "  reader.onload=function(e){",
        "    inputEl.value=e.target.result;pendingImage=null;preview.style.display='none';",
        "    refreshDetect();setStatus('Loaded '+(file.name||'file')+'. Press Analyze to continue.',false);",
        "    inputEl.focus();",
        "  };",
        "  reader.readAsText(file);",
        "}",
        "",
        "function startFromSource(kind,value){",
        "  setStatus('Submitting\\u2026',false);",
        "  fetch('/api/source',{method:'POST',headers:{'Content-Type':'application/json'},",
        "    body:JSON.stringify({kind:kind,value:value,goal:getGoal()})})",
        "    .then(function(res){if(!res.ok){throw new Error('request failed: '+res.status);}return res.json();})",
        "    .then(function(data){setStatus('',false);startRun(data.run_id,baseOpts());})",
        "    .catch(function(err){setStatus(String(err),true);});",
        "}",
        "",
        "function submit(){",
        "  if(pendingImage){uploadFile(pendingImage);return;}",
        "  var kind=detectKind(inputEl.value);",
        "  var value=inputEl.value.trim();",
        "  if(!kind||!value){setStatus('Paste a URL, some HTML, or drop a screenshot first.',true);return;}",
        "  startFromSource(kind,value);",
        "}",
        "if(analyzeBtn){analyzeBtn.addEventListener('click',submit);}",
        "",
        "inputEl.addEventListener('input',function(){if(pendingImage){pendingImage=null;preview.style.display='none';}refreshDetect();});",
        "inputEl.addEventListener('keydown',function(e){",
        "  if(e.key==='Enter'&&(e.metaKey||e.ctrlKey)){e.preventDefault();submit();return;}",
        "  if(e.key==='Enter'&&!e.shiftKey&&detectKind(inputEl.value)==='url'){e.preventDefault();submit();}",
        "});",
        "",
        "if(browseBtn){browseBtn.addEventListener('click',function(){fileInput.click();});}",
        "fileInput.addEventListener('change',function(e){if(e.target.files&&e.target.files[0]){stageImage(e.target.files[0]);}});",
        "",
        "smart.addEventListener('focusin',function(){smart.classList.add('dl-focus');});",
        "smart.addEventListener('focusout',function(){smart.classList.remove('dl-focus');});",
        "['dragenter','dragover'].forEach(function(ev){",
        "  smart.addEventListener(ev,function(e){e.preventDefault();e.stopPropagation();smart.classList.add('dl-drag');});",
        "});",
        "['dragleave','drop'].forEach(function(ev){",
        "  smart.addEventListener(ev,function(e){e.preventDefault();e.stopPropagation();smart.classList.remove('dl-drag');});",
        "});",
        "smart.addEventListener('drop',function(e){",
        "  var files=e.dataTransfer&&e.dataTransfer.files;",
        "  if(files&&files[0]){stageImage(files[0]);}",
        "});",
        "document.addEventListener('paste',function(e){",
        "  var items=(e.clipboardData||window.clipboardData).items;",
        "  if(!items){return;}",
        "  for(var i=0;i<items.length;i++){",
        "    if(items[i].type.indexOf('image')!==-1){stageImage(items[i].getAsFile());e.preventDefault();break;}",
        "  }",
        "});",
        "",
        "function resetApp(){",
        "  if(currentSocket){try{currentSocket.close();}catch(e){}currentSocket=null;}",
        "  currentRunId=null;pendingImage=null;lastResult=null;currentOpts={};prevTotal=null;",
        "  logEl.innerHTML='';toolRows={};clearAgentState();resetMilestones();",
        "  preview.style.display='none';previewImg.src='';",
        "  inputEl.value='';fileInput.value='';if(goalEl){goalEl.value='';}if(contextEl){contextEl.value='';}if(audienceEl){audienceEl.value='';}if(compareEl){compareEl.value='';}",
        "  refreshDetect();setStatus('',false);",
        "  progBar.className='dl-progress-bar';progBar.style.width='0%';",
        "  progText.textContent='Starting\\u2026';progPct.textContent='';",
        "  setRunStatus('running');",
        "  workingTab.setAttribute('disabled','');",
        "  resultsTab.setAttribute('disabled','');",
        "  resultsView.innerHTML='';",
        "  showView('landing');inputEl.focus();",
        "}",
        "if(resetBtn){resetBtn.addEventListener('click',resetApp);}",
        "",
        "function loadMode(){",
        "  var badge=document.getElementById('dl-mode-badge');",
        "  if(!badge){return;}",
        "  fetch('/api/preflight').then(function(r){return r.json();}).then(function(d){",
        "    badge.title=d.message||'';",
        "    if(d.mode==='dry'){badge.className='dl-mode-badge dl-mode-dry';badge.textContent='\\u25cf DEMO \\u00b7 scripted (not a real analysis)';}",
        "    else if(d.mode==='live'){badge.className='dl-mode-badge dl-mode-live';badge.textContent='\\u25cf LIVE';}",
        "    else {badge.className='dl-mode-badge dl-mode-warn';badge.textContent='\\u26a0 LIVE \\u00b7 not installed';}",
        "  }).catch(function(){});",
        "}",
        "refreshDetect();",
        "showView('landing');",
        "loadHistory();",
        "loadMode();",
        "try{inputEl.focus({preventScroll:true});}catch(e){inputEl.focus();}",
        "})();",
    ]
    return "<script>" + "\n".join(lines) + "</script>"


def build_landing_html() -> str:
    """Return the full Landing page HTML (Page_Worth chrome + smart-input UI)."""
    hero = (
        '<div style="text-align:center;margin:34px 0 24px">'
        + t._pw_eyebrow("Design intelligence", "var(--fg-accent)")
        + '<h1 style="font-family:var(--font-display);font-weight:300;font-size:46px;line-height:1.06;'
        'letter-spacing:-.015em;margin:16px 0 16px">Drop a screen.<br>Know what to '
        '<em style="font-style:italic;color:var(--fg-accent)">fix</em> first.</h1>'
        '<p style="font-family:var(--font-body);color:var(--fg-2);max-width:50ch;margin:0 auto;'
        'font-size:17px;line-height:1.6">Paste a URL, paste raw HTML, or drop a screenshot and '
        "the design loop will render it, score it across eight dimensions, and iterate a better version -- "
        "streaming every MAKER &rarr; LINTS &rarr; CRITIC &rarr; GATE step live.</p>"
        "</div>"
    )
    dims_section = (
        '<details class="dl-dims-disclosure">'
        '<summary class="dl-dims-summary">Judged on eight things</summary>'
        '<div class="dl-dims-body">'
        + _dims_grid()
        + "</div>"
        "</details>"
    )
    landing_view = (
        '<div data-pw-view="landing">'
        "<section>"
        + hero
        + _smart_input_section()
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
