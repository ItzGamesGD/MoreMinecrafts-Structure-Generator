"""Stage 24-F provenance: the vendored Stage 24-E objects are exact, verified, and used only when the git object is absent."""
import hashlib
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.stage24f import assemble as A  # noqa: E402

PINS = {p: h for h, p in (line.split("  ", 1) for line in (A.PROVENANCE / "SHA256SUMS").read_text().splitlines())}


def test_five_objects_are_vendored_and_pinned():
    assert len(PINS) == 5
    for path, h in PINS.items():
        assert hashlib.sha256((A.PROVENANCE / path).read_bytes()).hexdigest() == h


def test_vendored_copies_equal_the_git_objects_when_available():
    if subprocess.run(["git", "cat-file", "-e", A.STAGE24E_HEAD], cwd=ROOT, capture_output=True).returncode:
        pytest.skip("Stage 24-E commit not available in this clone (the vendored copies are the source)")
    for path in PINS:
        assert A.git_show(A.STAGE24E_HEAD, path) == (A.PROVENANCE / path).read_bytes()


def test_fallback_is_used_only_for_the_pinned_24e_commit_and_is_verified(monkeypatch, tmp_path):
    def missing(*a, **k):
        raise subprocess.CalledProcessError(128, "git show")
    monkeypatch.setattr(A.subprocess, "run", missing)
    path = next(iter(PINS))
    assert A.git_show(A.STAGE24E_HEAD, path) == (A.PROVENANCE / path).read_bytes()
    with pytest.raises(subprocess.CalledProcessError):
        A.git_show(A.STAGE24C_HEAD, path)                       # no fallback for any other commit
    # a tampered copy is rejected
    prov = tmp_path / "prov"
    (prov / Path(path).parent).mkdir(parents=True)
    (prov / path).write_bytes(b"tampered")
    (prov / "SHA256SUMS").write_text((A.PROVENANCE / "SHA256SUMS").read_text())
    monkeypatch.setattr(A, "PROVENANCE", prov)
    with pytest.raises(ValueError):
        A.git_show(A.STAGE24E_HEAD, path)
