from __future__ import annotations

import argparse
from pathlib import Path


def fail(message: str) -> None:
    raise SystemExit(message)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scaffold exporter for an MCD-rPPG PyTorch model to ONNX."
    )
    parser.add_argument(
        "--repo-root",
        required=True,
        help="Path to a local clone of https://github.com/ksyegorov/mcd_rppg",
    )
    parser.add_argument(
        "--checkpoint",
        required=True,
        help="Path to the trained PyTorch checkpoint for the SCNN 8-ROI model.",
    )
    parser.add_argument(
        "--output",
        default=str(Path(__file__).resolve().parents[1] / "models" / "mcd_rppg.onnx"),
        help="Output ONNX path.",
    )
    parser.add_argument(
        "--seq-len",
        type=int,
        default=120,
        help="Number of temporal steps to use in the dummy export input.",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    checkpoint = Path(args.checkpoint).resolve()
    output = Path(args.output).resolve()

    if not repo_root.exists():
        fail(f"Repo root not found: {repo_root}")
    if not checkpoint.exists():
        fail(f"Checkpoint not found: {checkpoint}")

    try:
        import torch
    except Exception as exc:  # pragma: no cover - depends on user environment
        fail(
            "PyTorch is required to export the model to ONNX. "
            f"Install torch in the export environment first. Original error: {exc}"
        )

    # We intentionally do not hardcode the upstream model import path because the
    # repository is notebook-first and may change. This script is the handoff
    # point where you wire the exact SCNN model class from the local clone.
    fail(
        "\n".join(
            [
                "ONNX export scaffold is ready, but the upstream model class still needs to be wired.",
                f"Repo root: {repo_root}",
                f"Checkpoint: {checkpoint}",
                f"Planned output: {output}",
                "",
                "Next manual step:",
                "1. Open the local mcd_rppg clone and identify the SCNN 8-ROI model class used in train_SCNN_8roi_mcd_rppg.ipynb.",
                "2. Instantiate that model, load the checkpoint, and export it with torch.onnx.export.",
                "3. Save the final file as models/mcd_rppg.onnx so this prototype auto-detects it.",
                "",
                "Suggested dummy input shape candidates to test:",
                f"- (1, 8, {args.seq_len})",
                f"- (1, {args.seq_len}, 8)",
            ]
        )
    )


if __name__ == "__main__":
    main()
