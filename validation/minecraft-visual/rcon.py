#!/usr/bin/env python3
"""Small bounded Minecraft RCON client for this disposable validation world."""
import socket, struct, sys, time
HOST, PORT, PASSWORD = "127.0.0.1", 25575, "sg01-visual-ci-only"

def packet(sock, rid, kind, body):
    data = struct.pack("<ii", rid, kind) + body.encode("utf-8") + b"\0\0"
    sock.sendall(struct.pack("<i", len(data)) + data)
    size = struct.unpack("<i", sock.recv(4))[0]
    payload = b""
    while len(payload) < size:
        payload += sock.recv(size-len(payload))
    got, typ = struct.unpack("<ii", payload[:8])
    if got == -1:
        raise RuntimeError("RCON authentication failed")
    return payload[8:-2].decode("utf-8", "replace")

with socket.create_connection((HOST, PORT), timeout=60) as sock:
    sock.settimeout(60)
    packet(sock, 1, 3, PASSWORD)
    for line in sys.stdin:
        cmd = line.rstrip("\n")
        if not cmd:
            continue
        try:
            result = packet(sock, 2, 2, cmd)
        except Exception as exc:
            print(f"COMMAND {cmd}\nERROR {type(exc).__name__}: {exc}", flush=True)
            sys.exit(1)
        print(f"COMMAND {cmd}\nRESULT {result}", flush=True)
        time.sleep(0.25)
