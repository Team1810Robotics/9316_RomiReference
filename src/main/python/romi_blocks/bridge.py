"""Local Blockly -> NT4 bridge for the RomiReference GirlScoutBlocks receiver.

Usage: py -3.14 bridge.py
Local only (127.0.0.1:8765). Requires pyntcore in the chosen Python.
"""

from __future__ import annotations

import json
import math
import re
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock

import ntcore

ROOT = Path(__file__).resolve().parent
HOST = "127.0.0.1"
PORT = 8765
MAX_BYTES = 1024
DIRECTION = re.compile(r"(forward|backward|left|right):([0-9]+(?:\.[0-9]+)?)(?::([0-9]+(?:\.[0-9]+)?))?\Z")


def validate_sequence(value: object) -> str:
    """Revalidate every browser-supplied program before writing to NetworkTables."""
    if not isinstance(value, str) or not value or len(value) > 250:
        raise ValueError("Provide 1-8 movement blocks")
    blocks = value.split(",")
    if not 1 <= len(blocks) <= 8:
        raise ValueError("Use between 1 and 8 blocks")
    total = 0.0
    normalized = []
    for block in blocks:
        match = DIRECTION.fullmatch(block.strip())
        if not match:
            raise ValueError("Unsupported block: " + block[:30])
        direction, duration_text, speed_text = match.groups()
        duration = float(duration_text)
        if not math.isfinite(duration) or not 0.1 <= duration <= 2.5:
            raise ValueError("Each movement must last 0.1-2.5 seconds")
        speed = float(speed_text) if speed_text is not None else (0.30 if direction in ("left", "right") else 0.35)
        if not math.isfinite(speed) or not 0.30 <= speed <= 0.60:
            raise ValueError("Speed must be from 30% to 60%")
        total += duration
        if total > 8.00001:
            raise ValueError("Program must be 8 seconds or less")
        normalized.append(f"{direction}:{duration:.2f}:{speed:.2f}")
    return ",".join(normalized)


class RomiBridge:
    def __init__(self):
        self.lock = Lock()
        self.nt = ntcore.NetworkTableInstance.getDefault()
        self.nt.startClient4("RomiBlocklyBrowser")
        self.nt.setServer("127.0.0.1")
        self.table = self.nt.getTable("GirlScoutBlocks")
        self.sequence = self.table.getEntry("sequence")
        self.run_id = self.table.getEntry("runId")
        self.stop_id = self.table.getEntry("stopId")
        self.status = self.table.getEntry("status")
        self.sensors = self.table.getSubTable("sensors")

    def connected(self) -> bool:
        return self.nt.isConnected()

    def snapshot(self) -> dict:
        last_update_ms = self.sensors.getEntry("stampMs").getDouble(0.0)
        available = self.connected() and self.sensors.getEntry("ready").getBoolean(False)
        age_ms = time.time() * 1000 - last_update_ms if last_update_ms else 1e10
        return {
            "connected": self.connected(),
            "status": self.status.getString("No status yet"),
            "sequence": self.sequence.getString(""),
            "sensors": {
                "available": available,
                "ageMs": age_ms,
                "gyroZDeg": self.sensors.getEntry("gyroZDeg").getDouble(0.0),
                "leftIn": self.sensors.getEntry("leftIn").getDouble(0.0),
                "rightIn": self.sensors.getEntry("rightIn").getDouble(0.0),
                "buttonA": self.sensors.getEntry("buttonA").getBoolean(False),
                "buttonB": self.sensors.getEntry("buttonB").getBoolean(False),
                "buttonC": self.sensors.getEntry("buttonC").getBoolean(False),
            }
        }

    def run(self, sequence: str) -> dict:
        checked = validate_sequence(sequence)
        with self.lock:
            if not self.connected():
                raise ConnectionError("WPILib simulation / NetworkTables is not connected")
            self.sequence.setString(checked)
            self.nt.flush()
            # A fresh ID causes the Java receiver to schedule the sequence.
            self.run_id.setInteger(time.time_ns())
            self.nt.flush()
        return {"ok": True, "message": "Submitted", "sequence": checked}

    def stop(self) -> dict:
        with self.lock:
            if not self.connected():
                raise ConnectionError("WPILib simulation / NetworkTables is not connected")
            self.stop_id.setInteger(time.time_ns())
            self.nt.flush()
        return {"ok": True, "message": "Stop requested"}


bridge = None  # initialized in main


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def _json(self, code: int, data: dict):
        payload = json.dumps(data).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if self.path == "/api/status":
            self._json(200, bridge.snapshot())
        else:
            super().do_GET()

    def do_POST(self):
        if self.path not in ("/api/run", "/api/stop"):
            self._json(404, {"error": "Unknown operation"})
            return
        origin = self.headers.get("Origin")
        if origin and origin not in (
            f"http://{HOST}:{PORT}", f"http://localhost:{PORT}"
        ):
            self._json(403, {"error": "Only this local editor may send commands"})
            return
        if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
            self._json(415, {"error": "Expected application/json"})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size < 2 or size > MAX_BYTES:
                raise ValueError("Invalid request size")
            body = json.loads(self.rfile.read(size).decode("utf-8"))
            if not isinstance(body, dict):
                raise ValueError("Invalid request object")
            result = bridge.run(body.get("sequence")) if self.path == "/api/run" else bridge.stop()
            self._json(200, result)
        except (ValueError, TypeError, UnicodeError, json.JSONDecodeError) as exc:
            self._json(400, {"error": str(exc)})
        except ConnectionError as exc:
            self._json(503, {"error": str(exc)})


def main():
    global bridge
    bridge = RomiBridge()
    print("Romi Blockly bridge is running.")
    print(f"Open http://{HOST}:{PORT} in a browser.")
    print("Keep this terminal open. Use Ctrl+C to stop it.")
    print("WPILib simulation must be running on this laptop; enable Teleoperated mode.")
    try:
        with ThreadingHTTPServer((HOST, PORT), Handler) as server:
            server.serve_forever()
    except KeyboardInterrupt:
        print("\nBridge stopped.")


if __name__ == "__main__":
    main()
