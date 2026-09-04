# EditOS backend

Real pipeline: FFmpeg (cut/silence/loudness/captions) + faster-whisper (transcription) + OpenCV (reference pacing) + Ollama (local reasoning).

**Tuned for low-spec CPUs (e.g. older i5, no GPU, 8GB RAM):**
- Ollama model: `llama3.2:1b` (~1GB download, ~1-2GB RAM to run)
- Whisper model: `tiny` (~75MB, works on 4GB RAM / 2 cores)

Both are set as the defaults below — you don't need to change anything for a modest laptop.

## Run it
```
docker compose up --build
docker exec -it editos-backend-ollama-1 ollama pull llama3.2:1b
```
API at http://localhost:8000 (docs at /docs).

## Pipeline
1. `POST /upload` — raw clips + optional reference → job_id
2. `POST /analyze` — real ffprobe/silencedetect/loudnorm on raw, real OpenCV cut-rhythm on reference
3. `POST /plan` — Ollama explains the plan from the measured facts (no invented numbers)
4. `POST /render` — real ffmpeg cut+concat+normalize → real mp4; optional Whisper transcript + burned captions

Point the existing `editos.html` frontend at this API instead of doing analysis in-browser, and you get frame-accurate cuts, real mp4 output, and real captions instead of the browser-only approximation.
