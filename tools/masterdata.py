"""Read/write the game's MasterMemory blob (MessagePack, per-table LZ4)."""
import io, struct
import msgpack, lz4.block


def _unpack(raw):
    return msgpack.unpackb(raw, raw=False, strict_map_key=False)


class MasterData:
    def __init__(self, blob: bytes):
        u = msgpack.Unpacker(io.BytesIO(blob), raw=False, strict_map_key=False)
        self.header = u.unpack()
        self.base = u.tell()
        self.blob = blob

    @classmethod
    def from_bundle(cls, bundle_path):
        import UnityPy
        env = UnityPy.load(bundle_path)
        for o in env.objects:
            if o.type.name == "TextAsset":
                s = o.read().m_Script
                return cls(s.encode("utf-8", "surrogateescape") if isinstance(s, str) else s)
        raise ValueError("no MasterData TextAsset in bundle")

    def table(self, name):
        off, ln = self.header[name]
        obj = msgpack.unpackb(self.blob[self.base + off:self.base + off + ln], raw=False,
                              strict_map_key=False, ext_hook=msgpack.ExtType)
        if isinstance(obj, msgpack.ExtType) and obj.code == 99:  # MessagePack-CSharp Lz4Block
            size = struct.unpack(">i", obj.data[1:5])[0]
            return _unpack(lz4.block.decompress(obj.data[5:], uncompressed_size=size))
        if isinstance(obj, list) and obj and isinstance(obj[0], msgpack.ExtType) and obj[0].code == 98:
            lens = list(msgpack.Unpacker(io.BytesIO(obj[0].data)))
            return _unpack(b"".join(lz4.block.decompress(c, uncompressed_size=l) for c, l in zip(obj[1:], lens)))
        return obj


def _lz4_ext(rows):
    raw = msgpack.packb(rows, use_bin_type=True)
    payload = b"\xd2" + struct.pack(">i", len(raw)) + lz4.block.compress(raw, store_size=False)
    return msgpack.packb(msgpack.ExtType(99, payload))


def rebuild(md: "MasterData", replaced: dict) -> bytes:
    """Return a new blob with tables in `replaced` (name -> rows) re-encoded; others copied byte-for-byte."""
    order = sorted(md.header.items(), key=lambda kv: kv[1][0])
    body, header = bytearray(), {}
    for name, (off, ln) in order:
        chunk = _lz4_ext(replaced[name]) if name in replaced else md.blob[md.base + off:md.base + off + ln]
        header[name] = (len(body), len(chunk))
        body += chunk
    # Keep the original header key order and fixed-width int32 offsets like MasterMemory writes them.
    out = bytearray(b"\xde" + struct.pack(">H", len(md.header)))
    for name in md.header:
        out += msgpack.packb(name)
        o, l = header[name]
        out += b"\x92\xd2" + struct.pack(">i", o) + b"\xd2" + struct.pack(">i", l)
    return bytes(out + body)
