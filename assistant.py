import json
import platform
import queue
import shlex
import subprocess
import threading
import urllib.parse
import webbrowser
from dataclasses import dataclass
from pathlib import Path
import tkinter as tk

import pyttsx3
import sounddevice as sd
from vosk import KaldiRecognizer, Model


WAKE_WORD = "jarvis"
SAMPLE_RATE = 16000


@dataclass
class AssistantConfig:
    model_path: Path = Path("models/vosk-model-small-en-us-0.15")


class JarvisAssistant:
    def __init__(self, config: AssistantConfig):
        self.config = config
        self.audio_queue: queue.Queue[bytes] = queue.Queue()
        self.stop_event = threading.Event()
        self.awaiting_command = False

        self.tts_engine = pyttsx3.init()
        self.tts_engine.setProperty("rate", 175)

        if not self.config.model_path.exists():
            raise FileNotFoundError(
                f"Vosk model not found at {self.config.model_path}. "
                "Download a free model from https://alphacephei.com/vosk/models and extract it there."
            )

        self.model = Model(str(self.config.model_path))
        self.recognizer = KaldiRecognizer(self.model, SAMPLE_RATE)

        self.root = tk.Tk()
        self.root.title("Jarvis Overlay")
        self.root.geometry("500x130+20+20")
        self.root.configure(bg="#0B132B")
        self.root.attributes("-topmost", True)

        self.status_var = tk.StringVar(value="Listening for wake word: 'jarvis'")
        self.input_var = tk.StringVar()
        self.last_heard_var = tk.StringVar(value="Heard: -")

        self._build_ui()

    def _build_ui(self) -> None:
        title = tk.Label(
            self.root,
            text="JARVIS",
            fg="#5BC0BE",
            bg="#0B132B",
            font=("Segoe UI", 16, "bold"),
        )
        title.pack(anchor="w", padx=12, pady=(8, 0))

        status = tk.Label(
            self.root,
            textvariable=self.status_var,
            fg="#E0FBFC",
            bg="#0B132B",
            font=("Segoe UI", 10),
        )
        status.pack(anchor="w", padx=12)

        heard = tk.Label(
            self.root,
            textvariable=self.last_heard_var,
            fg="#98C1D9",
            bg="#0B132B",
            font=("Segoe UI", 9),
        )
        heard.pack(anchor="w", padx=12, pady=(0, 8))

        entry_frame = tk.Frame(self.root, bg="#0B132B")
        entry_frame.pack(fill="x", padx=12, pady=(0, 12))

        entry = tk.Entry(entry_frame, textvariable=self.input_var, font=("Segoe UI", 10))
        entry.pack(side="left", fill="x", expand=True)
        entry.bind("<Return>", self._on_manual_command)

        send_btn = tk.Button(
            entry_frame,
            text="Run",
            command=self._on_manual_command,
            bg="#5BC0BE",
            fg="#0B132B",
            relief="flat",
            padx=12,
        )
        send_btn.pack(side="left", padx=(8, 0))

        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)

    def say(self, text: str) -> None:
        self.status_var.set(f"Jarvis: {text}")
        self.tts_engine.say(text)
        self.tts_engine.runAndWait()

    def _on_manual_command(self, _event=None) -> None:
        text = self.input_var.get().strip().lower()
        if not text:
            return
        self.input_var.set("")
        self.last_heard_var.set(f"Manual: {text}")
        threading.Thread(target=self.handle_command, args=(text,), daemon=True).start()

    def _audio_callback(self, indata, frames, time, status):
        if status:
            print(status)
        self.audio_queue.put(bytes(indata))

    def start_listening_thread(self) -> None:
        listener = threading.Thread(target=self._listen_loop, daemon=True)
        listener.start()

    def _listen_loop(self) -> None:
        with sd.RawInputStream(
            samplerate=SAMPLE_RATE,
            blocksize=8000,
            dtype="int16",
            channels=1,
            callback=self._audio_callback,
        ):
            while not self.stop_event.is_set():
                data = self.audio_queue.get()
                if self.recognizer.AcceptWaveform(data):
                    result = json.loads(self.recognizer.Result())
                    text = result.get("text", "").strip().lower()
                    if text:
                        self.root.after(0, self.last_heard_var.set, f"Heard: {text}")
                        self._route_speech(text)

    def _route_speech(self, text: str) -> None:
        if self.awaiting_command:
            self.awaiting_command = False
            threading.Thread(target=self.handle_command, args=(text,), daemon=True).start()
            return

        if WAKE_WORD in text:
            self.awaiting_command = True
            threading.Thread(target=self.say, args=("Yes?",), daemon=True).start()

    def handle_command(self, command: str) -> None:
        if command.startswith("open "):
            target = command.replace("open ", "", 1).strip()
            msg = self.open_application(target)
            self.say(msg)
            return

        if command.startswith("search "):
            query = command.replace("search ", "", 1).strip()
            self.search_in_chrome(query)
            self.say("Done.")
            return

        if command.startswith("run "):
            shell_cmd = command.replace("run ", "", 1).strip()
            msg = self.execute_terminal_command(shell_cmd)
            self.say(msg)
            return

        self.say("I can open apps, search, or run commands.")

    def open_application(self, app_name: str) -> str:
        app_name = app_name.lower()
        system = platform.system().lower()

        app_map = {
            "chrome": {
                "windows": ["start", "chrome"],
                "darwin": ["open", "-a", "Google Chrome"],
                "linux": ["google-chrome"],
            },
            "vscode": {
                "windows": ["code"],
                "darwin": ["open", "-a", "Visual Studio Code"],
                "linux": ["code"],
            },
            "terminal": {
                "windows": ["start", "cmd"],
                "darwin": ["open", "-a", "Terminal"],
                "linux": ["x-terminal-emulator"],
            },
            "notepad": {
                "windows": ["notepad"],
                "darwin": ["open", "-a", "TextEdit"],
                "linux": ["gedit"],
            },
        }

        if app_name not in app_map:
            return "App not mapped yet."

        cmd = app_map[app_name].get(system)
        if not cmd:
            return "This OS is not supported for that app."

        try:
            subprocess.Popen(cmd, shell=(system == "windows" and cmd[0] == "start"))
            return "Opening now."
        except Exception:
            return "Could not open it."

    def _chrome_candidates(self) -> list[Path]:
        home = Path.home()
        return [
            Path("/usr/bin/google-chrome"),
            Path("/usr/bin/chromium-browser"),
            Path("/usr/bin/chromium"),
            home / "AppData/Local/Google/Chrome/Application/chrome.exe",
            Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
            Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        ]

    def search_in_chrome(self, query: str) -> None:
        encoded = urllib.parse.quote_plus(query)
        url = f"https://www.google.com/search?q={encoded}"

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
            if result.returncode == 0:
                return "Command completed."
            return "Command failed."
        except Exception:
            return "Unable to run that command."

    def shutdown(self) -> None:
        self.stop_event.set()
        self.root.destroy()

    def run(self) -> None:
        self.start_listening_thread()
        self.root.mainloop()


if __name__ == "__main__":
    assistant = JarvisAssistant(AssistantConfig())
    assistant.run()
