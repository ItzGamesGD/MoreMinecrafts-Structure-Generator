"""Importable RCON client and disposable-server helper for the SG-02/SG-03 runtime checks."""
from __future__ import annotations

import socket
import struct
import subprocess
import time
from pathlib import Path

PASSWORD = "sg01-visual-ci-only"
PROPERTIES = """level-name=world
level-seed=173
online-mode=false
enable-rcon=true
rcon.password={password}
rcon.port={rcon_port}
server-port={port}
server-ip=127.0.0.1
motd=MoreMinecrafts structure acceptance runtime
level-type=minecraft:flat
gamemode=creative
difficulty=peaceful
spawn-monsters=false
spawn-animals=false
view-distance=8
simulation-distance=6
allow-flight=true
white-list=false
"""


class Rcon:
    def __init__(self, host: str = "127.0.0.1", port: int = 25575, password: str = PASSWORD):
        self.sock = socket.create_connection((host, port), timeout=30)
        self.sock.settimeout(120)
        self._send(1, 3, password)

    def _send(self, rid: int, kind: int, body: str) -> str:
        data = struct.pack("<ii", rid, kind) + body.encode() + b"\0\0"
        self.sock.sendall(struct.pack("<i", len(data)) + data)
        size = struct.unpack("<i", self._read(4))[0]
        payload = self._read(size)
        got, _ = struct.unpack("<ii", payload[:8])
        if got == -1:
            raise RuntimeError("RCON authentication failed")
        return payload[8:-2].decode("utf-8", "replace")

    def _read(self, count: int) -> bytes:
        out = b""
        while len(out) < count:
            chunk = self.sock.recv(count - len(out))
            if not chunk:
                raise ConnectionError("RCON closed")
            out += chunk
        return out

    def run(self, command: str) -> str:
        return self._send(2, 2, command)


def start_server(run_dir: Path, pack_dirs: dict[str, Path], java_cmd: str, log: Path, *, port: int = 25565, rcon_port: int = 25575):
    """Prepare a disposable flat world with the given packs enabled and start the server."""
    for busy in (port, rcon_port):
        probe = socket.socket()
        probe.settimeout(1)
        if probe.connect_ex(("127.0.0.1", busy)) == 0:
            probe.close()
            raise RuntimeError(f"port {busy} is already in use: a previous --keep-server run is still alive; stop it first")
        probe.close()
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "world/datapacks").mkdir(parents=True, exist_ok=True)
    for name, source in pack_dirs.items():
        target = run_dir / "world/datapacks" / name
        subprocess.run(["rm", "-rf", str(target)], check=True)
        subprocess.run(["cp", "-a", str(source), str(target)], check=True)
    (run_dir / "eula.txt").write_text("eula=true\n")
    (run_dir / "server.properties").write_text(PROPERTIES.format(password=PASSWORD, port=port, rcon_port=rcon_port))
    log.parent.mkdir(parents=True, exist_ok=True)
    handle = open(log, "w")
    proc = subprocess.Popen(java_cmd, shell=True, cwd=run_dir, stdout=handle, stderr=subprocess.STDOUT, start_new_session=True)
    for _ in range(240):
        if "Done (" in log.read_text(errors="replace"):
            return proc
        if proc.poll() is not None:
            raise RuntimeError("server exited early:\n" + log.read_text(errors="replace")[-3000:])
        time.sleep(1)
    raise RuntimeError("server did not finish startup")
