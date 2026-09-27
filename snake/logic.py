"""Pure game rules for Snake.

Nothing in this module imports pygame, so the whole simulation can be driven
and tested without a display. Time is measured in discrete steps; the caller
decides how many steps happen per second (see :attr:`Game.speed`).
"""

from __future__ import annotations

import random
from collections import deque
from enum import Enum
from typing import Iterable, NamedTuple

from .config import DEFAULT_DIFFICULTY, POINTS_PER_FOOD, Difficulty

# Two queued turns is enough to perform a U-turn (e.g. up then left) within a
# single frame, while still being short enough that stale key presses don't
# pile up and steer the snake long after the player let go.
MAX_BUFFERED_TURNS = 2


class Point(NamedTuple):
    """A cell on the board, with ``(0, 0)`` in the top-left corner."""

    x: int
    y: int


class Direction(Enum):
    """Movement directions as unit ``(dx, dy)`` vectors in screen space."""

    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

    @property
    def dx(self) -> int:
        return self.value[0]

    @property
    def dy(self) -> int:
        return self.value[1]

    def opposite(self) -> Direction:
        """Return the direction pointing the other way."""
        return Direction((-self.dx, -self.dy))


class StepResult(Enum):
    """What happened during a single call to :meth:`Game.step`."""

    MOVED = "moved"
    ATE = "ate"
    DIED = "died"
    WON = "won"


class Game:
    """The state of one round of Snake.

    Args:
        width: Board width in cells.
        height: Board height in cells.
        difficulty: Speed curve and score multiplier.
        wrap: If true, leaving one edge re-enters from the opposite edge
            instead of ending the game.
        rng: Random source for food placement; pass a seeded instance for
            reproducible games.
        start_length: Initial snake length, laid out horizontally.
        body: Explicit starting body (head first). Overrides ``start_length``
            and is mostly useful for tests and screenshots.
        direction: Initial heading.
    """

    def __init__(
        self,
        width: int,
        height: int,
        difficulty: Difficulty = DEFAULT_DIFFICULTY,
        *,
        wrap: bool = False,
        rng: random.Random | None = None,
        start_length: int = 3,
        body: Iterable[Point] | None = None,
        direction: Direction = Direction.RIGHT,
    ) -> None:
        if width < 4 or height < 2:
            raise ValueError("Board must be at least 4x2 cells")
        if start_length < 1:
            raise ValueError("start_length must be positive")

        self.width = width
        self.height = height
        self.difficulty = difficulty
        self.wrap = wrap
        self._rng = rng or random.Random()

        if body is None:
            cx, cy = width // 2, height // 2
            body = [Point(cx - i * direction.dx, cy - i * direction.dy) for i in range(start_length)]
        self._body: deque[Point] = deque(Point(*p) for p in body)
        self._occupied: set[Point] = set(self._body)
        if len(self._occupied) != len(self._body):
            raise ValueError("Snake body overlaps itself")
        if not all(self.in_bounds(p) for p in self._body):
            raise ValueError("Snake body lies outside the board")

        self.direction = direction
        self._turns: deque[Direction] = deque()
        self.score = 0
        self.foods_eaten = 0
        self.alive = True
        self.won = False
        self.food: Point | None = self._spawn_food()

    # -- queries ---------------------------------------------------------

    @property
    def head(self) -> Point:
        return self._body[0]

    @property
    def body(self) -> tuple[Point, ...]:
        """Snake segments from head to tail."""
        return tuple(self._body)

    @property
    def length(self) -> int:
        return len(self._body)

    @property
    def speed(self) -> float:
        """Current moves per second, rising with each piece of food eaten."""
        d = self.difficulty
        return min(d.max_speed, d.start_speed + d.speed_step * self.foods_eaten)

    @property
    def pending_turns(self) -> tuple[Direction, ...]:
        return tuple(self._turns)

    def in_bounds(self, p: Point) -> bool:
        return 0 <= p.x < self.width and 0 <= p.y < self.height

    # -- commands --------------------------------------------------------

    def queue_turn(self, direction: Direction) -> bool:
        """Buffer a turn to apply on a future step.

        Turns are validated against the *last queued* heading rather than the
        current one. Without that, pressing up then left faster than one step
        while moving right would be judged "left vs right" only after the up
        had been applied, letting the snake reverse into its own neck.

        Returns:
            True if the turn was accepted, False if it was a no-op, a reversal,
            or the buffer was full.
        """
        reference = self._turns[-1] if self._turns else self.direction
        if direction in (reference, reference.opposite()):
            return False
        if len(self._turns) >= MAX_BUFFERED_TURNS:
            return False
        self._turns.append(direction)
        return True

    def step(self) -> StepResult:
        """Advance the snake by one cell and resolve collisions and food."""
        if self.won:
            return StepResult.WON
        if not self.alive:
            return StepResult.DIED

        if self._turns:
            self.direction = self._turns.popleft()

        head = self.head
        new_head = Point(head.x + self.direction.dx, head.y + self.direction.dy)
        if self.wrap:
            new_head = Point(new_head.x % self.width, new_head.y % self.height)
        elif not self.in_bounds(new_head):
            self.alive = False
            return StepResult.DIED

        grows = new_head == self.food
        tail = self._body[-1]
        # The tail cell is vacated on this same step unless the snake grows,
        # so chasing your own tail is legal.
        if new_head in self._occupied and (grows or new_head != tail):
            self.alive = False
            return StepResult.DIED

        if not grows:
            self._body.pop()
            self._occupied.discard(tail)
        self._body.appendleft(new_head)
        self._occupied.add(new_head)

        if not grows:
            return StepResult.MOVED

        self.foods_eaten += 1
        self.score += POINTS_PER_FOOD * self.difficulty.score_multiplier
        self.food = self._spawn_food()
        if self.food is None:
            self.won = True
            return StepResult.WON
        return StepResult.ATE

    # -- internals -------------------------------------------------------

    def _spawn_food(self) -> Point | None:
        free = [
            Point(x, y)
            for y in range(self.height)
            for x in range(self.width)
            if Point(x, y) not in self._occupied
        ]
        return self._rng.choice(free) if free else None
