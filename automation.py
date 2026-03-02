import platform
import shlex
import subprocess
import time
import urllib.parse
import webbrowser
from pathlib import Path

try:
    import pyautogui
except Exception:
    pyautogui = None


class AutomationController:
    def __init__(self):
        self.system = platform.system().lower()

    def open_application(self, app_name: str) -> str:
        app_name = app_name.lower().strip()
        app_map = {
            "chrome": {"windows": ["cmd", "/c", "start", "", "chrome"], "darwin": ["open", "-a", "Google Chrome"], "linux": ["google-chrome"]},
            "discord": {"windows": ["cmd", "/c", "start", "", "discord"], "darwin": ["open", "-a", "Discord"], "linux": ["discord"]},
            "spotify": {"windows": ["cmd", "/c", "start", "", "spotify"], "darwin": ["open", "-a", "Spotify"], "linux": ["spotify"]},
            "vscode": {"windows": ["cmd", "/c", "start", "", "code"], "darwin": ["open", "-a", "Visual Studio Code"], "linux": ["code"]},
            "terminal": {"windows": ["cmd", "/c", "start", "", "cmd"], "darwin": ["open", "-a", "Terminal"], "linux": ["x-terminal-emulator"]},
            "notepad": {"windows": ["notepad"], "darwin": ["open", "-a", "TextEdit"], "linux": ["gedit"]},
            "whatsapp": {"windows": ["cmd", "/c", "start", "", "whatsapp"], "darwin": ["open", "-a", "WhatsApp"], "linux": ["whatsapp-for-linux"]},
        }
        try:
            if app_name in app_map:
                cmd = app_map[app_name].get(self.system)
                if not cmd:
                    return f"{app_name} is not mapped for this OS yet."
                subprocess.Popen(cmd)
                return f"Opening {app_name} sir"
            if self.system == "windows":
                subprocess.Popen(["cmd", "/c", "start", "", app_name])
            elif self.system == "darwin":
                subprocess.Popen(["open", "-a", app_name])
            else:
                subprocess.Popen([app_name])
            return f"Trying to open {app_name} sir"
        except Exception:
            return f"I could not find {app_name}. Tell me another app name and I will continue."

    def send_whatsapp_message(self, contact_name: str, message: str) -> bool:
        contact_name = contact_name.strip()
        message = message.strip()
        if pyautogui and self.system in {"windows", "darwin", "linux"}:
            try:
                self.open_application("whatsapp")
                time.sleep(2.0)
                # Search contact
                if self.system == "darwin":
                    pyautogui.hotkey("command", "f")
                else:
                    pyautogui.hotkey("ctrl", "f")
                time.sleep(0.25)
                pyautogui.typewrite(contact_name, interval=0.06)
                time.sleep(0.5)
                pyautogui.press("enter")
                time.sleep(0.6)
                pyautogui.typewrite(message, interval=0.06)
                pyautogui.press("enter")
                return True
            except Exception:
                pass

        # fallback: open WhatsApp Web with prefilled message (needs phone, so best effort)
        try:
            encoded = urllib.parse.quote_plus(message)
            webbrowser.open_new_tab(f"https://web.whatsapp.com/")
        except Exception:
            return False
        return False

    def _open_chrome(self, profile: str | None = None):
        if self.system == "windows":
            cmd = ["cmd", "/c", "start", "", "chrome"]
            if profile:
                cmd.append(f"--profile-directory={profile}")
            subprocess.Popen(cmd)
        elif self.system == "darwin":
            subprocess.Popen(["open", "-a", "Google Chrome"])
        else:
            subprocess.Popen(["google-chrome"])

    def human_search(self, query: str, profile: str | None = None):
        if pyautogui:
            try:
                self._open_chrome(profile)
                time.sleep(1.2)
                pyautogui.hotkey("command", "l") if self.system == "darwin" else pyautogui.hotkey("ctrl", "l")
                pyautogui.typewrite(query, interval=0.08)
                pyautogui.press("enter")
                return
            except Exception:
                pass
        self.search_in_chrome(query)

    def human_open_website(self, website: str, profile: str | None = None):
        if pyautogui:
            try:
                self._open_chrome(profile)
                time.sleep(1.2)
                pyautogui.hotkey("command", "l") if self.system == "darwin" else pyautogui.hotkey("ctrl", "l")
                pyautogui.typewrite(website, interval=0.08)
                pyautogui.press("enter")
                return
            except Exception:
                pass
        webbrowser.open_new_tab(website if website.startswith(("http://", "https://")) else f"https://{website}")

    def open_and_type(self, app_name: str, text_to_type: str):
        if pyautogui and self.system == "windows":
            pyautogui.hotkey("win", "r")
            time.sleep(0.3)
            pyautogui.typewrite("cmd" if app_name in {"terminal", "cmd"} else app_name, interval=0.06)
            pyautogui.press("enter")
            time.sleep(1.2)
            pyautogui.typewrite(text_to_type, interval=0.06)
            if app_name in {"terminal", "cmd"}:
                pyautogui.press("enter")
            return
        self.open_application(app_name)

    def search_in_chrome(self, query: str):
        url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"
        for path in self.chrome_candidates():
            if path.exists():
                webbrowser.register("jarvis_chrome", None, webbrowser.BackgroundBrowser(str(path)))
                webbrowser.get("jarvis_chrome").open_new_tab(url)
                return
        webbrowser.open_new_tab(url)

    def chrome_candidates(self) -> list[Path]:
        home = Path.home()
        return [
            Path("/usr/bin/google-chrome"), Path("/usr/bin/chromium-browser"), Path("/usr/bin/chromium"),
            home / "AppData/Local/Google/Chrome/Application/chrome.exe",
            Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
            Path("C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"),
            Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        ]

    def run_command(self, cmd: str) -> str:
        try:
            result = subprocess.run(shlex.split(cmd), capture_output=True, text=True, timeout=20)
            return "Command completed." if result.returncode == 0 else "Command failed."
        except Exception:
            return "Unable to run that command."
