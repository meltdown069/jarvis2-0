import argparse
import json
import os
import queue
import threading
import tkinter.simpledialog as simpledialog
from pathlib import Path
from typing import Any

import pyttsx3
import sounddevice as sd
from vosk import KaldiRecognizer, Model

from automation import AutomationController
from behavior import BehaviorEngine
from gui import JarvisGUI
from memory_store import MemoryStore

WAKE_WORD = "jarvis"
DEFAULT_SAMPLE_RATE = 16000


class JarvisAssistant:
    def __init__(
        self,
        model_path: Path | None = None,
        mic_device: int | None = None,
        mic_name: str | None = None,
        sample_rate: int | None = None,
        debug_asr: bool = False,
    ):
        self.model_path = model_path
        self.mic_device = mic_device
        self.mic_name = mic_name
        self.sample_rate = sample_rate
        self.debug_asr = debug_asr

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
        self.current_language = "english"
        self.tts_engine.setProperty("rate", 178)
        pref_lang = self.memory.get_pref("language") or "english"
        self.set_tts_language(pref_lang, announce=False)
        threading.Thread(target=self._tts_worker, daemon=True).start()

        self.gui = JarvisGUI(self._on_manual_command)
        self.gui.root.protocol("WM_DELETE_WINDOW", self.shutdown)
        self._ensure_one_time_gemini_prompt()

        self.voice_enabled = False
        self.model: Model | None = None
        self.recognizer: KaldiRecognizer | None = None
        self._initialize_voice_recognition()


    def _ensure_one_time_gemini_prompt(self):
        if self.memory.get_pref("gemini_prompted") == "yes":
            return

        prompt = (
            "Optional setup for heavy 3-step+ tasks:\n"
            "Enter your Gemini API key now (leave blank to skip).\n"
            "Basic commands will continue locally without API usage."
        )
        key = simpledialog.askstring("Jarvis Setup", prompt, parent=self.gui.root, show="*")
        if key and key.strip():
            self.memory.set_pref("gemini_api_key", key.strip())
            self.say("Gemini key saved. I will only use it for heavy multi-step tasks, sir.")
        else:
            self.say("No Gemini key saved. I will run tasks locally, sir.")
        self.memory.set_pref("gemini_prompted", "yes")

    def _resolve_input_device(self) -> int | None:
        if self.mic_name:
            devices = sd.query_devices()
            for idx, dev in enumerate(devices):
                if dev.get("max_input_channels", 0) > 0 and self.mic_name.lower() in str(dev.get("name", "")).lower():
                    return idx
        return self.mic_device

    def _resolve_sample_rate(self, device_index: int | None) -> int:
        if self.sample_rate:
            return int(self.sample_rate)
        if device_index is not None:
            try:
                dev: dict[str, Any] = sd.query_devices(device_index)
                default_sr = dev.get("default_samplerate")
                if default_sr:
                    return int(default_sr)
            except Exception:
                pass
        return DEFAULT_SAMPLE_RATE

    def trace_decision(self, user_said: str, tool: str, reason: str):
        print(f"user said: '{user_said}' so i will use {tool} to {reason}")

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

    def available_tts_languages(self) -> list[str]:
        voices = self.tts_engine.getProperty("voices") or []
        found = set()
        for v in voices:
            blob = f"{getattr(v, 'name', '')} {getattr(v, 'id', '')}".lower()
            for lang in ["english", "hindi", "spanish", "french", "german", "italian", "japanese", "korean", "chinese", "arabic", "russian", "portuguese"]:
                if lang in blob:
                    found.add(lang)
        if not found:
            found.add("english")
        return sorted(found)

    def set_tts_language(self, language: str, announce: bool = True) -> bool:
        target = language.strip().lower()
        aliases = {
            "en": "english", "eng": "english", "hindi": "hindi", "hi": "hindi",
            "es": "spanish", "sp": "spanish", "fr": "french", "de": "german",
            "it": "italian", "ja": "japanese", "jp": "japanese", "ko": "korean",
            "zh": "chinese", "cn": "chinese", "ar": "arabic", "ru": "russian", "pt": "portuguese",
        }
        target = aliases.get(target, target)
        voices = self.tts_engine.getProperty("voices") or []
        for v in voices:
            blob = f"{getattr(v, 'name', '')} {getattr(v, 'id', '')}".lower()
            if target in blob:
                self.tts_engine.setProperty("voice", v.id)
                self.current_language = target
                self.memory.set_pref("language", target)
                if announce:
                    self.say(f"Language switched to {target} sir")
                return True
        if announce:
            langs = ", ".join(self.available_tts_languages())
            self.say(f"I could not find {target}. Available: {langs}")
        return False

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
        self.mic_device = self._resolve_input_device()
        self.sample_rate = self._resolve_sample_rate(self.mic_device)

        for path in self._candidate_model_paths():
            if not (path.exists() and (path / "am").exists() and (path / "conf").exists()):
                continue
            try:
                self.model = Model(str(path))
                self.recognizer = KaldiRecognizer(self.model, self.sample_rate)
                self.recognizer.SetWords(True)
                self.voice_enabled = True
                self.gui.set_mode("Listening for wake word")
                self.gui.set_status(
                    f"Voice ON. Mic={self.mic_device if self.mic_device is not None else 'default'}, "
                    f"sample_rate={self.sample_rate}. Listening for wake word '{WAKE_WORD}'."
                )
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

    def _handle_recognized_text(self, text: str):
        if self.debug_asr:
            print(f"[asr-final] {text}")
        self.gui.root.after(0, self.gui.set_heard, f"Heard: {text}")
        self._route_speech(text)

    def _listen_loop(self):
        if not self.recognizer:
            return
        try:
            with sd.RawInputStream(
                samplerate=self.sample_rate,
                blocksize=4000,
                dtype="int16",
                channels=1,
                device=self.mic_device,
                callback=self._audio_callback,
            ):
                while not self.stop_event.is_set():
                    data = self.audio_queue.get()

                    # partial results improve wake-word responsiveness
                    if self.recognizer.AcceptWaveform(data):
                        result = json.loads(self.recognizer.Result())
                        text = result.get("text", "").strip().lower()
                        if text:
                            self._handle_recognized_text(text)
                    else:
                        partial = json.loads(self.recognizer.PartialResult()).get("partial", "").strip().lower()
                        if partial and self.debug_asr:
                            print(f"[asr-partial] {partial}")
                        if partial and WAKE_WORD in partial and not self.awaiting_command:
                            self.awaiting_command = True
                            self.say("Yes sir?")
        except Exception:
            self.voice_enabled = False
            self.gui.root.after(0, self.gui.set_mode, "Voice OFF - manual mode")
            self.gui.root.after(0, self.gui.set_status, "Voice OFF: microphone unavailable. Manual mode active.")

    def _route_speech(self, text: str):
        cleaned = self.behavior.cleanup(text)
        if self.awaiting_command:
            self.awaiting_command = False
            if cleaned and cleaned != WAKE_WORD:
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
    parser.add_argument("--mic-device", type=int, default=None, help="Microphone input device index from sounddevice query_devices()")
    parser.add_argument("--mic-name", type=str, default=None, help="Microphone name substring (case-insensitive), e.g. 'headset'")
    parser.add_argument("--sample-rate", type=int, default=None, help="Input sample rate for recognition (defaults to selected mic native rate)")
    parser.add_argument("--debug-asr", action="store_true", help="Print partial/final speech recognition results to terminal")
    parser.add_argument("--list-mics", action="store_true", help="List input microphone devices and exit")
    return parser.parse_args()


def list_mics() -> None:
    for idx, dev in enumerate(sd.query_devices()):
        if dev.get("max_input_channels", 0) > 0:
            print(f"[{idx}] {dev.get('name')} (inputs={dev.get('max_input_channels')}, default_sr={dev.get('default_samplerate')})")


if __name__ == "__main__":
    args = parse_args()
    if args.list_mics:
        list_mics()
        raise SystemExit(0)
    JarvisAssistant(
        model_path=args.model_path,
        mic_device=args.mic_device,
        mic_name=args.mic_name,
        sample_rate=args.sample_rate,
        debug_asr=args.debug_asr,
    ).run()
