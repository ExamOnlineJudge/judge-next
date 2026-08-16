#!/usr/bin/env python3
import http.server
import json
import os
import pty
import select
import shutil
import signal
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
from typing import Dict, Any

PORT = int(os.environ.get("PORT", "5055"))
HOST = os.environ.get("HOST", "0.0.0.0")

# Import or locate interactive_runner
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from toolchain_discovery import discover_installed_languages

# Dynamic language and toolchain catalog (auto-discovered on boot and cached)
_CACHED_CATALOG = None
_CACHE_TIME = 0

def get_dynamic_catalog():
    global _CACHED_CATALOG, _CACHE_TIME
    now = time.time()
    if _CACHED_CATALOG is None or now - _CACHE_TIME > 30: # Refresh every 30s
        try:
            _CACHED_CATALOG = discover_installed_languages()
            _CACHE_TIME = now
        except Exception as e:
            print(f"Warning: Toolchain discovery error: {e}", file=sys.stderr)
            if _CACHED_CATALOG is None:
                _CACHED_CATALOG = []
    return _CACHED_CATALOG

# In-memory interactive sessions
sessions: Dict[str, Any] = {}
sessions_lock = threading.Lock()

class JudgeHTTPHandler(http.server.BaseHTTPRequestHandler):
    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")
        query = urllib.parse.parse_qs(parsed.query)

        if path in ("/api/languages", "/languages"):
            catalog = get_dynamic_catalog()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_cors_headers()
            self.end_headers()
            response_payload = {
                "defaultLanguageId": "c",
                "languages": catalog,
                "total": len(catalog),
            }
            self.wfile.write(json.dumps(response_payload).encode("utf-8"))
            return

        if path in ("/api/health", "/health"):
            catalog = get_dynamic_catalog()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "languagesCount": len(catalog)}).encode("utf-8"))
            return

        self.send_response(404)
        self.send_header("Content-Type", "application/json")
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps({"error": "Not Found"}).encode("utf-8"))

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")

        content_length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(content_length)
        try:
            body = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
        except Exception:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Invalid JSON body"}).encode("utf-8"))
            return

        if path in ("/api/judge/run", "/run"):
            # Execute runner directly synchronously
            lang = body.get("language", "c23")
            code = body.get("code", "")
            stdin = body.get("stdin", "")
            runner_py = os.path.join(CURRENT_DIR, "interactive_runner.py")

            try:
                proc = subprocess.Popen(
                    [sys.executable, runner_py, lang, code],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                stdout, stderr = proc.communicate(input=stdin, timeout=10)
                lines = stdout.strip().split("\n")
                result_payload = {"stdout": stdout, "stderr": stderr}
                for line in reversed(lines):
                    try:
                        parsed_line = json.loads(line)
                        if parsed_line.get("type") in ("complete", "status"):
                            result_payload = parsed_line
                            break
                    except Exception:
                        pass

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(result_payload).encode("utf-8"))
            except subprocess.TimeoutExpired:
                proc.kill()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"type": "complete", "status": "TLE", "error": "Execution Timeout (5.0s exceeded)"}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            return

        self.send_response(404)
        self.send_header("Content-Type", "application/json")
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps({"error": "Not Found"}).encode("utf-8"))

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True

def run_server():
    catalog = get_dynamic_catalog()
    server = ThreadedHTTPServer((HOST, PORT), JudgeHTTPHandler)
    print(f"🚀 [EOJ Judge Server] Listening on http://{HOST}:{PORT} (Auto-Discovered Languages: {len(catalog)})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Stopping Judge Server...")
        server.server_close()

if __name__ == "__main__":
    run_server()
