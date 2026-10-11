"""Turn off CRIWARE's Windows spatial-audio output so sound keeps working under Wine.

The boot scene (level0) holds the CriWareInitializer, whose atomConfig has
useMicrosoftSpatialSound = true. CRIWARE then renders through ISpatialAudioClient, which Wine only
partly implements: about 10 seconds in, SAORS_BeginUpdatingAudioObjects fails (GetBuffer
0x88890006) and the game goes silent for the rest of the session. With the flag off, CRIWARE uses
plain WASAPI output, which Wine supports fully. On Windows this only drops spatial "Windows Sonic"
output, which the game's stereo mix doesn't need.

The scene stores no type trees, so the flag is found by layout: MonoBehaviour header, then
CriWareInitializer's fields in declaration order (CriFsConfig, then CriAtomConfig up to the flag).
The surrounding values are checked before anything is written.
"""
import struct

SCRIPT_CLASS = "CriWareInitializer"
FLAG_OFFSET = 0xD0  # useMicrosoftSpatialSound inside the serialized CriWareInitializer
# (offset, expected int32) sanity anchors around the flag: serverFrequency, maxParameterBlocks,
# editorPcmOutputConfig.bufferLength, linuxPulseLatencyUsec
ANCHORS = [(0x9C, 0x42700000), (0xB4, 1024), (0xC8, 4096), (0xD8, 60000)]


def apply(level0_path, script_assets_path, log=print):
    """Return level0 bytes with spatial audio disabled, or None if it is already off."""
    import UnityPy
    scripts = {o.path_id: o.read().m_ClassName for o in UnityPy.load(script_assets_path).objects
               if o.type.name == "MonoScript"}
    env = UnityPy.load(level0_path)
    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        raw = bytearray(obj.get_raw_data())
        if scripts.get(struct.unpack_from("<q", raw, 20)[0]) != SCRIPT_CLASS:
            continue
        for off, want in ANCHORS:
            got = struct.unpack_from("<i", raw, off)[0]
            assert got == want, f"unexpected CriWareInitializer layout at {off:#x}: {got} != {want}"
        if raw[FLAG_OFFSET] == 0:
            log("audio: spatial sound already off")
            return None
        assert raw[FLAG_OFFSET] == 1
        raw[FLAG_OFFSET] = 0
        obj.set_raw_data(bytes(raw))
        log("audio: CRIWARE Microsoft spatial sound off (plain WASAPI output)")
        return env.file.save()
    raise RuntimeError("CriWareInitializer not found in level0")
