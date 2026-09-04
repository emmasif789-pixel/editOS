# EditOS

**One repo, both halves of the project:**
- `/frontend/index.html` — the UI, deployed to Vercel: https://editos-emmasif789-9445s-projects.vercel.app
- everything else (`/app`, `Dockerfile`, `docker-compose.yml`) — the real backend (FFmpeg + faster-whisper + OpenCV + Ollama), runs locally via Docker

The frontend automatically detects and calls the backend when it's running on `localhost:8000` (badge in the top-right shows "Backend connected" vs "Browser-only mode"). No backend needed for the site to work — it falls back to doing real analysis in-browser — but the backend gives frame-accurate cuts, real mp4 export, and local AI reasoning via Ollama.

## Backend

Real pipeline: FFmpeg (cut/silence/loudness/captions) + faster-whisper (transcription) + OpenCV (reference pacing) + Ollama (local reasoning).

**Tuned for low-spec CPUs (e.g. older i5, no GPU, 8GB RAM):**
- Ollama model: `llama3.2:1b` (~1GB download, ~1-2GB RAM to run)
- Whisper model: `tiny` (~75MB, works on 4GB RAM / 2 cores)

Both are set as the defaults below — you don't need to change anything for a modest laptop.

## First-time setup
```
docker compose up --build
docker exec -it editos-backend-ollama-1 ollama pull llama3.2:1b
```

## Every time after that
Containers are set to `restart: unless-stopped`, so once built they come back automatically whenever Docker Desktop is running — you don't need to run any commands most of the time.

If you do need to start/stop manually (e.g. after fully quitting Docker Desktop), just double-click:
- **start.bat** — starts both containers in the background, no terminal window needs to stay open
- **stop.bat** — stops them

Or from the command line: `docker compose up -d` / `docker compose down`.

API at http://localhost:8000 (docs at /docs).

## Pipeline
1. `POST /upload` — raw clips + optional reference → job_id
2. `POST /analyze` — real ffprobe/silencedetect/loudnorm on raw, real OpenCV cut-rhythm on reference
3. `POST /plan` — Ollama explains the plan from the measured facts (no invented numbers)
4. `POST /render` — real ffmpeg cut+concat+normalize → real mp4; optional Whisper transcript + burned captions

Point the existing `editos.html` frontend at this API instead of doing analysis in-browser, and you get frame-accurate cuts, real mp4 output, and real captions instead of the browser-only approximation.
