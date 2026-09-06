import subprocess, json, re, os

try:
    import imageio_ffmpeg
    FFMPEG_BIN = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG_BIN = "ffmpeg"  # falls back to a system install if the pip package isn't present

def probe(path: str) -> dict:
    """Duration/audio-track probing without ffprobe (not bundled by imageio-ffmpeg) —
    parses ffmpeg's own '-i' stderr output instead, which every ffmpeg build prints."""
    proc = subprocess.run([FFMPEG_BIN, "-i", path], capture_output=True, text=True)
    log = proc.stderr
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", log)
    duration = 0.0
    if m:
        h, mnt, s = m.groups()
        duration = int(h) * 3600 + int(mnt) * 60 + float(s)
    has_audio = bool(re.search(r"Stream #\d+:\d+.*Audio:", log))
    return {"duration": duration, "has_audio": has_audio, "raw_probe_log": log}

def detect_silence(path: str, noise_db: str = "-30dB", min_dur: float = 0.55) -> list[dict]:
    """Real silence detection via ffmpeg's silencedetect filter."""
    cmd = [FFMPEG_BIN,"-i", path, "-af", f"silencedetect=noise={noise_db}:d={min_dur}", "-f","null","-"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    log = proc.stderr
    starts = [float(m) for m in re.findall(r"silence_start:\s*([\d.]+)", log)]
    ends   = [float(m) for m in re.findall(r"silence_end:\s*([\d.]+)", log)]
    gaps = []
    for i in range(min(len(starts), len(ends))):
        gaps.append({"start": starts[i], "end": ends[i]})
    return gaps

def measure_loudness(path: str) -> dict:
    """Real integrated loudness via ffmpeg loudnorm first pass (EBU R128)."""
    cmd = [FFMPEG_BIN,"-i", path, "-af", "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json", "-f","null","-"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", proc.stderr, re.S)
    if not m:
        return {"input_i": None}
    data = json.loads(m.group(0))
    # ffmpeg's loudnorm filter returns every value as a string (e.g. "-24.34") —
    # cast the numeric ones so API consumers don't get silent string-concat bugs.
    numeric_keys = ["input_i","input_tp","input_lra","input_thresh","output_i","output_tp","output_lra","output_thresh","target_offset"]
    for k in numeric_keys:
        if k in data:
            try:
                data[k] = float(data[k])
            except (TypeError, ValueError):
                pass
    return data

def compute_keep_segments(duration: float, silences: list[dict], pad: float = 0.10) -> list[dict]:
    segs, cursor = [], 0.0
    for s in silences:
        start = max(0.0, s["start"] + pad)
        end = max(start, s["end"] - pad)
        if start > cursor + 0.05:
            segs.append({"start": cursor, "end": start})
        cursor = max(cursor, end)
    if duration - cursor > 0.05:
        segs.append({"start": cursor, "end": duration})
    return [s for s in segs if s["end"] - s["start"] > 0.12]

def cut_and_concat(path: str, segments: list[dict], gain_db: float, out_path: str):
    """Frame-accurate cut of kept segments + concat + loudness normalize, real mp4 output."""
    tmp_dir = os.path.dirname(out_path)
    part_paths = []
    for i, seg in enumerate(segments):
        part = os.path.join(tmp_dir, f"part_{i}.mp4")
        subprocess.run([
            FFMPEG_BIN,"-y","-ss", str(seg["start"]), "-to", str(seg["end"]), "-i", path,
            "-af", f"volume={gain_db}dB",
            "-c:v","libx264","-preset","veryfast","-crf","20","-c:a","aac", part
        ], check=True, capture_output=True)
        part_paths.append(part)

    list_file = os.path.join(tmp_dir, "concat_list.txt")
    with open(list_file, "w") as f:
        for p in part_paths:
            f.write(f"file '{p}'\n")

    subprocess.run([
        FFMPEG_BIN,"-y","-f","concat","-safe","0","-i", list_file,
        "-c","copy", out_path
    ], check=True, capture_output=True)

    for p in part_paths:
        os.remove(p)
    os.remove(list_file)
    return out_path

def burn_captions(in_path: str, srt_path: str, out_path: str):
    """Real caption burn-in via ffmpeg subtitles filter (needs an .srt from whisper)."""
    subprocess.run([
        FFMPEG_BIN,"-y","-i", in_path,
        "-vf", f"subtitles={srt_path}:force_style='FontName=Arial,FontSize=20,PrimaryColour=&H3DFFC8&,BorderStyle=3,Outline=1,Alignment=2'",
        "-c:a","copy", out_path
    ], check=True, capture_output=True)
    return out_path
