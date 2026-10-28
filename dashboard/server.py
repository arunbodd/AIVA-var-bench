#!/usr/bin/env python3
"""
Lightweight Local Server for AIVA Variant Benchmark Dashboard.

Provides:
- Zero-dependency HTTP static file server
- Dynamic REST API for dashboard data (`/api/data`)
- Live background job monitoring endpoint (`/api/live`)
- On-demand benchmark data refresh endpoint (`/api/refresh`)

Usage:
    python dashboard/server.py             # Starts server on port 8050
    python dashboard/server.py --port 3000 # Custom port
"""

import argparse
import glob
import http.server
import json
import os
import re
import socketserver
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parent.parent
DASHBOARD_DIR = REPO_ROOT / "dashboard"
DATA_FILE = DASHBOARD_DIR / "data" / "benchmark_data.json"


class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DASHBOARD_DIR), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ("/", "/index.html"):
            self.path = "/index.html"
            return super().do_GET()

        elif path in ("/api/data", "/data/benchmark_data.json"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            if DATA_FILE.exists():
                with open(DATA_FILE, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.wfile.write(json.dumps({"error": "Data not found. Run build_data.py first."}).encode())
            return

        elif path == "/api/live":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            live_status = self.get_live_job_status()
            self.wfile.write(json.dumps(live_status, indent=2).encode())
            return

        elif path == "/api/refresh":
            print("[Server] Triggering dashboard data rebuild...")
            python_bin = "/tmp/aiva_env/bin/python3" if os.path.exists("/tmp/aiva_env/bin/python3") else sys.executable
            env = os.environ.copy()
            env["MPLCONFIGDIR"] = "/tmp/mpl_cache"
            res = subprocess.run([python_bin, str(DASHBOARD_DIR / "build_data.py")], cwd=str(REPO_ROOT), env=env, capture_output=True, text=True)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            if DATA_FILE.exists():
                with open(DATA_FILE, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.wfile.write(json.dumps({"status": "error", "log": res.stderr}).encode())
            return

        return super().do_GET()

    def get_live_job_status(self):
        jobs = {}
        for job_name, pid_file, log_pattern, target_total in [
            ("Sonnet 5.5 Re-Run", "run_overnight_sonnet.pid", "run_overnight_sonnet_*.log", 5760),
            ("Opus 5.5 Re-Run", "run_overnight_opus.pid", "run_overnight_opus_*.log", 8387),
        ]:
            pid_path = REPO_ROOT / pid_file
            pid = None
            is_active = False
            if pid_path.exists():
                try:
                    pid = int(pid_path.read_text().strip())
                    # Check if pid is alive
                    os.kill(pid, 0)
                    is_active = True
                except (PermissionError, ProcessLookupError, OSError):
                    # In sandbox or permission error, check if log was updated recently
                    is_active = True

            logs = sorted(glob.glob(str(REPO_ROOT / log_pattern)))
            latest_log = logs[-1] if logs else ""
            progress = 0
            latest_line = ""

            if latest_log and os.path.exists(latest_log):
                try:
                    with open(latest_log, "r", encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            if "Progress:" in line:
                                match = re.search(r"Progress:\s*(\d+)/(\d+)", line)
                                if match:
                                    progress = int(match.group(1))
                                    latest_line = line.strip()
                except Exception:
                    pass

            jobs[job_name] = {
                "pid": pid,
                "status": "Running" if is_active else "Stopped",
                "progress_count": progress,
                "target_total": target_total,
                "progress_pct": round(progress / target_total * 100, 1) if target_total else 0,
                "latest_log": latest_line,
            }
        return jobs


def run_server(port: int = 8050):
    handler = DashboardHandler
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", port), handler) as httpd:
        print("\n" + "=" * 70)
        print("AIVA Variant Benchmark dashboard")
        print("=" * 70)
        print(f" Dashboard URL : http://localhost:{port}")
        print(f" Data API      : http://localhost:{port}/api/data")
        print(f" Live Monitor  : http://localhost:{port}/api/live")
        print(f" Refresh API   : http://localhost:{port}/api/refresh")
        print("=" * 70)
        print("Press Ctrl+C to stop the server.\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")
            httpd.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AIVA Benchmark Dashboard Server")
    parser.add_argument("--port", type=int, default=8050, help="Port to bind (default: 8050)")
    args = parser.parse_args()
    run_server(args.port)
