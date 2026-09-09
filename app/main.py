import os, uuid, shutil, time
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import ffmpeg_utils, whisper_utils, vision_utils, gemini_utils

app = FastAPI(title="EditOS Backend")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DATA_DIR = os.environ.get("DATA_DIR", "/data")
os.makedirs(DATA_DIR, exist_ok=True)
app.mount("/files", StaticFiles(directory=DATA_DIR), name="files")

# How many completed jobs to keep before deleting the oldest (files + memory).
# No limit on how many edits you can generate — this just stops old ones from
# piling up on disk/RAM forever. Override with MAX_KEPT_JOBS env var.
MAX_KEPT_JOBS = int(os.environ.get("MAX_KEPT_JOBS", "20"))

JOBS: dict[str, dict] = {}  # in-memory job store (swap for redis/db in real prod)
JOB_ORDER: list[str] = []  # tracks insertion order so we know which to evict first


def _evict_old_jobs():
    while len(JOB_ORDER) > MAX_KEPT_JOBS:
        old_id = JOB_ORDER.pop(0)
        old_job = JOBS.pop(old_id, None)
        if old_job:
            try:
                shutil.rmtree(old_job["dir"], ignore_errors=True)
            except Exception:
                pass


def register_job(job_id: str, data: dict):
    JOBS[job_id] = data
    JOB_ORDER.append(job_id)
    _evict_old_jobs()


def job_dir(job_id: str) -> str:
    d = os.path.join(DATA_DIR, job_id)
    os.makedirs(d, exist_ok=True)
    return d


def get_job(job_id: str) -> dict:
    job = JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Unknown job_id '{job_id}' — did you call /upload first, or was it evicted (see /jobs), or did the server restart?")
    return job


@app.delete("/jobs")
def clear_all_jobs():
    """Manual full cleanup — wipes every stored job's files and frees the memory."""
    count = len(JOBS)
    for jid in list(JOBS.keys()):
        shutil.rmtree(JOBS[jid]["dir"], ignore_errors=True)
    JOBS.clear()
    JOB_ORDER.clear()
    return {"cleared": count}


@app.get("/jobs")
def list_jobs():
    return {"count": len(JOBS), "max_kept": MAX_KEPT_JOBS, "job_ids": JOB_ORDER}


@app.post("/upload")
async def upload(raw: list[UploadFile] = File(...), reference: UploadFile | None = File(None)):
    job_id = uuid.uuid4().hex[:12]
    d = job_dir(job_id)
    raw_paths = []
    for i, f in enumerate(raw):
        p = os.path.join(d, f"raw_{i}{os.path.splitext(f.filename)[1]}")
        with open(p, "wb") as out:
            shutil.copyfileobj(f.file, out)
        raw_paths.append(p)

    ref_path = None
    if reference is not None:
        ref_path = os.path.join(d, f"reference{os.path.splitext(reference.filename)[1]}")
        with open(ref_path, "wb") as out:
            shutil.copyfileobj(reference.file, out)

    register_job(job_id, {"raw_paths": raw_paths, "ref_path": ref_path, "dir": d})
    return {"job_id": job_id, "raw_files": len(raw_paths), "has_reference": ref_path is not None}


class AnalyzeRequest(BaseModel):
    job_id: str
    intent: str


@app.post("/analyze")
async def analyze(req: AnalyzeRequest):
    job = get_job(req.job_id)
    results = []
    total_duration = 0.0
    total_gap_time = 0.0
    total_gaps = 0

    for path in job["raw_paths"]:
        meta = ffmpeg_utils.probe(path)
        total_duration += meta["duration"]
        silences = ffmpeg_utils.detect_silence(path) if meta["has_audio"] else []
        gap_time = sum(g["end"] - g["start"] for g in silences)
        total_gap_time += gap_time
        total_gaps += len(silences)
        loud = ffmpeg_utils.measure_loudness(path) if meta["has_audio"] else {"input_i": None}
        results.append({
            "path": path, "duration": meta["duration"], "has_audio": meta["has_audio"],
            "silences": silences, "gap_time": gap_time, "loudness": loud,
        })

    ref_stats = None
    if job.get("ref_path"):
        ref_stats = vision_utils.analyze_reference_rhythm(job["ref_path"])

    job["files"] = results
    job["ref_stats"] = ref_stats
    job["intent"] = req.intent
    job["total_duration"] = total_duration

    return {
        "total_duration": total_duration,
        "total_silence_gaps": total_gaps,
        "total_silence_time": round(total_gap_time, 2),
        "reference_stats": ref_stats,
        "files": [{"path": r["path"], "duration": r["duration"], "gaps": len(r["silences"]), "silences": r["silences"], "loudness": r["loudness"]} for r in results],
    }


@app.post("/plan")
async def plan(job_id: str = Form(...)):
    job = get_job(job_id)
    facts = {
        "intent": job["intent"],
        "total_duration_sec": job["total_duration"],
        "silence_gaps": sum(len(f["silences"]) for f in job["files"]),
        "silence_time_sec": round(sum(f["gap_time"] for f in job["files"]), 2),
        "reference_measured": job["ref_stats"],
    }
    try:
        reasoning = await gemini_utils.generate_plan_reasoning(job["intent"], facts)
    except Exception as e:
        return JSONResponse(
            status_code=502,
            content={
                "error": "Couldn't get plan reasoning from Gemini.",
                "detail": str(e),
                "hint": "Make sure GEMINI_API_KEY is set as an environment variable on this server.",
                "facts": facts,
            },
        )
    job["plan_reasoning"] = reasoning
    return {"facts": facts, "reasoning": reasoning}


class RenderRequest(BaseModel):
    job_id: str
    burn_captions: bool = False
    gain_db: float = 0.0


@app.post("/render")
async def render(req: RenderRequest):
    job = get_job(req.job_id)
    d = job["dir"]
    out_parts = []

    for i, f in enumerate(job["files"]):
        segs = ffmpeg_utils.compute_keep_segments(f["duration"], f["silences"])
        out_path = os.path.join(d, f"cut_{i}.mp4")
        ffmpeg_utils.cut_and_concat(f["path"], segs, req.gain_db, out_path)
        out_parts.append(out_path)

    final_path = out_parts[0] if len(out_parts) == 1 else os.path.join(d, "final.mp4")
    if len(out_parts) > 1:
        list_file = os.path.join(d, "final_list.txt")
        with open(list_file, "w") as fh:
            for p in out_parts:
                fh.write(f"file '{p}'\n")
        import subprocess
        subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i", list_file, "-c","copy", final_path], check=True)

    if req.burn_captions and job["files"][0]["has_audio"]:
        transcript = whisper_utils.transcribe(job["raw_paths"][0])
        srt_path = whisper_utils.write_srt(transcript["srt"], os.path.join(d, "captions.srt"))
        captioned_path = os.path.join(d, "final_captioned.mp4")
        ffmpeg_utils.burn_captions(final_path, srt_path, captioned_path)
        final_path = captioned_path
        job["transcript"] = transcript

    rel = os.path.relpath(final_path, DATA_DIR)
    return {"video_url": f"/files/{rel}"}


@app.get("/health")
def health():
    return {"ok": True}
