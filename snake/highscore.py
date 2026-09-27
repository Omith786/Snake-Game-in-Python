"""Persistent high scores stored as a small JSON file."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

log = logging.getLogger(__name__)

ENV_VAR = "SNAKE_HIGHSCORE_FILE"
DEFAULT_FILENAME = ".snake_highscores.json"


def default_path() -> Path:
    """Return the high score file location.

    ``$SNAKE_HIGHSCORE_FILE`` wins if set; otherwise the file lives in the
    user's home directory so scores survive re-cloning the repository.
    """
    override = os.environ.get(ENV_VAR)
    return Path(override).expanduser() if override else Path.home() / DEFAULT_FILENAME


def score_key(difficulty_name: str, wrap: bool) -> str:
    """Build the key under which a mode's best score is recorded.

    Wrap-around mode is much more forgiving, so it gets its own table rather
    than competing with solid-wall scores.
    """
    return f"{difficulty_name.lower()}-{'wrap' if wrap else 'walls'}"


class HighScoreStore:
    """Best score per game mode, loaded eagerly and saved on every new record.

    A missing, unreadable or malformed file is treated as "no scores yet" so a
    corrupt file can never stop the game from starting.
    """

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_path()
        self._scores: dict[str, int] = self._load()

    def get(self, key: str) -> int:
        return self._scores.get(key, 0)

    def submit(self, key: str, score: int) -> bool:
        """Record ``score`` if it beats the stored best. Returns True on a new record."""
        if score <= self.get(key):
            return False
        self._scores[key] = score
        self._save()
        return True

    def as_dict(self) -> dict[str, int]:
        return dict(self._scores)

    def _load(self) -> dict[str, int]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        except (OSError, ValueError) as exc:
            log.warning("Ignoring unreadable high score file %s: %s", self.path, exc)
            return {}
        if not isinstance(data, dict):
            return {}
        return {
            str(k): v
            for k, v in data.items()
            if isinstance(v, int) and not isinstance(v, bool) and v >= 0
        }

    def _save(self) -> None:
        # Write to a sibling temp file and rename, so a crash mid-write can't
        # leave a truncated JSON file behind.
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(json.dumps(self._scores, indent=2, sort_keys=True), encoding="utf-8")
            os.replace(tmp, self.path)
        except OSError as exc:
            log.warning("Could not save high scores to %s: %s", self.path, exc)
