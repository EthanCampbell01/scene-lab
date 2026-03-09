from __future__ import annotations

import os
import time
from typing import Optional

import requests


def call_openrouter(system: str, user: str, timeout_s: int) -> str:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY env var is required for provider=openrouter")

    model = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://localhost/scene-kit",
        "X-Title": "Scene Kit Pipeline",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": float(os.getenv("OPENROUTER_TEMPERATURE", "0.7")),
    }

    r = requests.post(url, headers=headers, json=payload, timeout=timeout_s)
    r.raise_for_status()
    data = r.json()
    return data["choices"][0]["message"]["content"]


def call_ollama(system: str, user: str, timeout_s: int) -> str:
    model = os.getenv("OLLAMA_MODEL", "mistral:7b-instruct")
    base = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")

    temperature = float(os.getenv("OLLAMA_TEMPERATURE", "0.3"))
    num_predict = int(os.getenv("OLLAMA_NUM_PREDICT", "2048"))

    chat_url = f"{base}/api/chat"
    chat_payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "format": "json",
        "options": {
            "temperature": temperature,
            "num_predict": num_predict,
        },
    }

    r = requests.post(chat_url, json=chat_payload, timeout=timeout_s)
    r.raise_for_status()
    data = r.json()

    msg = data.get("message")
    if isinstance(msg, dict) and "content" in msg:
        return msg["content"]

    return data.get("response", "")


def model_call(provider: str, system: str, user: str, timeout_s: int, retries: int = 2) -> str:
    last_err: Optional[Exception] = None

    for attempt in range(retries + 1):
        try:
            if provider == "openrouter":
                return call_openrouter(system, user, timeout_s)
            return call_ollama(system, user, timeout_s)

        except Exception as e:
            last_err = e
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
            else:
                raise

    raise last_err