# Model Files

Drop future exported model files here.

## Expected filename

- `mcd_rppg.onnx`

## Current behavior

If `mcd_rppg.onnx` exists and can be loaded by `onnxruntime`,
the backend will prefer `MCDRPPGAdapter`.

If the file is missing or incompatible,
the backend automatically falls back to `ClassicalRPPGAdapter`.
