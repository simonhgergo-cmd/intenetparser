"""HTML of the local control panel (Hungarian UI)."""

PAGE = r"""<!doctype html>
<html lang="hu">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Internet Parser</title>
<style>
:root {
  --bg: #f7f7f5; --panel: #ffffff; --text: #1d1d1b; --muted: #6b6b66; --line: #e4e4df;
  --accent: #2f6fde; --accent-text: #ffffff; --ok: #2f9e5b; --warn: #c98a12; --bad: #d4483b; --chip: #efefea;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #141413; --panel: #1e1e1c; --text: #ecebe6; --muted: #9c9b94; --line: #33332f;
    --accent: #6b9cf0; --accent-text: #0f1720; --ok: #5cc488; --warn: #e7b13f; --bad: #ef6f62; --chip: #2a2a27;
  }
}
:root[data-theme="dark"] {
  --bg: #141413; --panel: #1e1e1c; --text: #ecebe6; --muted: #9c9b94; --line: #33332f;
  --accent: #6b9cf0; --accent-text: #0f1720; --ok: #5cc488; --warn: #e7b13f; --bad: #ef6f62; --chip: #2a2a27;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--text); font: 15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }
main { max-width: 980px; margin: 0 auto; padding: 20px 16px 64px; }
header { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; margin-bottom: 16px; }
h1 { font-size: 22px; margin: 0; }
h2 { font-size: 16px; margin: 0 0 10px; }
h3 { font-size: 14px; margin: 14px 0 6px; color: var(--muted); font-weight: 600; }
.pill { padding: 3px 12px; border-radius: 999px; font-size: 13px; background: var(--chip); color: var(--muted); }
.pill.run { background: color-mix(in srgb, var(--accent) 18%, transparent); color: var(--accent); }
.pill.err { background: color-mix(in srgb, var(--bad) 18%, transparent); color: var(--bad); }
nav { display: flex; gap: 4px; border-bottom: 1px solid var(--line); margin-bottom: 16px; overflow-x: auto; }
nav button { background: none; border: none; border-bottom: 2px solid transparent; padding: 8px 12px; font: inherit; color: var(--muted); cursor: pointer; white-space: nowrap; }
nav button.active { color: var(--text); border-bottom-color: var(--accent); font-weight: 600; }
.panel { background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 16px; margin-bottom: 16px; }
.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(150px, 100%), 1fr)); gap: 12px; margin-bottom: 16px; }
.stat { background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 12px 14px; }
.stat b { display: block; font-size: 22px; font-variant-numeric: tabular-nums; }
.stat span { color: var(--muted); font-size: 13px; }
.actions { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
button.btn, a.btn { font: inherit; padding: 8px 14px; border-radius: 8px; border: 1px solid var(--line); background: var(--panel); color: var(--text); cursor: pointer; text-decoration: none; display: inline-block; }
button.btn.primary { background: var(--accent); border-color: var(--accent); color: var(--accent-text); font-weight: 600; }
button.btn:disabled { opacity: .5; cursor: default; }
button.btn.small, a.btn.small { padding: 4px 10px; font-size: 13px; }
.msg { margin-top: 10px; font-size: 14px; color: var(--muted); }
.msg.err { color: var(--bad); } .msg.ok { color: var(--ok); }
.note { color: var(--muted); font-size: 13px; margin: 0 0 10px; }
pre.log { background: var(--bg); border: 1px solid var(--line); border-radius: 8px; padding: 10px; height: 260px; overflow: auto; font-size: 12px; margin: 0; white-space: pre-wrap; overflow-wrap: anywhere; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
td, th { text-align: left; padding: 6px; border-top: 1px solid var(--line); }
th { color: var(--muted); font-weight: 500; font-size: 13px; }
td.n { text-align: right; font-variant-numeric: tabular-nums; }
.tablewrap { overflow-x: auto; }
.checks { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(220px, 100%), 1fr)); gap: 2px 12px; }
label.check { display: flex; gap: 8px; align-items: flex-start; padding: 3px 0; cursor: pointer; }
label.check input { margin-top: 4px; }
.sens { color: var(--warn); font-size: 12px; }
.row { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; margin: 6px 0; }
input[type=text], input[type=password], input[type=number], select { font: inherit; padding: 6px 10px; border-radius: 6px; border: 1px solid var(--line); background: var(--panel); color: var(--text); max-width: 100%; }
.banner { border-left: 3px solid var(--warn); }
.hidden { display: none !important; }
footer { margin-top: 24px; display: flex; justify-content: flex-end; }
</style>
</head>
<body>
<main>
  <header>
    <h1>Internet Parser</h1>
    <span class="pill" id="pill">Betöltés…</span>
  </header>
  <nav>
    <button data-tab="overview" class="active">Áttekintés</button>
    <button data-tab="settings">Beállítások</button>
    <button data-tab="claude">Claude-hoz</button>
  </nav>

  <section id="tab-overview">
    <div class="panel banner hidden" id="firstrun">
      <b>Üdv!</b> Először nézd át a <a href="#" data-goto="settings">Beállításokat</a> (melyik csoportokat figyelje),
      aztán kattints a <b>Gyűjtés most</b> gombra.
    </div>
    <div class="stats">
      <div class="stat"><b id="s-posts">–</b><span>begyűjtött poszt és komment</span></div>
      <div class="stat"><b id="s-analyzed">–</b><span>elemezve</span></div>
      <div class="stat"><b id="s-db">–</b><span>adatbázis mérete</span></div>
      <div class="stat"><b id="s-last">–</b><span>utolsó befejezett futás</span></div>
    </div>
    <div class="panel">
      <div class="actions">
        <button class="btn primary" id="run-once">Gyűjtés most</button>
        <button class="btn" id="run-loop">Folyamatos gyűjtés</button>
        <button class="btn hidden" id="stop">Folyamatos gyűjtés leállítása</button>
        <a class="btn" id="open-report" href="/report" target="_blank" rel="noopener">Riport megnyitása ↗</a>
      </div>
      <p class="msg" id="run-msg"></p>
      <p class="note">A gyűjtés alatt a gépnek ébren kell maradnia. A folyamatos gyűjtés addig fut, amíg ez az oldal
        mögötti program fut (a fekete ablak).</p>
    </div>
    <div class="panel">
      <h2>Mit csinál most</h2>
      <pre class="log" id="log">Még nem futott.</pre>
    </div>
    <div class="panel">
      <h2>Források</h2>
      <div class="tablewrap"><table><thead><tr><th>Forrás</th><th class="n">Begyűjtve</th></tr></thead><tbody id="sources"></tbody></table></div>
    </div>
    <div class="panel">
      <h2>Becslés egy futásra</h2>
      <p class="note">A kérések száma és a forrásonkénti korlátok alapján. A források egyszerre futnak, a teljes idő a leglassabbé.</p>
      <div class="tablewrap"><table><thead><tr><th>Forrás</th><th class="n">~poszt</th><th class="n">~perc</th><th>Megjegyzés</th></tr></thead><tbody id="plan"></tbody></table></div>
    </div>
  </section>

  <section id="tab-settings" class="hidden">
    <div class="panel">
      <h2>Kiket figyeljen?</h2>
      <p class="note">Minden csoporthoz tartoznak közösségek (subredditek, Stack Exchange oldalak, hashtagek, app-kategóriák).
        Minél több csoport, annál tovább tart egy futás.</p>
      <div id="groups"></div>
      <label class="check" style="margin-top:10px"><input type="checkbox" id="sensitive">
        <span>Érzékeny közösségek is (egészség, fogyatékosság, LGBTQ+). Csak közösségi szinten címkézi, egyénekről nem következtet.</span></label>
    </div>
    <div class="panel">
      <h2>Források</h2>
      <div class="checks" id="sourcechecks"></div>
    </div>
    <div class="panel">
      <h2>Reddit</h2>
      <label class="check"><input type="radio" name="rmode" value="auto"><span><b>Automatikus</b> (ajánlott): archívum, vagy közvetlenül a Reddit, ha van jóváhagyott appod</span></label>
      <label class="check"><input type="radio" name="rmode" value="archive"><span><b>Archívum</b> (Arctic Shift): gyors, de néhány óra késés lehet</span></label>
      <label class="check"><input type="radio" name="rmode" value="official"><span><b>Közvetlenül a Reddit</b>: teljesen friss, app nélkül lassú (~1 óra)</span></label>
      <h3>Jóváhagyott Reddit app (nem kötelező)</h3>
      <div class="row">
        <input type="text" id="rid" placeholder="client ID" autocomplete="off">
        <input type="password" id="rsecret" placeholder="secret" autocomplete="off">
      </div>
    </div>
    <div class="panel">
      <h2>Ütemezés és tárhely</h2>
      <div class="row"><label for="every">Folyamatos gyűjtésnél ilyen gyakran:</label>
        <select id="every"><option value="6h">6 óránként</option><option value="12h">12 óránként</option><option value="1d">naponta</option></select></div>
      <div class="row"><label for="keep">Ennél régebbi posztok törlése (nap, 0 = soha):</label>
        <input type="number" id="keep" min="0" step="1" style="width:90px"></div>
      <p class="note">Kb. 1 KB posztonként. 12 óránkénti gyűjtésnél kb. 70 MB naponta.</p>
    </div>
    <div class="panel">
      <h2>Opcionális fiókok</h2>
      <div class="row"><input type="text" id="bsky" placeholder="Bluesky felhasználó (pl. nev.bsky.social)">
        <input type="password" id="bskypw" placeholder="Bluesky app jelszó"></div>
      <div class="row"><input type="password" id="ytkey" placeholder="YouTube API kulcs (ingyenes)" style="min-width:260px"></div>
      <p class="note">Az üresen hagyott jelszó- és kulcsmezők nem írják felül a már elmentett értéket.</p>
    </div>
    <div class="actions"><button class="btn primary" id="save">Mentés</button><span class="msg" id="save-msg"></span></div>
  </section>

  <section id="tab-claude" class="hidden">
    <div class="panel">
      <h2>Fájlok Claude-hoz</h2>
      <p class="note">Minden gyűjtés után frissülnek. Először a <b>summary.md</b>-t másold be Claude-ba: összevonja a problémákat
        és rangsorolt termékötleteket ad. A <b>pack_…</b> fájlok a posztokat tartalmazzák adagokban, részletes elemzéshez.</p>
      <div class="tablewrap"><table><tbody id="exports"><tr><td>Még nincs fájl. Indíts egy gyűjtést.</td></tr></tbody></table></div>
      <p class="msg" id="copy-msg"></p>
    </div>
  </section>

  <footer><button class="btn small" id="shutdown">Program leállítása</button></footer>
</main>
<script>
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const fmt = (n) => Number(n || 0).toLocaleString("hu-HU");
const time = (t) => t ? new Date(t * 1000).toLocaleString("hu-HU", {month: "short", day: "numeric", hour: "2-digit", minute: "2-digit"}) : "–";
const api = (path, body) => fetch(path, body === undefined ? {} : {
  method: "POST", headers: {"Content-Type": "application/json", "X-IParse": "1"}, body: JSON.stringify(body)
}).then(r => r.json());
const SOURCE_LABELS = {
  reddit: "Reddit", hackernews: "Hacker News", bluesky: "Bluesky (X helyett)", mastodon: "Mastodon",
  stackexchange: "Stack Exchange", appstore: "App Store értékelések", youtube: "YouTube kommentek (API kulcs kell)",
  tiktok: "TikTok (kísérleti, külön telepítés kell)", import: "Saját fájlok importálása",
};
const DIMS = {audience: "Kik ők", interest: "Mi érdekli őket", region: "Hol élnek"};

// tabs
function show(tab) {
  document.querySelectorAll("nav button").forEach(b => b.classList.toggle("active", b.dataset.tab === tab));
  ["overview", "settings", "claude"].forEach(t => $("tab-" + t).classList.toggle("hidden", t !== tab));
  if (tab === "settings") loadSettings();
  if (tab === "claude") loadExports();
}
document.querySelectorAll("nav button").forEach(b => b.onclick = () => show(b.dataset.tab));
document.querySelectorAll("[data-goto]").forEach(a => a.onclick = (e) => { e.preventDefault(); show(a.dataset.goto); });

// status
let wasRunning = false;
async function refresh() {
  let s;
  try { s = await api("/api/status"); } catch { $("pill").textContent = "A program nem fut"; $("pill").className = "pill err"; return; }
  $("s-posts").textContent = fmt(s.posts);
  $("s-analyzed").textContent = fmt(s.analyzed);
  $("s-db").textContent = s.db_mb + " MB";
  $("s-last").textContent = time(s.last_run || s.report_time);
  $("firstrun").classList.toggle("hidden", !s.first_run);
  const pill = $("pill");
  if (s.running && !s.next_run) { pill.textContent = "Gyűjtés folyamatban…"; pill.className = "pill run"; }
  else if (s.running && s.next_run) { pill.textContent = "Következő futás: " + time(s.next_run); pill.className = "pill run"; }
  else if (s.last_error) { pill.textContent = "Hiba az utolsó futásnál"; pill.className = "pill err"; }
  else { pill.textContent = "Készenlétben"; pill.className = "pill"; }
  $("run-once").disabled = !!s.running;
  $("run-loop").disabled = !!s.running;
  $("stop").classList.toggle("hidden", s.running !== "loop");
  $("stop").disabled = s.stopping;
  $("stop").textContent = s.stopping ? "Leáll a mostani futás után…" : "Folyamatos gyűjtés leállítása";
  $("open-report").classList.toggle("hidden", !s.report);
  $("run-msg").className = "msg" + (s.last_error ? " err" : "");
  $("run-msg").textContent = s.last_error ? "Hiba: " + s.last_error : "";
  const log = $("log"), atBottom = log.scrollTop + log.clientHeight >= log.scrollHeight - 20;
  if (s.log.length) log.textContent = s.log.join("\n");
  if (atBottom) log.scrollTop = log.scrollHeight;
  $("sources").innerHTML = Object.entries(s.by_source).sort((a, b) => b[1] - a[1])
    .map(([k, v]) => `<tr><td>${esc(SOURCE_LABELS[k] || k)}</td><td class="n">${fmt(v)}</td></tr>`).join("")
    || `<tr><td colspan="2">Még semmi.</td></tr>`;
  if (wasRunning && !s.running && !s.last_error && s.report) {
    $("run-msg").className = "msg ok";
    $("run-msg").innerHTML = 'Kész! <a href="/report" target="_blank" rel="noopener">Riport megnyitása ↗</a>';
  }
  wasRunning = !!s.running;
}
async function loadPlan() {
  const rows = await api("/api/plan");
  $("plan").innerHTML = rows.map(r => `<tr><td>${esc(SOURCE_LABELS[r.source] || r.source)}</td><td class="n">${fmt(r.items)}</td>
    <td class="n">${Math.max(1, Math.round(r.minutes))}</td><td>${esc(r.note)}</td></tr>`).join("")
    + (rows.length ? `<tr><th>Összesen</th><th class="n">${fmt(rows.reduce((a, r) => a + r.items, 0))}</th>
      <th class="n">${Math.max(1, Math.round(Math.max(...rows.map(r => r.minutes))))}</th><th></th></tr>` : "");
}
$("run-once").onclick = async () => { await api("/api/run", {loop: false}); refresh(); };
$("run-loop").onclick = async () => { await api("/api/run", {loop: true}); refresh(); };
$("stop").onclick = async () => { await api("/api/stop", {}); refresh(); };
$("shutdown").onclick = async () => {
  if (!confirm("Leállítod a programot? Egy futó gyűjtés megszakad.")) return;
  await api("/api/shutdown", {});
  document.body.innerHTML = '<main><h1>A program leállt.</h1><p>Újraindításhoz kattints duplán a start fájlra.</p></main>';
};

// settings
async function loadSettings() {
  const s = await api("/api/settings");
  $("groups").innerHTML = Object.entries(s.groups).map(([dim, groups]) => `
    <h3>${DIMS[dim]} <button class="btn small" data-all="${dim}">mind</button> <button class="btn small" data-none="${dim}">egyik sem</button></h3>
    <div class="checks">${groups.map(g => `<label class="check ${g.sensitive ? "sensitive-group" : ""}" ${g.sensitive && !s.include_sensitive ? 'style="display:none"' : ""}>
      <input type="checkbox" data-group="${esc(g.name)}" data-dim="${dim}" ${g.selected ? "checked" : ""}>
      <span>${esc(g.name)}${g.sensitive ? ' <span class="sens">érzékeny</span>' : ""}</span></label>`).join("")}</div>`).join("");
  document.querySelectorAll("[data-all]").forEach(b => b.onclick = () => setDim(b.dataset.all, true));
  document.querySelectorAll("[data-none]").forEach(b => b.onclick = () => setDim(b.dataset.none, false));
  $("sensitive").checked = s.include_sensitive;
  toggleSensitive();
  $("sourcechecks").innerHTML = Object.entries(s.sources).filter(([k]) => k !== "import").map(([k, on]) =>
    `<label class="check"><input type="checkbox" data-source="${k}" ${on ? "checked" : ""}><span>${esc(SOURCE_LABELS[k] || k)}</span></label>`).join("");
  document.querySelectorAll('input[name=rmode]').forEach(r => r.checked = r.value === s.reddit_mode);
  $("rid").value = s.reddit_client_id || "";
  $("rsecret").placeholder = s.reddit_has_secret ? "secret (elmentve)" : "secret";
  $("every").value = ["6h", "12h", "1d"].includes(s.every) ? s.every : "12h";
  $("keep").value = s.keep_days;
  $("bsky").value = s.bluesky_handle || "";
  $("bskypw").placeholder = s.bluesky_has_password ? "Bluesky app jelszó (elmentve)" : "Bluesky app jelszó";
  $("ytkey").placeholder = s.youtube_has_key ? "YouTube API kulcs (elmentve)" : "YouTube API kulcs (ingyenes)";
}
function setDim(dim, on) {
  document.querySelectorAll(`input[data-dim="${dim}"]`).forEach(c => {
    if (c.closest("label").style.display !== "none") c.checked = on;
  });
}
function toggleSensitive() {
  const on = $("sensitive").checked;
  document.querySelectorAll(".sensitive-group").forEach(l => {
    l.style.display = on ? "" : "none";
    if (!on) l.querySelector("input").checked = false;
  });
}
$("sensitive").onchange = toggleSensitive;
$("save").onclick = async () => {
  const body = {
    groups: [...document.querySelectorAll("input[data-group]:checked")].map(c => c.dataset.group),
    include_sensitive: $("sensitive").checked,
    sources: Object.fromEntries([...document.querySelectorAll("input[data-source]")].map(c => [c.dataset.source, c.checked])),
    reddit_mode: (document.querySelector("input[name=rmode]:checked") || {}).value || "auto",
    reddit_client_id: $("rid").value, reddit_client_secret: $("rsecret").value,
    every: $("every").value, keep_days: Number($("keep").value || 0),
    bluesky_handle: $("bsky").value, bluesky_password: $("bskypw").value, youtube_key: $("ytkey").value,
  };
  $("save-msg").className = "msg"; $("save-msg").textContent = "Mentés…";
  const r = await api("/api/settings", body);
  $("save-msg").className = "msg " + (r.ok ? "ok" : "err");
  $("save-msg").textContent = r.ok ? r.message : r.error;
  if (r.ok) { $("rsecret").value = $("bskypw").value = $("ytkey").value = ""; loadSettings(); loadPlan(); }
};

// exports
async function loadExports() {
  const files = await api("/api/exports");
  if (!files.length) return;
  $("exports").innerHTML = files.map(f => `<tr><td>${esc(f.name)}</td><td class="n">${fmt(f.kb)} KB</td>
    <td style="text-align:right;white-space:nowrap"><button class="btn small" data-copy="${esc(f.name)}">Másolás</button>
    <a class="btn small" href="/exports/${encodeURIComponent(f.name)}" target="_blank" rel="noopener">Megnyitás</a></td></tr>`).join("");
  document.querySelectorAll("[data-copy]").forEach(b => b.onclick = async () => {
    const text = await fetch("/exports/" + encodeURIComponent(b.dataset.copy)).then(r => r.text());
    try { await navigator.clipboard.writeText(text); $("copy-msg").className = "msg ok";
      $("copy-msg").textContent = b.dataset.copy + " a vágólapra másolva. Illeszd be Claude-ba (Ctrl+V / Cmd+V)."; }
    catch { $("copy-msg").className = "msg err"; $("copy-msg").textContent = "Nem sikerült másolni: nyisd meg a fájlt, és másold ki kézzel."; }
  });
}

refresh(); loadPlan();
setInterval(refresh, 2000);
</script>
</body>
</html>
"""
