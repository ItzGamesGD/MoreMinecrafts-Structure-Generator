"""Export the three perimeter-wall design prototypes to out/<design>/st03_wall_86.nbt and st03_wall_31.nbt.

  PYTHONPATH=.:experiments/st03-wall-redesign python experiments/st03-wall-redesign/build.py [a b c]
The batch-8 candidate NBTs (experiments/st03-batch8-perimeter-walls/out) are not touched.
"""

import importlib
import sys
from pathlib import Path

from common import export

ROOT = Path(__file__).resolve().parent
DESIGNS = {"a": "design_a", "b": "design_b", "c": "design_c", "b2": "design_b2"}


def design(key):
    return importlib.import_module(DESIGNS[key])


def main():
    for key in sys.argv[1:] or ("a", "b", "c"):
        m = design(key)
        export(key.upper(), {"MW86": m.mw86(), "MW31": m.mw31()}, ROOT / "out" / key)


if __name__ == "__main__":
    main()
