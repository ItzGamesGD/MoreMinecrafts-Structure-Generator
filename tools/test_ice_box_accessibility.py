#!/usr/bin/env python3
"""Regression gate for the original broken and repaired ice_box_1 candidate."""
from __future__ import annotations
import json
from inspect_ice_box_accessibility import Candidate, inspect
from render_approved_ancient_followup import ice_box

def main():
    c=Candidate("ice_box_1")
    ice_box(c)
    c.verify()
    result=inspect(c,"existing-candidate")
    # RED against the base implementation: these assertions must expose the
    # removed ladder support and disconnected surface-to-pantry route.
    assert all(result["checks"].values()), json.dumps(result["checks"],sort_keys=True)
    print("ICE_BOX_REPAIR_CHECKS="+json.dumps(result["checks"],sort_keys=True),flush=True)

if __name__=="__main__":
    main()
