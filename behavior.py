import re
import threading
from datetime import datetime


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
        alias = {"vs code": "vscode", "visual studio code": "vscode", "google chrome": "chrome", "command prompt": "terminal", "cmd": "terminal", "note pad": "notepad"}
        return alias.get(target, target)

    def looks_like_website(self, text: str) -> bool:
        if " " in text or not text:
            return False
        return bool(re.match(r"^(https?://)?[a-z0-9][a-z0-9\-]*(\.[a-z0-9\-]+)+([/?].*)?$", text))

    def resolve_profile(self, text: str):
        t = self.cleanup(text)
        choices = {"default": "Default", "profile 1": "Profile 1", "one": "Profile 1", "1": "Profile 1", "profile 2": "Profile 2", "two": "Profile 2", "2": "Profile 2"}
        for k, v in choices.items():
            if k in t:
                return v
        return None

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
            if action == "search":
                threading.Thread(target=self.app.automation.human_search, args=(payload, profile), daemon=True).start()
            else:
                threading.Thread(target=self.app.automation.human_open_website, args=(payload, profile), daemon=True).start()
            return

        if " and then " in cmd:
            steps = [x.strip() for x in cmd.split(" and then ") if x.strip()]
            self.app.say(f"Understood sir. I will execute {len(steps)} steps.")
            for i, step in enumerate(steps, 1):
                self.app.say(f"Step {i}: {step}")
                self.handle_command(step)
            return

        if cmd in {"time", "what is the time", "what s the time", "tell me the time"}:
            self.app.say(f"It is {datetime.now().strftime('%I:%M %p')} sir")
            return
        if cmd in {"who are you", "what are you", "who r you"}:
            self.app.say("I am Jarvis, your local assistant. I can open apps, search, type, run commands, and remember notes.")
            return

        mem = re.match(r"^remember\s+(.+)$", cmd)
        if mem:
            note = mem.group(1).strip()
            self.app.memory.remember(f"user_note: {note}")
            self.app.say("Got it sir. I will remember that.")
            return
        if cmd in {"memory", "show memory", "what do you remember"}:
            notes = self.app.memory.get_notes()
            self.app.say(f"I remember {len(notes)} notes. Latest: {notes[-1]['note']}" if notes else "I do not have notes yet, sir.")
            return

        m = re.match(r"^open\s+(.+?)\s+and\s+type\s+(.+)$", cmd)
        if m:
            app_name = self.normalize_target(m.group(1).strip())
            text_to_type = m.group(2).strip()
            self.app.start_task(f"open {app_name} and type")
            threading.Thread(target=self.app.automation.open_and_type, args=(app_name, text_to_type), daemon=True).start()
            self.app.finish_task("Done sir. Do you want me to continue with anything else?")
            return

        if cmd.startswith("open "):
            target = self.normalize_target(cmd.replace("open ", "", 1).strip())
            if self.looks_like_website(target):
                pref = self.app.memory.get_pref("chrome_profile")
                if pref:
                    self.app.start_task(f"open website in {pref}")
                    threading.Thread(target=self.app.automation.human_open_website, args=(target, pref), daemon=True).start()
                    self.app.finish_task("Website opened sir. Want me to type anything there?")
                else:
                    self.app.pending_action = ("website", target)
                    self.app.awaiting_profile_choice = True
                    self.app.say("I see multiple Chrome profiles possible. Which one should I open: profile 1, profile 2, or default?")
                return
            self.app.start_task(f"open {target}")
            msg = self.app.automation.open_application(target)
            self.app.say(msg)
            self.app.finish_task("Task completed sir.")
            return

        if cmd.startswith("search "):
            q = cmd.replace("search ", "", 1).strip()
            pref = self.app.memory.get_pref("chrome_profile")
            if pref:
                self.app.start_task(f"search {q}")
                threading.Thread(target=self.app.automation.human_search, args=(q, pref), daemon=True).start()
                self.app.finish_task("Search done sir. Should I open any result?")
            else:
                self.app.pending_action = ("search", q)
                self.app.awaiting_profile_choice = True
                self.app.say("Which Chrome profile should I use: profile 1, profile 2, or default?")
            return

        if cmd.startswith("run "):
            c = cmd.replace("run ", "", 1).strip()
            self.app.start_task(f"run {c}")
            result = self.app.automation.run_command(c)
            self.app.say(result)
            self.app.finish_task("Command done sir." if result == "Command completed." else "I hit an obstacle. Tell me an alternative command or say cancel.")
            return

        normalized = self.normalize_target(cmd)
        if normalized and len(normalized.split()) <= 3:
            self.app.start_task(f"open {normalized}")
            self.app.say(self.app.automation.open_application(normalized))
            self.app.finish_task("Task completed sir.")
            return

        self.app.say("Sorry sir, I did not get that. Could you rephrase?")
