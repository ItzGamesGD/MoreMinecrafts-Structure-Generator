"""Minimal real-server harness for Stage 24-C: RCON client, server lifecycle, Anvil reader."""
from __future__ import annotations

import os
import shutil
import socket
import struct
import subprocess
import time
import zlib
from pathlib import Path

import nbtlib


class Rcon:
    def __init__(self, port=25575, password="s24c", timeout=120):
        self.sock = socket.create_connection(("127.0.0.1", port), timeout=timeout)
        self._send(3, password)

    def _send(self, kind, body):
        payload = struct.pack("<ii", 1, kind) + body.encode() + b"\0\0"
        self.sock.sendall(struct.pack("<i", len(payload)) + payload)
        size = struct.unpack("<i", self._read(4))[0]
        return self._read(size)[8:-2].decode(errors="replace")

    def _read(self, n):
        data = b""
        while len(data) < n:
            chunk = self.sock.recv(n - len(data))
            if not chunk:
                raise ConnectionError("rcon closed")
            data += chunk
        return data

    def cmd(self, command):
        return self._send(2, command)


class Server:
    """Throw-away Minecraft Java server directory driven over RCON."""

    def __init__(self, root: Path, jar: Path, java: str, props: dict, datapack: Path | None = None,
                 heap="2G"):
        self.root, self.jar, self.java, self.heap = Path(root), Path(jar), java, heap
        if self.root.exists():
            shutil.rmtree(self.root)
        self.root.mkdir(parents=True)
        shutil.copy(self.jar, self.root / "server.jar")
        (self.root / "eula.txt").write_text("eula=true\n")
        base = {"online-mode": "false", "enable-rcon": "true", "rcon.port": "25575",
                "rcon.password": "s24c", "spawn-protection": "0", "max-tick-time": "-1",
                "view-distance": "6", "simulation-distance": "6", "spawn-monsters": "false",
                "difficulty": "peaceful", "level-name": "world", "allow-flight": "true"}
        base.update(props)
        self.props = base
        (self.root / "server.properties").write_text("".join(f"{k}={v}\n" for k, v in base.items()))
        if datapack:
            shutil.copytree(datapack, self.root / "world/datapacks" / Path(datapack).name)
        self.proc = None
        self.rcon = None

    def start(self, timeout=240):
        log = open(self.root / "server.log", "w")
        self.proc = subprocess.Popen([self.java, f"-Xmx{self.heap}", "-jar", "server.jar", "nogui"],
                                     cwd=self.root, stdout=log, stderr=subprocess.STDOUT)
        t0 = time.time()
        while time.time() - t0 < timeout:
            if "Done (" in (self.root / "server.log").read_text(errors="replace"):
                break
            if self.proc.poll() is not None:
                raise RuntimeError("server exited early")
            time.sleep(1)
        else:
            raise TimeoutError("server did not start")
        for attempt in range(30):  # RCON comes up a moment after "Done"
            try:
                self.rcon = Rcon(port=int(self.props.get("rcon.port", 25575)))
                break
            except ConnectionRefusedError:
                time.sleep(1)
        else:
            raise ConnectionRefusedError("rcon never came up")
        return self

    def cmd(self, c):
        return self.rcon.cmd(c)

    def flush(self):
        self.cmd("save-all flush")
        time.sleep(1)

    def stop(self):
        try:
            self.cmd("stop")
        except Exception:
            pass
        if self.proc:
            try:
                self.proc.wait(60)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        # keep only world data: the unpacked server libraries are ~150 MB per run
        for name in ("libraries", "versions", "server.jar", "logs", "cache"):
            target = self.root / name
            if target.is_dir():
                shutil.rmtree(target, ignore_errors=True)
            elif target.exists():
                target.unlink()


class World:
    """Read-only Anvil access to a saved dimension (blocks + block entities)."""

    def __init__(self, dim_root: Path):
        self.root = Path(dim_root)
        self._chunks = {}

    def chunk(self, cx, cz):
        key = (cx, cz)
        if key in self._chunks:
            return self._chunks[key]
        path = self.root / "region" / f"r.{cx >> 5}.{cz >> 5}.mca"
        result = None
        if path.exists():
            with open(path, "rb") as f:
                data = f.read()
            if len(data) < 8192:
                self._chunks[key] = None
                return None
            idx = ((cx & 31) + (cz & 31) * 32) * 4
            entry = struct.unpack(">I", data[idx:idx + 4])[0]
            off, cnt = entry >> 8, entry & 255
            if off:
                start = off * 4096
                length = struct.unpack(">I", data[start:start + 4])[0]
                comp = data[start + 4]
                raw = data[start + 5:start + 4 + length]
                raw = zlib.decompress(raw) if comp == 2 else raw
                result = _parse(raw)
        self._chunks[key] = result
        return result

    def block(self, x, y, z):
        ch = self.chunk(x >> 4, z >> 4)
        if ch is None:
            return None
        sy = y >> 4
        for sec in ch["sections"]:
            if int(sec["Y"]) != sy:
                continue
            bs = sec.get("block_states")
            if bs is None:
                return None
            pal = bs["palette"]
            if len(pal) == 1:
                return _state(pal[0])
            bits = max(4, (len(pal) - 1).bit_length())
            per = 64 // bits
            longs = [int(v) & 0xFFFFFFFFFFFFFFFF for v in bs["data"]]
            i = ((y & 15) << 8) | ((z & 15) << 4) | (x & 15)
            val = (longs[i // per] >> ((i % per) * bits)) & ((1 << bits) - 1)
            return _state(pal[val])
        return None

    def block_entity(self, x, y, z):
        ch = self.chunk(x >> 4, z >> 4)
        if ch is None:
            return None
        for be in ch.get("block_entities", []):
            if (int(be["x"]), int(be["y"]), int(be["z"])) == (x, y, z):
                return be
        return None

    def structure_starts(self, chunk_box=None):
        """chunk_box = (cx0, cz0, cx1, cz1) inclusive limits the scan."""
        out = []
        for path in sorted((self.root / "region").glob("*.mca")):
            rx, rz = map(int, path.stem.split(".")[1:3])
            for cz in range(32):
                for cx in range(32):
                    gx, gz = rx * 32 + cx, rz * 32 + cz
                    if chunk_box and not (chunk_box[0] <= gx <= chunk_box[2] and chunk_box[1] <= gz <= chunk_box[3]):
                        continue
                    ch = self.chunk(rx * 32 + cx, rz * 32 + cz)
                    self._chunks.pop((gx, gz), None) if ch is None or "structures" not in ch else None
                    if ch and "structures" in ch:
                        for name, st in ch["structures"].get("starts", {}).items():
                            if "Children" in st or "children" in st:
                                out.append((name, rx * 32 + cx, rz * 32 + cz, st))
        return out


def _parse(raw):
    import io
    f = nbtlib.File.parse(io.BytesIO(raw))
    return f


def _state(p):
    name = str(p["Name"])
    props = {str(k): str(v) for k, v in p.get("Properties", {}).items()}
    if props:
        return name + "[" + ",".join(f"{k}={v}" for k, v in sorted(props.items())) + "]"
    return name
