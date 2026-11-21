"""page-server: a small local web page for a voice chatbot, using only Python's standard library.

Usage: python page-server.py [PORT=8765]
Open http://127.0.0.1:PORT/ on this computer. The page records from the microphone and sends the sound to /talk.
Here /talk only says how much sound arrived: put speech-whisper, the answer and voice-piper or voice-kokoro in reply().
It listens on 127.0.0.1 only, so other computers on the wifi cannot open it.
"""
import http.server
import json
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
MAX_UPLOAD = 20 * 1024 * 1024

PAGE = """<!doctype html><html lang="hi"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Helpline</title>
<style>body{font:18px system-ui;max-width:36em;margin:2em auto;padding:0 1em}button{font-size:1.2em;padding:.6em 1.2em}
#log p{margin:.4em 0}</style>
<h1>Ask a question</h1><button id="b">Hold to speak</button><div id="log"></div>
<script>
const b = document.getElementById('b'), log = document.getElementById('log');
let rec, parts = [];
function say(t){ const p = document.createElement('p'); p.textContent = t; log.prepend(p); }
async function start(){
  const s = await navigator.mediaDevices.getUserMedia({audio: true});
  rec = new MediaRecorder(s); parts = [];
  rec.ondataavailable = e => parts.push(e.data);
  rec.onstop = async () => {
    s.getTracks().forEach(t => t.stop());
    const r = await fetch('/talk', {method: 'POST', body: new Blob(parts, {type: rec.mimeType})});
    const j = await r.json(); say(j.text);
    if (j.audio_url) new Audio(j.audio_url).play();
  };
  rec.start();
}
b.onpointerdown = start; b.onpointerup = () => rec && rec.state === 'recording' && rec.stop();
</script></html>"""


def reply(audio: bytes, mime: str) -> dict:
    """Turn the question's sound into an answer. Replace this with speech-whisper, an answer, and a voice."""
    return {"text": f"Got {len(audio)} bytes of {mime or 'sound'}."}


class Handler(http.server.BaseHTTPRequestHandler):
    def send(self, code, ctype, body):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/":
            return self.send(200, "text/html; charset=utf-8", PAGE.encode())
        self.send(404, "text/plain", b"not found")

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        if self.path != "/talk" or n > MAX_UPLOAD:
            return self.send(400, "application/json", b'{"text": "too large or wrong address"}')
        answer = reply(self.rfile.read(n), self.headers.get("Content-Type", ""))
        self.send(200, "application/json", json.dumps(answer, ensure_ascii=False).encode())

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"open http://127.0.0.1:{PORT}/")
    srv.serve_forever()
