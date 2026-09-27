"""Headless tests for screen flow, timing and rendering."""

import random

import pygame
import pytest

from snake.app import MAX_FRAME_SECONDS, Screen, SnakeApp
from snake.config import DIFFICULTIES, WINDOW_HEIGHT, WINDOW_WIDTH
from snake.highscore import HighScoreStore
from snake.logic import Direction, Point


@pytest.fixture
def app(tmp_path):
    pygame.init()
    surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
    store = HighScoreStore(tmp_path / "scores.json")
    yield SnakeApp(surface, store, rng=random.Random(1))
    pygame.quit()


def test_title_screen_options(app):
    assert app.screen is Screen.TITLE
    app.handle_key(pygame.K_RIGHT)
    assert app.difficulty is DIFFICULTIES[2]
    app.handle_key(pygame.K_RIGHT)
    assert app.difficulty is DIFFICULTIES[0]  # cycles round
    app.handle_key(pygame.K_m)
    assert app.wrap and app.game.wrap
    assert app.key == "easy-wrap"


def test_start_pause_resume(app):
    app.handle_key(pygame.K_RETURN)
    assert app.screen is Screen.PLAYING
    app.handle_key(pygame.K_p)
    assert app.screen is Screen.PAUSED
    head = app.game.head
    app.update(1.0)
    assert app.game.head == head  # paused games do not advance
    app.handle_key(pygame.K_p)
    assert app.screen is Screen.PLAYING


def test_update_steps_at_game_speed(app):
    app.start()
    app.game.food = Point(0, 0)
    start_x = app.game.head.x
    interval = 1.0 / app.game.speed
    app.update(interval * 2.5)
    assert app.game.head.x == start_x + 2


def test_long_frames_are_clamped(app):
    app.start()
    app.game.food = Point(0, 0)
    start_x = app.game.head.x
    app.update(10.0)
    expected = int(MAX_FRAME_SECONDS * app.game.speed)
    assert app.game.head.x == start_x + expected


def test_arrow_keys_queue_turns(app):
    app.start()
    app.handle_key(pygame.K_UP)
    app.handle_key(pygame.K_a)
    assert app.game.pending_turns == (Direction.UP, Direction.LEFT)


def test_death_records_high_score_and_restart(app):
    app.start()
    app.game.score = 40
    app.game.food = Point(0, 0)
    app.game.queue_turn(Direction.UP)
    app.update(5.0)
    for _ in range(50):
        if app.screen is Screen.GAME_OVER:
            break
        app.update(MAX_FRAME_SECONDS)
    assert app.screen is Screen.GAME_OVER
    assert app.new_record
    assert app.best == 40

    app.handle_key(pygame.K_SPACE)
    assert app.screen is Screen.PLAYING
    assert app.game.score == 0 and app.game.alive


@pytest.mark.parametrize("screen", list(Screen))
def test_every_screen_renders(app, screen):
    app.screen = screen
    app.draw()
    # The board should not be a flat colour once something is drawn on it.
    colours = {app.surface.get_at((x, 300))[:3] for x in range(0, WINDOW_WIDTH, 7)}
    assert len(colours) > 1
