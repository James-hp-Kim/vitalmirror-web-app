from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect the ONNX model used by VitalMirror.")
    parser.add_argument(
        "--model",
        default=str(Path(__file__).resolve().parents[1] / "models" / "mcd_rppg.onnx"),
        help="Path to the ONNX file.",
    )
    args = parser.parse_args()

    model_path = Path(args.model).resolve()
    if not model_path.exists():
        raise SystemExit(f"Model file not found: {model_path}")

    try:
        import onnxruntime as ort
    except Exception as exc:  # pragma: no cover
        raise SystemExit(f"onnxruntime is required. Original error: {exc}")

    session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
    payload = {
        "model": str(model_path),
        "inputs": [
            {
                "name": inp.name,
                "shape": inp.shape,
                "type": inp.type,
            }
            for inp in session.get_inputs()
        ],
        "outputs": [
            {
                "name": out.name,
                "shape": out.shape,
                "type": out.type,
            }
            for out in session.get_outputs()
        ],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
