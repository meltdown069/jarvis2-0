# Jarvis 2.0 (Free Local Desktop Assistant)

This project gives you a **free, local Jarvis-style assistant** with:
- an always-on-top hi-fi styled overlay window,
- wake word listening for **"jarvis"**,
- short spoken replies,
- opening applications,
- running terminal commands,
- slow human-like browser search/open automation (mouse + keyboard control).

It uses only free local components (no premium APIs).

## What it does

Commands after wake word:
- `open chrome`
- `open discord`
- `open spotify`
- `open vscode`
- `open terminal`
- `open notepad`
- `open youtube.com` (opens Chrome, focuses address bar, types, enters slowly)
- `open this app discord` (natural app phrase supported)
- `search best laptops 2026` (opens Chrome and types query slowly)
- `run pwd`

Natural phrases also work:
- `hey jarvis search youtube.com`
- `jarvis open discord`
- `jarvis open this app spotify`

### Case sensitivity fixed

App names are normalized, so `open Notepad`, `open notepad`, and even bare `notepad` are treated the same.

## UI

The overlay has a higher-fidelity Jarvis look with:
- animated central orb,
- neon title and mode badge,
- conversation panel,
- transcript panel,
- command console input.

## Setup

### 1) Install Python deps

```bash
pip install -r requirements.txt
```

### 2) Download a free Vosk model

Download from: https://alphacephei.com/vosk/models

Recommended:
- `vosk-model-small-en-us-0.15`

Extract so the model folder directly contains:

```text
am/
conf/
```

Example:

```text
models/vosk-model-small-en-us-0.15/
  am/
  conf/
```

### 3) Run

```bash
python assistant.py
```

Optional custom path:

```bash
python assistant.py --model-path "C:/path/to/vosk-model-small-en-us-0.15"
```

## Human-like action behavior

For `open <website>` and `search <query>`, Jarvis now:
1. Speaks first,
2. Opens/focuses Chrome,
3. Uses keyboard shortcuts for address bar,
4. Types with slower human-like speed,
5. Presses Enter.

If GUI automation fails/unavailable, it falls back to normal browser open.

## Troubleshooting

- If voice model fails, Jarvis starts in manual mode.
- If microphone fails, manual input still works.

## Security warning

`run <command>` executes local shell commands. Use only on your own trusted machine.
