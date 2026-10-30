"""The Séance Room: a dependency-free local web server.

Serves the UI in revenant/web and streams spirit replies from Ollama over server-sent events.
It binds to loopback only and nothing in here talks to the internet.
"""
import json
import mimetypes
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from . import __version__, ollama, spirits
from .cli import model_for

WEB = (Path(__file__).resolve().parent / "web").resolve()
MAX_BODY = 64 * 1024      # bytes accepted in a chat request
MAX_TURNS = 12            # most recent messages kept as context
MAX_CHARS = 2000          # per message
LOOPBACK = {"127.0.0.1", "localhost", "::1"}
HEX = spirits.HEX
CSP = ("default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
       "script-src 'self'; connect-src 'self'; font-src 'self'; frame-ancestors 'none'; base-uri 'none'")

for _ext, _kind in ((".woff2", "font/woff2"), (".js", "text/javascript"),
                    (".css", "text/css"), (".svg", "image/svg+xml")):
    mimetypes.add_type(_kind, _ext)


def public(spirit):
    """What the browser may know about a spirit (never the prompts)."""
    return {
        "name": spirit["name"],
        "display": spirit["display"],
        "short": spirit["display_short"],
        "glyph": spirit.get("glyph", "☠"),
        "born": spirit.get("born"),
        "death": spirit.get("cause_of_death"),
        "greeting": spirit.get("greeting", ""),
        "hex": HEX.get(spirit.get("color"), "#f3e9d2"),
        "model": model_for(spirit),
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "Revenant/" + __version__
    allowed_hosts = frozenset()

    def log_message(self, fmt, *args):  # keep the terminal quiet; the ghost is the only thing talking
        pass

    # ------------------------------------------------------------ helpers
    def _headers(self, code, ctype, length=None, extra=()):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        if length is not None:
            self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", CSP)
        self.send_header("Referrer-Policy", "no-referrer")
        for k, v in extra:
            self.send_header(k, v)
        self.end_headers()

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self._headers(code, "application/json; charset=utf-8", len(body))
        self.wfile.write(body)

    def _fail(self, code, message):
        self._json(code, {"error": message})

    def _sse(self, obj):
        self.wfile.write(b"data: " + json.dumps(obj).encode() + b"\n\n")
        self.wfile.flush()

    def _host_ok(self):
        # Defends against DNS rebinding: only our own loopback names are served.
        return self.headers.get("Host", "").lower() in self.allowed_hosts

    # ------------------------------------------------------------ GET
    def do_GET(self):
        if not self._host_ok():
            return self._fail(403, "unexpected Host header")
        path = urlsplit(self.path).path
        if path == "/api/spirits":
            return self._json(200, [public(spirits.load(n)) for n in spirits.names()])
        if path == "/api/status":
            try:
                models = ollama.list_models()
            except ollama.OllamaError:
                models = []
            return self._json(200, {"ollama": ollama.is_up(), "models": models, "version": __version__})
        if path.startswith("/api/"):
            return self._fail(404, "no such endpoint")
        self._static(path)

    def _static(self, path):
        rel = path.lstrip("/") or "index.html"
        target = (WEB / rel).resolve()
        if not target.is_relative_to(WEB) or not target.is_file():
            return self._fail(404, "not found")
        data = target.read_bytes()
        ctype = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("text/javascript", "image/svg+xml"):
            ctype += "; charset=utf-8"
        self._headers(200, ctype, len(data))
        self.wfile.write(data)

    # ------------------------------------------------------------ POST
    def do_POST(self):
        if not self._host_ok():
            return self._fail(403, "unexpected Host header")
        if urlsplit(self.path).path != "/api/chat":
            return self._fail(404, "no such endpoint")
        origin = self.headers.get("Origin")
        if origin and origin.lower() not in {"http://" + h for h in self.allowed_hosts}:
            return self._fail(403, "cross-origin request refused")
        if self.headers.get("Content-Type", "").split(";")[0].strip().lower() != "application/json":
            return self._fail(415, "send application/json")
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            return self._fail(411, "Content-Length required")
        if length < 0 or length > MAX_BODY:
            return self._fail(413, "request too large")
        try:
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                raise ValueError
        except ValueError:
            return self._fail(400, "invalid JSON")
        self._chat(body)

    def _chat(self, body):
        name = body.get("spirit")
        if not isinstance(name, str) or name not in spirits.names():  # whitelist: name becomes a file path
            return self._fail(400, "unknown spirit")
        raw = body.get("messages")
        if not isinstance(raw, list):
            return self._fail(400, "messages must be a list")
        msgs = []
        for m in raw[-MAX_TURNS:]:
            if not isinstance(m, dict):
                continue
            role, content = m.get("role"), m.get("content")
            if role in ("user", "assistant") and isinstance(content, str) and content.strip():
                msgs.append({"role": role, "content": content[:MAX_CHARS]})
        while msgs and msgs[0]["role"] == "assistant":
            msgs.pop(0)
        if not msgs or msgs[-1]["role"] != "user":
            return self._fail(400, "the last message must come from the user")

        spirit = spirits.load(name)
        model = model_for(spirit)
        system = spirit.get("seance_system") or spirit["system"]
        gen = ollama.chat_stream([{"role": "system", "content": system}] + msgs, model)

        self._headers(200, "text/event-stream; charset=utf-8", extra=(("X-Accel-Buffering", "no"),))
        t0, chunks, stats = time.perf_counter(), 0, {}
        try:
            for ev in gen:  # {"token": str} pieces, then one {"done": True, ...Ollama's own timings}
                if "token" in ev:
                    chunks += 1
                    self._sse({"t": ev["token"]})
                elif ev.get("done"):
                    stats = ev
            tps = None
            if stats.get("eval_count") and stats.get("eval_duration"):
                tps = round(stats["eval_count"] / (stats["eval_duration"] / 1e9), 1)
            self._sse({"done": True, "ms": int((time.perf_counter() - t0) * 1000),
                       "tokens": stats.get("eval_count") or chunks, "tps": tps, "model": model})
        except ollama.OllamaError as e:
            self._sse({"error": str(e), "kind": "model" if ollama.is_up() else "down", "model": model})
        except (BrokenPipeError, ConnectionResetError):
            pass  # the visitor left; closing the generator tells Ollama to stop
        finally:
            gen.close()


def serve(host="127.0.0.1", port=8666):
    hosts = {f"{host}:{port}"}
    if host in LOOPBACK:
        hosts |= {f"127.0.0.1:{port}", f"localhost:{port}", f"[::1]:{port}"}
    else:
        print(f"warning: binding to {host} exposes the Séance Room beyond this machine.", file=sys.stderr)
    Handler.allowed_hosts = frozenset(h.lower() for h in hosts)
    try:
        httpd = ThreadingHTTPServer((host, port), Handler)
    except OSError as e:
        print(f"cannot open the Séance Room on {host}:{port}: {e}", file=sys.stderr)
        return 1
    httpd.daemon_threads = True
    print(f"  The Séance Room is open: http://{'localhost' if host in LOOPBACK else host}:{port}")
    print("  Ctrl+C ends the séance.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  The séance is over.")
    finally:
        httpd.server_close()
    return 0
