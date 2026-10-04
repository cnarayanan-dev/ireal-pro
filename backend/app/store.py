"""Song storage: built-in songs plus user songs persisted to a JSON file."""

from __future__ import annotations

import json
import os
import re
import threading
import uuid
from pathlib import Path

from .songs import BUILTIN_SONGS

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "user_songs.json"


class SongStore:
    def __init__(self, path: Path | str | None = None):
        self.path = Path(path or os.environ.get("SONGS_FILE", DEFAULT_PATH))
        self._lock = threading.Lock()

    def _load_user(self) -> list[dict]:
        if not self.path.exists():
            return []
        return json.loads(self.path.read_text())

    def _save_user(self, songs: list[dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(songs, indent=2))
        tmp.replace(self.path)

    def all(self) -> list[dict]:
        builtin = [{**s, "builtin": True} for s in BUILTIN_SONGS]
        user = [{**s, "builtin": False} for s in self._load_user()]
        return builtin + user

    def get(self, song_id: str) -> dict | None:
        return next((s for s in self.all() if s["id"] == song_id), None)

    def create(self, data: dict) -> dict:
        with self._lock:
            songs = self._load_user()
            slug = re.sub(r"[^a-z0-9]+", "-", data["title"].lower()).strip("-") or "song"
            song = {**data, "id": f"{slug}-{uuid.uuid4().hex[:6]}"}
            songs.append(song)
            self._save_user(songs)
        return {**song, "builtin": False}

    def update(self, song_id: str, data: dict) -> dict | None:
        with self._lock:
            songs = self._load_user()
            for i, s in enumerate(songs):
                if s["id"] == song_id:
                    songs[i] = {**data, "id": song_id}
                    self._save_user(songs)
                    return {**songs[i], "builtin": False}
        return None

    def delete(self, song_id: str) -> bool:
        with self._lock:
            songs = self._load_user()
            kept = [s for s in songs if s["id"] != song_id]
            if len(kept) == len(songs):
                return False
            self._save_user(kept)
        return True
