import random

import pytest

from snake.config import DIFFICULTIES, POINTS_PER_FOOD, Difficulty
from snake.logic import MAX_BUFFERED_TURNS, Direction, Game, Point, StepResult

NORMAL = DIFFICULTIES[1]


def make_game(**kwargs) -> Game:
    kwargs.setdefault("rng", random.Random(0))
    return Game(kwargs.pop("width", 10), kwargs.pop("height", 8), **kwargs)


def test_initial_snake_is_centred_and_food_is_free():
    game = make_game()
    assert game.head == Point(5, 4)
    assert game.body == (Point(5, 4), Point(4, 4), Point(3, 4))
    assert game.food is not None and game.food not in game.body
    assert game.alive and game.score == 0


def test_step_moves_head_and_drops_tail():
    game = make_game()
    game.food = Point(0, 0)
    assert game.step() is StepResult.MOVED
    assert game.body == (Point(6, 4), Point(5, 4), Point(4, 4))


def test_eating_grows_scores_and_respawns_food():
    game = make_game()
    game.food = Point(6, 4)
    assert game.step() is StepResult.ATE
    assert game.length == 4
    assert game.foods_eaten == 1
    assert game.score == POINTS_PER_FOOD * NORMAL.score_multiplier
    assert game.food is not None and game.food not in game.body


def test_speed_increases_with_food_and_is_capped():
    difficulty = Difficulty("T", start_speed=5, speed_step=1, max_speed=7, score_multiplier=1)
    game = make_game(difficulty=difficulty)
    assert game.speed == 5
    game.foods_eaten = 1
    assert game.speed == 6
    game.foods_eaten = 50
    assert game.speed == 7


def test_wall_collision_kills_when_not_wrapping():
    game = make_game(body=[Point(9, 0)], direction=Direction.RIGHT)
    game.food = Point(0, 7)
    assert game.step() is StepResult.DIED
    assert not game.alive
    # A dead game stays dead and does not move.
    assert game.step() is StepResult.DIED
    assert game.head == Point(9, 0)


@pytest.mark.parametrize(
    ("start", "direction", "expected"),
    [
        (Point(9, 3), Direction.RIGHT, Point(0, 3)),
        (Point(0, 3), Direction.LEFT, Point(9, 3)),
        (Point(4, 0), Direction.UP, Point(4, 7)),
        (Point(4, 7), Direction.DOWN, Point(4, 0)),
    ],
)
def test_wrap_mode_passes_through_edges(start, direction, expected):
    game = make_game(body=[start], direction=direction, wrap=True)
    game.food = Point(1, 1)
    assert game.step() is StepResult.MOVED
    assert game.head == expected


def test_running_into_own_body_kills():
    # A 5-long snake curled so that turning down hits its own body.
    body = [Point(3, 3), Point(4, 3), Point(4, 4), Point(3, 4), Point(2, 4)]
    game = make_game(body=body, direction=Direction.LEFT)
    game.food = Point(0, 0)
    game.queue_turn(Direction.DOWN)
    assert game.step() is StepResult.DIED


def test_moving_into_vacating_tail_is_allowed():
    # A 2x2 loop: the head chases the tail cell, which moves away this step.
    body = [Point(3, 3), Point(4, 3), Point(4, 4), Point(3, 4)]
    game = make_game(body=body, direction=Direction.DOWN)
    game.food = Point(0, 0)
    assert game.step() is StepResult.MOVED
    assert game.head == Point(3, 4)


def test_moving_into_tail_while_growing_kills():
    body = [Point(3, 3), Point(4, 3), Point(4, 4), Point(3, 4)]
    game = make_game(body=body, direction=Direction.DOWN)
    # Food cannot normally sit on the snake, but this pins down the rule that
    # a growing snake keeps its tail, so that cell is not free.
    game.food = Point(3, 4)
    assert game.step() is StepResult.DIED


def test_reversal_is_rejected():
    game = make_game()
    assert not game.queue_turn(Direction.LEFT)
    assert not game.queue_turn(Direction.RIGHT)  # same direction is a no-op
    assert game.pending_turns == ()


def test_quick_double_turn_does_not_self_collide():
    """Pressing up then left within one step must not reverse into the neck."""
    game = make_game()
    game.food = Point(0, 0)
    assert game.queue_turn(Direction.UP)
    assert game.queue_turn(Direction.LEFT)
    assert game.step() is StepResult.MOVED
    assert game.head == Point(5, 3)
    assert game.step() is StepResult.MOVED
    assert game.head == Point(4, 3)
    assert game.alive


def test_turn_is_validated_against_last_queued_direction():
    game = make_game()  # heading right
    assert game.queue_turn(Direction.UP)
    # Down would reverse the queued "up", so it must be ignored even though it
    # is perpendicular to the current heading.
    assert not game.queue_turn(Direction.DOWN)
    assert game.pending_turns == (Direction.UP,)


def test_turn_buffer_is_bounded():
    game = make_game()
    turns = [Direction.UP, Direction.LEFT, Direction.DOWN, Direction.RIGHT]
    accepted = [game.queue_turn(t) for t in turns]
    assert sum(accepted) == MAX_BUFFERED_TURNS
    assert len(game.pending_turns) == MAX_BUFFERED_TURNS


def test_filling_the_board_wins():
    # 4x2 board with 7 cells occupied: eating the last free cell fills it.
    body = [Point(0, 1), Point(1, 1), Point(2, 1), Point(3, 1), Point(3, 0), Point(2, 0), Point(1, 0)]
    game = Game(4, 2, NORMAL, body=body, direction=Direction.UP, rng=random.Random(0))
    assert game.food == Point(0, 0)
    assert game.step() is StepResult.WON
    assert game.won and game.food is None
    assert game.step() is StepResult.WON


def test_food_placement_is_reproducible_with_seed():
    a = make_game(rng=random.Random(42))
    b = make_game(rng=random.Random(42))
    assert a.food == b.food


@pytest.mark.parametrize(
    "body",
    [
        [Point(1, 1), Point(1, 1)],
        [Point(-1, 0)],
        [Point(10, 0)],
    ],
)
def test_invalid_bodies_are_rejected(body):
    with pytest.raises(ValueError):
        make_game(body=body)


def test_direction_opposites():
    for d in Direction:
        assert d.opposite().opposite() is d
        assert (d.dx + d.opposite().dx, d.dy + d.opposite().dy) == (0, 0)
