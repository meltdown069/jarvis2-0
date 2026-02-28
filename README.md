# Jarvis 2.0 (Free Local Desktop Assistant)

This project gives you a **free, local Jarvis-style assistant** with:
- an always-on-top mini overlay window,
- wake word listening for **"jarvis"**,
- short spoken replies,
- opening applications,
- running terminal commands,
- searching Google in Chrome.

It uses only free local components (no premium APIs).

## What it does

Commands after wake word:
- `open chrome`
- `open vscode`
- `open terminal`
- `open notepad`
- `search best laptops 2026`
- `run pwd`

Flow:
1. Say: `jarvis`
2. Jarvis replies: `Yes?`
3. Say one command (open/search/run)

You can also type commands manually in the overlay input box.

## Setup

### 1) Install Python deps

```bash
pip install -r requirements.txt
```

### 2) Download a free Vosk model

Download a small English model from: https://alphacephei.com/vosk/models

Recommended:
- `vosk-model-small-en-us-0.15`

Extract it to:

```text
models/vosk-model-small-en-us-0.15
```

### 3) Run

```bash
python assistant.py
```

## Notes

- TTS is local via `pyttsx3`.
- Speech recognition is local via `vosk`.
- App launch mappings are in `open_application()` inside `assistant.py`.
- Add more apps by extending that mapping.

## Security warning

The `run <command>` feature executes local shell commands. Only use this on your own trusted machine.
