"""POST /api/analyze

Two ways to call it:
  1. Raw audio bytes as the body (Content-Type: audio/*), optional ?filename=call.mp3
     -> transcribed with Groq's hosted Whisper, then scored.
  2. JSON {"text": "..."} -> skips transcription and only scores the text
     (handy for testing without an API key).

Needs the GROQ_API_KEY environment variable for audio uploads.
Vercel limits request bodies to ~4.5 MB, so keep clips short.
"""
import json
import os
import sys
import uuid
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.dirname(__file__))
from _scorer import score_text  # noqa: E402

GROQ_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
GROQ_MODEL = "whisper-large-v3-turbo"
MAX_BYTES = 4 * 1024 * 1024  # stay under Vercel's 4.5 MB body limit


def transcribe(audio: bytes, filename: str, content_type: str) -> str:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set on the server.")

    boundary = uuid.uuid4().hex
    parts = []

    def field(name, value):
        parts.append(
            (f"--{boundary}\r\nContent-Disposition: form-data; "
             f'name="{name}"\r\n\r\n{value}\r\n').encode()
        )

    field("model", GROQ_MODEL)
    field("response_format", "json")
    field("temperature", "0")
    parts.append(
        (f"--{boundary}\r\nContent-Disposition: form-data; "
         f'name="file"; filename="{filename}"\r\n'
         f"Content-Type: {content_type}\r\n\r\n").encode()
    )
    parts.append(audio)
    parts.append(f"\r\n--{boundary}--\r\n".encode())
    body = b"".join(parts)

    req = urllib.request.Request(
        GROQ_URL,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "scam-detector-demo/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=40) as resp:
            return json.loads(resp.read()).get("text", "").strip()
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")[:300]
        raise RuntimeError(f"Speech-to-text failed ({e.code}): {detail}")


class handler(BaseHTTPRequestHandler):
    def _send(self, status: int, payload: dict):
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            if length <= 0:
                return self._send(400, {"error": "Empty request body."})
            if length > MAX_BYTES:
                return self._send(413, {"error": "File too large. Use a clip under 4 MB."})

            body = self.rfile.read(length)
            ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip()

            if ctype == "application/json":
                text = str(json.loads(body).get("text", "")).strip()
                if not text:
                    return self._send(400, {"error": "No text provided."})
            else:
                qs = parse_qs(urlparse(self.path).query)
                filename = os.path.basename(qs.get("filename", ["call.mp3"])[0]) or "call.mp3"
                filename = filename.replace('"', "")
                text = transcribe(body, filename, ctype or "application/octet-stream")
                if not text:
                    return self._send(200, {
                        "transcript": "", "score": 0, "level": "LOW",
                        "reasons": [], "note": "No speech detected in the audio.",
                    })

            score, level, reasons = score_text(text)
            self._send(200, {
                "transcript": text, "score": score,
                "level": level, "reasons": reasons,
            })
        except json.JSONDecodeError:
            self._send(400, {"error": "Invalid JSON."})
        except Exception as e:  # keep the demo friendly instead of a bare 500
            self._send(500, {"error": str(e)})

    def do_GET(self):
        self._send(200, {"status": "ok", "use": "POST audio bytes or {\"text\": ...}"})
