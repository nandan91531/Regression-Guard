#!/usr/bin/env python3
"""
Regression Guard HTTP Web Server & SSE Streaming API.
"""

import json
import os
import queue
import sys
import threading
import time
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import requests

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from regression_guard.config import Config
from regression_guard.cli import run as run_pipeline

PORT = 8000
HOST = "127.0.0.1"
UI_DIR = os.path.join(os.path.dirname(__file__), "ui")
log_queue = queue.Queue()

class RegressionGuardHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=UI_DIR, **kwargs)

    def do_GET(self):
        if self.path == "/api/models":
            self.handle_api_models()
        elif self.path == "/api/stream":
            self.handle_api_stream()
        elif self.path == "/api/report":
            self.handle_api_report()
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == "/api/run":
            self.handle_api_run()
        else:
            self.send_error(404, "Endpoint not found")

    def handle_api_models(self):
        try:
            res = requests.get("http://localhost:11434/api/tags", timeout=5)
            if res.status_code == 200:
                data = res.json()
                models = data.get("models", [])
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"models": models}).encode("utf-8"))
                return
        except Exception:
            pass

        # Fallback default models list
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"models": [{"name": "llama3.2"}]}).encode("utf-8"))

    def handle_api_run(self):
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)
        payload = json.loads(post_data.decode("utf-8"))

        config = Config(
            repo=payload.get("repo", "humanize"),
            buggy_commit=payload.get("buggy", "7574e0c"),
            fixed_commit=payload.get("fixed", "823ad60"),
            test_file=payload.get("test_file", "tests/test_filesize.py"),
            model=payload.get("model", "llama3.2"),
            timeout=int(payload.get("timeout", 180)),
            max_attempts=int(payload.get("max_attempts", 3)),
            keep_workspaces=False
        )

        # Clear log queue
        while not log_queue.empty():
            try:
                log_queue.get_nowait()
            except queue.Empty:
                break

        def log_callback(msg: str):
            log_queue.put(msg)

        def worker():
            try:
                run_pipeline(config, log_callback=log_callback)
            except Exception as e:
                log_queue.put(f"❌ Server Execution Error: {e}")

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "started"}).encode("utf-8"))

    def handle_api_stream(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        idle_count = 0
        while idle_count < 180:
            try:
                msg = log_queue.get(timeout=1.0)
                formatted_msg = f"data: {msg}\n\n"
                self.wfile.write(formatted_msg.encode("utf-8"))
                self.wfile.flush()
                idle_count = 0
                if "STEP_COMPLETE" in msg or "⚠️ Could not generate" in msg:
                    break
            except (queue.Empty, Exception):
                idle_count += 1

    def handle_api_report(self):
        report_path = os.path.join(os.path.dirname(__file__), "regression_report.md")
        if os.path.exists(report_path):
            with open(report_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/markdown; charset=utf-8")
            self.end_headers()
            self.wfile.write(content.encode("utf-8"))
        else:
            self.send_error(444, "Report not found")

def start_server():
    server_address = (HOST, PORT)
    ThreadingHTTPServer.allow_reuse_address = True
    httpd = ThreadingHTTPServer(server_address, RegressionGuardHandler)
    print(f"🚀 Regression Guard Web UI running at http://{HOST}:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        httpd.server_close()

if __name__ == "__main__":
    start_server()
