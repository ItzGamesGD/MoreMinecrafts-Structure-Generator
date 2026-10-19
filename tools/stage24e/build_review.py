"""Offline, phone-friendly comparison page + PROPOSALS.md + ZIP for the Stage 24-E roof/massing alternatives."""
from __future__ import annotations

import hashlib
import html
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24d.lib import TITLES  # noqa: E402
from tools.stage24e.render_options import VIEWS, D24E, SCALE  # noqa: E402

REV = D24E / "review"
HOUSES = ["large_ruin_1", "medium_ruin_1", "medium_ruin_2", "small_ruin_1", "small_ruin_2"]
INTENT = {
    "large_ruin_1": "Most substantial redesign requested: taller body, pronounced rising roof, courtyard kept.",
    "medium_ruin_1": "Roof read as a flat slab; wants depth, layering, character (no pointed roof required).",
    "medium_ruin_2": "Upper floor works; the two masses should read as one intentional design, not a box on a box.",
    "small_ruin_1": "More carefully composed roof, proportionate to the small footprint.",
    "small_ruin_2": "More carefully composed roof; keep it compact and avoid crowding the 6×2 interior.",
}


def load(name, default=None):
    p = D24E / name
    return json.loads(p.read_text()) if p.exists() else default


def fig(src, cap):
    return f'<figure><a href="#" data-full="{src}"><img loading="lazy" src="{src}" alt="{html.escape(cap)}"></a><figcaption>{html.escape(cap)}</figcaption></figure>'


def build():
    static = load("static-checks.json", {})
    live = load("live-summary.json", {})
    wg = load("worldgen-compat.json", {})
    secs, md_rows = [], []
    for m in HOUSES:
        opts = [k for k in static.get(m, {}) if k != "current"]
        cards = []
        for k in ["current"] + opts:
            r = static[m][k]
            dims = "×".join(map(str, r["dimensions"]))
            auth = r.get("requires_authorisation")
            title = "Current — Stage 24-C final (unchanged)" if k == "current" else f"Option {k} — {r['title']}"
            lv = live.get(m, {}).get(k)
            lv_txt = "n/a (baseline, see Stage 24-C)" if k == "current" else (f"{lv['ok']}/{lv['total']} simulated-player steps, placement mismatches {lv['placement_mismatches']}" if lv else "LIVE PENDING")
            w = wg.get(m, {}).get(k)
            w_txt = "" if not auth else (f"Generation test: {w['summary']}" if w else "Generation test: PENDING")
            badges = ('<span class="b warn">LARGER NBT — needs owner authorisation</span>' if auth else '<span class="b ok">within Stage 24-C bounds</span>') if k != "current" else '<span class="b base">baseline</span>'
            imgs = "".join(fig(f"assets/{m}/{k}-{vn}.jpg", f"{title.split(' — ')[0]} · {lab}") for vn, (lab, *_r) in VIEWS.items())
            cards.append(f'''<div class="card" id="{m}-{k}"><h3>{html.escape(title)}</h3><div class="badges">{badges}<span class="b">{dims}</span></div>
<ul class="small"><li>Static functional checks: {"PASS" if r["static_pass"] else "FAIL " + ", ".join(r.get("failed_checks", []))} — walkable cells {r["walkable_cells"]}/{r["baseline_walkable_cells"]}</li>
<li>Live (real 26.1.2 server): {html.escape(lv_txt)}</li>{f"<li>{html.escape(w_txt)}</li>" if w_txt else ""}
{"".join(f"<li>{html.escape(n)}</li>" for n in r.get("notes", []))}</ul><div class="grid">{imgs}</div></div>''')
            if k != "current":
                md_rows.append(f"| {m} | {k} | {html.escape(r['title'])} | {dims} | {'**yes**' if auth else 'no'} | {'PASS' if r['static_pass'] else 'FAIL'} | {lv_txt} | [front](review/assets/{m}/{k}-front34.jpg) · [street](review/assets/{m}/{k}-street.jpg) · [cutaway](review/assets/{m}/{k}-section.jpg) |")
        sheets = "".join(fig(f"assets/{m}/compare-{vn}.jpg", f"All options · {lab}") for vn, (lab, *_r) in VIEWS.items())
        choices = "".join(f'<label><input type="radio" name="d-{m}" value="{k}"> {"Keep current" if k == "current" else "Option " + k}</label>' for k in ["current"] + opts)
        secs.append(f'''<section id="{m}"><h2>{html.escape(TITLES[m])}</h2><p class="small">{html.escape(INTENT[m])} Same camera and scale ({SCALE[m]} px/block) for every option.</p>
<h3>Side-by-side</h3><div class="grid wide">{sheets}</div>{"".join(cards)}
<div class="decide" data-module="{m}"><h3>Owner preference (not a final selection by the designer)</h3><label><input type="radio" name="d-{m}" value="pending" checked> Pending</label>{choices}
<label><input type="radio" name="d-{m}" value="rework"> None — rework</label><textarea placeholder="Notes, e.g. combine A's eaves with B's gable…"></textarea></div></section>''')
    nav = "".join(f'<a href="#{m}">{html.escape(TITLES[m].split(" — ")[0])}</a>' for m in HOUSES)
    page = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Ancient City houses — roof alternatives</title><style>
:root{{--bg:#12151a;--fg:#e8ecf1;--mut:#9aa6b4;--card:#1b2027;--ln:#2c343e;--ok:#2f8f5b;--warn:#b7791f;--ac:#6cb6ff}}
@media (prefers-color-scheme:light){{:root{{--bg:#f4f6f9;--fg:#1a2028;--mut:#5b6877;--card:#fff;--ln:#d6dde6}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 -apple-system,system-ui,"Segoe UI",sans-serif;padding:0 16px 80px}}
header{{padding:20px 0 8px}}h1{{font-size:1.45rem;margin:0 0 4px}}h2{{font-size:1.3rem;margin:30px 0 4px}}h3{{font-size:1rem;margin:16px 0 6px}}
nav{{position:sticky;top:0;z-index:5;background:var(--bg);display:flex;gap:8px;overflow-x:auto;padding:8px 0;border-bottom:1px solid var(--ln)}}
nav a{{flex:none;padding:8px 12px;border:1px solid var(--ln);border-radius:999px;color:var(--fg);text-decoration:none;font-size:.85rem;background:var(--card)}}
.notice{{background:var(--card);border:1px solid var(--ln);border-left:4px solid var(--warn);padding:10px 12px;border-radius:8px;margin:12px 0;font-size:.9rem}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:10px}}.grid.wide{{grid-template-columns:1fr}}
figure{{margin:0;background:var(--card);border:1px solid var(--ln);border-radius:10px;overflow:hidden}}figure img{{display:block;width:100%;height:auto}}figcaption{{padding:5px 9px;font-size:.75rem;color:var(--mut)}}
.card{{background:var(--card);border:1px solid var(--ln);border-radius:12px;padding:10px 12px;margin:14px 0}}.small{{font-size:.85rem;color:var(--mut)}}
.badges{{display:flex;flex-wrap:wrap;gap:6px}}.b{{font-size:.72rem;padding:3px 8px;border-radius:6px;background:#3a4350;color:#fff}}.b.ok{{background:var(--ok)}}.b.warn{{background:var(--warn)}}.b.base{{background:#55606e}}
section{{border-top:1px solid var(--ln);scroll-margin-top:56px}}.decide{{background:var(--card);border:1px solid var(--ln);border-radius:10px;padding:12px;margin:16px 0}}
.decide label{{display:inline-block;margin:4px 12px 4px 0}}textarea{{width:100%;margin-top:8px;padding:10px;font:inherit;background:var(--bg);color:var(--fg);border:1px solid var(--ln);border-radius:8px;min-height:80px}}
button{{font:inherit;padding:12px 16px;border-radius:10px;border:1px solid var(--ln);background:var(--ac);color:#06121f;font-weight:600;margin:6px 8px 6px 0}}
#lb{{position:fixed;inset:0;background:rgba(0,0,0,.92);display:none;z-index:20;overflow:auto}}#lb img{{display:block;width:max(100vw,1000px);margin:0 auto}}
</style></head><body><header><h1>Ancient City houses — roof &amp; massing alternatives</h1>
<div class="small">Stage 24-E · alternatives for owner comparison · no option is selected · watchtowers and sauna untouched</div></header>
<nav>{nav}<a href="#export">Export</a></nav>
<div class="notice">Renders use the real Minecraft 26.1.2 block models and textures from the actual proposal NBTs, with flat studio lighting — <b>not</b> in-game screenshots. Options marked <b>LARGER NBT</b> raise the structure height and need your authorisation before any implementation; all proposals are separate files, the Stage 24-C candidates are unchanged, so every option is reversible.</div>
{"".join(secs)}
<section id="export"><h2>Export your preferences</h2><div class="notice">Stored only in this browser; nothing is sent to GitHub.</div>
<button id="bj">Download JSON</button><button id="bc">Copy as text</button><pre id="out" class="small" style="white-space:pre-wrap"></pre></section>
<div id="lb"><img alt=""></div>
<script>(function(){{var K="stage24e-prefs-v1",st={{}};try{{st=JSON.parse(localStorage.getItem(K)||"{{}}")}}catch(e){{}}
function save(){{try{{localStorage.setItem(K,JSON.stringify(st))}}catch(e){{}}out()}}
document.querySelectorAll(".decide").forEach(function(b){{var m=b.dataset.module,s=st[m]||{{}};b.querySelectorAll("input").forEach(function(r){{if(s.choice===r.value)r.checked=true;r.onchange=function(){{(st[m]=st[m]||{{}}).choice=r.value;save()}}}});var t=b.querySelector("textarea");t.value=s.note||"";t.oninput=function(){{(st[m]=st[m]||{{}}).note=t.value;save()}}}});
function data(){{var o={{stage:"24-E",exported_at:new Date().toISOString(),note:"Local export; not synced to GitHub. A choice is a preference, not an implementation authorisation.",houses:{{}}}};{json.dumps(HOUSES)}.forEach(function(m){{var s=st[m]||{{}};o.houses[m]={{choice:s.choice||"pending",note:s.note||""}}}});return o}}
function text(){{var o=data(),l=["Stage 24-E roof preferences ("+o.exported_at+")"];for(var m in o.houses)l.push(m+": "+o.houses[m].choice+(o.houses[m].note?" — "+o.houses[m].note:""));return l.join("\\n")}}
function out(){{document.getElementById("out").textContent=text()}}
document.getElementById("bj").onclick=function(){{var a=document.createElement("a");a.href=URL.createObjectURL(new Blob([JSON.stringify(data(),null,2)],{{type:"application/json"}}));a.download="stage24e-roof-preferences.json";a.click()}};
document.getElementById("bc").onclick=function(){{var t=text();if(navigator.clipboard)navigator.clipboard.writeText(t).then(function(){{alert("Copied")}},function(){{prompt("Copy:",t)}});else prompt("Copy:",t)}};
var lb=document.getElementById("lb"),li=lb.querySelector("img");document.querySelectorAll("a[data-full]").forEach(function(a){{a.onclick=function(e){{e.preventDefault();li.src=a.dataset.full;lb.style.display="block"}}}});lb.onclick=function(){{lb.style.display="none"}};out()}})();</script></body></html>'''
    (REV / "index.html").write_text(page, encoding="utf8")
    hashes = {}
    for p in sorted((D24E / "proposals").rglob("candidate.nbt")):
        hashes[str(p.relative_to(D24E))] = hashlib.sha256(p.read_bytes()).hexdigest()
    (D24E / "PROPOSALS.md").write_text(f"""# Stage 24-E — residential roof and massing alternatives (owner comparison)

Open `review/index.html` (offline) or the ZIP `stage-24e-roof-alternatives.zip`. No option has been selected; the Stage 24-C candidates in
`../stage-24b/*/restored.nbt` are unchanged, and every proposal is a separate file under `proposals/<module>/<option>/candidate.nbt` (fully reversible).

| House | Option | Concept | Size (x×y×z) | Larger NBT (needs authorisation) | Static checks | Live server test | Images |
|---|---|---|---|---|---|---|---|
{chr(10).join(md_rows)}

Proposal SHA-256: {json.dumps(hashes, indent=1)}
""")
    zp = D24E / "stage-24e-roof-alternatives.zip"
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_STORED) as z:
        for p in sorted(REV.rglob("*")):
            if p.is_file():
                z.write(p, "stage-24e-review/" + str(p.relative_to(REV)))
        z.write(D24E / "PROPOSALS.md", "stage-24e-review/PROPOSALS.md")
    print("zip", round(zp.stat().st_size / 1e6, 1), "MB", "images", len(list(REV.rglob("*.jpg"))))


if __name__ == "__main__":
    build()
