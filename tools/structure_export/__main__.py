"""CLI: python -m tools.structure_export <command> <config.toml> [...]

convert  write the template .nbt and its report from the config
check    convert in memory, require byte-identical committed outputs, run the independent verifier
mmb      read-only compatibility check against a MoreMinecrafts-Beta checkout
live     place the template on a real server jar matching the pinned reference
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import block_entities
from . import convert as C
from .errors import ExportError
from .verify import VerificationError, verify


def _verify(config: C.Config) -> dict:
    return verify(
        config.nbt_path,
        config.source,
        C.load_reference(config.target),
        config.air,
        C.load_connectivity(config.target),
        block_entities.load(config.target),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m tools.structure_export", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("convert", "check"):
        sub.add_parser(name).add_argument("configs", nargs="+", type=Path)
    mmb = sub.add_parser("mmb")
    mmb.add_argument("config", type=Path)
    mmb.add_argument("--mmb", type=Path, required=True, help="MoreMinecrafts-Beta checkout (read only)")
    mmb.add_argument("--expect-commit")
    live = sub.add_parser("live")
    live.add_argument("config", type=Path)
    live.add_argument("--server-jar", type=Path, required=True)
    live.add_argument("--java", default="java")
    live.add_argument("--work", type=Path)
    args = parser.parse_args(argv)

    try:
        if args.command == "convert":
            for path in args.configs:
                result = C.convert(C.load_config(path))
                C.write(result)
                summary = _verify(result.config)
                print(
                    json.dumps(
                        {
                            "config": str(path),
                            "output": result.report["output"],
                            "sha256": result.report["output_sha256"],
                            "verify": summary,
                        },
                        sort_keys=True,
                    )
                )
        elif args.command == "check":
            failed = False
            for path in args.configs:
                result = C.convert(C.load_config(path))
                config = result.config
                same_nbt = config.nbt_path.is_file() and config.nbt_path.read_bytes() == result.nbt
                same_report = config.report_path.is_file() and config.report_path.read_text() == C.report_text(
                    result.report
                )
                summary = _verify(config) if same_nbt else None
                failed |= not (same_nbt and same_report)
                print(
                    json.dumps(
                        {
                            "config": str(path),
                            "reproducible_nbt": same_nbt,
                            "reproducible_report": same_report,
                            "verify": summary,
                        },
                        sort_keys=True,
                    )
                )
            return 1 if failed else 0
        elif args.command == "mmb":
            from .mmb_compat import check

            config = C.load_config(args.config)
            print(
                json.dumps(
                    check(
                        config.nbt_path, config.structure_id, config.datapack, args.mmb.resolve(), args.expect_commit
                    ),
                    indent=2,
                    sort_keys=True,
                )
            )
        elif args.command == "live":
            from .live import run

            result = run(C.load_config(args.config), args.server_jar, args.java, args.work)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0 if result["result"] == "PASS" else 1
    except (ExportError, VerificationError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
