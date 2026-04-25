# VitalMirror Web App

VitalMirror is a camera-based wellness check prototype. It captures browser camera frames, estimates expression and rPPG-style signals, then returns mood, stress load, recovery, signal quality, and coaching feedback.

This is a wellness MVP, not a medical diagnosis tool.

## Features

- 30-second browser camera scan
- Photo-based expression-only fallback
- Mobile control deck and `/phone` route
- Server-side expression + rPPG + fusion pipeline
- HR, RMSSD, SDNN, RR, signal quality, valence, arousal
- SQLite feedback loop for local development
- CSV export for offline training experiments

## Local Run

Use the bundled Python runtime path if you are running inside Codex, or any Python environment with `requirements.txt` installed.

```powershell
pip install -r requirements.txt
python server.py
```

Open:

- http://127.0.0.1:8765/
- http://127.0.0.1:8765/phone

For same-Wi-Fi phone testing on Windows, run:

```powershell
.\open_vitalmirror_phone.cmd
```

## Vercel Deployment

The project is prepared as:

- `public/` for the static web app
- `api/index.py` for the Python Flask API entrypoint
- `vercel.json` for routing `/api/*`, `/`, and `/phone`

Vercel runtime storage is ephemeral, so SQLite feedback data on Vercel should be treated as temporary. Use a persistent database before production use.

Helpful Windows scripts:

```powershell
.\publish_github.cmd
.\deploy_vercel.cmd
```

If authentication is missing:

```powershell
gh auth login --hostname github.com --git-protocol https --web --scopes repo
npx vercel@33 login
```

## Important Notes

- Camera access requires `localhost` or HTTPS.
- Mobile camera access on a deployed site requires the Vercel HTTPS URL.
- The current rPPG and expression adapters are prototype-grade. Replace them with validated models before real-world use.
- Do not present the output as medical diagnosis.

## Model Integration

See [REAL_MODEL_INTEGRATION.md](REAL_MODEL_INTEGRATION.md) for the path toward a real expression model and MCD-rPPG inference stack.
