import httpx, os, json

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://ollama:11434")
MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:1b")

async def generate_plan_reasoning(intent: str, facts: dict) -> str:
    """Ask the local model to explain the edit plan in plain language, grounded in real measured facts."""
    prompt = f"""You are EditOS, an AI video editor. Explain the edit plan for a "{intent}" video in 4-6 short bullet points, in plain confident language. Base every claim ONLY on these measured facts, do not invent numbers:

{json.dumps(facts, indent=2)}

Output plain bullet points, no preamble."""
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(f"{OLLAMA_URL}/api/generate", json={
            "model": MODEL, "prompt": prompt, "stream": False
        })
        r.raise_for_status()
        return r.json().get("response", "").strip()
