"""Render a mid-game frame headlessly and save it to docs/screenshot.png.

Run from the project root:  python scripts/screenshot.py
"""

from __future__ import annotations

import os
import random
import sys
import tempfile
from pathlib import Path

# Must be set before pygame initialises its video subsystem.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pygame  # noqa: E402

from snake.app import Screen, SnakeApp  # noqa: E402
from snake.config import DIFFICULTIES, GRID_HEIGHT, GRID_WIDTH, WINDOW_HEIGHT, WINDOW_WIDTH  # noqa: E402
from snake.highscore import HighScoreStore  # noqa: E402
from snake.logic import Direction, Game, Point  # noqa: E402


def winding_body() -> list[Point]:
    """A hand-drawn path, tail first, so the snake shows a few bends."""
    moves = [(1, 0)] * 7 + [(0, -1)] * 5 + [(1, 0)] * 6 + [(0, 1)] * 2 + [(1, 0)] * 3
    x, y = 3, 13
    path = [Point(x, y)]
    for dx, dy in moves:
        x, y = x + dx, y + dy
        path.append(Point(x, y))
    return path[::-1]


def main(out: Path = ROOT / "docs" / "screenshot.png") -> None:
    pygame.init()
    surface = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    with tempfile.TemporaryDirectory() as tmp:
        store = HighScoreStore(Path(tmp) / "scores.json")
        store.submit("normal-walls", 340)
        app = SnakeApp(surface, store, difficulty=DIFFICULTIES[1], rng=random.Random(7))
        game = Game(
            GRID_WIDTH,
            GRID_HEIGHT,
            app.difficulty,
            rng=random.Random(7),
            body=winding_body(),
            direction=Direction.RIGHT,
        )
        game.food = Point(19, 4)
        game.foods_eaten = 21
        game.score = 21 * 10 * app.difficulty.score_multiplier
        app.game = game
        app.screen = Screen.PLAYING
        app.draw()
        out.parent.mkdir(parents=True, exist_ok=True)
        pygame.image.save(surface, str(out))
    pygame.quit()
    print(f"Saved {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
