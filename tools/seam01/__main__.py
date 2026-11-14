"""python -m tools.seam01 {generate|live} ..."""

# ruff: noqa: E501
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from . import patches as P
from . import synthetic


def main() -> int:
    ap = argparse.ArgumentParser(prog="tools.seam01")
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate", help="write the patch sets of the four rotations (synthetic module contents)")
    g.add_argument("--out", type=Path, required=True)
    lv = sub.add_parser("live", help="assemble + patch on a real 26.3 server and compare with the whole structure")
    lv.add_argument("--server-jar", type=Path, required=True)
    lv.add_argument("--java", default="java")
    lv.add_argument("--work", type=Path, default=None)
    lv.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()
    if a.cmd == "generate":
        from . import export

        sources = synthetic.sources()
        templates, _ = export.export_all(Path(tempfile.mkdtemp(prefix="seam01-")) / "pack", sources)
        a.out.mkdir(parents=True, exist_ok=True)
        base = P.generate(0, sources, templates)
        for q in range(4):
            ps = P.patchset(q, P.rotate(base, q))
            (a.out / f"patches_q{q}.json").write_text(json.dumps(ps, indent=1, sort_keys=True) + "\n")
        return 0
    import hashlib

    from tools.structure_export import convert as C

    from . import live

    if hashlib.sha1(a.server_jar.read_bytes()).hexdigest() != C.load_reference("26.3")["server_jar_sha1"]:
        raise SystemExit("server jar is not the pinned 26.3 jar")
    res = live.run(a.server_jar, a.java, a.work or Path(tempfile.mkdtemp(prefix="seam01-live-")))
    text = json.dumps(res, indent=2, sort_keys=True) + "\n"
    if a.out:
        a.out.write_text(text)
    print(f"{res['result']}" if a.out else text)
    return 0 if res["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
