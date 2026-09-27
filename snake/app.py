"""The pygame application: window, input handling, timing and screen flow."""

from __future__ import annotations

import random
from enum import Enum, auto

import pygame

from .config import (
    DIFFICULTIES,
    FPS,
    GRID_HEIGHT,
    GRID_WIDTH,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    Difficulty,
)
from .highscore import HighScoreStore, score_key
from .logic import Direction, Game, StepResult
from .render import HudInfo, Renderer

KEY_DIRECTIONS: dict[int, Direction] = {
    pygame.K_UP: Direction.UP,
    pygame.K_w: Direction.UP,
    pygame.K_DOWN: Direction.DOWN,
    pygame.K_s: Direction.DOWN,
    pygame.K_LEFT: Direction.LEFT,
    pygame.K_a: Direction.LEFT,
    pygame.K_RIGHT: Direction.RIGHT,
    pygame.K_d: Direction.RIGHT,
}
CONFIRM_KEYS = {pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE}

# If the window stalls (dragged, laptop asleep) we'd otherwise try to replay
# every missed step at once and the snake would teleport into a wall.
MAX_FRAME_SECONDS = 0.25


class Screen(Enum):
    TITLE = auto()
    PLAYING = auto()
    PAUSED = auto()
    GAME_OVER = auto()


class SnakeApp:
    """Owns the game loop and the transitions between title, play, pause and game over.

    Input handling and timing are exposed as :meth:`handle_key` and
    :meth:`update` so they can be exercised without a real window.
    """

    def __init__(
        self,
        surface: pygame.Surface,
        store: HighScoreStore,
        difficulty: Difficulty = DIFFICULTIES[1],
        wrap: bool = False,
        rng: random.Random | None = None,
    ) -> None:
        self.surface = surface
        self.renderer = Renderer(surface)
        self.store = store
        self.difficulty = difficulty
        self.wrap = wrap
        self._rng = rng or random.Random()
        self.screen = Screen.TITLE
        self.running = True
        self.new_record = False
        self._accumulator = 0.0
        self.game = self._new_game()

    # -- state helpers ---------------------------------------------------

    @property
    def key(self) -> str:
        return score_key(self.difficulty.name, self.wrap)

    @property
    def best(self) -> int:
        return self.store.get(self.key)

    def _new_game(self) -> Game:
        return Game(GRID_WIDTH, GRID_HEIGHT, self.difficulty, wrap=self.wrap, rng=self._rng)

    def start(self) -> None:
        """Begin a fresh round with the current settings."""
        self.game = self._new_game()
        self.new_record = False
        self._accumulator = 0.0
        self.screen = Screen.PLAYING

    def _cycle_difficulty(self, delta: int) -> None:
        i = DIFFICULTIES.index(self.difficulty)
        self.difficulty = DIFFICULTIES[(i + delta) % len(DIFFICULTIES)]
        self.game = self._new_game()

    def _finish(self) -> None:
        self.new_record = self.store.submit(self.key, self.game.score)
        self.screen = Screen.GAME_OVER

    # -- input and timing ------------------------------------------------

    def handle_key(self, key: int) -> None:
        """React to a single key press according to the current screen."""
        if self.screen is Screen.TITLE:
            if key in CONFIRM_KEYS:
                self.start()
            elif key in (pygame.K_LEFT, pygame.K_a):
                self._cycle_difficulty(-1)
            elif key in (pygame.K_RIGHT, pygame.K_d):
                self._cycle_difficulty(1)
            elif key == pygame.K_m:
                self.wrap = not self.wrap
                self.game = self._new_game()
            elif key == pygame.K_ESCAPE:
                self.running = False

        elif self.screen is Screen.PLAYING:
            if key in KEY_DIRECTIONS:
                self.game.queue_turn(KEY_DIRECTIONS[key])
            elif key in (pygame.K_p, pygame.K_ESCAPE):
                self.screen = Screen.PAUSED

        elif self.screen is Screen.PAUSED:
            if key in (pygame.K_p, pygame.K_SPACE):
                self.screen = Screen.PLAYING
            elif key == pygame.K_ESCAPE:
                self.game = self._new_game()
                self.screen = Screen.TITLE

        elif self.screen is Screen.GAME_OVER:
            if key in CONFIRM_KEYS:
                self.start()
            elif key == pygame.K_ESCAPE:
                self.game = self._new_game()
                self.screen = Screen.TITLE

    def update(self, dt: float) -> None:
        """Advance the simulation by ``dt`` seconds of wall-clock time.

        Rendering runs at a fixed frame rate while the snake moves at
        ``game.speed`` steps per second, so steps are driven by an accumulator
        rather than one per frame.
        """
        if self.screen is not Screen.PLAYING:
            return
        self._accumulator += min(dt, MAX_FRAME_SECONDS)
        while self._accumulator >= (interval := 1.0 / self.game.speed):
            self._accumulator -= interval
            if self.game.step() in (StepResult.DIED, StepResult.WON):
                self._finish()
                return

    # -- drawing ---------------------------------------------------------

    def draw(self) -> None:
        mode = "Wrap" if self.wrap else "Walls"
        hud = HudInfo(
            score=self.game.score,
            best=max(self.best, self.game.score),
            mode_label=f"{self.difficulty.name}  /  {mode}  /  {self.game.speed:.1f} moves/s",
        )
        self.renderer.draw_game(self.game, hud)
        if self.screen is Screen.TITLE:
            self.renderer.draw_title(self.difficulty.name, self.wrap, self.best)
        elif self.screen is Screen.PAUSED:
            self.renderer.draw_paused()
        elif self.screen is Screen.GAME_OVER:
            self.renderer.draw_game_over(
                self.game.score, self.best, self.new_record, self.game.won
            )

    # -- main loop -------------------------------------------------------

    def run(self) -> None:
        """Run until the window is closed or the player quits from the title screen."""
        clock = pygame.time.Clock()
        while self.running:
            dt = clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    self.handle_key(event.key)
                elif event.type == pygame.WINDOWFOCUSLOST and self.screen is Screen.PLAYING:
                    self.screen = Screen.PAUSED
            self.update(dt)
            self.draw()
            pygame.display.flip()


def main(difficulty: Difficulty = DIFFICULTIES[1], wrap: bool = False) -> None:
    """Open the game window and play until the user quits."""
    pygame.init()
    try:
        pygame.display.set_caption("Snake")
        surface = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        SnakeApp(surface, HighScoreStore(), difficulty=difficulty, wrap=wrap).run()
    finally:
        pygame.quit()
