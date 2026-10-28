"""Self-contained HTML report (one file, no server, works offline)."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Internet Parser Report</title>
<style>
:root {
  --bg: #f7f7f5; --panel: #ffffff; --text: #1d1d1b; --muted: #6b6b66; --line: #e4e4df;
  --accent: #2f6fde; --problem: #d4483b; --wish: #c98a12; --joy: #2f9e5b; --topic: #6b5bd2;
  --chip: #efefea;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #141413; --panel: #1e1e1c; --text: #ecebe6; --muted: #9c9b94; --line: #33332f;
    --accent: #6b9cf0; --problem: #ef6f62; --wish: #e7b13f; --joy: #5cc488; --topic: #9d90f0;
    --chip: #2a2a27;
  }
}
:root[data-theme="dark"] {
  --bg: #141413; --panel: #1e1e1c; --text: #ecebe6; --muted: #9c9b94; --line: #33332f;
  --accent: #6b9cf0; --problem: #ef6f62; --wish: #e7b13f; --joy: #5cc488; --topic: #9d90f0;
  --chip: #2a2a27;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--text);
  font: 15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }
main { max-width: 1200px; margin: 0 auto; padding: 24px 16px 64px; }
h1 { font-size: 24px; margin: 0 0 4px; }
.sub { color: var(--muted); margin: 0 0 20px; }
.note { background: var(--panel); border: 1px solid var(--line); border-left: 3px solid var(--wish);
  padding: 10px 14px; border-radius: 6px; color: var(--muted); font-size: 13px; margin-bottom: 20px; }
.controls { display: flex; flex-wrap: wrap; gap: 12px; align-items: center; margin-bottom: 16px; }
select, input { font: inherit; padding: 6px 10px; border-radius: 6px; border: 1px solid var(--line);
  background: var(--panel); color: var(--text); max-width: 100%; }
.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(150px, 100%), 1fr)); gap: 12px; margin-bottom: 20px; }
.stat { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 12px 14px; }
.stat b { display: block; font-size: 22px; font-variant-numeric: tabular-nums; }
.stat span { color: var(--muted); font-size: 13px; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(340px, 100%), 1fr)); gap: 16px; }
.panel { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 14px 16px; min-width: 0; }
.panel h2 { font-size: 16px; margin: 0 0 2px; display: flex; align-items: center; gap: 8px; }
.panel h2 i { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
.panel p.hint { color: var(--muted); font-size: 13px; margin: 0 0 10px; }
.row { border-top: 1px solid var(--line); padding: 8px 0; }
.row summary { cursor: pointer; list-style: none; display: grid; grid-template-columns: 1fr auto; gap: 4px 10px; }
.row summary::-webkit-details-marker { display: none; }
.theme { font-weight: 600; overflow-wrap: anywhere; }
.count { color: var(--muted); font-variant-numeric: tabular-nums; font-size: 13px; }
.bar { grid-column: 1 / -1; height: 4px; background: var(--chip); border-radius: 2px; overflow: hidden; }
.bar span { display: block; height: 100%; }
.ex { margin: 8px 0 0; padding: 0; list-style: none; }
.ex li { font-size: 13px; color: var(--muted); border-left: 2px solid var(--line); padding: 2px 0 2px 10px; margin: 6px 0; overflow-wrap: anywhere; }
.ex a { color: var(--accent); text-decoration: none; }
.chips { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 6px; }
.chip { background: var(--chip); border-radius: 10px; padding: 0 8px; font-size: 12px; color: var(--muted); }
.empty { color: var(--muted); font-size: 13px; padding: 8px 0; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
td, th { text-align: left; padding: 4px 6px; border-top: 1px solid var(--line); }
th { color: var(--muted); font-weight: 500; }
td.n { text-align: right; font-variant-numeric: tabular-nums; }
.seglist { cursor: pointer; }
.seglist tr:hover td { background: var(--chip); }
</style>
</head>
<body>
<main>
  <h1>Internet Parser Report</h1>
  <p class="sub" id="sub"></p>
  <div class="note">Segments are approximate. <b>audience:</b> comes from the community a post was in
    (r/Parenting means "parents' community", not proof the author is a parent). <b>age / gender / role / life:</b>
    only when authors said it about themselves. Counts come from a keyword analyser: use them to find
    leads, then read the quotes or run the LLM export before acting on them.</div>
  <div class="stats" id="stats"></div>
  <div class="controls">
    <label>Segment <select id="seg"></select></label>
    <input id="filter" type="search" placeholder="Filter themes...">
  </div>
  <div class="grid" id="grid"></div>
  <div class="panel" style="margin-top:16px">
    <h2>All segments</h2>
    <p class="hint">Click a row to open it.</p>
    <div style="overflow-x:auto"><table class="seglist"><thead><tr><th>Segment</th><th class="n">Posts</th><th class="n">Avg sentiment</th>
      <th class="n">Problems</th><th class="n">Wishes</th></tr></thead><tbody id="segtable"></tbody></table></div>
  </div>
</main>
<script>
const DATA = __DATA__;
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const fmt = (n) => Number(n).toLocaleString();
const PANELS = [
  ["problems", "Problems", "--problem", "Complaints and struggles, weighted by engagement and negativity."],
  ["wishes", "Wishes and requests", "--wish", "“I wish there was…”, “is there an app…”, “I'd pay for…”. The strongest product signal."],
  ["joys", "What makes people happy", "--joy", "Things people love, recommend or call a game changer."],
  ["topics", "Most talked about", "--topic", "Phrases in the most posts. For sub-segments, ranked by how much more this segment talks about it than everyone else."],
];

$("sub").textContent = `${fmt(DATA.totals.posts)} posts analysed · generated ${DATA.generated}`;
$("stats").innerHTML = [["Posts", DATA.totals.posts], ...Object.entries(DATA.totals.by_source)]
  .map(([k, v]) => `<div class="stat"><b>${fmt(v)}</b><span>${esc(k)}</span></div>`).join("");

const order = ["all", "audience", "age", "gender", "role", "life", "housing", "platform"];
const names = Object.keys(DATA.segments).sort((a, b) => {
  const da = order.indexOf(a.split(":")[0]), db = order.indexOf(b.split(":")[0]);
  return (da < 0 ? 99 : da) - (db < 0 ? 99 : db) || DATA.segments[b].posts - DATA.segments[a].posts;
});
const groups = {};
names.forEach(n => (groups[n.includes(":") ? n.split(":")[0] : "overall"] ??= []).push(n));
$("seg").innerHTML = Object.entries(groups).map(([g, ns]) =>
  `<optgroup label="${esc(g)}">${ns.map(n => `<option value="${esc(n)}">${esc(n === "all" ? "Everyone" : n.split(":").slice(1).join(":"))} (${fmt(DATA.segments[n].posts)})</option>`).join("")}</optgroup>`).join("");

$("segtable").innerHTML = names.map(n => {
  const s = DATA.segments[n];
  return `<tr data-seg="${esc(n)}"><td>${esc(n)}</td><td class="n">${fmt(s.posts)}</td><td class="n">${s.avg_sentiment.toFixed(2)}</td>
    <td class="n">${s.problems.length}</td><td class="n">${s.wishes.length}</td></tr>`;
}).join("");
$("segtable").addEventListener("click", e => {
  const tr = e.target.closest("tr"); if (!tr) return;
  $("seg").value = tr.dataset.seg; render(); window.scrollTo({top: 0, behavior: "smooth"});
});

function themeRow(t, max, color) {
  const ex = (t.examples || []).map(e =>
    `<li>“${esc(e.quote)}” ${e.url ? `<a href="${esc(e.url)}" target="_blank" rel="noopener">${esc(e.source)} ↗</a>` : esc(e.source)}</li>`).join("");
  const chips = Object.entries(t.sources || {}).map(([s, n]) => `<span class="chip">${esc(s)} ${n}</span>`).join("");
  return `<details class="row"><summary><span class="theme">${esc(t.theme)}</span>
    <span class="count">${fmt(t.mentions)} posts</span>
    <span class="bar"><span style="width:${(100 * t.score / max).toFixed(1)}%;background:var(${color})"></span></span></summary>
    <div class="chips">${chips}</div><ul class="ex">${ex}</ul></details>`;
}
function topicRow(t, max, color) {
  return `<div class="row"><div style="display:grid;grid-template-columns:1fr auto;gap:4px 10px">
    <span class="theme">${esc(t.topic)}</span><span class="count">${fmt(t.posts)} posts${t.lift && t.lift !== 1 ? ` · ${t.lift}×` : ""}</span>
    <span class="bar"><span style="width:${(100 * t.posts / max).toFixed(1)}%;background:var(${color})"></span></span></div></div>`;
}
function render() {
  const seg = DATA.segments[$("seg").value];
  const q = $("filter").value.trim().toLowerCase();
  $("grid").innerHTML = PANELS.map(([key, title, color, hint]) => {
    let items = seg[key] || [];
    if (q) items = items.filter(t => (t.theme || t.topic).includes(q) ||
      (t.examples || []).some(e => e.quote.toLowerCase().includes(q)));
    const max = Math.max(1, ...items.map(t => key === "topics" ? t.posts : t.score));
    const body = items.length ? items.map(t => key === "topics" ? topicRow(t, max, color) : themeRow(t, max, color)).join("")
      : `<div class="empty">Nothing here yet for this segment. Collect more data or lower min_mentions.</div>`;
    return `<section class="panel"><h2><i style="background:var(${color})"></i>${title}</h2><p class="hint">${hint}</p>${body}</section>`;
  }).join("");
}
$("seg").addEventListener("change", render);
$("filter").addEventListener("input", render);
render();
</script>
</body>
</html>
"""


def write_report(agg: dict, path: Path) -> Path:
    data = dict(agg)
    data["generated"] = datetime.fromtimestamp(agg["generated_at"]).strftime("%Y-%m-%d %H:%M")
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(TEMPLATE.replace("__DATA__", payload), encoding="utf-8")
    return path
