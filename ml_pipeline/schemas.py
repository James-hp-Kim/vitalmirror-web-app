from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class CaptureTelemetry:
    brightness: int
    motion: int
    ambient_noise: int
    duration_seconds: int = 30
    sample_fps: float = 0.0
    frame_count: int = 0
    face_detected_ratio: float = 1.0
    device_user_agent: str = ""
    frame_samples: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ExpressionOutput:
    dominant_emoji: str
    valence: float
    arousal: float
    confidence: float
    emotion_probs: dict[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class RPPGOutput:
    hr: int
    rmssd: int
    sdnn: int
    rr: int
    signal_quality: int
    confidence: float
    source: str = "mock"


@dataclass(slots=True)
class FusionOutput:
    mood_index: int
    stress_index: int
    recovery_index: int
    confidence: int
    emoji: str
    advice_id: str
    advice_title: str
    advice_body: str
