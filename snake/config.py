"""Tunable constants: board size, window layout and difficulty presets."""

from __future__ import annotations

from dataclasses import dataclass

GRID_WIDTH = 24
GRID_HEIGHT = 18
CELL_SIZE = 28
HUD_HEIGHT = 56

WINDOW_WIDTH = GRID_WIDTH * CELL_SIZE
WINDOW_HEIGHT = GRID_HEIGHT * CELL_SIZE + HUD_HEIGHT

FPS = 60
POINTS_PER_FOOD = 10


@dataclass(frozen=True)
class Difficulty:
    """A speed curve and scoring multiplier.

    Speeds are in snake moves per second. Each piece of food adds
    ``speed_step`` to the current speed until ``max_speed`` is reached.
    """

    name: str
    start_speed: float
    speed_step: float
    max_speed: float
    score_multiplier: int


DIFFICULTIES: tuple[Difficulty, ...] = (
    Difficulty("Easy", start_speed=6.0, speed_step=0.25, max_speed=12.0, score_multiplier=1),
    Difficulty("Normal", start_speed=8.0, speed_step=0.4, max_speed=16.0, score_multiplier=2),
    Difficulty("Hard", start_speed=11.0, speed_step=0.6, max_speed=22.0, score_multiplier=3),
)

DEFAULT_DIFFICULTY = DIFFICULTIES[1]


def difficulty_by_name(name: str) -> Difficulty:
    """Look up a difficulty preset case-insensitively."""
    for difficulty in DIFFICULTIES:
        if difficulty.name.lower() == name.lower():
            return difficulty
    choices = ", ".join(d.name for d in DIFFICULTIES)
    raise ValueError(f"Unknown difficulty {name!r} (choose from {choices})")
