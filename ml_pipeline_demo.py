from __future__ import annotations

import json

from ml_pipeline import CaptureTelemetry, VitalMirrorFusionPipeline


def main() -> None:
    pipeline = VitalMirrorFusionPipeline()
    telemetry = CaptureTelemetry(
        brightness=64,
        motion=18,
        ambient_noise=12,
        duration_seconds=30,
        frame_count=900,
        face_detected_ratio=0.97,
        device_user_agent="demo",
    )
    result = pipeline.infer(telemetry)
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
