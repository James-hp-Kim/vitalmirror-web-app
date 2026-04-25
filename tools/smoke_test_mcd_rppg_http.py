from __future__ import annotations

import argparse
import base64
import json
import sys
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import server as vm_server


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Start the VitalMirror HTTP server in-process and verify the active rPPG path with sample video frames."
    )
    parser.add_argument(
        "--video",
        default=r"C:\Users\scj94\codex_projects\vitalmirror_training\data\mcd_rppg_sample\video\4932_FullHDwebcam_after.avi",
        help="Video file used to synthesize browser-like frame samples.",
    )
    parser.add_argument("--width", type=int, default=320, help="Frame sample width.")
    parser.add_argument("--height", type=int, default=240, help="Frame sample height.")
    parser.add_argument("--jpeg-quality", type=int, default=80, help="JPEG quality for frame samples.")
    parser.add_argument("--sample-every", type=int, default=7, help="Use every Nth frame from the source video.")
    parser.add_argument("--max-frames", type=int, default=120, help="Maximum number of sampled frames.")
    parser.add_argument("--sample-fps", type=float, default=4.0, help="Reported sample FPS.")
    return parser.parse_args()


def fetch_json(url: str, payload: dict | None = None) -> dict:
    if payload is None:
        request = urllib.request.Request(url)
    else:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def sample_video_frames(video_path: Path, width: int, height: int, jpeg_quality: int, sample_every: int, max_frames: int) -> list[str]:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise SystemExit(f"Failed to open video: {video_path}")

    frames: list[str] = []
    try:
        index = 0
        while len(frames) < max_frames:
            ok, frame = cap.read()
            if not ok:
                break
            if index % sample_every == 0:
                resized = cv2.resize(frame, (width, height))
                ok_jpg, buffer = cv2.imencode(".jpg", resized, [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality])
                if ok_jpg:
                    encoded = base64.b64encode(buffer.tobytes()).decode("ascii")
                    frames.append("data:image/jpeg;base64," + encoded)
            index += 1
    finally:
        cap.release()

    if not frames:
        raise SystemExit("No frame samples were generated from the source video.")
    return frames


def main() -> None:
    args = parse_args()
    video_path = Path(args.video).resolve()
    if not video_path.exists():
        raise SystemExit(f"Video path not found: {video_path}")

    vm_server.init_db()
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), vm_server.VitalMirrorHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    try:
        port = httpd.server_address[1]
        health = fetch_json(f"http://127.0.0.1:{port}/api/health")
        frames = sample_video_frames(
            video_path,
            width=args.width,
            height=args.height,
            jpeg_quality=args.jpeg_quality,
            sample_every=args.sample_every,
            max_frames=args.max_frames,
        )
        payload = {
            "brightness": 52,
            "motion": 18,
            "ambient_noise": 12,
            "duration_seconds": 30,
            "sample_fps": args.sample_fps,
            "frame_count": len(frames),
            "face_detected_ratio": 1.0,
            "frame_samples": frames,
            "device_user_agent": "codex-smoke-test",
        }
        analysis = fetch_json(f"http://127.0.0.1:{port}/api/analyze", payload)
        print(
            json.dumps(
                {
                    "port": port,
                    "health_rppg_adapter": health["summary"]["rppg_adapter"],
                    "frame_count": len(frames),
                    "rppg_source": analysis.get("rppg_source"),
                    "signal_quality": analysis.get("signal_quality"),
                    "confidence": analysis.get("confidence"),
                    "hr": analysis.get("hr"),
                    "emoji": analysis.get("emoji"),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    finally:
        httpd.shutdown()
        httpd.server_close()


if __name__ == "__main__":
    main()
