from __future__ import annotations

from dataclasses import asdict

from .expression_adapter import ClassicalExpressionAdapter, ExpressionModelAdapter
from .rppg_adapter import ClassicalRPPGAdapter, RPPGModelAdapter, build_default_rppg_adapter
from .schemas import CaptureTelemetry, FusionOutput


def _clamp_int(value: float, low: int, high: int) -> int:
    return max(low, min(high, round(value)))


class VitalMirrorFusionPipeline:
    """Combines expression signals and rPPG signals into service outputs."""

    def __init__(
        self,
        expression_adapter: ExpressionModelAdapter | None = None,
        rppg_adapter: RPPGModelAdapter | None = None,
    ) -> None:
        self.expression_adapter = expression_adapter or ClassicalExpressionAdapter()
        self.rppg_adapter = rppg_adapter or build_default_rppg_adapter()
        self.rppg_fallback_adapter = ClassicalRPPGAdapter()

    def infer(self, telemetry: CaptureTelemetry) -> dict:
        expression = self.expression_adapter.infer(telemetry)
        try:
            rppg = self.rppg_adapter.infer(telemetry)
        except Exception:
            rppg = self.rppg_fallback_adapter.infer(telemetry)

        stress_index = _clamp_int(
            54
            + ((rppg.hr - 70) * 1.2)
            + ((38 - rppg.rmssd) * 0.9)
            + (expression.arousal * 15)
            - (expression.valence * 6),
            12,
            94,
        )

        recovery_index = _clamp_int(
            100 - stress_index + ((rppg.signal_quality - 55) * 0.32) + (expression.valence * 8),
            10,
            90,
        )

        mood_index = _clamp_int(
            (recovery_index * 0.55)
            + ((1 + expression.valence) * 18)
            + ((1 - max(expression.arousal, 0)) * 10)
            + ((rppg.signal_quality - 50) * 0.18),
            15,
            92,
        )

        confidence = _clamp_int(
            ((rppg.confidence * 100) * 0.7) + (expression.confidence * 100 * 0.3),
            20,
            94,
        )

        advice_id, advice_title, advice_body = self._choose_advice(stress_index, recovery_index, rppg.signal_quality)

        fusion = FusionOutput(
            mood_index=mood_index,
            stress_index=stress_index,
            recovery_index=recovery_index,
            confidence=confidence,
            emoji=expression.dominant_emoji,
            advice_id=advice_id,
            advice_title=advice_title,
            advice_body=advice_body,
        )

        return {
            "fusion": asdict(fusion),
            "expression": asdict(expression),
            "rppg": asdict(rppg),
        }

    @property
    def expression_adapter_name(self) -> str:
        return type(self.expression_adapter).__name__

    @property
    def rppg_adapter_name(self) -> str:
        return type(self.rppg_adapter).__name__

    @staticmethod
    def _choose_advice(stress_index: int, recovery_index: int, signal_quality: int) -> tuple[str, str, str]:
        if signal_quality < 45:
            return (
                "recheck",
                "환경을 정돈한 뒤 다시 측정해보세요",
                "얼굴 가림이나 조명 변화가 커 보입니다. 얼굴을 중앙에 두고 밝은 곳에서 다시 측정하면 더 안정적인 결과를 얻을 수 있습니다.",
            )
        if stress_index >= 70:
            return (
                "breathing_reset",
                "호흡 리셋을 먼저 해보세요",
                "긴장 부하가 높게 감지되었습니다. 60~90초 동안 천천히 호흡한 뒤 상태 변화를 다시 확인해보세요.",
            )
        if recovery_index <= 40:
            return (
                "light_recovery",
                "지금은 회복 행동을 먼저 권장합니다",
                "회복 여력이 낮아 보입니다. 물 한 잔, 목과 어깨 이완, 3분 걷기 중 하나를 먼저 해보세요.",
            )
        return (
            "steady_focus",
            "현재 상태는 비교적 안정적입니다",
            "지금 해야 할 한 가지를 정하고 짧은 집중 세션으로 이어가보세요. 무리한 해석보다 추세를 쌓는 것이 중요합니다.",
        )
