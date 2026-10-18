"""OS-level file, network and process-denial checks for disposable blueprint workers."""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from mcbuild.dsl import os_confinement
from mcbuild.dsl.sandbox import run_blueprint_isolated
from mcbuild.voxel import VoxelGrid


def test_real_kernel_denies_file_network_and_spawn(tmp_path):
    secret = tmp_path / "private-test.txt"
    secret.write_text("harmless fixture", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-I", "-m", "mcbuild.dsl.os_confinement", str(secret)],
        capture_output=True,
        text=True,
        check=True,
        timeout=15,
    )
    assert json.loads(result.stdout) == {
        "peer_signal_denied": True,
        "peer_limit_denied": True,
        "file_denied": True,
        "network_denied": True,
        "spawn_denied": True,
    }


def test_legitimate_blueprint_remains_functional_under_syscall_filter():
    result = run_blueprint_isolated("fill(0, 0, 0, 2, 0, 2, 'stone')", VoxelGrid())
    assert len(result) == 9


def test_seccomp_installation_is_fail_closed_on_unsupported_arch(monkeypatch):
    monkeypatch.setattr(os_confinement.platform, "machine", lambda: "unsupported-arch")
    with pytest.raises(OSError, match="only verified"):
        os_confinement.install()
