"""Minimal static web server for the Atlas demo - Railway / cloud ready.

Serves ONLY atlas_nis2_intake.html (at '/'), so nothing else in the repo -
the engine source, tests, README, or the internal .docx files - is ever
exposed on the public URL. Binds to 0.0.0.0 on the platform's $PORT.

No third-party dependencies; standard library only.
    Local:   python server.py        (then open http://localhost:8765)
    Railway: runs automatically via the Procfile ('web: python server.py').
"""

import http.server
import os
import socketserver

PORT = int(os.environ.get("PORT", "8765"))
ARTIFACT = "atlas_nis2_intake.html"


class Handler(http.server.BaseHTTPRequestHandler):
    def _send(self, body: bytes = b"", code: int = 200,
              ctype: str = "text/html; charset=utf-8") -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html", "/" + ARTIFACT):
            try:
                with open(ARTIFACT, "rb") as f:
                    self._send(f.read())
            except OSError:
                self._send(b"artifact not found", 500, "text/plain")
        else:
            self._send(b"not found", 404, "text/plain")

    def do_HEAD(self) -> None:  # platform health checks
        self._send()

    def log_message(self, *args) -> None:  # quiet logs
        pass


if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
        print(f"Atlas demo serving on 0.0.0.0:{PORT}")
        httpd.serve_forever()
