const S = JSON.parse(sessionStorage.getItem("fs") || "null"); if (!S) location = "index.html";
const $ = id => document.getElementById(id), logout = () => { sessionStorage.clear(); location = "index.html"; };
const api = (p, o = {}) => fetch(API + p, { ...o, headers: { Authorization: "Bearer " + S.token, "Content-Type": "application/json" } }).then(r => { if (r.status == 401) logout(); return r.json(); });
const post = (p, b) => api(p, { method: "POST", body: JSON.stringify(b) });
const COL = { HIGH: "#b3402a", MEDIUM: "#d08a2e", LOW: "#6b8f4e", CLEAR: "#9c8b7a" }, PAL = ["#5c3d2e", "#a86f44", "#d9a066", "#8a9a5b", "#c9694a", "#b8a38a"];
const inr = n => "Rs " + Number(n).toLocaleString("en-IN");
let INV = null, ACT = 0, ENT = null, SEEDS = [];
$("who").textContent = `${S.name} · ${S.title}`;

/* ---------- charts (inline SVG) ---------- */
function bars(d, w = 320, h = 190) {
  if (!d.length) return '<p class="mu">No data</p>';
  const m = Math.max(...d.map(x => x.v), 1), bw = (w - 20) / d.length;
  return `<svg viewBox="0 0 ${w} ${h}" width="100%">` + d.map((x, i) => { const bh = (h - 55) * x.v / m, px = 15 + i * bw;
    return `<rect x="${px + 4}" y="${h - 32 - bh}" width="${bw - 8}" height="${bh}" rx="3" fill="${x.c}"/><text x="${px + bw / 2}" y="${h - 36 - bh}" text-anchor="middle" font-size="10">${x.t ?? x.v}</text><text x="${px + bw / 2}" y="${h - 16}" text-anchor="middle" font-size="9">${x.l}</text>`; }).join("") + `<line x1="12" y1="${h - 32}" x2="${w}" y2="${h - 32}" stroke="#dccbab"/></svg>`;
}
function pie(d) {
  const T = d.reduce((a, x) => a + x.v, 0); if (!T) return '<p class="mu">No findings in view</p>';
  let a0 = -Math.PI / 2, s = '<svg viewBox="0 0 320 190" width="100%">';
  d.forEach(x => { const a1 = a0 + 2 * Math.PI * x.v / T, P = t => [80 + 68 * Math.cos(t), 95 + 68 * Math.sin(t)], [x0, y0] = P(a0), [x1, y1] = P(a1);
    s += d.length == 1 ? `<circle cx="80" cy="95" r="68" fill="${x.c}"/>` : `<path d="M80,95 L${x0},${y0} A68,68 0 ${a1 - a0 > Math.PI ? 1 : 0} 1 ${x1},${y1}Z" fill="${x.c}" stroke="#fffaf0"/>`; a0 = a1; });
  d.forEach((x, i) => s += `<rect x="165" y="${30 + i * 22}" width="11" height="11" fill="${x.c}"/><text x="182" y="${40 + i * 22}" font-size="10">${x.l} (${Math.round(100 * x.v / T)}%)</text>`);
  return s + "</svg>";
}

/* ---------- graph ---------- */
function graph(g, flagged) {
  const W = 560, H = 330, n = g.nodes.length, pos = {};
  g.nodes.forEach((x, i) => { const a = 2 * Math.PI * i / n - Math.PI / 2; pos[x.id] = [W / 2 + 210 * Math.cos(a), H / 2 + 115 * Math.sin(a)]; });
  let s = `<svg viewBox="0 0 ${W} ${H}" width="100%"><defs><marker id="ar" markerWidth="9" markerHeight="9" refX="19" refY="4.5" orient="auto"><path d="M0,0L9,4.5L0,9z" fill="#5c3d2e"/></marker><marker id="arf" markerWidth="9" markerHeight="9" refX="19" refY="4.5" orient="auto"><path d="M0,0L9,4.5L0,9z" fill="#b3402a"/></marker></defs>`;
  g.edges.forEach(e => { const a = pos[e.s], b = pos[e.d]; if (!a || !b) return; const fl = e.id && flagged.has(e.id), tx = e.kind == "txn";
    s += `<line x1="${a[0]}" y1="${a[1]}" x2="${b[0]}" y2="${b[1]}" stroke="${tx ? (fl ? "#b3402a" : "#5c3d2e") : "#a86f44"}" stroke-width="${tx ? (fl ? 3.5 : 2) : 1.2}" ${tx ? `marker-end="url(#${fl ? "arf" : "ar"})"` : 'stroke-dasharray="4 3"'}/>`;
    s += `<text x="${(a[0] + b[0]) / 2}" y="${(a[1] + b[1]) / 2 - 4}" text-anchor="middle" font-size="9" font-weight="${fl ? 700 : 400}">${e.label}</text>`; });
  g.nodes.forEach(x => { const [px, py] = pos[x.id];
    s += x.type == "employee" ? `<rect x="${px - 10}" y="${py - 10}" width="20" height="20" rx="4" fill="#a86f44"/>` : `<circle cx="${px}" cy="${py}" r="11" fill="#5c3d2e"/>`;
    s += `<text x="${px}" y="${py + 26}" text-anchor="middle" font-weight="600">${x.label}</text>`; });
  return s + "</svg>";
}
function flowTable(a) {
  const amt = Object.fromEntries(a.timeline.filter(e => e.amt).map(e => [e.id, e.amt])), acc = {};
  a.graph.edges.filter(e => e.kind == "txn").forEach(e => { const v = amt[e.id] || 0; (acc[e.s] ??= { i: 0, o: 0 }).o += v; (acc[e.d] ??= { i: 0, o: 0 }).i += v; });
  const rows = Object.entries(acc).filter(([k]) => k != "EXT");
  return rows.length ? `<table><tr><th>Account</th><th>Money in</th><th>Money out</th><th>Net</th></tr>${rows.map(([k, v]) => `<tr><td>${k}</td><td>${inr(v.i)}</td><td>${inr(v.o)}</td><td>${v.i - v.o >= 0 ? "+" : "-"}${inr(Math.abs(v.i - v.o))}</td></tr>`).join("")}</table>` : '<p class="mu">No money movement in this activity.</p>';
}

/* ---------- data + filters ---------- */
async function init() {
  const m = await api("/metrics"); ENT = await api("/entities"); SEEDS = await api("/seeds"); fillEntities(); $("etype").onchange = fillEntities; drawSeeds();
}
function fillEntities() { $("eid").innerHTML = ($("etype").value == "employee" ? ENT.employees.map(x => [x.id, `${x.id} - ${x.name}`]) : ENT.accounts.map(x => [x.id, `${x.id} - ${x.owner}`])).map(([v, t]) => `<option value="${v}">${t}</option>`).join(""); }
function drawSeeds() {
  const L = SEEDS.filter(s => s.score >= +$("fscore").value && ($("fstat").value == "ALL" || s.decision == $("fstat").value));
  $("seeds").innerHTML = L.map(s => `<div class="seed"><b>${s.name}</b> <span class="mu">${s.role}</span><br><span class="badge ${s.score >= .6 ? "HIGH" : "MEDIUM"}">seed ${s.score}</span> <span class="tag">${s.decision}</span>
   <p>${s.signals.join(" · ")}</p><p>${s.window[0].slice(0, 10)} → ${s.window[1].slice(0, 10)}</p><button class="p" onclick="open_('seed','${s.id}')">Investigate</button> <button onclick="dismiss('${s.id}')">Dismiss</button></div>`).join("") || '<span class="mu">No seeds match the filters.</span>';
}
async function dismiss(id) { await post(`/seeds/${id}/decision`, { decision: "DISMISSED" }); SEEDS = await api("/seeds"); drawSeeds(); }
const startManual = () => open_($("etype").value, $("eid").value);
async function open_(type, id) {
  const r = await post("/investigations", { type, id }); if (r.error) return alert(r.error);
  if (type == "seed") { await post(`/seeds/${id}/decision`, { decision: "ACCEPTED" }); SEEDS = await api("/seeds"); drawSeeds(); }
  INV = r; ACT = 0; $("frisk").value = "ALL";
  $("fcat").innerHTML = ["ALL", ...new Set(r.activities.flatMap(a => a.findings.map(f => f.category)))].map(c => `<option>${c}</option>`).join(""); render();
}
function resetF() { ["frisk", "fcat", "fstat"].forEach(i => $(i).value = "ALL"); $("fscore").value = 0; ACT = 0; drawSeeds(); if (INV) render(); }
const visible = () => INV.activities.filter(a => ($("frisk").value == "ALL" || a.level == $("frisk").value) && ($("fcat").value == "ALL" || a.findings.some(f => f.category == $("fcat").value)));

/* ---------- render ---------- */
function render() {
  const V = visible(), c = INV.case; if (ACT >= V.length) ACT = 0; const a = V[ACT];
  const flagged = new Set(V.flatMap(x => x.findings.flatMap(f => f.event_ids))), cat = {};
  V.forEach(x => x.findings.forEach(f => cat[f.category] = (cat[f.category] || 0) + f.points));
  const txs = V.flatMap(x => x.timeline.filter(e => e.amt)).slice(0, 12);
  let h = `<div class="card" style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:10px;align-items:center"><div><h2 style="margin:0">${INV.id} — ${INV.subject} <span class="badge ${INV.overall_level}">${INV.overall_level}</span></h2><div class="mu">${INV.summary}</div></div>
   <div><select id="as"><option>Investigator A</option><option>Investigator B</option><option>Compliance Head</option></select> <select id="st"><option>ASSIGNED</option><option>UNDER REVIEW</option><option>ESCALATED</option><option>CLOSED</option></select> <button class="p" onclick="saveCase()">Assign</button>
   <a href="${API}/investigations/${INV.id}/report.docx?token=${S.token}"><button class="p">⬇ Word report</button></a><div class="mu" style="text-align:right;margin-top:4px">Case: ${c.status}${c.assignee ? " / " + c.assignee : ""}</div></div></div>
  <div class="kpis"><div class="kpi"><b>${INV.overall_score}/100</b><small>Highest activity risk</small></div><div class="kpi"><b>${V.length}/${INV.activities.length}</b><small>Activities in view</small></div>
   <div class="kpi"><b>${V.reduce((s, x) => s + x.counts.rules, 0)}</b><small>Rule findings</small></div><div class="kpi"><b>${inr(txs.reduce((s, e) => s + e.amt, 0))}</b><small>Value in view</small></div></div>
  <div class="g3"><div class="card"><h3>Risk score by activity</h3>${bars(V.map(x => ({ l: x.id, v: x.score, c: COL[x.level] })))}</div>
   <div class="card"><h3>Findings by category</h3>${pie(Object.entries(cat).map(([l, v], i) => ({ l, v, c: PAL[i % 6] })))}</div>
   <div class="card"><h3>Transaction values (₹ thousands)</h3>${bars(txs.map(e => ({ l: e.id, v: e.amt, t: Math.round(e.amt / 1000) + "k", c: flagged.has(e.id) ? "#b3402a" : "#d9a066" })))}<div class="legend"><span><i style="background:#b3402a"></i>flagged by a rule</span><span><i style="background:#d9a066"></i>not flagged</span></div></div></div>`;
  if (!a) return $("inv").innerHTML = h + '<div class="card mu">No activities match the current filters.</div>';
  const txn = a.timeline.filter(e => e.kind == "TXN"), fl = txn.filter(e => flagged.has(e.id)).length;
  h += `<div class="tabs">${V.map((x, i) => `<div class="tab ${i == ACT ? "on" : ""}" onclick="ACT=${i};render()">${x.id}: ${x.title} <span class="badge ${x.level}">${x.score}</span></div>`).join("")}</div>
  <div class="g2"><div class="card"><h3>Rule findings — why this was flagged</h3>${a.findings.map(f => `<div class="f"><b>+${f.points} · ${f.rule_id} v${f.version}</b> · ${f.category}<br>${f.explanation}<small>Condition: ${f.condition}</small><small>Observed: ${f.observed} · Evidence: ${f.event_ids.join(", ")}</small>${f.policy_context ? `<small>Policy: ${f.policy_context}</small>` : ""}</div>`).join("") || '<p class="mu">No rules triggered — activity is consistent with role and policy.</p>'}
    ${a.evidence_gaps.length ? `<h3 style="margin-top:12px">Evidence gaps</h3>${a.evidence_gaps.map(g => `<div class="gap">⚠ ${g}</div>`).join("")}` : ""}</div>
   <div class="card"><h3>Money-flow &amp; action graph</h3>${graph(a.graph, flagged)}
    <div class="legend"><span><i style="background:#5c3d2e;border-radius:50%"></i>Account</span><span><i style="background:#a86f44"></i>Employee</span><span><i style="background:#5c3d2e;height:3px;vertical-align:3px"></i>Money transfer (arrow = direction)</span><span><i style="background:#b3402a;height:3px;vertical-align:3px"></i>Transfer cited by a rule</span><span>- - Employee action on account</span></div>
    <div class="explain"><b>How to read this:</b> arrows show where money moved, labelled with the amount. Dashed lines show which employee acted on which account. ${txn.length ? `${fl} of ${txn.length} transfer(s) here are cited as evidence by rule findings and drawn in red.` : "There are no transfers here, only employee actions."} ${a.findings[0] ? `<br><b>Key insight:</b> ${a.findings[0].explanation}.` : ""}</div></div></div>
  <div class="g2"><div class="card"><h3>Money in / out per account</h3>${flowTable(a)}</div>
   <div class="card"><h3>Activity timeline</h3>${a.timeline.map(e => `<div class="ev ${e.kind} ${flagged.has(e.id) ? "flag" : ""}"><small>${e.ts.replace("T", " ")} · ${e.id}${flagged.has(e.id) ? " · cited in finding" : ""}</small><br>${e.text}</div>`).join("")}</div></div>`;
  $("inv").innerHTML = h; $("as").value = c.assignee || "Investigator A"; $("st").value = c.status == "OPEN" ? "ASSIGNED" : c.status;
}
async function saveCase() { INV.case = await post(`/investigations/${INV.id}/case`, { assignee: $("as").value, status: $("st").value }); render(); }
init();
