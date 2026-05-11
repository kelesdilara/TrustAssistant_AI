import requests

from backend.app.core.config import settings


def ask_ollama(prompt: str) -> str:
    response = requests.post(
        f"{settings.ollama_base_url}/api/generate",
        json={
            "model": settings.ollama_model,
            "prompt": prompt,
            "stream": False,
        },
        timeout=120,
    )

    response.raise_for_status()

    data = response.json()
    return data.get("response", "").strip()