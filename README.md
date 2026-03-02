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
- `open notepad and type i am cool`
- `open cmd and type whoami`
- `what is the time`

- `who are you`
- `what is on my screen` (Jarvis will ask you to describe and guide next actions)

- `remember buy milk tomorrow`
- `what do you remember`

- `run pwd`
- `open notepad and then open chrome and then search ai news`

Natural phrases also work:
- `hey jarvis search youtube.com`
- `jarvis open discord`
- `jarvis open this app spotify`

### Case sensitivity + normal command fixes

App names are normalized, so `open Notepad`, `open notepad`, and bare `notepad` are treated the same.

Compound commands now work:
- `open notepad and type i am cool`
- `open cmd and type whoami`


### Chatty + self-aware behavior

- Task progress voice: Jarvis now announces when a task starts and when it completes.
- Jarvis now asks follow-up questions when needed (for example Chrome profile selection).
- For Chrome actions (`search ...`, `open youtube.com`), Jarvis asks: profile 1, profile 2, or default.
- After actions, Jarvis gives conversational follow-ups like asking what to do next on screen.

## UI

The overlay has a higher-fidelity Jarvis look with:
- animated central orb,
- neon title and mode badge,
- conversation panel,
- transcript panel,
- command console input.


## File structure (modularized)

- `assistant.py`: app bootstrap + voice loop orchestration
- `gui.py`: all Tkinter UI rendering/animation
- `behavior.py`: command parsing + conversational behavior logic
- `automation.py`: app/browser/typing/command automation actions
- `memory_store.py`: persistent memory (notes/preferences)

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

## Obstacle handling + memory

- If Jarvis hits an obstacle (app/command fails), it asks you what to do next and continues based on your answer.
- Jarvis stores memory in `jarvis_memory.json` (notes + preferences such as Chrome profile).


## Task chains

- Jarvis can execute chained tasks separated by `and then`.
- If blocked in a step, Jarvis asks what to do and continues from your answer.
