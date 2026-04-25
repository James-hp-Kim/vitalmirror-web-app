# Real Model Integration

## Goal

Replace the current classical prototype stack with a real multi-signal stack:

- facial expression model
- rPPG model trained from `MCD-rPPG`
- fusion layer for emoji and wellness outputs

## Recommended stack

### Expression branch

- Current prototype: OpenCV classical face/smile based adapter
- Next target: `Py-Feat` or another open-source expression model
- Output:
  - valence
  - arousal
  - emotion probabilities
  - optional action units

### rPPG branch

- Current prototype: OpenCV face ROI + temporal green-channel extraction + FFT HR estimate
- Next target: `MCD-rPPG` baseline model from the paper/repository
- Drop exported ONNX weights into `models/mcd_rppg.onnx` to activate the ONNX adapter path
- Output:
  - predicted PPG waveform
  - HR
  - RMSSD
  - SDNN
  - RR
  - signal quality

### Fusion branch

- Combine expression + rPPG + quality metadata
- Generate:
  - mood index
  - stress index
  - recovery index
  - emoji
  - coaching message

## Files added in this prototype

- `ml_pipeline/schemas.py`
- `ml_pipeline/expression_adapter.py`
- `ml_pipeline/rppg_adapter.py`
- `ml_pipeline/fusion.py`
- `ml_pipeline_demo.py`
- `tools/export_mcd_rppg_onnx.py`
- `tools/inspect_mcd_rppg_onnx.py`

## How to swap in real models

### 1. Expression

Replace `MockExpressionAdapter` with `PyFeatExpressionAdapter` implementation.

Expected flow:

1. receive frame buffer
2. sample representative frames
3. run face/expression inference
4. aggregate to valence/arousal/emotion probabilities

### 2. rPPG

Replace `MockRPPGAdapter` with `MCDRPPGAdapter` implementation.

Expected flow:

1. collect 20-30 second frame sequence
2. run face mesh / ROI extraction
3. build ROI temporal traces
4. feed traces into trained model
5. recover PPG and derive HR / HRV / RR

Current upgrade:

- `ClassicalRPPGAdapter` now extracts 8 ROI traces from real frame samples
- `MCDRPPGAdapter` auto-activates when `models/mcd_rppg.onnx` exists

### 3. Fusion

Keep `VitalMirrorFusionPipeline`, but replace the temporary rule weights with:

- validated heuristics
- or a supervised fusion model trained on your app data

## Suggested backend flow

1. browser captures 30 seconds
2. backend stores raw session metadata
3. expression adapter processes sampled frames
4. rPPG adapter processes the frame buffer
5. fusion pipeline produces final output
6. user confirms emoji / mood fit
7. feedback is stored for retraining

## Suggested training data loop

- store prediction outputs in DB
- store user-selected emoji and self-report
- export joined dataset to CSV/Parquet
- retrain expression/fusion layers in batch
- deploy only validated model versions

## Important caution

Do not treat facial expression alone as a direct diagnosis of depression or anxiety.
Use it as one signal among:

- expression
- rPPG
- self-report
- sensor data later
