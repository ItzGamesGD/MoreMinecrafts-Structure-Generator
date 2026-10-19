"""Assemble the offline static gallery (index.html + assets), OWNER-REVIEW.md and the downloadable ZIP."""
from __future__ import annotations

import html
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.stage24d.lib import *  # noqa
from tools.stage24d.config import CFG
from tools.stage24d.content import DESIGN, LIMITS, STATUS, QUESTIONS

_ov = D24 / "content-overrides.json"
if _ov.exists():  # a later stage may describe its own final candidates without editing this module
    _o = json.loads(_ov.read_text())
    DESIGN = {**DESIGN, **_o.get("DESIGN", {})}
    LIMITS = {**LIMITS, **_o.get("LIMITS", {})}
    STATUS = _o.get("STATUS", STATUS)

G = D24 / "gallery"
AS = G / "assets"


def imgs(m, names):
    return [n for n in names if (AS / m / f"{n}.jpg").exists()]


def counts(m):
    b = blocks_of(load_nbt(S24B / m / "restored.nbt"))
    c = {}
    for st, _ in b.values():
        n = st.split("[")[0].replace("minecraft:", "")
        c[n] = c.get(n, 0) + 1
    return c


def fig(path, cap):
    return f'<figure><a href="#" data-full="{path}"><img loading="lazy" src="{path}" alt="{html.escape(cap)}"></a><figcaption>{html.escape(cap)}</figcaption></figure>'


def section(m, man, v5):
    """one building section; `man` follows the INPUT-MANIFEST.json schema"""
    c = CFG[m]
    mm = man["modules"][m]
    dims = "×".join(map(str, mm["final_dimensions_xyz"]))
    odims = "×".join(map(str, mm["original_dimensions_xyz"]))
    cnt = counts(m)
    facts = [f"Dimensions: <b>{dims}</b> (original {odims})"]
    for k, lab in (("gray_bed", "beds"), ("barrel", "barrels"), ("chest", "chests"), ("ladder", "ladders"), ("soul_lantern", "soul lanterns"), ("water", "water blocks"), ("spruce_door", "door blocks")):
        if cnt.get(k):
            facts.append(f"{cnt[k] // 2 if k == 'gray_bed' else cnt[k]} {lab}" if k == "gray_bed" else f"{cnt[k]} {lab}")
    facts.append(f"Jigsaws preserved: {mm['jigsaws']['final']}/{mm['jigsaws']['original']} (metadata identical)")
    facts.append(f"Block entities preserved: {mm['block_entities']['final']} (identical)")
    sr = mm["stage24c_repair"]
    kinds = "; ".join(f"{k} ×{v}" for k, v in list(sr["by_kind"].items())[:6]) or "none"
    ext = [("front", "Front exterior"), ("rear", "Rear exterior"), ("left", "Left exterior"), ("right", "Right exterior"), ("elevated", "Elevated three-quarter"), ("roof", "Roof view"), ("entrance", "Entrance close-up")]
    inn = [("interior-dollhouse", "Interior — roof removed"), ("interior-section", "Interior — vertical section")] + [(f"floor-{i}", f"Floor-by-floor {i}") for i in range(1, 9) if (AS / m / f"floor-{i}.jpg").exists()]
    cmpn = [("compare-a", "Original vs restored (front three-quarter)"), ("compare-b", "Original vs restored (rear three-quarter)")]
    cmpn += [(f"stage24c-vs-final-{v}", f"Stage 24-C candidate vs final ({lab})") for v, lab in
             (("front34", "front three-quarter"), ("rear34", "rear three-quarter"), ("street", "street elevation"), ("side", "side silhouette"))]
    deg = [("v5-degradation-a", "V5: pristine vs naturally generated (front)"), ("v5-degradation-b", "V5: pristine vs naturally generated (rear)")]
    sect = lambda title, lst: f'<h3>{title}</h3><div class="grid">' + "".join(fig(f"assets/{m}/{n}.jpg", f"{TITLES[m]} — {lab}") for n, lab in lst if (AS / m / f"{n}.jpg").exists()) + "</div>"
    v5t = v5[m]
    lost = ", ".join(v5t["lost_critical"]) or "none in this sampled piece"
    st = "".join(f'<span class="badge {"pend" if "PENDING" in s else "ok"}">{html.escape(s)}</span>' for s in STATUS)
    return f'''<section id="{m}"><h2>{html.escape(TITLES[m])}</h2>
<p class="mono">{m} · candidate sha256 {mm["candidate_sha256"][:16]}… · source blob {mm["source_blob_sha1"][:10]}…</p>
<div class="badges">{st}</div>
<div class="cols"><div><h3>Design characteristics</h3><ul>{"".join(f"<li>{html.escape(x)}</li>" for x in DESIGN[m])}</ul>
<h3>Facts</h3><ul>{"".join(f"<li>{x}</li>" for x in facts)}</ul></div>
<div><h3>Known defects / limitations</h3><ul>{"".join(f"<li>{html.escape(x)}</li>" for x in LIMITS[m])}</ul>
<h3>{html.escape(man.get("repair_label", "Stage 24-C repairs vs PR #10"))} ({sr["changed_cells_vs_pr10"]} cells)</h3><p class="small">{html.escape(kinds)}</p>
<h3>Vanilla degradation sample</h3><p class="small">Seed {v5t["seed"]}, rotation {v5t["rotation"]}: lost critical blocks: {html.escape(lost)}; {v5t["cracked"]} cracked substitutions; {v5t["sculk_overlay"]} sculk-overlaid blocks.</p></div></div>
{sect("Exterior", ext)}{sect("Interior and cutaways", inn)}{sect("Original versus restored", cmpn)}{sect("Vanilla degradation (V5)", deg)}
<div class="decide" data-module="{m}"><h3>Owner decision</h3>
<label><input type="radio" name="d-{m}" value="pending" checked> Pending</label>
<label><input type="radio" name="d-{m}" value="approve"> Approve</label>
<label><input type="radio" name="d-{m}" value="changes"> Request changes</label>
<label><input type="radio" name="d-{m}" value="discuss"> Needs discussion</label>
<textarea placeholder="Comments / design decisions for {html.escape(TITLES[m])}…"></textarea></div></section>'''


def build():
    man = json.loads((D24 / "INPUT-MANIFEST.json").read_text())
    v5 = json.loads((D24 / "v5-data.json").read_text())
    pdata = json.loads((D24 / "priority-data.json").read_text())
    prof = pdata["v1_roof_profiles"]
    prow = "".join(f"<tr><td>{k.replace('_', ' ')}</td><td>{v['levels']}</td><td>{v['max_top']}</td><td>{html.escape(json.dumps(v['heights']))}</td></tr>" for k, v in prof.items())
    pri = f'''<section id="priority"><h2>Priority design questions</h2>
<h3>V1 — Roof differentiation</h3><p>The four flat-roofed houses are visually close; <code>medium_ruin_2</code> adds a second roof level. The previously designed residential prototypes (chamber, tall ruin) use pitched or multi-level roofs. Nothing was redesigned.</p>
{fig("assets/priority/v1-roof-differentiation-threequarter.jpg", "V1 three-quarter comparison, identical scale")}{fig("assets/priority/v1-roof-differentiation-side-silhouette.jpg", "V1 side silhouettes, identical scale")}
<div class="tw"><table><tr><th>building</th><th>distinct roof heights</th><th>max height</th><th>top-block height → columns</th></tr>{prow}</table></div>
<h3>V2 — Partial second floor (medium_ruin_2)</h3>{fig("assets/priority/v2-medium-ruin-2-second-floor.jpg", "V2 exterior, stair section, roof-off and upper-level views")}
<h3>V3 — Watchtower silhouettes</h3>{fig("assets/priority/v3-watchtower-silhouettes.jpg", "V3 large vs medium watchtower at identical scale")}
<h3>V4 — Sauna reception opening at (11,2,33)</h3><p>Removed block: <code>{html.escape(pdata["v4_removed_block"])}</code> (outlined red).</p>{fig("assets/priority/v4-sauna-reception-opening.jpg", "V4 before and after from both sides, oblique and in plan")}
<h3>V5 — Vanilla degradation</h3><p>Each building section contains a pristine-vs-generated sheet from a real 26.1.2 Ancient City. Degradation was <b>not</b> removed; its treatment is an owner decision.</p>
<div class="decide" id="questions"><h3>Owner decisions on V1–V5</h3>{"".join(f'<div class="q" data-q="{k}"><b>{k} — {html.escape(t)}</b><select><option value="">Pending</option>{"".join(f"<option>{html.escape(o)}</option>" for o in opts)}</select><textarea placeholder="Notes for {k}…"></textarea></div>' for k, (t, opts) in QUESTIONS.items())}</div></section>'''
    secs = "".join(section(m, man, v5) for m in MODULES)
    nav = "".join(f'<a href="#{m}">{html.escape(TITLES[m].split(" — ")[0])}</a>' for m in MODULES)
    page = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{html.escape(man.get("gallery_title", "Ancient City restoration — visual review"))}</title><style>
:root{{--bg:#12151a;--fg:#e8ecf1;--mut:#9aa6b4;--card:#1b2027;--ln:#2c343e;--ok:#2f8f5b;--pend:#b7791f;--ac:#6cb6ff}}
@media (prefers-color-scheme:light){{:root{{--bg:#f4f6f9;--fg:#1a2028;--mut:#5b6877;--card:#fff;--ln:#d6dde6}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 -apple-system,system-ui,"Segoe UI",sans-serif;padding:0 16px 80px}}
header{{padding:20px 0 8px}}h1{{font-size:1.5rem;margin:0 0 4px}}h2{{font-size:1.3rem;margin:32px 0 6px}}h3{{font-size:1rem;margin:18px 0 6px;color:var(--mut);text-transform:uppercase;letter-spacing:.04em}}
nav{{position:sticky;top:0;z-index:5;background:var(--bg);display:flex;gap:8px;overflow-x:auto;padding:8px 0;border-bottom:1px solid var(--ln);-webkit-overflow-scrolling:touch}}
nav a{{flex:none;padding:8px 12px;border:1px solid var(--ln);border-radius:999px;color:var(--fg);text-decoration:none;font-size:.85rem;background:var(--card)}}
.notice{{background:var(--card);border:1px solid var(--ln);border-left:4px solid var(--pend);padding:10px 12px;border-radius:8px;margin:12px 0;font-size:.9rem}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px}}figure{{margin:0;background:var(--card);border:1px solid var(--ln);border-radius:10px;overflow:hidden}}
figure img{{display:block;width:100%;height:auto}}figcaption{{padding:6px 10px;font-size:.78rem;color:var(--mut)}}
.cols{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px 28px}}ul{{padding-left:20px;margin:6px 0}}li{{margin:3px 0}}
.badges{{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0}}.badge{{font-size:.72rem;padding:3px 8px;border-radius:6px;color:#fff;background:var(--ok)}}.badge.pend{{background:var(--pend)}}
.mono,code{{font-family:ui-monospace,Menlo,monospace;font-size:.78rem;color:var(--mut)}}.small{{font-size:.85rem;color:var(--mut)}}
section{{border-top:1px solid var(--ln);padding-top:6px;scroll-margin-top:56px}}.decide{{background:var(--card);border:1px solid var(--ln);border-radius:10px;padding:12px;margin:16px 0}}
.decide label{{display:inline-block;margin:4px 12px 4px 0;font-size:.95rem}}.decide input[type=radio]{{width:18px;height:18px;vertical-align:-3px}}
textarea,select{{width:100%;margin-top:8px;padding:10px;font:inherit;background:var(--bg);color:var(--fg);border:1px solid var(--ln);border-radius:8px}}textarea{{min-height:84px}}
.q{{margin:12px 0}}.tw{{overflow-x:auto}}table{{border-collapse:collapse;font-size:.82rem;min-width:520px}}td,th{{border:1px solid var(--ln);padding:4px 8px;text-align:left}}
button{{font:inherit;padding:12px 16px;border-radius:10px;border:1px solid var(--ln);background:var(--ac);color:#06121f;font-weight:600;margin:6px 8px 6px 0}}
#lb{{position:fixed;inset:0;background:rgba(0,0,0,.92);display:none;z-index:20;overflow:auto;-webkit-overflow-scrolling:touch}}#lb img{{display:block;max-width:none;width:max(100vw,900px);margin:0 auto}}#lb b{{position:fixed;right:12px;top:8px;color:#fff;font-size:2rem;z-index:21}}
</style></head><body>
<header><h1>{html.escape(man.get("gallery_title", "Ancient City restoration — visual review gallery"))}</h1>
<div class="small">{html.escape(man.get("gallery_subtitle", "Stage 24-D · Minecraft Java 26.1.2 · Stage 24-C final candidates (PR #16 head " + man["stage_24c_head"][:10] + ")"))} · all eight: <b>OWNER REVIEW PENDING</b></div></header>
<nav><a href="#priority">V1–V5</a>{nav}<a href="#export">Export</a></nav>
<div class="notice"><b>How these images were made.</b> Every image is rendered from the actual restored NBT block states with the vanilla 26.1.2 client's block models and textures (stairs, slabs, walls, doors, beds, lanterns, water, glass and orientation are real). Lighting is flat studio shading — <b>not</b> in-game lighting — and beds/chests/skulls are rebuilt from entity textures. These are <b>not Minecraft-client screenshots</b>. The blocky figure beside entrances is a 1.8-block scale reference. Tap an image to enlarge.</div>
{pri}{secs}
<section id="export"><h2>Your decisions</h2><div class="notice">Selections are stored only in this browser. Nothing is sent to GitHub — export them and paste the text into the PR or send the JSON file.</div>
<button id="bj">Download decisions (JSON)</button><button id="bc">Copy as text</button><button id="br">Clear all</button><pre id="out" class="small" style="white-space:pre-wrap"></pre></section>
<div id="lb"><b>×</b><img alt=""></div>
<script>
(function(){{
var KEY="{man.get("storage_key", "stage24d-decisions-v1")}",st={{}};try{{st=JSON.parse(localStorage.getItem(KEY)||"{{}}")}}catch(e){{}}
function save(){{try{{localStorage.setItem(KEY,JSON.stringify(st))}}catch(e){{}}render()}}
document.querySelectorAll(".decide[data-module]").forEach(function(box){{var m=box.dataset.module,s=st[m]||{{}};
 box.querySelectorAll("input[type=radio]").forEach(function(r){{if(s.decision===r.value)r.checked=true;r.onchange=function(){{(st[m]=st[m]||{{}}).decision=r.value;save()}}}});
 var t=box.querySelector("textarea");t.value=s.comment||"";t.oninput=function(){{(st[m]=st[m]||{{}}).comment=t.value;save()}}}});
document.querySelectorAll(".q").forEach(function(q){{var k=q.dataset.q,s=st[k]||{{}},sel=q.querySelector("select"),t=q.querySelector("textarea");sel.value=s.choice||"";t.value=s.comment||"";
 sel.onchange=function(){{(st[k]=st[k]||{{}}).choice=sel.value;save()}};t.oninput=function(){{(st[k]=st[k]||{{}}).comment=t.value;save()}}}});
function data(){{var o={{stage:"{man.get("stage_label", "24-D")}",exported_at:new Date().toISOString(),baseline_stage_24c_head:"{man["stage_24c_head"]}",note:"Local export from the offline gallery; not synced to GitHub. Unset decisions mean OWNER REVIEW PENDING.",modules:{{}},questions:{{}}}};
 {json.dumps(list(MODULES))}.forEach(function(m){{var s=st[m]||{{}};o.modules[m]={{decision:s.decision||"pending",comment:s.comment||""}}}});
 {json.dumps(list(QUESTIONS))}.forEach(function(k){{var s=st[k]||{{}};o.questions[k]={{choice:s.choice||"pending",comment:s.comment||""}}}});return o}}
function text(){{var o=data(),l=["Stage {man.get("stage_label", "24-D")} owner review ("+o.exported_at+")",""];for(var m in o.modules)l.push(m+": "+o.modules[m].decision+(o.modules[m].comment?" — "+o.modules[m].comment:""));l.push("");for(var k in o.questions)l.push(k+": "+o.questions[k].choice+(o.questions[k].comment?" — "+o.questions[k].comment:""));return l.join("\\n")}}
function render(){{document.getElementById("out").textContent=text()}}
document.getElementById("bj").onclick=function(){{var a=document.createElement("a");a.href=URL.createObjectURL(new Blob([JSON.stringify(data(),null,2)],{{type:"application/json"}}));a.download="{man.get("storage_key", "stage24d")}-owner-decisions.json";a.click()}};
document.getElementById("bc").onclick=function(){{var t=text();if(navigator.clipboard&&navigator.clipboard.writeText){{navigator.clipboard.writeText(t).then(function(){{alert("Copied")}},function(){{prompt("Copy:",t)}})}}else{{prompt("Copy:",t)}}}};
document.getElementById("br").onclick=function(){{if(confirm("Clear all decisions?")){{st={{}};save();location.reload()}}}};
var lb=document.getElementById("lb"),li=lb.querySelector("img");
document.querySelectorAll("a[data-full]").forEach(function(a){{a.onclick=function(e){{e.preventDefault();li.src=a.dataset.full;lb.style.display="block";lb.scrollTop=0}}}});
lb.onclick=function(){{lb.style.display="none"}};render();
}})();
</script></body></html>'''
    (G / "index.html").write_text(page, encoding="utf8")
    return len(list(AS.rglob("*.jpg")))


def owner_review(n_images):
    man = json.loads((D24 / "INPUT-MANIFEST.json").read_text())
    rows = []
    for m in MODULES:
        base = f"gallery/assets/{m}"
        rows.append(f"| [{TITLES[m]}]({base}/front.jpg) | [exterior]({base}/elevated.jpg) · [roof]({base}/roof.jpg) | [interior]({base}/interior-dollhouse.jpg) · [section]({base}/interior-section.jpg) · [floors]({base}/floor-1.jpg) | [original vs restored]({base}/compare-a.jpg) · [V5 degradation]({base}/v5-degradation-a.jpg) | VISUAL PENDING · OWNER REVIEW PENDING | ☐ approve ☐ changes ☐ discuss |")
    q = "\n".join(f"| {k} | {t} | {' / '.join(o)} | |" for k, (t, o) in QUESTIONS.items())
    (D24 / "OWNER-REVIEW.md").write_text(f"""# Owner review — Ancient City restorations (Stage {man.get('stage_label', '24-D')})

Open `gallery/index.html` (works offline; the ZIP `{man.get('zip_name', 'stage-24d-offline-gallery.zip')}` contains the same). Baseline: Stage 24-C head `{man['stage_24c_head']}`.
Images are model-accurate renders of the final NBTs (26.1.2 block models/textures, studio lighting) — **not Minecraft-client screenshots**. No visual approval is implied.

## Per-module decisions

| Building | Exterior | Interior | Comparisons | Status | Decision |
|---|---|---|---|---|---|
{chr(10).join(rows)}

## Priority questions

| # | Question | Options | Decision |
|---|---|---|---|
{q}

Images: [V1 roofs](gallery/assets/priority/v1-roof-differentiation-threequarter.jpg) ([side](gallery/assets/priority/v1-roof-differentiation-side-silhouette.jpg)) · [V2 second floor](gallery/assets/priority/v2-medium-ruin-2-second-floor.jpg) · [V3 towers](gallery/assets/priority/v3-watchtower-silhouettes.jpg) · [V4 sauna opening](gallery/assets/priority/v4-sauna-reception-opening.jpg) · V5 = `v5-degradation-*.jpg` in every building folder.

Total images: {n_images}. Decisions entered in the gallery are exported locally (JSON/text); they do not update GitHub.
""")


def make_zip():
    man = json.loads((D24 / "INPUT-MANIFEST.json").read_text())
    zp = D24 / man.get("zip_name", "stage-24d-offline-gallery.zip")
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_STORED) as z:  # JPEGs are already compressed
        for p in sorted(G.rglob("*")):
            if p.is_file():
                z.write(p, "stage-24d-gallery/" + str(p.relative_to(G)))
        z.write(D24 / "OWNER-REVIEW.md", "stage-24d-gallery/OWNER-REVIEW.md")
        if (D24 / "VALIDATION-MATRIX.md").exists():
            z.write(D24 / "VALIDATION-MATRIX.md", "stage-24d-gallery/VALIDATION-MATRIX.md")
    return zp


if __name__ == "__main__":
    n = build()
    owner_review(n)
    zp = make_zip()
    print("images", n, "zip", zp, round(zp.stat().st_size / 1e6, 1), "MB")
