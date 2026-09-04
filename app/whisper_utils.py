from faster_whisper import WhisperModel

_model = None

def get_model(size: str = "tiny"):
    global _model
    if _model is None:
        _model = WhisperModel(size, device="cpu", compute_type="int8")
    return _model

def transcribe(path: str, size: str = "tiny") -> dict:
    model = get_model(size)
    segments, info = model.transcribe(path, vad_filter=True)
    words = []
    srt_lines = []
    for i, seg in enumerate(segments, start=1):
        words.append({"start": seg.start, "end": seg.end, "text": seg.text.strip()})
        srt_lines.append(str(i))
        srt_lines.append(f"{_ts(seg.start)} --> {_ts(seg.end)}")
        srt_lines.append(seg.text.strip())
        srt_lines.append("")
    return {"language": info.language, "segments": words, "srt": "\n".join(srt_lines)}

def _ts(t: float) -> str:
    h = int(t // 3600); m = int((t % 3600) // 60); s = int(t % 60); ms = int((t - int(t)) * 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def write_srt(srt_text: str, out_path: str) -> str:
    with open(out_path, "w") as f:
        f.write(srt_text)
    return out_path
