"""Tiny stdlib-only Ollama client. No pip installs needed, nothing leaves localhost."""
import json
import os
import urllib.error
import urllib.request

_raw = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
HOST = _raw if _raw.startswith("http") else "http://" + _raw
DEFAULT_MODEL = os.environ.get("REVENANT_MODEL", "qwen2.5:3b")


class OllamaError(RuntimeError):
    pass


def _get(path, timeout=3):
    with urllib.request.urlopen(HOST + path, timeout=timeout) as r:
        return r.read().decode()


def is_up():
    try:
        return "Ollama is running" in _get("/")
    except (urllib.error.URLError, OSError):
        return False


def list_models():
    try:
        data = json.loads(_get("/api/tags"))
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise OllamaError(f"cannot reach Ollama at {HOST}: {e}")
    return [m["name"] for m in data.get("models", [])]


def chat(messages, model=None, *, keep_alive="30m", num_predict=60,
         temperature=0.9, timeout=30):
    payload = {
        "model": model or DEFAULT_MODEL,
        "messages": messages,
        "stream": False,
        "keep_alive": keep_alive,
        "options": {"num_predict": num_predict, "temperature": temperature},
    }
    req = urllib.request.Request(
        HOST + "/api/chat",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.load(r)
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise OllamaError(str(e))
    try:
        return data["message"]["content"].strip()
    except KeyError:
        raise OllamaError(f"unexpected reply: {data}")


def chat_stream(messages, model=None, *, keep_alive="30m", num_predict=220,
                temperature=0.8, timeout=120):
    """Yield {"token": str} per piece, then one {"done": True, ...} carrying Ollama's own timings."""
    payload = {
        "model": model or DEFAULT_MODEL,
        "messages": messages,
        "stream": True,
        "keep_alive": keep_alive,
        "options": {"num_predict": num_predict, "temperature": temperature},
    }
    req = urllib.request.Request(
        HOST + "/api/chat",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            for raw in r:
                raw = raw.strip()
                if not raw:
                    continue
                obj = json.loads(raw)
                if obj.get("error"):
                    raise OllamaError(obj["error"])
                piece = (obj.get("message") or {}).get("content", "")
                if piece:
                    yield {"token": piece}
                if obj.get("done"):
                    yield {"done": True, "eval_count": obj.get("eval_count"),
                           "eval_duration": obj.get("eval_duration"),
                           "load_duration": obj.get("load_duration")}
                    return
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = json.loads(e.read()).get("error", "")
        except (ValueError, OSError):
            pass
        raise OllamaError(detail or f"Ollama answered HTTP {e.code}")
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise OllamaError(str(e))
