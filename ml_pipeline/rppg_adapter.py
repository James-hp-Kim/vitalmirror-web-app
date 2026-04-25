from __future__ import annotations

import base64
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass

import cv2
import numpy as np

from .schemas import CaptureTelemetry, RPPGOutput


try:
    import onnxruntime as ort
except Exception:  # pragma: no cover - optional dependency
    ort = None


def _clamp_int(value: float, low: int, high: int) -> int:
    return max(low, min(high, round(value)))


@dataclass(slots=True)
class _FaceSignalStats:
    traces: np.ndarray
    roi_rgb: np.ndarray
    face_ratio: float
    motion_score: float


class RPPGModelAdapter(ABC):
    @abstractmethod
    def infer(self, telemetry: CaptureTelemetry) -> RPPGOutput:
        raise NotImplementedError


class MockRPPGAdapter(RPPGModelAdapter):
    """Fallback stand-in for an MCD-rPPG based inference stack."""

    def infer(self, telemetry: CaptureTelemetry) -> RPPGOutput:
        quality = _clamp_int(
            (telemetry.brightness * 0.9)
            + ((100 - telemetry.motion) * 0.7)
            + ((100 - telemetry.ambient_noise) * 0.2)
            + (telemetry.face_detected_ratio * 8),
            20,
            95,
        )
        hr = _clamp_int(68 + (telemetry.motion * 0.2), 55, 120)
        rmssd = _clamp_int(54 - (telemetry.motion * 0.25) - (telemetry.ambient_noise * 0.18), 18, 72)
        sdnn = _clamp_int(48 - (telemetry.motion * 0.18) - (telemetry.ambient_noise * 0.16), 20, 70)
        rr = _clamp_int(14 + (telemetry.motion * 0.05) + max(0, 55 - telemetry.brightness) * 0.04, 10, 24)

        return RPPGOutput(
            hr=hr,
            rmssd=rmssd,
            sdnn=sdnn,
            rr=rr,
            signal_quality=quality,
            confidence=min(0.94, max(0.2, quality / 100)),
            source="mock-rppg",
        )


class ROITraceExtractor:
    """Extracts 8 ROI temporal traces roughly aligned with the MCD-rPPG idea."""

    def __init__(self) -> None:
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self.face_detector = cv2.CascadeClassifier(cascade_path)

    def extract(self, frame_samples: list[str]) -> _FaceSignalStats:
        roi_rows: list[np.ndarray] = []
        roi_rgb_rows: list[np.ndarray] = []
        face_hits = 0
        last_center = None
        motion_scores: list[float] = []

        for sample in frame_samples:
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
                motion_scores.append(float(np.linalg.norm(center - last_center)))
            last_center = center

            # Approximate 8-region layout over forehead / cheeks / mid-face.
            rois = self._roi_boxes(x, y, w, h)
            roi_means = []
            roi_rgb_means = []
            for rx, ry, rw, rh in rois:
                roi = frame[ry : ry + rh, rx : rx + rw]
                if roi.size == 0:
                    roi_means.append(0.0)
                    roi_rgb_means.append((0.0, 0.0, 0.0))
                else:
                    rgb_mean = np.mean(roi[:, :, ::-1], axis=(0, 1))
                    roi_means.append(float(rgb_mean[1]))
                    roi_rgb_means.append(tuple(float(v) for v in rgb_mean))
            roi_rows.append(np.asarray(roi_means, dtype=np.float32))
            roi_rgb_rows.append(np.asarray(roi_rgb_means, dtype=np.float32))

        if not roi_rows:
            traces = np.zeros((0, 8), dtype=np.float32)
            roi_rgb = np.zeros((0, 8, 3), dtype=np.float32)
        else:
            traces = np.vstack(roi_rows)
            roi_rgb = np.stack(roi_rgb_rows)

        face_ratio = face_hits / max(1, len(frame_samples))
        motion_score = float(np.mean(motion_scores)) if motion_scores else 0.0
        return _FaceSignalStats(traces=traces, roi_rgb=roi_rgb, face_ratio=face_ratio, motion_score=motion_score)

    @staticmethod
    def _roi_boxes(x: int, y: int, w: int, h: int) -> list[tuple[int, int, int, int]]:
        upper_y = int(y + h * 0.16)
        mid_y = int(y + h * 0.34)
        roi_w = max(4, int(w * 0.22))
        roi_h = max(4, int(h * 0.14))
        left1 = int(x + w * 0.12)
        left2 = int(x + w * 0.36)
        right1 = int(x + w * 0.58)
        right2 = int(x + w * 0.74) - roi_w

        return [
            (left1, upper_y, roi_w, roi_h),
            (left2, upper_y, roi_w, roi_h),
            (right1, upper_y, roi_w, roi_h),
            (right2, upper_y, roi_w, roi_h),
            (left1, mid_y, roi_w, roi_h),
            (left2, mid_y, roi_w, roi_h),
            (right1, mid_y, roi_w, roi_h),
            (right2, mid_y, roi_w, roi_h),
        ]

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


class ClassicalRPPGAdapter(RPPGModelAdapter):
    """Simple frame-sequence rPPG-style estimator using ROI temporal traces."""

    def __init__(self) -> None:
        self.extractor = ROITraceExtractor()
        self.fallback = MockRPPGAdapter()

    def infer(self, telemetry: CaptureTelemetry) -> RPPGOutput:
        if not telemetry.frame_samples or telemetry.sample_fps <= 0:
            return self.fallback.infer(telemetry)

        stats = self.extractor.extract(telemetry.frame_samples)
        if len(stats.traces) < max(24, int(telemetry.sample_fps * 8)) or stats.face_ratio < 0.35:
            fallback = self.fallback.infer(telemetry)
            fallback.source = "mock-rppg-fallback"
            return fallback

        # Average across ROIs after light detrending.
        traces = self._normalize_traces(stats.traces)
        fused_signal = traces.mean(axis=1)
        hr = self._estimate_hr(fused_signal, telemetry.sample_fps)
        rmssd = self._estimate_rmssd(fused_signal)
        sdnn = self._estimate_sdnn(fused_signal)
        rr = self._estimate_rr(hr)

        quality = _clamp_int(
            22
            + (stats.face_ratio * 42)
            + (100 - stats.motion_score) * 0.18
            + min(18, float(np.std(fused_signal)) * 100),
            18,
            95,
        )
        confidence = max(0.18, min(0.93, quality / 100))

        return RPPGOutput(
            hr=hr,
            rmssd=rmssd,
            sdnn=sdnn,
            rr=rr,
            signal_quality=quality,
            confidence=confidence,
            source="classical-rppg",
        )

    @staticmethod
    def _normalize_traces(traces: np.ndarray) -> np.ndarray:
        normed = traces.astype(np.float32).copy()
        for idx in range(normed.shape[1]):
            channel = normed[:, idx]
            channel = ClassicalRPPGAdapter._detrend(channel)
            normed[:, idx] = channel
        return normed

    @staticmethod
    def _detrend(signal: np.ndarray) -> np.ndarray:
        if signal.size < 5:
            return signal
        window = max(3, int(signal.size * 0.08))
        kernel = np.ones(window, dtype=np.float32) / window
        baseline = np.convolve(signal, kernel, mode="same")
        centered = signal - baseline
        std = centered.std()
        if std > 1e-6:
            centered = centered / std
        return centered

    @staticmethod
    def _estimate_hr(signal: np.ndarray, fps: float) -> int:
        n = signal.size
        freqs = np.fft.rfftfreq(n, d=1.0 / fps)
        power = np.abs(np.fft.rfft(signal)) ** 2
        valid = (freqs >= 0.75) & (freqs <= 3.0)
        if not np.any(valid):
            return 72
        target_freq = freqs[valid][np.argmax(power[valid])]
        return _clamp_int(target_freq * 60.0, 48, 126)

    @staticmethod
    def _estimate_rmssd(signal: np.ndarray) -> int:
        diffs = np.diff(signal)
        if diffs.size == 0:
            return 32
        return _clamp_int(np.sqrt(np.mean(diffs**2)) * 18 + 24, 16, 88)

    @staticmethod
    def _estimate_sdnn(signal: np.ndarray) -> int:
        if signal.size == 0:
            return 28
        return _clamp_int(float(signal.std()) * 16 + 26, 18, 84)

    @staticmethod
    def _estimate_rr(hr: int) -> int:
        rr = 11 + ((hr - 60) / 12)
        return _clamp_int(rr, 10, 24)


class MCDRPPGAdapter(RPPGModelAdapter):
    """ONNX-backed adapter for a future exported MCD-rPPG model.

    If the ONNX file is missing or incompatible, the caller should fall back.
    """

    def __init__(self, model_path: str) -> None:
        if ort is None:
            raise RuntimeError("onnxruntime is not available in this environment.")
        self.model_path = model_path
        self.extractor = ROITraceExtractor()
        self.session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
        self.input_name = self.session.get_inputs()[0].name

    @classmethod
    def from_default_location(cls) -> "MCDRPPGAdapter | None":
        default_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "models",
            "mcd_rppg.onnx",
        )
        if not os.path.exists(default_path):
            return None
        try:
            return cls(default_path)
        except Exception:
            return None

    def infer(self, telemetry: CaptureTelemetry) -> RPPGOutput:
        if not telemetry.frame_samples or telemetry.sample_fps <= 0:
            raise RuntimeError("Frame samples are required for MCD-rPPG inference.")

        stats = self.extractor.extract(telemetry.frame_samples)
        if len(stats.traces) < max(24, int(telemetry.sample_fps * 8)) or stats.face_ratio < 0.35:
            raise RuntimeError("Insufficient face ROI traces for MCD-rPPG inference.")

        model_features = self._build_model_features(stats.roi_rgb, telemetry.sample_fps)
        model_input = self._prepare_input(model_features)
        outputs = self.session.run(None, {self.input_name: model_input})
        ppg_wave = np.asarray(outputs[0]).astype(np.float32).reshape(-1)
        ppg_wave = ClassicalRPPGAdapter._detrend(ppg_wave)

        hr = ClassicalRPPGAdapter._estimate_hr(ppg_wave, telemetry.sample_fps)
        rmssd = ClassicalRPPGAdapter._estimate_rmssd(ppg_wave)
        sdnn = ClassicalRPPGAdapter._estimate_sdnn(ppg_wave)
        rr = ClassicalRPPGAdapter._estimate_rr(hr)

        quality = _clamp_int(
            25 + (stats.face_ratio * 40) + min(16, float(np.std(ppg_wave)) * 100),
            20,
            96,
        )

        return RPPGOutput(
            hr=hr,
            rmssd=rmssd,
            sdnn=sdnn,
            rr=rr,
            signal_quality=quality,
            confidence=max(0.2, min(0.95, quality / 100)),
            source="mcd-rppg-onnx",
        )

    def _prepare_input(self, traces: np.ndarray) -> np.ndarray:
        input_meta = self.session.get_inputs()[0]
        input_shape = input_meta.shape
        _, c = traces.shape
        if len(input_shape) == 3:
            # Common candidates: [B, C, T] or [B, T, C]
            if input_shape[1] in (8, None, "None") or input_shape[1] == c:
                return traces.T[np.newaxis, :, :].astype(np.float32)
            return traces[np.newaxis, :, :].astype(np.float32)
        if len(input_shape) == 2:
            return traces.astype(np.float32)
        return traces.T[np.newaxis, :, :].astype(np.float32)

    @staticmethod
    def _build_model_features(roi_rgb: np.ndarray, fps: float) -> np.ndarray:
        if roi_rgb.ndim != 3 or roi_rgb.shape[1:] != (8, 3):
            raise RuntimeError("Expected ROI RGB traces with shape (time, 8, 3).")

        time_steps = roi_rgb.shape[0]
        features: list[np.ndarray] = []
        for roi_index in range(roi_rgb.shape[1]):
            rgb = roi_rgb[:, roi_index, :].astype(np.float32)
            rgb_norm = rgb.copy()
            rgb_norm -= rgb_norm.mean(axis=0, keepdims=True)
            rgb_std = rgb_norm.std(axis=0, keepdims=True) + 1e-6
            rgb_norm /= rgb_std
            pos = MCDRPPGAdapter._pos_channel(rgb, fps)
            roi_features = np.concatenate([rgb_norm, pos[:, None]], axis=1)
            features.append(roi_features)
        return np.concatenate(features, axis=1).astype(np.float32)

    @staticmethod
    def _pos_channel(rgb: np.ndarray, fps: float, window_sec: float = 1.6) -> np.ndarray:
        window = max(2, int(round(window_sec * fps)))
        if rgb.shape[0] < window:
            return ClassicalRPPGAdapter._detrend(rgb.mean(axis=1))

        out = np.zeros(rgb.shape[0], dtype=np.float32)
        projection = np.asarray([[0, 1, -1], [-2, 1, 1], [-1, 2, -1]], dtype=np.float32)

        for start in range(0, rgb.shape[0] - window + 1):
            segment = rgb[start : start + window].T
            mean = segment.mean(axis=1, keepdims=True) + 1e-6
            normalized = segment / mean
            s = projection @ normalized
            s0 = s[0]
            s1 = s[1]
            alpha = np.std(s0) / (np.std(s1) + 1e-4)
            h = s0 + alpha * s1
            out[start : start + window] += h.astype(np.float32)

        return ClassicalRPPGAdapter._detrend(out)


def build_default_rppg_adapter() -> RPPGModelAdapter:
    if os.environ.get("VM_FORCE_CLASSICAL_RPPG", "").lower() in {"1", "true", "yes"}:
        return ClassicalRPPGAdapter()
    mcd_adapter = MCDRPPGAdapter.from_default_location()
    if mcd_adapter is not None:
        return mcd_adapter
    return ClassicalRPPGAdapter()
