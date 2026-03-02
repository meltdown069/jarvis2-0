import json
from datetime import datetime
from pathlib import Path
from typing import Any


class MemoryStore:
    def __init__(self, path: Path | str = "jarvis_memory.json"):
        self.path = Path(path)
        self.data: dict[str, Any] = self._load()

    def _load(self) -> dict[str, Any]:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text())
            except Exception:
                pass
        return {"notes": [], "prefs": {}}

    def save(self) -> None:
        try:
            self.path.write_text(json.dumps(self.data, indent=2))
        except Exception:
            pass

    def remember(self, note: str) -> None:
        notes = self.data.setdefault("notes", [])
        notes.append({"ts": datetime.now().isoformat(timespec="seconds"), "note": note})
        self.data["notes"] = notes[-100:]
        self.save()

    def get_notes(self) -> list[dict[str, str]]:
        return self.data.get("notes", [])

    def set_pref(self, key: str, value: str) -> None:
        prefs = self.data.setdefault("prefs", {})
        prefs[key] = value
        self.save()

    def get_pref(self, key: str) -> str | None:
        return self.data.get("prefs", {}).get(key)
