"""Annotate the user's ACTUAL page with redline markers.

A senior lead points at *where* on the page the problem is. This injects a
self-contained overlay (no network, no deps) into the user's own HTML that
outlines problem elements and drops numbered badges next to them, plus a fixed
legend. The result is saved as annotated.html and shown as "Your page,
annotated" in Results -- the one place we render the user's real markup, not the
demo before/after fixtures.

Deterministic and client-side: the overlay re-detects the same objective issues
the audit checks (missing alt, vague link text, gradient/slop backgrounds, low
contrast) from the live DOM, so the markers always match what actually renders.
"""

from __future__ import annotations

# Plain (non-f) string: the JS uses its own braces; keep it verbatim.
_OVERLAY = r"""
<style>
  .__dlmk{position:absolute;z-index:2147483000;transform:translate(-50%,-50%);
    background:#a4392a;color:#fff;font:700 11px/1 -apple-system,Segoe UI,Roboto,sans-serif;
    min-width:18px;height:18px;border-radius:9px;display:flex;align-items:center;justify-content:center;
    padding:0 5px;box-shadow:0 1px 3px rgba(0,0,0,.4)}
  .__dlmk.warn{background:#c98a2b}
  .__dlol{outline:2px dashed #a4392a !important;outline-offset:1px}
  .__dlol.warn{outline-color:#c98a2b !important}
  #__dllegend{position:fixed;right:12px;bottom:12px;z-index:2147483001;max-width:300px;
    background:#fff;border:1px solid #e6ddcc;border-radius:8px;box-shadow:0 4px 16px rgba(0,0,0,.18);
    font:500 12px/1.4 -apple-system,Segoe UI,Roboto,sans-serif;color:#211d18;padding:12px 14px}
  #__dllegend h4{margin:0 0 8px;font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:#8a5a1f}
  #__dllegend li{margin:4px 0;list-style:none;display:flex;gap:8px;align-items:flex-start}
  #__dllegend .n{flex:none;width:16px;height:16px;border-radius:8px;background:#a4392a;color:#fff;
    font-weight:700;font-size:10px;display:flex;align-items:center;justify-content:center}
  #__dllegend .n.warn{background:#c98a2b}
  #__dllegend .empty{color:#6e6356;font-style:italic}
</style>
<script>
(function(){
  function ready(fn){if(document.readyState!=='loading'){fn();}else{document.addEventListener('DOMContentLoaded',fn);}}
  function lum(c){var m=c.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);if(!m)return null;
    function f(v){v=v/255;return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4);}
    return 0.2126*f(+m[1])+0.7152*f(+m[2])+0.0722*f(+m[3]);}
  function bg(el){var n=el;while(n){var c=getComputedStyle(n).backgroundColor;
    if(c&&c.indexOf('rgba(0, 0, 0, 0)')===-1&&c!=='transparent')return c;n=n.parentElement;}return 'rgb(255,255,255)';}
  ready(function(){
    var items=[];
    function mark(el,label,warn){
      if(!el||!el.getBoundingClientRect)return;
      var r=el.getBoundingClientRect();
      if(r.width===0&&r.height===0)return;
      var n=items.length+1;
      el.classList.add('__dlol');if(warn)el.classList.add('warn');
      var b=document.createElement('div');b.className='__dlmk'+(warn?' warn':'');b.textContent=n;
      b.style.left=(window.scrollX+r.left+8)+'px';b.style.top=(window.scrollY+r.top+8)+'px';
      document.body.appendChild(b);
      items.push({n:n,label:label,warn:warn});
    }
    // 1. images missing alt
    Array.prototype.forEach.call(document.querySelectorAll('img:not([alt])'),function(im){
      mark(im,'Image has no alt text',false);});
    // 2. gradient / slop backgrounds
    Array.prototype.forEach.call(document.querySelectorAll('*'),function(el){
      var bi=getComputedStyle(el).backgroundImage||'';
      if(bi.indexOf('gradient')!==-1 && el.offsetWidth>200 && el.offsetHeight>120){
        mark(el,'Gradient hero -- a slop default (restraint)',true);}
    });
    // 3. vague link text
    Array.prototype.forEach.call(document.querySelectorAll('a'),function(a){
      var t=(a.textContent||'').trim().toLowerCase();
      if(t==='click here'||t==='here'||t==='read more'||t==='learn more'){
        mark(a,'Vague link text: "'+t+'"',true);}
    });
    // 4. low-contrast text (first few offenders)
    var lc=0;
    Array.prototype.forEach.call(document.querySelectorAll('p,span,a,li,h1,h2,h3,td'),function(el){
      if(lc>=4)return;
      var txt=(el.textContent||'').trim();if(txt.length<2)return;
      var fg=lum(getComputedStyle(el).color),bgl=lum(bg(el));
      if(fg===null||bgl===null)return;
      var ratio=(Math.max(fg,bgl)+0.05)/(Math.min(fg,bgl)+0.05);
      if(ratio<4.5){mark(el,'Low contrast text ('+ratio.toFixed(1)+':1)',false);lc++;}
    });
    var leg=document.createElement('div');leg.id='__dllegend';
    var html='<h4>Redlines · '+items.length+'</h4>';
    if(items.length===0){html+='<div class="empty">No element-level issues flagged.</div>';}
    else{html+='<ul style="margin:0;padding:0">';
      items.forEach(function(it){html+='<li><span class="n'+(it.warn?' warn':'')+'">'+it.n+'</span><span>'+it.label+'</span></li>';});
      html+='</ul>';}
    leg.innerHTML=html;document.body.appendChild(leg);
  });
})();
</script>
"""


def annotate_html(html: str) -> str:
    """Return the user's HTML with the redline overlay injected before </body>
    (or appended if there's no body tag). Never raises."""
    try:
        low = (html or "").lower()
        idx = low.rfind("</body>")
        if idx != -1:
            return html[:idx] + _OVERLAY + html[idx:]
        return (html or "") + _OVERLAY
    except Exception:
        return html or ""
