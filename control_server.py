#!/usr/bin/env python3
"""Safety-focused local web controller for the Tennis PCA9685 project."""

import json
import math
import os
import re
import signal
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


HOST = "192.168.99.1"
PORT = 8080
BASE = Path("/home/pi/Tennis")
RUN_DIR = BASE / ".run"
PID_FILE = RUN_DIR / "tennis.pid"
LOG_FILE = RUN_DIR / "tennis.log"
INDEX_FILE = BASE / "web" / "index.html"
TENNIS = Path("/home/pi/.local/bin/tennis")
HEARTBEAT_TIMEOUT = 8.0
ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")

DEFAULT_SETTINGS = {
    "channel_a": 2, "channel_b": 4,
    "enabled_a": True, "enabled_b": True,
    "a_pct": 30.0, "b_pct": 30.0,
}
CHANNEL_OPTIONS = range(1, 8)


class ControlState:
    def __init__(self):
        self.lock = threading.RLock()
        self.watchdog_armed = False
        self.last_heartbeat = 0.0
        self.started_at = None
        self.active_settings = None
        self.last_event = "Control service started; hardware remains safely off"
        self.last_error = None


STATE = ControlState()
SHUTDOWN = threading.Event()


def clean_output(value):
    return ANSI_RE.sub("", value or "").strip()


def run_tennis(*args, timeout=12):
    env = os.environ.copy()
    env["HOME"] = "/home/pi"
    result = subprocess.run(
        [str(TENNIS), *args],
        text=True,
        capture_output=True,
        timeout=timeout,
        env=env,
        check=False,
    )
    output = clean_output("\n".join(part for part in (result.stdout, result.stderr) if part))
    if result.returncode != 0:
        raise RuntimeError(output or f"tennis {' '.join(args)} failed ({result.returncode})")
    return output


def process_command(pid):
    try:
        return Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode("utf-8", "replace")
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        return ""


def find_controller():
    candidates = []
    try:
        candidates.append(int(PID_FILE.read_text().strip()))
    except (FileNotFoundError, ValueError):
        pass

    try:
        proc_entries = Path("/proc").iterdir()
    except OSError:
        proc_entries = []
    for entry in proc_entries:
        if entry.name.isdigit():
            candidates.append(int(entry.name))

    seen = set()
    for pid in candidates:
        if pid in seen:
            continue
        seen.add(pid)
        command = process_command(pid)
        if str(BASE / "pca_ch1_30pct.py") in command:
            return pid, "steady"
    return None, None


def status_payload():
    pid, mode = find_controller()
    now = time.time()
    with STATE.lock:
        if pid is None and not STATE.watchdog_armed:
            STATE.started_at = None
            STATE.active_settings = None
        elapsed = max(0, int(now - STATE.started_at)) if STATE.started_at else 0
        heartbeat_age = max(0.0, time.monotonic() - STATE.last_heartbeat) if STATE.watchdog_armed else None
        return {
            "ok": True,
            "running": pid is not None,
            "mode": mode,
            "pid": pid,
            "elapsed_seconds": elapsed,
            "settings": dict(STATE.active_settings) if STATE.active_settings else None,
            "watchdog_armed": STATE.watchdog_armed,
            "heartbeat_timeout_seconds": int(HEARTBEAT_TIMEOUT),
            "heartbeat_age_seconds": round(heartbeat_age, 1) if heartbeat_age is not None else None,
            "last_event": STATE.last_event,
            "last_error": STATE.last_error,
            "server_time": int(now),
        }


def parse_settings(data):
    settings = {}
    for name in ("enabled_a", "enabled_b"):
        raw = data.get(name, DEFAULT_SETTINGS[name])
        if type(raw) is not bool:
            raise ValueError(f"{name} must be true or false")
        settings[name] = raw
    if not (settings["enabled_a"] or settings["enabled_b"]):
        raise ValueError("Turn on Motor A or Motor B before starting")
    for name in ("channel_a", "channel_b"):
        raw = data.get(name, DEFAULT_SETTINGS[name])
        if type(raw) is not int or raw not in CHANNEL_OPTIONS:
            raise ValueError(f"{name} must be a channel from 1 to 7")
        settings[name] = raw
    if settings["enabled_a"] and settings["enabled_b"] and settings["channel_a"] == settings["channel_b"]:
        raise ValueError("Choose two different channels")
    for name in ("a_pct", "b_pct"):
        default = DEFAULT_SETTINGS[name]
        raw = data.get(name, default)
        if isinstance(raw, bool):
            raise ValueError(f"Invalid value for {name}")
        try:
            value = float(raw)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid value for {name}") from exc
        minimum, maximum = 0.0, 100.0
        if not math.isfinite(value) or not minimum <= value <= maximum:
            raise ValueError(f"{name} must be between {minimum:g} and {maximum:g}")
        settings[name] = round(value, 1)
    return settings


def stop_motor(reason):
    with STATE.lock:
        STATE.watchdog_armed = False
    try:
        output = run_tennis("off")
        with STATE.lock:
            STATE.started_at = None
            STATE.active_settings = None
            STATE.last_event = reason
            STATE.last_error = None
        return output
    except Exception as exc:
        with STATE.lock:
            STATE.last_error = f"Stop failed: {exc}"
            STATE.last_event = reason
        raise


def format_number(value):
    return f"{value:g}"


def start_motor(mode, settings):
    if mode != "steady":
        raise ValueError("Only steady mode is available")
    stop_motor("Pre-start safety reset completed")
    args = [
        mode,
        "--channel-a",
        str(settings["channel_a"]),
        "--channel-b",
        str(settings["channel_b"]),
        "--a-pct",
        format_number(settings["a_pct"]),
        "--b-pct",
        format_number(settings["b_pct"]),
    ]
    if not settings["enabled_a"]:
        args.append("--disable-a")
    if not settings["enabled_b"]:
        args.append("--disable-b")
    output = run_tennis(*args)
    now = time.monotonic()
    with STATE.lock:
        STATE.watchdog_armed = True
        STATE.last_heartbeat = now
        STATE.started_at = time.time()
        STATE.active_settings = dict(settings)
        active = []
        if settings["enabled_a"]:
            active.append(f"A ch{settings['channel_a']} {settings['a_pct']:g}%")
        if settings["enabled_b"]:
            active.append(f"B ch{settings['channel_b']} {settings['b_pct']:g}%")
        STATE.last_event = f"{mode.upper()} started: {', '.join(active)}; running until stopped"
        STATE.last_error = None
    return output


def watchdog_loop():
    while not SHUTDOWN.wait(0.5):
        stop_reason = None
        with STATE.lock:
            armed = STATE.watchdog_armed
            heartbeat_expired = armed and time.monotonic() - STATE.last_heartbeat > HEARTBEAT_TIMEOUT
        if armed:
            pid, _ = find_controller()
            if pid is None:
                stop_reason = "Controller process ended unexpectedly; hardware reset completed"
            elif heartbeat_expired:
                stop_reason = "Control page disconnected for over 8 seconds; motor stopped automatically"
        if stop_reason:
            with STATE.lock:
                STATE.watchdog_armed = False
            try:
                stop_motor(stop_reason)
            except Exception:
                pass


class Handler(BaseHTTPRequestHandler):
    server_version = "TennisControl/1.2"

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} - {fmt % args}", flush=True)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:",
        )
        super().end_headers()

    def send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        if self.headers.get_content_type() != "application/json":
            raise ValueError("Request must use application/json")
        length = int(self.headers.get("Content-Length", "0"))
        if length < 1 or length > 4096:
            raise ValueError("Invalid request size")
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/":
            try:
                body = INDEX_FILE.read_bytes()
            except OSError as exc:
                self.send_json({"ok": False, "error": str(exc)}, 500)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif path == "/api/status":
            self.send_json(status_payload())
        elif path == "/api/log":
            try:
                lines = LOG_FILE.read_text(errors="replace").splitlines()[-40:]
            except FileNotFoundError:
                lines = []
            self.send_json({"ok": True, "lines": lines})
        else:
            self.send_json({"ok": False, "error": "Not found"}, 404)

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        try:
            if path == "/api/start":
                data = self.read_json()
                if data.get("safety_ack") is not True:
                    raise ValueError("Complete the safety check before starting")
                settings = parse_settings(data)
                output = start_motor(str(data.get("mode", "")), settings)
                self.send_json({**status_payload(), "message": output})
            elif path == "/api/stop":
                output = stop_motor("Emergency Stop pressed")
                self.send_json({**status_payload(), "message": output})
            elif path == "/api/heartbeat":
                self.read_json()
                with STATE.lock:
                    if STATE.watchdog_armed:
                        STATE.last_heartbeat = time.monotonic()
                self.send_json(status_payload())
            else:
                self.send_json({"ok": False, "error": "Not found"}, 404)
        except (ValueError, json.JSONDecodeError) as exc:
            self.send_json({"ok": False, "error": str(exc)}, 400)
        except subprocess.TimeoutExpired:
            self.send_json({"ok": False, "error": "Control command timed out. Disconnect motor power now."}, 504)
        except Exception as exc:
            self.send_json({"ok": False, "error": str(exc)}, 500)


def main():
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    stop_motor("Control service started; safety reset completed")
    watchdog = threading.Thread(target=watchdog_loop, name="watchdog", daemon=True)
    watchdog.start()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    server.daemon_threads = True

    def request_shutdown(signum, frame):
        del signum, frame
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, request_shutdown)
    signal.signal(signal.SIGINT, request_shutdown)
    print(f"Tennis control panel: http://{HOST}:{PORT}", flush=True)
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        SHUTDOWN.set()
        server.server_close()
        try:
            stop_motor("Control service stopped; safety reset completed")
        except Exception:
            pass


if __name__ == "__main__":
    main()
