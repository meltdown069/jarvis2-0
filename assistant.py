import argparse
import json
import os
import platform
import queue
import re
import shlex
import subprocess
import threading
import time
import urllib.parse
import webbrowser
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
import tkinter as tk

import pyttsx3
import sounddevice as sd
from vosk import KaldiRecognizer, Model

try:
    import pyautogui
except Exception:
    pyautogui = None

WAKE_WORD = "jarvis"
SAMPLE_RATE = 16000


@dataclass
class AssistantConfig:
    model_path: Path | None = None


class JarvisAssistant:
    def __init__(self, config: AssistantConfig):
        self.config = config
        self.audio_queue: queue.Queue[bytes] = queue.Queue()
        self.tts_queue: queue.Queue[str] = queue.Queue()
        self.stop_event = threading.Event()
        self.awaiting_command = False
        self.voice_enabled = False
        self.model: Model | None = None
        self.recognizer: KaldiRecognizer | None = None
        self.pulse_phase = 0

        self.pending_action: tuple[str, str] | None = None
        self.awaiting_profile_choice = False
        self.awaiting_obstacle_resolution = False
        self.current_task = ""

        self.memory_path = Path("jarvis_memory.json")
        self.memory: dict[str, Any] = self._load_memory()

        self.tts_engine = pyttsx3.init()
        self.tts_engine.setProperty("rate", 178)
        threading.Thread(target=self._tts_worker, daemon=True).start()

        self.root = tk.Tk()
        self.root.title("JARVIS")
        self.root.geometry("920x560+20+20")
        self.root.configure(bg="#020914")
        self.root.attributes("-topmost", True)

        self.status_var = tk.StringVar(value="Booting systems…")
        self.input_var = tk.StringVar()
        self.last_heard_var = tk.StringVar(value="Heard: -")
        self.mode_var = tk.StringVar(value="Listening for wake word")

        self._build_ui()
        self._animate_orb()
        self._initialize_voice_recognition()

    def _load_memory(self) -> dict[str, Any]:
        if self.memory_path.exists():
            try:
                return json.loads(self.memory_path.read_text())
            except Exception:
                pass
        return {"notes": [], "prefs": {}}

    def _save_memory(self) -> None:
        try:
            self.memory_path.write_text(json.dumps(self.memory, indent=2))
        except Exception:
            pass

    def _remember(self, note: str) -> None:
        notes = self.memory.setdefault("notes", [])
        notes.append({"ts": datetime.now().isoformat(timespec="seconds"), "note": note})
        self.memory["notes"] = notes[-50:]
        self._save_memory()

    def _set_pref(self, key: str, value: str) -> None:
        prefs = self.memory.setdefault("prefs", {})
        prefs[key] = value
        self._save_memory()

    def _get_pref(self, key: str) -> str | None:
        return self.memory.get("prefs", {}).get(key)


    def _start_task(self, description: str) -> None:
        self.current_task = description
        self.say(f"Starting task: {description}")

    def _finish_task(self, message: str) -> None:
        self.current_task = ""
        self.say(message)

    def _build_ui(self) -> None:
        shell = tk.Frame(self.root, bg="#040E1D", highlightbackground="#113554", highlightthickness=1)
        shell.pack(fill="both", expand=True, padx=10, pady=10)

        topbar = tk.Frame(shell, bg="#040E1D")
        topbar.pack(fill="x", padx=12, pady=(10, 4))
        tk.Label(topbar, text="J.A.R.V.I.S", fg="#5EE6FF", bg="#040E1D", font=("Segoe UI", 14, "bold")).pack(side="left")
        tk.Label(topbar, text="LOCAL MODE", fg="#A8D9FF", bg="#0E2640", padx=10, pady=3, font=("Segoe UI", 9, "bold")).pack(side="right")

        body = tk.Frame(shell, bg="#040E1D")
        body.pack(fill="both", expand=True, padx=10, pady=8)

        left = tk.Frame(body, bg="#040E1D")
        left.pack(side="left", fill="both", expand=True)

        self.orb = tk.Canvas(left, width=430, height=410, bg="#040E1D", highlightthickness=0)
        self.orb.pack(pady=(8, 0))
        self._draw_orb(0)

        tk.Label(left, text="J.A.R.V.I.S", fg="#DDF3FF", bg="#040E1D", font=("Segoe UI", 20, "bold")).pack(pady=(8, 2))
        tk.Label(left, textvariable=self.mode_var, fg="#9EE7FF", bg="#092035", padx=12, pady=4, font=("Segoe UI", 9)).pack()

        right = tk.Frame(body, bg="#071425", highlightbackground="#113554", highlightthickness=1)
        right.pack(side="right", fill="both", expand=False, padx=(8, 0))
        right.configure(width=360)

        tk.Label(right, text="Conversation", fg="#D7EEFF", bg="#071425", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=12, pady=(10, 6))

        status_wrap = tk.Frame(right, bg="#0A1D33", highlightbackground="#1E3F63", highlightthickness=1)
        status_wrap.pack(fill="x", padx=10, pady=(0, 8))
        tk.Label(status_wrap, textvariable=self.status_var, fg="#D5EAFF", bg="#0A1D33", justify="left", wraplength=320, padx=8, pady=8, font=("Segoe UI", 10)).pack(fill="x")

        heard_wrap = tk.Frame(right, bg="#081528")
        heard_wrap.pack(fill="x", padx=10, pady=(0, 8))
        tk.Label(heard_wrap, textvariable=self.last_heard_var, fg="#8FBEE8", bg="#081528", anchor="w", padx=8, pady=6, font=("Consolas", 10)).pack(fill="x")

        entry_wrap = tk.Frame(right, bg="#071425")
        entry_wrap.pack(side="bottom", fill="x", padx=10, pady=10)

        entry = tk.Entry(entry_wrap, textvariable=self.input_var, font=("Segoe UI", 11), bg="#05101D", fg="#E6F5FF", insertbackground="#E6F5FF", relief="flat")
        entry.pack(side="left", fill="x", expand=True, ipady=6)
        entry.bind("<Return>", self._on_manual_command)
        tk.Button(entry_wrap, text="SEND", command=self._on_manual_command, bg="#28C3FF", fg="#01101A", relief="flat", padx=12, pady=6, font=("Segoe UI", 9, "bold")).pack(side="left", padx=(8, 0))

        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)

    def _draw_orb(self, phase: int) -> None:
        self.orb.delete("all")
        cx, cy = 215, 190
        r1 = 44 + (phase % 8)
        r2 = 72 + ((phase * 2) % 10)
        r3 = 102 + ((phase * 3) % 12)
        self.orb.create_oval(cx - r3, cy - r3, cx + r3, cy + r3, outline="#11385A", width=2)
        self.orb.create_oval(cx - r2, cy - r2, cx + r2, cy + r2, outline="#1A5A87", width=2)
        self.orb.create_oval(cx - r1, cy - r1, cx + r1, cy + r1, outline="#2A8CC4", width=2)
        self.orb.create_oval(cx - 34, cy - 34, cx + 34, cy + 34, fill="#0B4D7B", outline="#4BC3FF", width=2)
        self.orb.create_text(cx, cy + 2, text="••••", fill="#7CE1FF", font=("Segoe UI", 14, "bold"))

    def _animate_orb(self) -> None:
        self.pulse_phase = (self.pulse_phase + 1) % 60
        self._draw_orb(self.pulse_phase)
        if not self.stop_event.is_set():
            self.root.after(130, self._animate_orb)

    def _candidate_model_paths(self) -> list[Path]:
        candidates: list[Path] = []
        if self.config.model_path:
            candidates.append(self.config.model_path)
        env_value = os.environ.get("VOSK_MODEL_PATH")
        if env_value:
            candidates.append(Path(env_value))
        models_dir = Path("models")
        candidates.extend([models_dir / "vosk-model-small-en-us-0.15", models_dir / "vosk-model-en-us-0.22", models_dir / "vosk-model-small-en-in-0.4"])
        if models_dir.exists():
            for sub in models_dir.iterdir():
                if sub.is_dir() and sub.name.startswith("vosk-model"):
                    candidates.append(sub)
                    nested = sub / sub.name
                    if nested.exists() and nested.is_dir() and nested.name.startswith("vosk-model"):
                        candidates.append(nested)
        unique: list[Path] = []
        seen: set[str] = set()
        for path in candidates:
            key = str(path.resolve()) if path.exists() else str(path)
            if key not in seen:
                seen.add(key)
                unique.append(path)
        return unique

    def _is_valid_model_dir(self, path: Path) -> bool:
        return path.exists() and path.is_dir() and (path / "am").exists() and (path / "conf").exists()

    def _initialize_voice_recognition(self) -> None:
        valid = [p for p in self._candidate_model_paths() if self._is_valid_model_dir(p)]
        if not valid:
            self.voice_enabled = False
            self.mode_var.set("Voice OFF - manual mode")
            self.status_var.set("Voice OFF: model missing. Manual commands still work.")
            return
        for model_dir in valid:
            try:
                self.model = Model(str(model_dir))
                self.recognizer = KaldiRecognizer(self.model, SAMPLE_RATE)
                self.voice_enabled = True
                self.mode_var.set("Listening for wake word")
                self.status_var.set(f"Voice ON. Listening for wake word '{WAKE_WORD}'.")
                return
            except Exception:
                continue
        self.voice_enabled = False
        self.mode_var.set("Voice OFF - manual mode")
        self.status_var.set("Voice OFF: model failed to load. Manual commands still work.")

    def say(self, text: str) -> None:
        self.status_var.set(f"Jarvis: {text}")
        self.tts_queue.put(text)

    def _tts_worker(self) -> None:
        while not self.stop_event.is_set():
            try:
                text = self.tts_queue.get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
            except Exception:
                continue

    def _audio_callback(self, indata, _frames, _time_info, status):
        if status:
            print(status)
        self.audio_queue.put(bytes(indata))

    def start_listening_thread(self) -> None:
        if not self.voice_enabled or not self.recognizer:
            return
        threading.Thread(target=self._listen_loop, daemon=True).start()

    def _listen_loop(self) -> None:
        if not self.recognizer:
            return
        try:
            with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=8000, dtype="int16", channels=1, callback=self._audio_callback):
                while not self.stop_event.is_set():
                    data = self.audio_queue.get()
                    if self.recognizer.AcceptWaveform(data):
                        result = json.loads(self.recognizer.Result())
                        text = result.get("text", "").strip().lower()
                        if text:
                            self.root.after(0, self.last_heard_var.set, f"Heard: {text}")
                            self._route_speech(text)
        except Exception:
            self.voice_enabled = False
            self.root.after(0, self.mode_var.set, "Voice OFF - manual mode")
            self.root.after(0, self.status_var.set, "Voice OFF: microphone unavailable. Manual mode active.")

    def _on_manual_command(self, _event=None) -> None:
        text = self.input_var.get().strip().lower()
        if not text:
            return
        self.input_var.set("")
        self.last_heard_var.set(f"Manual: {text}")
        threading.Thread(target=self.handle_command, args=(text,), daemon=True).start()

    def _cleanup_command_text(self, text: str) -> str:
        cleaned = re.sub(r"[^a-z0-9:/?&.=+_\- ]", " ", text.lower())
        cleaned = re.sub(r"\b(hey|hi|hello|please|jarvis|buddy|sir|can you|could you|would you)\b", " ", cleaned)
        return re.sub(r"\s+", " ", cleaned).strip()

    def _extract_inline_command(self, text: str) -> str:
        cleaned = self._cleanup_command_text(text)
        if cleaned.startswith(WAKE_WORD):
            cleaned = cleaned[len(WAKE_WORD):].strip()
        for phrase in ["search ", "open ", "run ", "what is the time", "what s the time", "time", "who are you"]:
            idx = cleaned.find(phrase)
            if idx != -1:
                return cleaned[idx:].strip()
        return ""

    def _route_speech(self, text: str) -> None:
        if self.awaiting_command:
            self.awaiting_command = False
            cleaned = self._cleanup_command_text(text)
            if cleaned:
                threading.Thread(target=self.handle_command, args=(cleaned,), daemon=True).start()
            return
        if WAKE_WORD in text:
            inline_command = self._extract_inline_command(text)
            if inline_command:
                threading.Thread(target=self.handle_command, args=(inline_command,), daemon=True).start()
            else:
                self.awaiting_command = True
                self.say("Yes sir?")

    def _looks_like_website(self, text: str) -> bool:
        if " " in text or not text:
            return False
        return bool(re.match(r"^(https?://)?[a-z0-9][a-z0-9\-]*(\.[a-z0-9\-]+)+([/?].*)?$", text))

    def _normalize_open_target(self, target: str) -> str:
        target = target.strip().lower()
        target = re.sub(r"^(this|the)\s+", "", target)
        target = re.sub(r"^(app|application)\s+", "", target)
        target = re.sub(r"^(app|application)\s+(called|named)\s+", "", target)
        target = re.sub(r"^(called|named)\s+", "", target).strip()
        alias_map = {"vs code": "vscode", "visual studio code": "vscode", "google chrome": "chrome", "command prompt": "terminal", "cmd": "terminal", "note pad": "notepad"}
        return alias_map.get(target, target)

    def _extract_open_and_type(self, command: str) -> tuple[str, str] | None:
        m = re.match(r"^open\s+(.+?)\s+and\s+type\s+(.+)$", command)
        if not m:
            return None
        return self._normalize_open_target(m.group(1).strip()), m.group(2).strip()

    def _resolve_chrome_profile_choice(self, text: str) -> str | None:
        t = self._cleanup_command_text(text)
        choices = {"default": "Default", "profile 1": "Profile 1", "one": "Profile 1", "1": "Profile 1", "profile 2": "Profile 2", "two": "Profile 2", "2": "Profile 2"}
        for k, v in choices.items():
            if k in t:
                return v
        return None

    def _maybe_handle_obstacle_followup(self, command: str) -> bool:
        if not self.awaiting_obstacle_resolution or not self.pending_action:
            return False
        if command in {"cancel", "stop", "leave it"}:
            self.awaiting_obstacle_resolution = False
            self.pending_action = None
            self.say("Okay sir, cancelled.")
            return True
        action, _payload = self.pending_action
        self.awaiting_obstacle_resolution = False
        self.pending_action = None
        if action == "open_app":
            self.say(f"Trying {command} instead, sir.")
            self.say(self.open_application(command))
            return True
        if action == "run_cmd":
            self.say("Trying your alternative command now, sir.")
            self.say(self.execute_terminal_command(command))
            return True
        return False

    def _maybe_handle_profile_followup(self, command: str) -> bool:
        if not self.awaiting_profile_choice or not self.pending_action:
            return False
        profile = self._resolve_chrome_profile_choice(command)
        if not profile:
            self.say("Please tell me profile 1, profile 2, or default.")
            return True
        action, payload = self.pending_action
        self.awaiting_profile_choice = False
        self.pending_action = None
        self._set_pref("chrome_profile", profile)
        self.say(f"Opening {profile} now, sir.")
        if action == "search":
            threading.Thread(target=self.search_human_like, args=(payload, profile), daemon=True).start()
        elif action == "website":
            threading.Thread(target=self.open_website_human_like, args=(payload, profile), daemon=True).start()
        return True

    def handle_command(self, command: str) -> None:
        command = self._cleanup_command_text(command)
        if not command:
            return
        if self._maybe_handle_obstacle_followup(command):
            return
        if self._maybe_handle_profile_followup(command):
            return

        if command in {"time", "what is the time", "what s the time", "tell me the time"}:
            self.say(f"It is {datetime.now().strftime('%I:%M %p')} sir")
            return
        if command in {"who are you", "what are you", "who r you"}:
            self.say("I am Jarvis, your local assistant. I can open apps, search, type, run commands, and remember notes.")
            return
        if command in {"what is on my screen", "what s on my screen", "what do you see"}:
            self.say("I cannot fully read your screen yet. Describe what you see and I will guide you step by step.")
            return

        mem = re.match(r"^remember\s+(.+)$", command)
        if mem:
            self._remember(f"user_note: {mem.group(1).strip()}")
            self.say("Got it sir. I will remember that.")
            return
        if command in {"memory", "show memory", "what do you remember"}:
            notes = self.memory.get("notes", [])
            if notes:
                self.say(f"I remember {len(notes)} notes. Latest: {notes[-1]['note']}")
            else:
                self.say("I do not have notes yet, sir.")
            return

        open_type = self._extract_open_and_type(command)
        if open_type:
            app_name, text_to_type = open_type
            self._start_task(f"open {app_name} and type text")
            threading.Thread(target=self.open_and_type_human_like, args=(app_name, text_to_type), daemon=True).start()
            return

        if command.startswith("open "):
            target = self._normalize_open_target(command.replace("open ", "", 1).strip())
            if self._looks_like_website(target):
                pref = self._get_pref("chrome_profile")
                if pref:
                    self._start_task(f"open website in {pref}")
                    threading.Thread(target=self.open_website_human_like, args=(target, pref), daemon=True).start()
                else:
                    self.pending_action = ("website", target)
                    self.awaiting_profile_choice = True
                    self.say("I see multiple Chrome profiles possible. Which one should I open: profile 1, profile 2, or default?")
                return
            self._start_task(f"open {target}")
            self.say(self.open_application(target))
            return

        if command.startswith("search "):
            query = command.replace("search ", "", 1).strip()
            pref = self._get_pref("chrome_profile")
            if pref:
                self._start_task(f"search {query}")
                threading.Thread(target=self.search_human_like, args=(query, pref), daemon=True).start()
            else:
                self.pending_action = ("search", query)
                self.awaiting_profile_choice = True
                self.say("Which Chrome profile should I use: profile 1, profile 2, or default?")
            return

        if command.startswith("run "):
            cmd_to_run = command.replace("run ", "", 1).strip()
            self._start_task(f"run {cmd_to_run}")
            result = self.execute_terminal_command(cmd_to_run)
            self.say(result)
            if result == "Command failed.":
                self.pending_action = ("run_cmd", cmd_to_run)
                self.awaiting_obstacle_resolution = True
                self.say("I hit an obstacle. Tell me an alternative command or say cancel.")
            return

        normalized = self._normalize_open_target(command)
        if normalized and len(normalized.split()) <= 3:
            self.say(self.open_application(normalized))
            return

        self.say("Sorry sir, I did not get that. Could you rephrase?")

    def open_application(self, app_name: str) -> str:
        app_name = app_name.lower().strip()
        system = platform.system().lower()

        if pyautogui and system == "windows":
            try:
                self.open_app_human_like_windows(app_name)
                return f"Opening {app_name} sir"
            except Exception:
                pass

        app_map = {
            "chrome": {"windows": ["cmd", "/c", "start", "", "chrome"], "darwin": ["open", "-a", "Google Chrome"], "linux": ["google-chrome"]},
            "discord": {"windows": ["cmd", "/c", "start", "", "discord"], "darwin": ["open", "-a", "Discord"], "linux": ["discord"]},
            "spotify": {"windows": ["cmd", "/c", "start", "", "spotify"], "darwin": ["open", "-a", "Spotify"], "linux": ["spotify"]},
            "vscode": {"windows": ["cmd", "/c", "start", "", "code"], "darwin": ["open", "-a", "Visual Studio Code"], "linux": ["code"]},
            "terminal": {"windows": ["cmd", "/c", "start", "", "cmd"], "darwin": ["open", "-a", "Terminal"], "linux": ["x-terminal-emulator"]},
            "notepad": {"windows": ["notepad"], "darwin": ["open", "-a", "TextEdit"], "linux": ["gedit"]},
        }

        try:
            if app_name in app_map:
                cmd = app_map[app_name].get(system)
                if not cmd:
                    return "This OS is not supported for that app."
                subprocess.Popen(cmd)
                return f"Opening {app_name} sir"
            if system == "windows":
                subprocess.Popen(["cmd", "/c", "start", "", app_name])
            elif system == "darwin":
                subprocess.Popen(["open", "-a", app_name])
            else:
                subprocess.Popen([app_name])
            return f"Trying to open {app_name} sir"
        except Exception:
            self.pending_action = ("open_app", app_name)
            self.awaiting_obstacle_resolution = True
            return f"I could not find {app_name}. Tell me another app name and I will continue." 

    def open_app_human_like_windows(self, app_name: str) -> None:
        quick = {"notepad": "notepad", "terminal": "cmd", "cmd": "cmd"}
        if app_name in quick:
            pyautogui.hotkey("win", "r")
            time.sleep(0.3)
            pyautogui.typewrite(quick[app_name], interval=0.06)
            pyautogui.press("enter")
            return
        pyautogui.press("win")
        time.sleep(0.35)
        pyautogui.typewrite(app_name, interval=0.065)
        time.sleep(0.35)
        pyautogui.press("enter")

    def open_and_type_human_like(self, app_name: str, text_to_type: str) -> None:
        target = self._normalize_open_target(app_name)
        if pyautogui and platform.system().lower() == "windows":
            try:
                if target in {"terminal", "cmd", "command prompt"}:
                    target = "cmd"
                self.open_app_human_like_windows(target)
                time.sleep(1.3)
                pyautogui.typewrite(text_to_type, interval=0.06)
                if target == "cmd":
                    pyautogui.press("enter")
                self._finish_task("Done sir. Do you want me to continue with anything else?")
                return
            except Exception:
                pass
        self.say(self.open_application(target))

    def _open_chrome_window(self, profile: str | None = None) -> None:
        system = platform.system().lower()
        if system == "windows":
            if profile:
                subprocess.Popen(["cmd", "/c", "start", "", "chrome", f"--profile-directory={profile}"])
            else:
                subprocess.Popen(["cmd", "/c", "start", "", "chrome"])
        elif system == "darwin":
            subprocess.Popen(["open", "-a", "Google Chrome"])
        else:
            subprocess.Popen(["google-chrome"])

    def search_human_like(self, query: str, profile: str | None = None) -> None:
        if pyautogui:
            try:
                self._open_chrome_window(profile)
                time.sleep(1.3)
                if platform.system().lower() == "darwin":
                    pyautogui.hotkey("command", "l")
                else:
                    pyautogui.hotkey("ctrl", "l")
                pyautogui.typewrite(query, interval=0.08)
                time.sleep(0.2)
                pyautogui.press("enter")
                self._finish_task("Search done sir. Should I open any result?")
                return
            except Exception:
                pass
        self.search_in_chrome(query)

    def open_website_human_like(self, website: str, profile: str | None = None) -> None:
        normalized = website if website.startswith(("http://", "https://")) else f"https://{website}"
        if not pyautogui:
            webbrowser.open_new_tab(normalized)
            return
        try:
            self._open_chrome_window(profile)
            time.sleep(1.2)
            if platform.system().lower() == "darwin":
                pyautogui.hotkey("command", "l")
            else:
                pyautogui.hotkey("ctrl", "l")
            pyautogui.typewrite(website, interval=0.08)
            pyautogui.press("enter")
            self._finish_task("Website opened sir. Want me to type anything there?")
        except Exception:
            webbrowser.open_new_tab(normalized)

    def _chrome_candidates(self) -> list[Path]:
        home = Path.home()
        return [
            Path("/usr/bin/google-chrome"), Path("/usr/bin/chromium-browser"), Path("/usr/bin/chromium"),
            home / "AppData/Local/Google/Chrome/Application/chrome.exe",
            Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
            Path("C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"),
            Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        ]

    def search_in_chrome(self, query: str) -> None:
        url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"
        for chrome_path in self._chrome_candidates():
            if chrome_path.exists():
                webbrowser.register("jarvis_chrome", None, webbrowser.BackgroundBrowser(str(chrome_path)))
                webbrowser.get("jarvis_chrome").open_new_tab(url)
                return
        webbrowser.open_new_tab(url)

    def execute_terminal_command(self, cmd: str) -> str:
        try:
            args = shlex.split(cmd)
            result = subprocess.run(args, capture_output=True, text=True, timeout=20)
            return "Command completed." if result.returncode == 0 else "Command failed."
        except Exception:
            return "Unable to run that command."

    def shutdown(self) -> None:
        self.stop_event.set()
        self.root.destroy()

    def run(self) -> None:
        self.start_listening_thread()
        self.root.mainloop()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Free local Jarvis assistant")
    parser.add_argument("--model-path", type=Path, default=None, help="Path to extracted Vosk model folder (contains am/ and conf/)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    JarvisAssistant(AssistantConfig(model_path=args.model_path)).run()
