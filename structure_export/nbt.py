"""Small deterministic NBT reader/writer for vanilla structure templates.

The module intentionally uses only the Python standard library so exports do not depend on
mcbuild's optional authoring/runtime packages. Values use normal Python scalars, lists, and dicts.
"""

from __future__ import annotations

import gzip
import io
import struct

END, BYTE, SHORT, INT, LONG, FLOAT, DOUBLE, BYTE_ARRAY, STRING, LIST, COMPOUND, INT_ARRAY, LONG_ARRAY = range(13)


def _string(value: str) -> bytes:
    encoded = value.encode("utf-8")
    if len(encoded) > 65535:
        raise ValueError("NBT string exceeds the 65535-byte limit")
    return struct.pack(">H", len(encoded)) + encoded


def _tag_type(value: object) -> int:
    if isinstance(value, bool):
        return BYTE
    if isinstance(value, int):
        return INT if -(2**31) <= value < 2**31 else LONG
    if isinstance(value, float):
        return DOUBLE
    if isinstance(value, str):
        return STRING
    if isinstance(value, dict):
        return COMPOUND
    if isinstance(value, (bytes, bytearray)):
        return BYTE_ARRAY
    if isinstance(value, list):
        if not value:
            return LIST
        tags = {_tag_type(item) for item in value}
        if len(tags) != 1:
            raise ValueError("NBT lists must contain values of one tag type")
        return LIST
    raise TypeError(f"Unsupported NBT value: {type(value).__name__}")


def _write_payload(stream: io.BytesIO, tag_type: int, value: object) -> None:
    if tag_type == BYTE:
        stream.write(struct.pack(">b", int(value)))
    elif tag_type == SHORT:
        stream.write(struct.pack(">h", int(value)))
    elif tag_type == INT:
        stream.write(struct.pack(">i", int(value)))
    elif tag_type == LONG:
        stream.write(struct.pack(">q", int(value)))
    elif tag_type == FLOAT:
        stream.write(struct.pack(">f", float(value)))
    elif tag_type == DOUBLE:
        stream.write(struct.pack(">d", float(value)))
    elif tag_type == BYTE_ARRAY:
        raw = bytes(value)
        stream.write(struct.pack(">i", len(raw)))
        stream.write(raw)
    elif tag_type == STRING:
        stream.write(_string(str(value)))
    elif tag_type == LIST:
        values = value
        assert isinstance(values, list)
        child_type = _tag_type(values[0]) if values else END
        stream.write(struct.pack(">bi", child_type, len(values)))
        for child in values:
            _write_payload(stream, child_type, child)
    elif tag_type == COMPOUND:
        compound = value
        assert isinstance(compound, dict)
        for name in sorted(compound):
            child = compound[name]
            child_type = _tag_type(child)
            stream.write(struct.pack(">b", child_type))
            stream.write(_string(name))
            _write_payload(stream, child_type, child)
        stream.write(b"\x00")
    elif tag_type == INT_ARRAY:
        values = value
        stream.write(struct.pack(">i", len(values)))
        for item in values:
            stream.write(struct.pack(">i", item))
    elif tag_type == LONG_ARRAY:
        values = value
        stream.write(struct.pack(">i", len(values)))
        for item in values:
            stream.write(struct.pack(">q", item))
    else:
        raise ValueError(f"Unsupported NBT tag type: {tag_type}")


def write_nbt(root: dict[str, object]) -> bytes:
    """Write a deterministic gzip-compressed unnamed NBT root compound."""
    stream = io.BytesIO()
    stream.write(struct.pack(">b", COMPOUND))
    stream.write(_string(""))
    _write_payload(stream, COMPOUND, root)
    data = bytearray(gzip.compress(stream.getvalue(), compresslevel=9, mtime=0))
    # Python 3.13 changed the gzip header OS byte from 3 (Unix) to 255 (unknown); pin it so the
    # output is identical across interpreter versions.
    data[9] = 3
    return bytes(data)


class _Reader:
    def __init__(self, payload: bytes):
        self.stream = io.BytesIO(payload)

    def take(self, size: int) -> bytes:
        value = self.stream.read(size)
        if len(value) != size:
            raise ValueError("Truncated NBT payload")
        return value

    def string(self) -> str:
        length = struct.unpack(">H", self.take(2))[0]
        return self.take(length).decode("utf-8")

    def payload(self, tag_type: int) -> object:
        if tag_type == BYTE:
            return struct.unpack(">b", self.take(1))[0]
        if tag_type == SHORT:
            return struct.unpack(">h", self.take(2))[0]
        if tag_type == INT:
            return struct.unpack(">i", self.take(4))[0]
        if tag_type == LONG:
            return struct.unpack(">q", self.take(8))[0]
        if tag_type == FLOAT:
            return struct.unpack(">f", self.take(4))[0]
        if tag_type == DOUBLE:
            return struct.unpack(">d", self.take(8))[0]
        if tag_type == BYTE_ARRAY:
            length = struct.unpack(">i", self.take(4))[0]
            return self.take(length)
        if tag_type == STRING:
            return self.string()
        if tag_type == LIST:
            child_type, length = struct.unpack(">bi", self.take(5))
            if length < 0 or (child_type == END and length):
                raise ValueError("Invalid NBT list header")
            return [self.payload(child_type) for _ in range(length)]
        if tag_type == COMPOUND:
            result = {}
            while True:
                child_type = struct.unpack(">b", self.take(1))[0]
                if child_type == END:
                    return result
                name = self.string()
                if name in result:
                    raise ValueError(f"Duplicate NBT compound key: {name}")
                result[name] = self.payload(child_type)
        if tag_type in (INT_ARRAY, LONG_ARRAY):
            length = struct.unpack(">i", self.take(4))[0]
            width = 4 if tag_type == INT_ARRAY else 8
            code = ">i" if tag_type == INT_ARRAY else ">q"
            if length < 0:
                raise ValueError("Invalid NBT array length")
            return [struct.unpack(code, self.take(width))[0] for _ in range(length)]
        raise ValueError(f"Invalid NBT tag type: {tag_type}")


def read_nbt(data: bytes) -> dict[str, object]:
    """Read a gzip-compressed or raw named NBT root compound."""
    payload = gzip.decompress(data) if data[:2] == b"\x1f\x8b" else data
    reader = _Reader(payload)
    root_type = struct.unpack(">b", reader.take(1))[0]
    if root_type != COMPOUND:
        raise ValueError("Structure template root must be an NBT compound")
    root_name = reader.string()
    root_value = reader.payload(root_type)
    if reader.stream.read(1):
        raise ValueError("Trailing bytes after NBT root compound")
    return {"name": root_name, "value": root_value}
