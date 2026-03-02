# Jarvis 2.0 (Free Local Desktop Assistant)

This project gives you a **free, local Jarvis-style assistant** with:
- a hi-fi styled overlay window with optional pin-on-top,
- wake word listening for **"jarvis"**,
- short spoken replies,
- opening applications,
- multilingual speaking (voice language switching based on installed TTS voices),
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
- `speak in hindi`
- `set language to spanish`
- `what languages do you speak`
- `security tools` (lists defensive tools Jarvis can guide you with)
- `open notepad and then open chrome and then search tech news`
- terminal debug trace: `user said: ... so i will use ...` for each command
- `open whatsapp and search gauri contact and if you find her send her a hi`

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
- floating particle field around orb,
- voice-reactive waveform rings while Jarvis speaks,
- neon title and mode badge,
- conversation panel,
- transcript panel,
- command console input.
- window is **not always-on-top by default**; use the `PIN ON/PIN OFF` button in the title bar whenever you want to pin/unpin it.


## File structure (modularized)

- `assistant.py`: app bootstrap + voice loop orchestration
- `gui.py`: all Tkinter UI rendering/animation
- `behavior.py`: command parsing + conversational behavior logic
- `automation.py`: app/browser/typing/command automation actions
- `memory_store.py`: persistent memory (notes/preferences)

### Heavy task planner (optional Gemini key)

- On first launch, Jarvis asks one time for an optional Gemini API key.
- The key is used only for heavy chained commands with **3 or more** `and then` steps.
- Normal commands and 1-2 step chains run locally and do not use the API.
- You can skip the key and everything still works in local mode.

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

For better speech recognition on your machine:

```bash
python assistant.py --list-mics
python assistant.py --mic-device 2 --sample-rate 16000
python assistant.py --mic-name "headset"
python assistant.py --mic-name "realtek" --debug-asr
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


## Security scope

- Jarvis can help with **defensive/ethical security guidance** (hardening, legal lab learning, checklists).
- Jarvis can assist with **authorized defensive workflows** using tools like nmap, ncat, wireshark, nikto, skipfish, wapiti, OWASP ZAP, Burp Suite, Autopsy, and Binwalk.
- Jarvis does **not** provide unauthorized or harmful hacking instructions.
- Jarvis will not execute or automate offensive tools/flows (for example phishing, brute-force, exploit runners, credential theft, or attack chains).


## Speech recognition quality tips

- Jarvis now uses partial recognition to detect wake word faster.
- If speech is still inaccurate, list microphones and pick the correct `--mic-device`.
- By default Jarvis now uses your selected microphone's native sample rate for better accuracy.
- You can still override with `--sample-rate 16000` (or your device's best value).
- You can pick a microphone by name with `--mic-name "<part-of-device-name>"`.
- Use `--debug-asr` to print partial/final recognition text in terminal for tuning.
- Use the larger Vosk model (`vosk-model-en-us-0.22`) for better accuracy if your machine can handle it.
