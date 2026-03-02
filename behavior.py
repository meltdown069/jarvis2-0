import json
import re
import threading
from datetime import datetime
from urllib import error, request


class BehaviorEngine:
    def __init__(self, app):
        self.app = app

    def cleanup(self, text: str) -> str:
        cleaned = re.sub(r"[^a-z0-9:/?&.=+_\- ]", " ", text.lower())
        cleaned = re.sub(r"\b(hey|hi|hello|please|jarvis|buddy|sir|can you|could you|would you)\b", " ", cleaned)
        return re.sub(r"\s+", " ", cleaned).strip()

    def normalize_target(self, target: str) -> str:
        target = target.strip().lower()
        target = re.sub(r"^(this|the)\s+", "", target)
        target = re.sub(r"^(app|application)\s+", "", target)
        target = re.sub(r"^(app|application)\s+(called|named)\s+", "", target)
        target = re.sub(r"^(called|named)\s+", "", target).strip()
        alias = {
            "vs code": "vscode",
            "visual studio code": "vscode",
            "google chrome": "chrome",
            "command prompt": "terminal",
            "cmd": "terminal",
            "note pad": "notepad",
        }
        return alias.get(target, target)

    def looks_like_website(self, text: str) -> bool:
        if " " in text or not text:
            return False
        return bool(re.match(r"^(https?://)?[a-z0-9][a-z0-9\-]*(\.[a-z0-9\-]+)+([/?].*)?$", text))

    def resolve_profile(self, text: str):
        t = self.cleanup(text)
        choices = {
            "default": "Default",
            "profile 1": "Profile 1",
            "one": "Profile 1",
            "1": "Profile 1",
            "profile 2": "Profile 2",
            "two": "Profile 2",
            "2": "Profile 2",
        }
        for k, v in choices.items():
            if k in t:
                return v
        return None

    def _trace(self, user_said: str, tool: str, reason: str):
        self.app.trace_decision(user_said, tool, reason)

    def _maybe_refine_complex_steps(self, raw_steps: list[str], original_command: str) -> list[str]:
        if len(raw_steps) < 3:
            return raw_steps

        api_key = self.app.memory.get_pref("gemini_api_key")
        if not api_key:
            self.app.say("This looks like a heavy multi-step task. Add a Gemini API key in memory to improve planning quality.")
            return raw_steps

        self._trace(original_command, "gemini_planner", f"optimize {len(raw_steps)} step plan")
        prompt = (
            "You are planning desktop assistant actions. Return JSON only in the format "
            "{\"steps\":[\"step one\",\"step two\"]}. Keep max 6 short action steps. "
            f"User request: {original_command}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2},
        }
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"

        try:
            req = request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with request.urlopen(req, timeout=20) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            text = body["candidates"][0]["content"]["parts"][0]["text"].strip()
            # tolerate markdown fenced json
            text = text.replace("```json", "").replace("```", "").strip()
            data = json.loads(text)
            steps = [self.cleanup(x) for x in data.get("steps", []) if isinstance(x, str) and self.cleanup(x)]
            if steps:
                self.app.say("Heavy task planner is ready sir. Executing optimized steps.")
                return steps[:6]
        except (error.URLError, TimeoutError, KeyError, ValueError, json.JSONDecodeError):
            self.app.say("Planner failed, sir. I will continue with local step-by-step execution.")
        return raw_steps

    def handle_command(self, command: str):
        cmd = self.cleanup(command)
        if not cmd:
            return

        if self.app.awaiting_profile_choice and self.app.pending_action:
            profile = self.resolve_profile(cmd)
            if not profile:
                self.app.say("Please tell me profile 1, profile 2, or default.")
                return
            action, payload = self.app.pending_action
            self.app.pending_action = None
            self.app.awaiting_profile_choice = False
            self.app.memory.set_pref("chrome_profile", profile)
            self.app.start_task(f"continue {action} with {profile}")
            self._trace(command, "profile_followup", f"continue {action} with {profile}")
            if action == "search":
                threading.Thread(target=self.app.automation.human_search, args=(payload, profile), daemon=True).start()
            else:
                threading.Thread(target=self.app.automation.human_open_website, args=(payload, profile), daemon=True).start()
            return

        if " and then " in cmd:
            steps = [x.strip() for x in cmd.split(" and then ") if x.strip()]
            steps = self._maybe_refine_complex_steps(steps, command)
            self._trace(command, "task_chain", f"execute {len(steps)} chained steps")
            self.app.say(f"Understood sir. I will execute {len(steps)} steps.")
            for i, step in enumerate(steps, 1):
                self.app.say(f"Step {i}: {step}")
                self.handle_command(step)
            return

        if cmd in {"time", "what is the time", "what s the time", "tell me the time"}:
            self._trace(command, "time_intent", "reply with current time")
            self.app.say(f"It is {datetime.now().strftime('%I:%M %p')} sir")
            return

        if cmd in {"who are you", "what are you", "who r you"}:
            self._trace(command, "identity_intent", "introduce assistant capabilities")
            self.app.say("I am Jarvis. I can open apps, search, type, run commands, and remember notes for you.")
            return

        lang_match = re.match(r"^(set|change|switch)\s+(language\s+to\s+)?([a-z]+)$", cmd)
        if lang_match:
            lang = lang_match.group(3)
            self._trace(command, "language_switch", f"switch TTS language to {lang}")
            self.app.set_tts_language(lang)
            return
        if cmd.startswith("speak in "):
            lang = cmd.replace("speak in ", "", 1).strip()
            self._trace(command, "language_switch", f"switch TTS language to {lang}")
            self.app.set_tts_language(lang)
            return
        if cmd in {"what languages do you speak", "which languages do you speak", "languages", "list languages"}:
            self._trace(command, "language_list", "list installed TTS languages")
            langs = ", ".join(self.app.available_tts_languages())
            self.app.say(f"I can speak in: {langs}")
            return

        blocked_security_terms = [
            "hack", "hacking", "exploit", "payload", "sql injection", "ddos", "phishing",
            "hydra", "sqlmap", "zphisher", "metasploit", "meterpreter", "bruteforce", "brute force",
        ]
        if any(k in cmd for k in blocked_security_terms):
            self._trace(command, "security_guard", "block offensive or unauthorized cybersecurity actions")
            self.app.say("I can only help with defensive, authorized security work. I cannot run or automate attack tools.")
            self.app.say("If you want, I can help with safe tasks like system hardening checks, patch audit steps, log review, and legal lab setup guidance.")
            return

        # whatsapp task: open whatsapp and search <name> contact and if you find her send her a hi
        whatsapp_match = re.match(r"^open\s+whatsapp\s+and\s+search\s+(.+?)\s+contact\s+and\s+if\s+you\s+find\s+.+?\s+send\s+.+?\s+(?:a\s+)?(.+)$", cmd)
        if whatsapp_match:
            contact = whatsapp_match.group(1).strip()
            msg = whatsapp_match.group(2).strip()
            self._trace(command, "whatsapp_send_message", f"open whatsapp, find {contact}, send '{msg}'")
            self.app.start_task(f"send whatsapp message to {contact}")
            ok = self.app.automation.send_whatsapp_message(contact, msg)
            if ok:
                self.app.finish_task(f"Message sent to {contact}, sir.")
            else:
                self.app.finish_task(f"I could not complete message send automatically. Please check WhatsApp window for {contact}.")
            return

        mem = re.match(r"^remember\s+(.+)$", cmd)
        if mem:
            note = mem.group(1).strip()
            self._trace(command, "memory_write", f"store note '{note}'")
            self.app.memory.remember(f"user_note: {note}")
            self.app.say("Got it sir. I will remember that.")
            return
        if cmd in {"memory", "show memory", "what do you remember"}:
            self._trace(command, "memory_read", "read latest saved notes")
            notes = self.app.memory.get_notes()
            self.app.say(f"I remember {len(notes)} notes. Latest: {notes[-1]['note']}" if notes else "I do not have notes yet, sir.")
            return

        m = re.match(r"^open\s+(.+?)\s+and\s+type\s+(.+)$", cmd)
        if m:
            app_name = self.normalize_target(m.group(1).strip())
            text_to_type = m.group(2).strip()
            self._trace(command, "open_and_type", f"open {app_name} then type '{text_to_type}'")
            self.app.start_task(f"open {app_name} and type")
            threading.Thread(target=self.app.automation.open_and_type, args=(app_name, text_to_type), daemon=True).start()
            self.app.finish_task("Done sir. Do you want me to continue with anything else?")
            return

        if cmd.startswith("open "):
            target = self.normalize_target(cmd.replace("open ", "", 1).strip())
            if self.looks_like_website(target):
                pref = self.app.memory.get_pref("chrome_profile")
                if pref:
                    self._trace(command, "human_open_website", f"open {target} in chrome profile {pref}")
                    self.app.start_task(f"open website in {pref}")
                    threading.Thread(target=self.app.automation.human_open_website, args=(target, pref), daemon=True).start()
                    self.app.finish_task("Website opened sir. Want me to type anything there?")
                else:
                    self._trace(command, "profile_request", "ask for chrome profile before website task")
                    self.app.pending_action = ("website", target)
                    self.app.awaiting_profile_choice = True
                    self.app.say("I see multiple Chrome profiles possible. Which one should I open: profile 1, profile 2, or default?")
                return
            self._trace(command, "open_application", f"open app {target}")
            self.app.start_task(f"open {target}")
            msg = self.app.automation.open_application(target)
            self.app.say(msg)
            self.app.finish_task("Task completed sir.")
            return

        if cmd.startswith("search "):
            q = cmd.replace("search ", "", 1).strip()
            pref = self.app.memory.get_pref("chrome_profile")
            if pref:
                self._trace(command, "human_search", f"search '{q}' with profile {pref}")
                self.app.start_task(f"search {q}")
                threading.Thread(target=self.app.automation.human_search, args=(q, pref), daemon=True).start()
                self.app.finish_task("Search done sir. Should I open any result?")
            else:
                self._trace(command, "profile_request", "ask for chrome profile before search")
                self.app.pending_action = ("search", q)
                self.app.awaiting_profile_choice = True
                self.app.say("Which Chrome profile should I use: profile 1, profile 2, or default?")
            return

        if cmd.startswith("run "):
            c = cmd.replace("run ", "", 1).strip()
            self._trace(command, "run_command", f"execute shell command '{c}'")
            self.app.start_task(f"run {c}")
            result = self.app.automation.run_command(c)
            self.app.say(result)
            self.app.finish_task("Command done sir." if result == "Command completed." else "I hit an obstacle. Tell me an alternative command or say cancel.")
            return

        normalized = self.normalize_target(cmd)
        if normalized and len(normalized.split()) <= 3:
            self._trace(command, "open_application", f"open app {normalized}")
            self.app.start_task(f"open {normalized}")
            self.app.say(self.app.automation.open_application(normalized))
            self.app.finish_task("Task completed sir.")
            return

        self._trace(command, "fallback", "ask user to rephrase unknown intent")
        self.app.say("Sorry sir, I did not get that. Could you rephrase?")
