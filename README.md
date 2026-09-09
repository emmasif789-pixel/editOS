# EditOS

**One repo, both halves of the project:**
- `/frontend/index.html` — the UI, deployed to Vercel: https://editos-emmasif789-9445s-projects.vercel.app
- everything else (`/app`, `Dockerfile`, `docker-compose.yml`) — the real backend (FFmpeg + faster-whisper + OpenCV + Gemini), runs locally via Docker or hosted on Render

The frontend automatically detects and calls the backend when one is reachable (badge in the top-right shows "Backend connected" vs "Browser-only mode"). No backend needed for the site to work — it falls back to doing real analysis in-browser — but the backend gives frame-accurate cuts, real mp4 export, and AI reasoning via Gemini.

## Backend

Real pipeline: FFmpeg via `imageio-ffmpeg` (cut/silence/loudness/captions — no system install needed, works without Docker too) + faster-whisper (transcription) + OpenCV (reference pacing) + Gemini API (plan reasoning).

**Tuned for low-spec CPUs (e.g. older i5, no GPU, 8GB RAM):**
- Whisper model: `tiny` (~75MB, works on 4GB RAM / 2 cores) — lazy-loaded, so it costs nothing in RAM until a caption request actually happens

## Setup

1. Copy `.env.example` to `.env` and put your real Gemini API key in it:
   ```
   cp .env.example .env
   ```
2. Start it:
   ```
   docker compose up --build
   ```

## Every time after that
The container is set to `restart: unless-stopped`, so once built it comes back automatically whenever Docker Desktop is running — you don't need to run any commands most of the time.

If you do need to start/stop manually, just double-click:
- **start.bat** — starts it in the background, no terminal window needs to stay open
- **stop.bat** — stops it

Or from the command line: `docker compose up -d` / `docker compose down`.

API at http://localhost:8000 (docs at /docs).

## Hosting on Render (no Docker required there)
This backend also runs as a plain Python web service (Render's free tier doesn't support Docker without a paid plan in some workspace types) — FFmpeg is bundled via the `imageio-ffmpeg` pip package, no system install needed:
- **Runtime**: Docker (if your Render workspace allows free Docker) or Python
- **Build command**: `pip install -r requirements.txt`
- **Start command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Environment variable**: `GEMINI_API_KEY` — set your real key directly in Render's dashboard, never commit it to git

## Pipeline
1. `POST /upload` — raw clips + optional reference → job_id
2. `POST /analyze` — real ffmpeg silencedetect/loudnorm on raw, real OpenCV cut-rhythm on reference
3. `POST /plan` — Gemini explains the plan from the measured facts (no invented numbers)
4. `POST /render` — real ffmpeg cut+concat+normalize → real mp4; optional Whisper transcript + burned captions
5. `GET /jobs` / `DELETE /jobs` — see or wipe stored jobs. Jobs auto-evict (oldest first) past `MAX_KEPT_JOBS` (default 20) so disk/memory never grow unbounded.

