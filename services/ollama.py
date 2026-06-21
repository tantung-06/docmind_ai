"""
services/ollama.py — Giao tiếp với Ollama API (streaming + health check)
"""

import json
import requests
from config import OLLAMA_BASE_URL, OLLAMA_MODEL


def chat_stream(messages: list[dict]):
    """
    Generator: gọi Ollama /api/chat với stream=True, yield từng token.

    Args:
        messages: Danh sách message theo chuẩn OpenAI Chat format.

    Yields:
        str — từng token text từ model.
    """
    url     = f"{OLLAMA_BASE_URL}/api/chat"
    payload = {
        "model":   OLLAMA_MODEL,
        "messages": messages,
        "stream":  True,
        "keep_alive": "10m",
        "options": {
            "temperature": 0.1,
            "num_ctx": 2048,
            "num_predict": 256
            },
    }
    try:
        with requests.post(url, json=payload, stream=True, timeout=120) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                data  = json.loads(line)
                token = data.get("message", {}).get("content", "")
                if token:
                    yield token
                if data.get("done"):
                    break
    except requests.exceptions.ConnectionError:
        yield f"\n\nKhông thể kết nối Ollama tại {OLLAMA_BASE_URL}"
    except Exception as exc:
        yield f"\n\nLỗi: {exc}"


def health() -> dict:
    """
    Kiểm tra Ollama đang chạy và model đã được tải chưa.

    Returns:
        dict với các key: ok, models, target_model, model_ready.
    """
    try:
        r      = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        models = [m["name"] for m in r.json().get("models", [])]
        return {
            "ok":          True,
            "models":      models,
            "target_model": OLLAMA_MODEL,
            "model_ready": any(OLLAMA_MODEL in m for m in models),
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc), "models": [], "model_ready": False}