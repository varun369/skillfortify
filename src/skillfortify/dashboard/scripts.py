"""Embedded JavaScript for the SkillFortify HTML dashboard report.

Provides interactive filtering, collapsible sections, and dynamic
rendering of the dashboard data that is injected as a JSON payload.
No external libraries -- vanilla ES6 only.

Security note: All dynamic text is escaped via the ``esc()`` helper
before DOM insertion. The data payload is generated server-side by
SkillFortify itself (not from untrusted user input). The innerHTML
usage is intentional for building table rows from pre-escaped strings
and is safe in this self-contained report context.
"""

from __future__ import annotations

DASHBOARD_JS: str = r"""
(function(){
"use strict";
var D=window.__SKILLFORTIFY_DATA__;
if(!D){document.body.textContent="No data embedded.";return;}

/* --- Escape HTML helper (XSS prevention) --- */
function esc(t){
  if(!t)return"";
  var d=document.createElement("div");
  d.appendChild(document.createTextNode(String(t)));
  return d.textContent.replace(/&/g,"&amp;").replace(/</g,"&lt;")
    .replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}

/* --- Safe DOM builder for stat cards --- */
function mkCard(val,label,cls){
  var d=document.createElement("div");
  d.className="stat-card "+cls;
  var vEl=document.createElement("div");
  vEl.className="value";vEl.textContent=String(val);
  var lEl=document.createElement("div");
  lEl.className="label";lEl.textContent=label;
  d.appendChild(vEl);d.appendChild(lEl);return d;
}

var s=D.summary;
var statsEl=document.getElementById("stats-grid");
var cards=[
  [s.total_skills,"Total Skills","total"],
  [s.safe_count,"Safe","safe"],
  [s.unsafe_count,"Unsafe","critical"],
  [s.critical_count,"Critical","critical"],
  [s.high_count,"High","high"],
  [s.medium_count,"Medium","medium"],
  [s.low_count,"Low","low"]
];
cards.forEach(function(c){statsEl.appendChild(mkCard(c[0],c[1],c[2]));});

var tsEl=document.getElementById("scan-ts");
if(tsEl&&s.scan_timestamp){tsEl.textContent="Scan: "+s.scan_timestamp;}

/* --- Framework coverage chips --- */
var fwEl=document.getElementById("fw-chips");
if(fwEl){
  var cov=D.framework_coverage||[];
  if(cov.length===0){
    var em=document.createElement("div");em.className="empty-state";
    var p=document.createElement("p");p.textContent="No frameworks detected";
    em.appendChild(p);fwEl.appendChild(em);
  }else{
    cov.forEach(function(f){
      var ch=document.createElement("span");ch.className="chip detected";
      ch.appendChild(document.createTextNode(f.framework+" "));
      var cnt=document.createElement("span");cnt.className="count";
      cnt.textContent=String(f.count);ch.appendChild(cnt);
      fwEl.appendChild(ch);
    });
  }
}

/* --- Risk bar --- */
var barEl=document.getElementById("risk-bar");
if(barEl){
  var total=s.critical_count+s.high_count+s.medium_count+s.low_count;
  if(total>0){
    [[s.critical_count,"seg-critical","CRITICAL"],
     [s.high_count,"seg-high","HIGH"],
     [s.medium_count,"seg-medium","MEDIUM"],
     [s.low_count,"seg-low","LOW"]
    ].forEach(function(sg){
      if(sg[0]>0){
        var el=document.createElement("div");
        el.className="segment "+sg[1];
        el.style.width=(sg[0]/total*100)+"%";
        el.textContent=String(sg[0]);el.title=sg[2]+": "+sg[0];
        barEl.appendChild(el);
      }
    });
  }else{
    var body=barEl.parentNode.querySelector(".section-body");
    if(body){body.textContent="No findings -- all skills passed.";}
  }
}

/* --- Findings table --- */
var tBody=document.getElementById("findings-body");
var findings=D.findings||[];

function mkTd(txt,cls){
  var td=document.createElement("td");
  if(cls)td.className=cls;
  td.textContent=txt||"";return td;
}
function mkBadgeTd(sev){
  var td=document.createElement("td");
  var sp=document.createElement("span");
  sp.className="badge badge-"+sev;sp.textContent=sev;
  td.appendChild(sp);return td;
}
function renderFindings(rows){
  while(tBody.firstChild)tBody.removeChild(tBody.firstChild);
  if(rows.length===0){
    var tr=document.createElement("tr");
    var td=document.createElement("td");td.colSpan=6;
    td.className="empty-state";
    td.textContent="No findings match the current filters.";
    tr.appendChild(td);tBody.appendChild(tr);return;
  }
  rows.forEach(function(r){
    var tr=document.createElement("tr");
    tr.appendChild(mkTd(r.skill_name));
    tr.appendChild(mkTd(r.format));
    tr.appendChild(mkBadgeTd(r.severity));
    tr.appendChild(mkTd(r.message));
    tr.appendChild(mkTd(r.attack_class));
    tr.appendChild(mkTd(r.evidence,"evidence-cell"));
    tBody.appendChild(tr);
  });
}
renderFindings(findings);

/* --- Populate filter dropdowns --- */
var sevFilter=document.getElementById("filter-severity");
var fwFilter=document.getElementById("filter-framework");
function addOpt(sel,v){
  var o=document.createElement("option");o.value=v;o.textContent=v;
  sel.appendChild(o);
}
if(sevFilter){
  ["ALL","CRITICAL","HIGH","MEDIUM","LOW"].forEach(function(v){addOpt(sevFilter,v);});
}
if(fwFilter){
  var fws=new Set();findings.forEach(function(f){fws.add(f.format);});
  addOpt(fwFilter,"ALL");
  Array.from(fws).sort().forEach(function(v){addOpt(fwFilter,v);});
}
function applyFilters(){
  var sv=sevFilter?sevFilter.value:"ALL";
  var fw=fwFilter?fwFilter.value:"ALL";
  renderFindings(findings.filter(function(r){
    return(sv==="ALL"||r.severity===sv)&&(fw==="ALL"||r.format===fw);
  }));
}
if(sevFilter)sevFilter.addEventListener("change",applyFilters);
if(fwFilter)fwFilter.addEventListener("change",applyFilters);

/* --- Capabilities matrix --- */
var capBody=document.getElementById("cap-body");
var caps=D.capabilities||[];
var resources=["filesystem","network","shell","environment","skill_invoke",
  "clipboard","browser","database"];
if(capBody){
  if(caps.length===0){
    var tr=document.createElement("tr");var td=document.createElement("td");
    td.colSpan=resources.length+1;td.className="empty-state";
    td.textContent="No capability data available.";
    tr.appendChild(td);capBody.appendChild(tr);
  }else{
    caps.forEach(function(row){
      var tr=document.createElement("tr");
      tr.appendChild(mkTd(row.skill_name));
      resources.forEach(function(r){
        var level=row.capabilities[r]||"NONE";
        tr.appendChild(mkTd(level,level));
      });
      capBody.appendChild(tr);
    });
  }
}

/* --- Collapsible sections --- */
document.querySelectorAll(".section-header").forEach(function(hdr){
  hdr.addEventListener("click",function(){
    var body=hdr.nextElementSibling;if(!body)return;
    var hidden=body.classList.toggle("hidden");
    hdr.classList.toggle("collapsed",hidden);
  });
});
})();
"""
