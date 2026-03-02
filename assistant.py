import argparse
import json
import os
import queue
import threading
from pathlib import Path

import pyttsx3
import sounddevice as sd
from vosk import KaldiRecognizer, Model

from automation import AutomationController
from behavior import BehaviorEngine
from gui import JarvisGUI
from memory_store import MemoryStore

WAKE_WORD = "jarvis"
SAMPLE_RATE = 16000


class JarvisAssistant:
    def __init__(self, model_path: Path | None = None):
        self.model_path = model_path
        self.audio_queue: queue.Queue[bytes] = queue.Queue()
        self.tts_queue: queue.Queue[str] = queue.Queue()
        self.stop_event = threading.Event()

        self.awaiting_command = False
        self.awaiting_profile_choice = False
        self.pending_action: tuple[str, str] | None = None
        self.current_task = ""

        self.memory = MemoryStore("jarvis_memory.json")
        self.automation = AutomationController()
        self.behavior = BehaviorEngine(self)

        self.tts_engine = pyttsx3.init()
        self.tts_engine.setProperty("rate", 178)
        threading.Thread(target=self._tts_worker, daemon=True).start()

        self.gui = JarvisGUI(self._on_manual_command)
        self.gui.root.protocol("WM_DELETE_WINDOW", self.shutdown)

        self.voice_enabled = False
        self.model: Model | None = None
        self.recognizer: KaldiRecognizer | None = None
        self._initialize_voice_recognition()

    def start_task(self, description: str):
        self.current_task = description
        self.say(f"Starting task: {description}")

    def finish_task(self, message: str):
        self.current_task = ""
        self.say(message)

    def say(self, text: str):
        self.gui.set_status(f"Jarvis: {text}")
        self.gui.pulse_speaking(0.85)
        self.tts_queue.put(text)

    def _tts_worker(self):
        while not self.stop_event.is_set():
            try:
                text = self.tts_queue.get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                self.gui.root.after(0, self.gui.set_speaking, True)
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
            except Exception:
                continue
            finally:
                self.gui.root.after(0, self.gui.set_speaking, False)

    def _candidate_model_paths(self) -> list[Path]:
        candidates = []
        if self.model_path:
            candidates.append(self.model_path)
        env_value = os.environ.get("VOSK_MODEL_PATH")
        if env_value:
            candidates.append(Path(env_value))
        models_dir = Path("models")
        candidates += [
            models_dir / "vosk-model-small-en-us-0.15",
            models_dir / "vosk-model-en-us-0.22",
            models_dir / "vosk-model-small-en-in-0.4",
        ]
        return candidates

    def _initialize_voice_recognition(self):
        for path in self._candidate_model_paths():
            if not (path.exists() and (path / "am").exists() and (path / "conf").exists()):
                continue
            try:
                self.model = Model(str(path))
                self.recognizer = KaldiRecognizer(self.model, SAMPLE_RATE)
                self.voice_enabled = True
                self.gui.set_mode("Listening for wake word")
                self.gui.set_status(f"Voice ON. Listening for wake word '{WAKE_WORD}'.")
                return
            except Exception:
                continue

        self.voice_enabled = False
        self.gui.set_mode("Voice OFF - manual mode")
        self.gui.set_status("Voice OFF: model missing/invalid. Manual mode active.")

    def _on_manual_command(self, text: str):
        self.gui.set_heard(f"Manual: {text}")
        threading.Thread(target=self.behavior.handle_command, args=(text,), daemon=True).start()

    def _audio_callback(self, indata, _frames, _time_info, status):
        if status:
            print(status)
        self.audio_queue.put(bytes(indata))

    def _listen_loop(self):
        if not self.recognizer:
            return
        try:
            with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=8000, dtype="int16", channels=1, callback=self._audio_callback):
                while not self.stop_event.is_set():
                    data = self.audio_queue.get()
                    if self.recognizer.AcceptWaveform(data):
                        result = json.loads(self.recognizer.Result())
                        text = result.get("text", "").strip().lower()
                        if not text:
                            continue
                        self.gui.root.after(0, self.gui.set_heard, f"Heard: {text}")
                        self._route_speech(text)
        except Exception:
            self.voice_enabled = False
            self.gui.root.after(0, self.gui.set_mode, "Voice OFF - manual mode")
            self.gui.root.after(0, self.gui.set_status, "Voice OFF: microphone unavailable. Manual mode active.")

    def _route_speech(self, text: str):
        cleaned = self.behavior.cleanup(text)
        if self.awaiting_command:
            self.awaiting_command = False
            if cleaned:
                threading.Thread(target=self.behavior.handle_command, args=(cleaned,), daemon=True).start()
            return

        if WAKE_WORD in cleaned:
            stripped = cleaned.replace(WAKE_WORD, "").strip()
            if stripped:
                threading.Thread(target=self.behavior.handle_command, args=(stripped,), daemon=True).start()
            else:
                self.awaiting_command = True
                self.say("Yes sir?")

    def run(self):
        if self.voice_enabled:
            threading.Thread(target=self._listen_loop, daemon=True).start()
        self.gui.root.mainloop()

    def shutdown(self):
        self.stop_event.set()
        self.gui.root.destroy()


def parse_args():
    parser = argparse.ArgumentParser(description="Free local Jarvis assistant")
    parser.add_argument("--model-path", type=Path, default=None, help="Path to Vosk model folder (contains am/ and conf/)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    JarvisAssistant(model_path=args.model_path).run()
