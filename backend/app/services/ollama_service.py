import requests

from backend.app.core.config import settings


def ask_ollama(prompt: str) -> str:
    response = requests.post(
        f"{settings.ollama_base_url}/api/generate",
        json={
            "model": settings.ollama_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_ctx": 1024,
                "num_predict": 250,
                "temperature": 0.3,
                "num_thread": 0,
            },
        },
        timeout=60,
    )

    response.raise_for_status()

    data = response.json()
    return data.get("response", "").strip()