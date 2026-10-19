"""Fast saved-world reader (numpy) and a small vanilla-server/RCON driver for the SG-01 stress harness."""
from __future__ import annotations

import gzip
import re
import socket
import struct
import subprocess
import sys
import time
import zlib
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from structure_export.nbt import read_nbt  # noqa: E402


def norm(entry):
    """Saved palette entries: {Name, Properties} (26.x) or legacy {id, properties}, or a bare string."""
    if isinstance(entry, str):
        return {"id": entry}
    if "" in entry:
        return {"id": entry[""]}
    if "Name" in entry:
        return {"id": entry["Name"], **({"properties": entry["Properties"]} if entry.get("Properties") else {})}
    return entry


def read_chunk(region_dir: Path, cx: int, cz: int):
    path = region_dir / f"r.{cx // 32}.{cz // 32}.mca"
    if not path.exists():
        return None
    with path.open("rb") as f:
        f.seek(((cx % 32) + (cz % 32) * 32) * 4)
        loc = f.read(4)
        off = int.from_bytes(loc[:3], "big")
        if off == 0:
            return None
        f.seek(off * 4096)
        length = struct.unpack(">I", f.read(4))[0]
        comp = f.read(1)[0]
        payload = f.read(length - 1)
    raw = {1: gzip.decompress, 2: zlib.decompress, 3: lambda b: b}[comp](payload)
    return read_nbt(raw)["value"]


def _unpack(palette_len: int, data, count: int, min_bits: int) -> np.ndarray:
    if palette_len == 1:
        return np.zeros(count, dtype=np.int32)
    bits = max(min_bits, (palette_len - 1).bit_length())
    per = 64 // bits
    longs = np.array([v & 0xFFFFFFFFFFFFFFFF for v in data], dtype=np.uint64)
    shifts = (np.arange(per, dtype=np.uint64) * np.uint64(bits))
    vals = (longs[:, None] >> shifts[None, :]) & np.uint64((1 << bits) - 1)
    return vals.reshape(-1)[:count].astype(np.int32)


class Chunk:
    def __init__(self, nbt: dict) -> None:
        self.nbt = nbt
        self.status = nbt.get("Status") or nbt.get("status")
        self.sections: dict[int, tuple[list, np.ndarray]] = {}
        self.biomes: dict[int, tuple[list, np.ndarray]] = {}
        for sec in nbt.get("sections", []):
            y = int(sec["Y"])
            bs = sec.get("block_states")
            if bs:
                palette = [norm(e) for e in bs["palette"]]
                idx = _unpack(len(palette), bs.get("data", []), 4096, 4)
                self.sections[y] = (palette, idx)
            bm = sec.get("biomes")
            if bm:
                bpal = [e if isinstance(e, str) else e.get("", e) for e in bm["palette"]]
                self.biomes[y] = (bpal, _unpack(len(bpal), bm.get("data", []), 64, 1))

    def block_id(self, x: int, y: int, z: int) -> str:
        sec = self.sections.get(y >> 4)
        if sec is None:
            return "minecraft:air"
        palette, idx = sec
        return palette[idx[((y & 15) << 8) | ((z & 15) << 4) | (x & 15)]]["id"]

    def state(self, x: int, y: int, z: int) -> dict:
        sec = self.sections.get(y >> 4)
        if sec is None:
            return {"id": "minecraft:air"}
        palette, idx = sec
        return palette[idx[((y & 15) << 8) | ((z & 15) << 4) | (x & 15)]]

    def biome(self, x: int, y: int, z: int) -> str:
        sec = self.biomes.get(y >> 4)
        if sec is None:
            return "unknown"
        palette, idx = sec
        return palette[idx[(((y & 15) >> 2) << 4) | (((z & 15) >> 2) << 2) | ((x & 15) >> 2)]]


class World:
    """Lazy chunk cache over a region directory (re-create after a save to see new data)."""

    def __init__(self, region_dir: Path) -> None:
        self.region_dir = region_dir
        self.cache: dict[tuple[int, int], Chunk | None] = {}

    def chunk(self, cx: int, cz: int) -> Chunk | None:
        key = (cx, cz)
        if key not in self.cache:
            nbt = read_chunk(self.region_dir, cx, cz)
            self.cache[key] = Chunk(nbt) if nbt else None
        return self.cache[key]

    def state(self, x: int, y: int, z: int) -> dict:
        c = self.chunk(x >> 4, z >> 4)
        return {"id": "minecraft:unloaded"} if c is None else c.state(x, y, z)

    def block_id(self, x: int, y: int, z: int) -> str:
        return self.state(x, y, z)["id"]

    def biome(self, x: int, y: int, z: int) -> str:
        c = self.chunk(x >> 4, z >> 4)
        return "unloaded" if c is None else c.biome(x, y, z)


class Rcon:
    def __init__(self, port: int, password: str, timeout: float = 120) -> None:
        self.sock = socket.create_connection(("127.0.0.1", port), timeout=timeout)
        self.sock.settimeout(timeout)
        self._send(3, password)

    def _recv(self, n: int) -> bytes:
        buf = b""
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("RCON closed")
            buf += chunk
        return buf

    def _send(self, kind: int, body: str) -> str:
        data = struct.pack("<ii", 2, kind) + body.encode() + b"\0\0"
        self.sock.sendall(struct.pack("<i", len(data)) + data)
        size = struct.unpack("<i", self._recv(4))[0]
        payload = self._recv(size)
        rid = struct.unpack("<i", payload[:4])[0]
        if rid == -1:
            raise RuntimeError("RCON auth failed")
        return payload[8:-2].decode("utf-8", "replace")

    def cmd(self, command: str) -> str:
        return self._send(2, command)


class Server:
    def __init__(self, java: str, jar: Path, run_dir: Path, seed: int, pack: Path, port: int = 25575, *, extra_props: dict | None = None,
                 extra_args: list[str] | None = None, xmx: str = "3G", launcher: list[str] | None = None,
                 launcher_cwd: Path | None = None, env: dict | None = None, start_timeout: int = 300) -> None:
        self.run_dir, self.port = run_dir, port
        (run_dir / "world" / "datapacks").mkdir(parents=True, exist_ok=True)
        subprocess.run(["cp", "-a", str(pack), str(run_dir / "world" / "datapacks" / "sg01")], check=True)
        (run_dir / "eula.txt").write_text("eula=true\n")
        props = {"level-name": "world", "level-seed": str(seed), "online-mode": "false", "enable-rcon": "true",
                 "rcon.password": "sg01-stress", "rcon.port": str(port), "server-port": str(port - 100), "server-ip": "127.0.0.1",
                 "gamemode": "survival", "difficulty": "peaceful", "spawn-monsters": "false", "spawn-animals": "false",
                 "view-distance": "3", "simulation-distance": "3", "generate-structures": "true", "white-list": "false",
                 "level-type": "minecraft:normal", "max-tick-time": "-1", **(extra_props or {})}
        (run_dir / "server.properties").write_text("".join(f"{k}={v}\n" for k, v in props.items()))
        self.log_path = run_dir / "server.log"
        self.log = self.log_path.open("w")
        import os
        command = launcher or [java, f"-Xmx{xmx}", *(extra_args or []), "-jar", str(jar), "nogui"]
        self.proc = subprocess.Popen(command, cwd=launcher_cwd or run_dir, stdout=self.log, stderr=subprocess.STDOUT,
                                     stdin=subprocess.DEVNULL, env={**os.environ, **(env or {})}, start_new_session=True)
        deadline = time.time() + start_timeout
        while time.time() < deadline:
            if self.proc.poll() is not None:
                raise RuntimeError(f"server exited early:\n{self.log_path.read_text()[-3000:]}")
            if "Done (" in self.log_path.read_text(errors="replace"):
                break
            time.sleep(1)
        else:
            raise RuntimeError("server start timeout")
        self.rcon = Rcon(port, "sg01-stress")

    def cmd(self, c: str) -> str:
        return self.rcon.cmd(c)

    @property
    def region_dir(self) -> Path:
        for p in (self.run_dir / "world/dimensions/minecraft/overworld/region", self.run_dir / "world/region"):
            if p.is_dir():
                return p
        raise FileNotFoundError("no overworld region dir")

    def save(self) -> None:
        self.cmd("save-all flush")

    def stop(self) -> None:
        import os, signal
        try:
            self.cmd("stop")
            self.proc.wait(timeout=90)
        except Exception:
            pass
        try:
            os.killpg(self.proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        self.log.close()


def export_chunks(region_dir: Path, chunks: list[tuple[int, int]], dest_dir: Path) -> int:
    """Copy the given chunks' raw (still-compressed) payloads into fresh region files, so a small saved-world excerpt can be kept."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    by_region: dict[tuple[int, int], dict[int, bytes]] = {}
    for cx, cz in chunks:
        path = region_dir / f"r.{cx // 32}.{cz // 32}.mca"
        if not path.exists():
            continue
        with path.open("rb") as f:
            f.seek(((cx % 32) + (cz % 32) * 32) * 4)
            off = int.from_bytes(f.read(4)[:3], "big")
            if off == 0:
                continue
            f.seek(off * 4096)
            length = struct.unpack(">I", f.read(4))[0]
            by_region.setdefault((cx // 32, cz // 32), {})[(cx % 32) + (cz % 32) * 32] = f.read(length)  # compression byte + payload
    written = 0
    for (rx, rz), slots in by_region.items():
        header = bytearray(8192)
        body = bytearray()
        sector = 2
        for slot, data in sorted(slots.items()):
            record = struct.pack(">I", len(data)) + data
            record += b"\0" * (-len(record) % 4096)
            count = len(record) // 4096
            header[slot * 4: slot * 4 + 4] = sector.to_bytes(3, "big") + bytes([count])
            body += record
            sector += count
            written += 1
        (dest_dir / f"r.{rx}.{rz}.mca").write_bytes(bytes(header) + bytes(body))
    return written
