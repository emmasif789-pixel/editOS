import httpx, os, json

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"


async def generate_plan_reasoning(intent: str, facts: dict) -> str:
    """Ask Gemini to explain the edit plan in plain language, grounded ONLY in
    real measured facts from ffmpeg/OpenCV — no invented numbers."""
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set on this server")

    prompt = f"""You are EditOS, an AI video editor. Explain the edit plan for a "{intent}" video in 4-6 short bullet points, in plain confident language. Base every claim ONLY on these measured facts, do not invent numbers:

{json.dumps(facts, indent=2)}

Output plain bullet points, no preamble."""

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            GEMINI_URL,
            params={"key": GEMINI_API_KEY},
            json={"contents": [{"parts": [{"text": prompt}]}]},
        )
        r.raise_for_status()
        data = r.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except (KeyError, IndexError, TypeError):
            raise RuntimeError(f"Unexpected Gemini response shape: {json.dumps(data)[:300]}")
