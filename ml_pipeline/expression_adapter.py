from __future__ import annotations

import base64
from abc import ABC, abstractmethod

import cv2
import numpy as np

from .schemas import CaptureTelemetry, ExpressionOutput


def _clamp_float(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


class ExpressionModelAdapter(ABC):
    @abstractmethod
    def infer(self, telemetry: CaptureTelemetry) -> ExpressionOutput:
        raise NotImplementedError


class MockExpressionAdapter(ExpressionModelAdapter):
    """Fallback stand-in for a real facial-expression model."""

    def infer(self, telemetry: CaptureTelemetry) -> ExpressionOutput:
        valence = _clamp_float((telemetry.brightness - 50) / 50, -1.0, 1.0)
        arousal = _clamp_float((telemetry.motion - 20) / 50, -1.0, 1.0)

        if valence > 0.2 and arousal < 0.25:
            emoji = "🙂"
            probs = {"calm": 0.56, "happy": 0.24, "neutral": 0.20}
        elif arousal > 0.45:
            emoji = "😮"
            probs = {"tense": 0.51, "surprised": 0.22, "neutral": 0.27}
        elif valence < -0.2:
            emoji = "😔"
            probs = {"low": 0.48, "sad": 0.18, "neutral": 0.34}
        else:
            emoji = "😐"
            probs = {"neutral": 0.64, "calm": 0.19, "low": 0.17}

        return ExpressionOutput(
            dominant_emoji=emoji,
            valence=round(valence, 3),
            arousal=round(arousal, 3),
            confidence=0.52,
            emotion_probs=probs,
        )


class ClassicalExpressionAdapter(ExpressionModelAdapter):
    """Simple frame-based expression estimator using OpenCV cascades."""

    def __init__(self) -> None:
        base = cv2.data.haarcascades
        self.face_detector = cv2.CascadeClassifier(base + "haarcascade_frontalface_default.xml")
        self.smile_detector = cv2.CascadeClassifier(base + "haarcascade_smile.xml")
        self.fallback = MockExpressionAdapter()

    def infer(self, telemetry: CaptureTelemetry) -> ExpressionOutput:
        if not telemetry.frame_samples:
            return self.fallback.infer(telemetry)

        smile_hits = 0
        face_hits = 0
        motion_points = []
        last_center = None

        for sample in telemetry.frame_samples[:: max(1, len(telemetry.frame_samples) // 30)]:
            frame = self._decode_frame(sample)
            if frame is None:
                continue
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(40, 40))
            if len(faces) == 0:
                continue

            x, y, w, h = max(faces, key=lambda face: face[2] * face[3])
            face_hits += 1
            center = np.array([x + w / 2, y + h / 2], dtype=np.float32)
            if last_center is not None:
                motion_points.append(float(np.linalg.norm(center - last_center)))
            last_center = center

            face_roi = gray[y : y + h, x : x + w]
            smiles = self.smile_detector.detectMultiScale(face_roi, scaleFactor=1.7, minNeighbors=20, minSize=(20, 20))
            if len(smiles) > 0:
                smile_hits += 1

        if face_hits == 0:
            return self.fallback.infer(telemetry)

        smile_ratio = smile_hits / face_hits
        avg_motion = np.mean(motion_points) if motion_points else 0.0
        valence = _clamp_float((smile_ratio * 1.6) - 0.35 + ((telemetry.brightness - 50) / 180), -1.0, 1.0)
        arousal = _clamp_float(((telemetry.motion / 100) * 0.7) + min(0.25, avg_motion / 120) - 0.2, -1.0, 1.0)
        confidence = _clamp_float(0.35 + (face_hits / max(1, len(telemetry.frame_samples))) * 0.45, 0.25, 0.82)

        if valence > 0.35 and arousal < 0.35:
            emoji = "🙂"
            probs = {"calm": 0.48, "happy": 0.37, "neutral": 0.15}
        elif arousal > 0.45:
            emoji = "😮"
            probs = {"tense": 0.49, "surprised": 0.21, "neutral": 0.30}
        elif valence < -0.15:
            emoji = "😔"
            probs = {"low": 0.44, "sad": 0.20, "neutral": 0.36}
        else:
            emoji = "😐"
            probs = {"neutral": 0.58, "calm": 0.24, "low": 0.18}

        return ExpressionOutput(
            dominant_emoji=emoji,
            valence=round(valence, 3),
            arousal=round(arousal, 3),
            confidence=round(confidence, 3),
            emotion_probs=probs,
        )

    @staticmethod
    def _decode_frame(data_url: str):
        if "," in data_url:
            _, encoded = data_url.split(",", 1)
        else:
            encoded = data_url
        try:
            raw = base64.b64decode(encoded)
        except Exception:
            return None
        arr = np.frombuffer(raw, dtype=np.uint8)
        if arr.size == 0:
            return None
        return cv2.imdecode(arr, cv2.IMREAD_COLOR)


class PyFeatExpressionAdapter(ExpressionModelAdapter):
    """Integration placeholder for a real Py-Feat backed model."""

    def __init__(self) -> None:
        self._available = self._check_availability()

    @staticmethod
    def _check_availability() -> bool:
        try:
            import feat  # noqa: F401
        except Exception:
            return False
        return True

    def infer(self, telemetry: CaptureTelemetry) -> ExpressionOutput:
        if not self._available:
            raise RuntimeError("Py-Feat is not installed in this environment.")

        raise NotImplementedError(
            "Hook Py-Feat frame inference here. Feed frame batches, collect valence/arousal "
            "or emotion probabilities, then map them into ExpressionOutput."
        )
