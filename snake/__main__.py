"""Command-line entry point: ``python -m snake``."""

from __future__ import annotations

import argparse
import os

from .config import DEFAULT_DIFFICULTY, DIFFICULTIES, difficulty_by_name
from .highscore import ENV_VAR


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="snake", description="Play Snake.")
    parser.add_argument(
        "--difficulty",
        choices=[d.name.lower() for d in DIFFICULTIES],
        default=DEFAULT_DIFFICULTY.name.lower(),
        help="starting difficulty (can also be changed on the title screen)",
    )
    parser.add_argument(
        "--wrap",
        action="store_true",
        help="start in wrap-around mode, where the snake passes through the edges",
    )
    parser.add_argument(
        "--highscore-file",
        help=f"where to store high scores (default: ${ENV_VAR} or ~/.snake_highscores.json)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if args.highscore_file:
        os.environ[ENV_VAR] = args.highscore_file
    # Imported late so --help works without initialising pygame.
    from .app import main as run_app

    run_app(difficulty=difficulty_by_name(args.difficulty), wrap=args.wrap)


if __name__ == "__main__":
    main()
