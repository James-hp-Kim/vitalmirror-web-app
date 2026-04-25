from __future__ import annotations

import csv
import json
import mimetypes
import os
import sqlite3
import sys
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

try:
    from flask import Flask, jsonify, redirect, request, send_file
except Exception:  # pragma: no cover - optional in local stdlib-only mode
    Flask = None

ROOT = Path(__file__).resolve().parent
PUBLIC_DIR = ROOT / "public"
RUNTIME_ROOT = Path("/tmp/vitalmirror") if os.environ.get("VERCEL") else ROOT
DATA_DIR = RUNTIME_ROOT / "data"
DB_PATH = DATA_DIR / "vitalmirror.db"
EXPORT_DIR = DATA_DIR / "exports"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml_pipeline import CaptureTelemetry, VitalMirrorFusionPipeline

PIPELINE = VitalMirrorFusionPipeline()


@dataclass
class AnalysisResult:
    session_id: str
    measured_at: str
    mood_index: int
    stress_index: int
    recovery_index: int
    hr: int
    rmssd: int
    sdnn: int
    rr: int
    signal_quality: int
    confidence: int
    brightness: int
    motion: int
    ambient_noise: int
    emoji: str
    valence: float
    arousal: float
    expression_confidence: float
    rppg_source: str
    advice_id: str
    advice_title: str
    advice_body: str
    disclaimer: str


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def clamp_int(value: float, low: int, high: int) -> int:
    return max(low, min(high, round(value)))


def get_db() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_column(conn: sqlite3.Connection, table: str, column: str, column_def: str) -> None:
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_def}")


def init_db() -> None:
    with get_db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS analyses (
                session_id TEXT PRIMARY KEY,
                measured_at TEXT NOT NULL,
                mood_index INTEGER NOT NULL,
                stress_index INTEGER NOT NULL,
                recovery_index INTEGER NOT NULL,
                hr INTEGER NOT NULL,
                rmssd INTEGER NOT NULL,
                sdnn INTEGER NOT NULL,
                rr INTEGER NOT NULL,
                signal_quality INTEGER NOT NULL,
                confidence INTEGER NOT NULL,
                brightness INTEGER NOT NULL,
                motion INTEGER NOT NULL,
                ambient_noise INTEGER NOT NULL,
                emoji TEXT,
                valence REAL,
                arousal REAL,
                expression_confidence REAL,
                rppg_source TEXT,
                advice_id TEXT NOT NULL,
                advice_title TEXT NOT NULL,
                advice_body TEXT NOT NULL,
                disclaimer TEXT NOT NULL,
                device_user_agent TEXT
            );

            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                logged_at TEXT NOT NULL,
                session_id TEXT NOT NULL,
                feedback TEXT NOT NULL,
                self_report_mood INTEGER,
                self_report_anxiety INTEGER,
                notes TEXT,
                device_user_agent TEXT,
                FOREIGN KEY (session_id) REFERENCES analyses(session_id)
            );
            """
        )

        ensure_column(conn, "analyses", "emoji", "TEXT")
        ensure_column(conn, "analyses", "valence", "REAL")
        ensure_column(conn, "analyses", "arousal", "REAL")
        ensure_column(conn, "analyses", "expression_confidence", "REAL")
        ensure_column(conn, "analyses", "rppg_source", "TEXT")


def build_analysis(payload: dict[str, Any]) -> AnalysisResult:
    telemetry = CaptureTelemetry(
        brightness=clamp_int(float(payload.get("brightness", 52)), 0, 100),
        motion=clamp_int(float(payload.get("motion", 18)), 0, 100),
        ambient_noise=clamp_int(float(payload.get("ambient_noise", 12)), 0, 100),
        duration_seconds=clamp_int(float(payload.get("duration_seconds", 30)), 5, 120),
        sample_fps=max(0.0, float(payload.get("sample_fps", 0.0))),
        frame_count=clamp_int(float(payload.get("frame_count", 0)), 0, 10000),
        face_detected_ratio=max(0.0, min(1.0, float(payload.get("face_detected_ratio", 1.0)))),
        device_user_agent=payload.get("device_user_agent", ""),
        frame_samples=list(payload.get("frame_samples", [])),
    )

    pipeline_output = PIPELINE.infer(telemetry)
    fusion = pipeline_output["fusion"]
    expression = pipeline_output["expression"]
    rppg = pipeline_output["rppg"]

    return AnalysisResult(
        session_id=str(uuid.uuid4()),
        measured_at=utc_now_iso(),
        mood_index=fusion["mood_index"],
        stress_index=fusion["stress_index"],
        recovery_index=fusion["recovery_index"],
        hr=rppg["hr"],
        rmssd=rppg["rmssd"],
        sdnn=rppg["sdnn"],
        rr=rppg["rr"],
        signal_quality=rppg["signal_quality"],
        confidence=fusion["confidence"],
        brightness=telemetry.brightness,
        motion=telemetry.motion,
        ambient_noise=telemetry.ambient_noise,
        emoji=fusion["emoji"],
        valence=expression["valence"],
        arousal=expression["arousal"],
        expression_confidence=expression["confidence"],
        rppg_source=rppg["source"],
        advice_id=fusion["advice_id"],
        advice_title=fusion["advice_title"],
        advice_body=fusion["advice_body"],
        disclaimer="프로토타입 출력입니다. 실제 웰니스 신호로 사용하기 전 검증된 표정 모델과 MCD-rPPG 추론 스택으로 교체해야 합니다.",
    )


def build_photo_analysis(payload: dict[str, Any]) -> AnalysisResult:
    telemetry = CaptureTelemetry(
        brightness=clamp_int(float(payload.get("brightness", 52)), 0, 100),
        motion=0,
        ambient_noise=0,
        duration_seconds=5,
        sample_fps=0.0,
        frame_count=clamp_int(float(payload.get("frame_count", 1)), 0, 10),
        face_detected_ratio=max(0.0, min(1.0, float(payload.get("face_detected_ratio", 1.0)))),
        device_user_agent=payload.get("device_user_agent", ""),
        frame_samples=list(payload.get("frame_samples", [])),
    )

    expression = asdict(PIPELINE.expression_adapter.infer(telemetry))
    valence = expression["valence"]
    arousal = expression["arousal"]
    stress_index = clamp_int(52 + (arousal * 18) - (valence * 8), 14, 88)
    recovery_index = clamp_int(64 + (valence * 18) - (max(arousal, 0) * 10), 12, 90)
    mood_index = clamp_int((recovery_index * 0.58) + ((1 + valence) * 16) + ((1 - max(arousal, 0)) * 8), 15, 92)
    confidence = clamp_int(expression["confidence"] * 100, 20, 94)

    advice_id, advice_title, advice_body = PIPELINE._choose_advice(stress_index, recovery_index, 0)

    return AnalysisResult(
        session_id=str(uuid.uuid4()),
        measured_at=utc_now_iso(),
        mood_index=mood_index,
        stress_index=stress_index,
        recovery_index=recovery_index,
        hr=0,
        rmssd=0,
        sdnn=0,
        rr=0,
        signal_quality=0,
        confidence=confidence,
        brightness=telemetry.brightness,
        motion=0,
        ambient_noise=0,
        emoji=expression["dominant_emoji"],
        valence=expression["valence"],
        arousal=expression["arousal"],
        expression_confidence=expression["confidence"],
        rppg_source="photo-expression-only",
        advice_id=advice_id,
        advice_title=advice_title,
        advice_body=advice_body,
        disclaimer="사진 모드는 표정만 추정합니다. 단일 이미지는 신뢰 가능한 HR, HRV, 호흡 지표를 제공할 수 없습니다.",
    )


def save_analysis(result: AnalysisResult, payload: dict[str, Any]) -> None:
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO analyses (
                session_id, measured_at, mood_index, stress_index, recovery_index,
                hr, rmssd, sdnn, rr, signal_quality, confidence,
                brightness, motion, ambient_noise, emoji, valence, arousal,
                expression_confidence, rppg_source,
                advice_id, advice_title, advice_body, disclaimer, device_user_agent
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result.session_id,
                result.measured_at,
                result.mood_index,
                result.stress_index,
                result.recovery_index,
                result.hr,
                result.rmssd,
                result.sdnn,
                result.rr,
                result.signal_quality,
                result.confidence,
                result.brightness,
                result.motion,
                result.ambient_noise,
                result.emoji,
                result.valence,
                result.arousal,
                result.expression_confidence,
                result.rppg_source,
                result.advice_id,
                result.advice_title,
                result.advice_body,
                result.disclaimer,
                payload.get("device_user_agent", ""),
            ),
        )


def save_feedback(payload: dict[str, Any]) -> None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT session_id FROM analyses WHERE session_id = ?",
            (payload.get("session_id", ""),),
        ).fetchone()
        if row is None:
            raise ValueError("Unknown session_id")

        conn.execute(
            """
            INSERT INTO feedback (
                logged_at, session_id, feedback, self_report_mood,
                self_report_anxiety, notes, device_user_agent
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                utc_now_iso(),
                payload.get("session_id", ""),
                payload.get("feedback", ""),
                payload.get("self_report_mood"),
                payload.get("self_report_anxiety"),
                payload.get("notes", ""),
                payload.get("device_user_agent", ""),
            ),
        )


def export_feedback_csv() -> Path:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_path = EXPORT_DIR / f"feedback_dataset_{stamp}.csv"

    with get_db() as conn, export_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "session_id",
                "measured_at",
                "mood_index",
                "stress_index",
                "recovery_index",
                "hr",
                "rmssd",
                "sdnn",
                "rr",
                "signal_quality",
                "confidence",
                "brightness",
                "motion",
                "ambient_noise",
                "emoji",
                "valence",
                "arousal",
                "expression_confidence",
                "rppg_source",
                "advice_id",
                "feedback",
                "self_report_mood",
                "self_report_anxiety",
                "notes",
                "device_user_agent",
                "feedback_logged_at",
            ]
        )
        rows = conn.execute(
            """
            SELECT
                a.session_id,
                a.measured_at,
                a.mood_index,
                a.stress_index,
                a.recovery_index,
                a.hr,
                a.rmssd,
                a.sdnn,
                a.rr,
                a.signal_quality,
                a.confidence,
                a.brightness,
                a.motion,
                a.ambient_noise,
                a.emoji,
                a.valence,
                a.arousal,
                a.expression_confidence,
                a.rppg_source,
                a.advice_id,
                f.feedback,
                f.self_report_mood,
                f.self_report_anxiety,
                f.notes,
                COALESCE(f.device_user_agent, a.device_user_agent) AS device_user_agent,
                f.logged_at
            FROM analyses a
            LEFT JOIN feedback f ON f.session_id = a.session_id
            ORDER BY a.measured_at DESC, f.logged_at DESC
            """
        ).fetchall()
        for row in rows:
            writer.writerow([row[column] for column in row.keys()])

    return export_path


def get_summary() -> dict[str, Any]:
    with get_db() as conn:
        counts = conn.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM analyses) AS analyses_count,
                (SELECT COUNT(*) FROM feedback) AS feedback_count,
                (SELECT COUNT(*) FROM feedback WHERE feedback = 'like') AS likes_count,
                (SELECT COUNT(*) FROM feedback WHERE feedback = 'dislike') AS dislikes_count
            """
        ).fetchone()
        recent = conn.execute(
            """
            SELECT
                a.session_id,
                a.measured_at,
                a.mood_index,
                a.stress_index,
                a.recovery_index,
                a.emoji,
                a.advice_id,
                f.feedback
            FROM analyses a
            LEFT JOIN feedback f ON f.session_id = a.session_id
            ORDER BY a.measured_at DESC
            LIMIT 5
            """
        ).fetchall()

    return {
        "analyses_count": counts["analyses_count"],
        "feedback_count": counts["feedback_count"],
        "likes_count": counts["likes_count"],
        "dislikes_count": counts["dislikes_count"],
        "pipeline_mode": "expression+rppg+fusion",
        "expression_adapter": PIPELINE.expression_adapter_name,
        "rppg_adapter": PIPELINE.rppg_adapter_name,
        "recent_sessions": [dict(row) for row in recent],
    }


def health_payload() -> dict[str, Any]:
    return {
        "status": "ok",
        "db_path": str(DB_PATH),
        "export_dir": str(EXPORT_DIR),
        "summary": get_summary(),
    }


class VitalMirrorHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(PUBLIC_DIR), **kwargs)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, format: str, *args: Any) -> None:
        sys.stderr.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), format % args))

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/index.html", "/phone"):
            self._send_file(PUBLIC_DIR / "index.html", "text/html; charset=utf-8")
            return

        if parsed.path.startswith("/css/") or parsed.path.startswith("/js/"):
            relative_path = parsed.path.lstrip("/")
            file_path = (PUBLIC_DIR / relative_path).resolve()
            try:
                file_path.relative_to(PUBLIC_DIR.resolve())
            except ValueError:
                self._json_response({"error": "Invalid path"}, status=HTTPStatus.BAD_REQUEST)
                return

            if not file_path.exists() or not file_path.is_file():
                self._json_response({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)
                return

            guessed_type, _ = mimetypes.guess_type(str(file_path))
            content_type = guessed_type or "application/octet-stream"
            if content_type.startswith("text/") or content_type in {"application/javascript", "application/json"}:
                content_type = f"{content_type}; charset=utf-8"
            self._send_file(file_path, content_type)
            return

        if parsed.path == "/api/health":
            self._json_response(health_payload())
            return

        if parsed.path == "/api/export-feedback":
            export_path = export_feedback_csv()
            params = parse_qs(parsed.query)
            if params.get("download", ["0"])[0] == "1":
                self._send_file(export_path, "text/csv; charset=utf-8", as_attachment=True)
            else:
                self._json_response({"status": "exported", "export_path": str(export_path)})
            return

        return super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/analyze":
            payload = self._read_json()
            result = build_analysis(payload)
            save_analysis(result, payload)
            self._json_response(asdict(result))
            return

        if parsed.path == "/api/analyze-photo":
            payload = self._read_json()
            result = build_photo_analysis(payload)
            save_analysis(result, payload)
            self._json_response(asdict(result))
            return

        if parsed.path == "/api/feedback":
            payload = self._read_json()
            try:
                save_feedback(payload)
            except ValueError as exc:
                self._json_response({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            self._json_response({"status": "saved", "db_path": str(DB_PATH), "summary": get_summary()})
            return

        self._json_response({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return {}

    def _send_file(self, file_path: Path, content_type: str, as_attachment: bool = False) -> None:
        body = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if as_attachment:
            self.send_header("Content-Disposition", f'attachment; filename="{file_path.name}"')
        self.end_headers()
        self.wfile.write(body)

    def _json_response(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if Flask is not None:
    app = Flask(__name__, static_folder=None)

    @app.after_request
    def _disable_cache(response):
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.route("/")
    def _root_redirect():
        return redirect("/index.html", code=307)

    @app.route("/phone")
    def _phone_redirect():
        return redirect("/index.html", code=307)

    @app.get("/api/health")
    def api_health():
        init_db()
        return jsonify(health_payload())

    @app.post("/api/analyze")
    def api_analyze():
        init_db()
        payload = request.get_json(silent=True) or {}
        result = build_analysis(payload)
        save_analysis(result, payload)
        return jsonify(asdict(result))

    @app.post("/api/analyze-photo")
    def api_analyze_photo():
        init_db()
        payload = request.get_json(silent=True) or {}
        result = build_photo_analysis(payload)
        save_analysis(result, payload)
        return jsonify(asdict(result))

    @app.post("/api/feedback")
    def api_feedback():
        init_db()
        payload = request.get_json(silent=True) or {}
        try:
            save_feedback(payload)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST
        return jsonify({"status": "saved", "db_path": str(DB_PATH), "summary": get_summary()})

    @app.get("/api/export-feedback")
    def api_export_feedback():
        init_db()
        export_path = export_feedback_csv()
        if request.args.get("download", "0") == "1":
            return send_file(
                export_path,
                mimetype="text/csv",
                as_attachment=True,
                download_name=export_path.name,
                max_age=0,
            )
        return jsonify({"status": "exported", "export_path": str(export_path)})


def run() -> None:
    init_db()
    port = int(os.environ.get("PORT", "8765"))
    host = os.environ.get("HOST", "127.0.0.1")
    server = ThreadingHTTPServer((host, port), VitalMirrorHandler)
    print(f"VitalMirror prototype running at http://{host}:{port}")
    print(f"Database: {DB_PATH}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
    finally:
        server.server_close()


if __name__ == "__main__":
    run()
