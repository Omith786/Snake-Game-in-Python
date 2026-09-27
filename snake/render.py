"""Drawing code. Reads game state but never changes it."""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from .config import CELL_SIZE, HUD_HEIGHT
from .logic import Direction, Game, Point

Colour = tuple[int, int, int]

BACKGROUND: Colour = (18, 20, 28)
TILE_DARK: Colour = (26, 29, 40)
TILE_LIGHT: Colour = (30, 34, 46)
HUD_BG: Colour = (14, 15, 21)
TEXT: Colour = (228, 231, 238)
TEXT_DIM: Colour = (140, 146, 162)
ACCENT: Colour = (120, 220, 140)
WALL: Colour = (86, 94, 118)
WRAP_EDGE: Colour = (70, 120, 170)
SNAKE_HEAD: Colour = (132, 230, 120)
SNAKE_TAIL: Colour = (38, 128, 92)
FOOD: Colour = (238, 84, 84)
FOOD_SHINE: Colour = (255, 190, 180)
EYE: Colour = (16, 18, 24)
EYE_WHITE: Colour = (240, 244, 236)
GOLD: Colour = (246, 200, 90)

SEGMENT_INSET = 3
LINE_GAP = 6


@dataclass(frozen=True)
class HudInfo:
    """Values shown in the top bar."""

    score: int
    best: int
    mode_label: str


def _lerp(a: Colour, b: Colour, t: float) -> Colour:
    return (
        round(a[0] + (b[0] - a[0]) * t),
        round(a[1] + (b[1] - a[1]) * t),
        round(a[2] + (b[2] - a[2]) * t),
    )


class Renderer:
    """Draws the board, HUD and menu overlays onto a pygame surface."""

    def __init__(self, surface: pygame.Surface) -> None:
        self.surface = surface
        self.font_title = pygame.font.Font(None, 84)
        self.font_large = pygame.font.Font(None, 48)
        self.font_medium = pygame.font.Font(None, 32)
        self.font_small = pygame.font.Font(None, 24)
        self.board_rect = pygame.Rect(
            0, HUD_HEIGHT, surface.get_width(), surface.get_height() - HUD_HEIGHT
        )
        self._veil = pygame.Surface(self.board_rect.size, pygame.SRCALPHA)
        self._veil.fill((10, 11, 16, 220))

    # -- public API ------------------------------------------------------

    def draw_game(self, game: Game, hud: HudInfo) -> None:
        """Draw the HUD, board, food and snake for the current frame."""
        self.surface.fill(BACKGROUND)
        self._draw_hud(hud)
        self._draw_board(game)
        if game.food is not None:
            self._draw_food(game.food)
        self._draw_snake(game)

    def draw_title(self, difficulty_name: str, wrap: bool, best: int) -> None:
        mode = "Wrap-around edges" if wrap else "Solid walls"
        self._overlay(
            [
                ("SNAKE", self.font_title, ACCENT),
                ("", self.font_small, TEXT),
                (f"<  {difficulty_name}  >", self.font_large, TEXT),
                (f"{mode}   (M to toggle)", self.font_medium, TEXT_DIM),
                (f"Best: {best}", self.font_medium, GOLD),
                ("", self.font_small, TEXT),
                ("Enter or Space to start", self.font_medium, TEXT),
                ("Arrows / WASD to steer, P to pause, Esc to quit", self.font_small, TEXT_DIM),
            ]
        )

    def draw_paused(self) -> None:
        self._overlay(
            [
                ("Paused", self.font_large, TEXT),
                ("P or Space to resume, Esc for menu", self.font_small, TEXT_DIM),
            ]
        )

    def draw_game_over(self, score: int, best: int, new_record: bool, won: bool) -> None:
        heading = "You filled the board!" if won else "Game over"
        lines = [
            (heading, self.font_large, ACCENT if won else FOOD),
            (f"Score: {score}", self.font_medium, TEXT),
        ]
        if new_record:
            lines.append(("New high score!", self.font_medium, GOLD))
        else:
            lines.append((f"Best: {best}", self.font_medium, TEXT_DIM))
        lines += [
            ("", self.font_small, TEXT),
            ("Enter or Space to play again, Esc for menu", self.font_small, TEXT_DIM),
        ]
        self._overlay(lines)

    # -- helpers ---------------------------------------------------------

    def _cell_rect(self, p: Point) -> pygame.Rect:
        return pygame.Rect(
            self.board_rect.x + p.x * CELL_SIZE,
            self.board_rect.y + p.y * CELL_SIZE,
            CELL_SIZE,
            CELL_SIZE,
        )

    def _draw_hud(self, hud: HudInfo) -> None:
        bar = pygame.Rect(0, 0, self.surface.get_width(), HUD_HEIGHT)
        pygame.draw.rect(self.surface, HUD_BG, bar)
        cy = bar.centery
        self._blit(f"Score {hud.score}", self.font_medium, TEXT, midleft=(16, cy))
        self._blit(hud.mode_label, self.font_small, TEXT_DIM, center=(bar.centerx, cy))
        self._blit(f"Best {hud.best}", self.font_medium, GOLD, midright=(bar.right - 16, cy))

    def _draw_board(self, game: Game) -> None:
        for y in range(game.height):
            for x in range(game.width):
                colour = TILE_LIGHT if (x + y) % 2 else TILE_DARK
                pygame.draw.rect(self.surface, colour, self._cell_rect(Point(x, y)))
        # The border colour hints at the mode: grey walls kill, blue edges wrap.
        edge = WRAP_EDGE if game.wrap else WALL
        pygame.draw.rect(self.surface, edge, self.board_rect, width=2)

    def _draw_food(self, food: Point) -> None:
        rect = self._cell_rect(food)
        radius = CELL_SIZE // 2 - 4
        pygame.draw.circle(self.surface, FOOD, rect.center, radius)
        shine = (rect.centerx - radius // 3, rect.centery - radius // 3)
        pygame.draw.circle(self.surface, FOOD_SHINE, shine, max(2, radius // 4))

    def _draw_snake(self, game: Game) -> None:
        body = game.body
        n = len(body)
        # Paint tail first so the head always ends up on top.
        for i in range(n - 1, -1, -1):
            colour = _lerp(SNAKE_HEAD, SNAKE_TAIL, i / max(1, n - 1))
            rect = self._cell_rect(body[i]).inflate(-2 * SEGMENT_INSET, -2 * SEGMENT_INSET)
            pygame.draw.rect(self.surface, colour, rect, border_radius=7)
            if i + 1 < n:
                self._bridge(body[i], body[i + 1], colour)
        self._draw_eyes(body[0], game.direction)

    def _bridge(self, a: Point, b: Point, colour: Colour) -> None:
        """Fill the inset gap between two adjacent segments so the body looks continuous."""
        if abs(a.x - b.x) + abs(a.y - b.y) != 1:
            return  # Segments split across a wrapped edge; leave the gap.
        ra, rb = self._cell_rect(a), self._cell_rect(b)
        joint = ra.union(rb).inflate(-2 * SEGMENT_INSET, -2 * SEGMENT_INSET)
        if a.x == b.x:
            joint.update(joint.x, min(ra.centery, rb.centery), joint.width, CELL_SIZE)
        else:
            joint.update(min(ra.centerx, rb.centerx), joint.y, CELL_SIZE, joint.height)
        pygame.draw.rect(self.surface, colour, joint)

    def _draw_eyes(self, head: Point, direction: Direction) -> None:
        cx, cy = self._cell_rect(head).center
        forward, side = CELL_SIZE // 10, CELL_SIZE // 5
        # Perpendicular to the heading, so the eyes sit side by side.
        px, py = -direction.dy, direction.dx
        for sign in (1, -1):
            ex = cx + direction.dx * forward + px * side * sign
            ey = cy + direction.dy * forward + py * side * sign
            pygame.draw.circle(self.surface, EYE_WHITE, (ex, ey), 4)
            pygame.draw.circle(self.surface, EYE, (ex + direction.dx, ey + direction.dy), 2)

    def _overlay(self, lines: list[tuple[str, pygame.font.Font, Colour]]) -> None:
        self.surface.blit(self._veil, self.board_rect.topleft)
        heights = [font.get_linesize() + LINE_GAP for _, font, _ in lines]
        y = self.board_rect.centery - sum(heights) // 2
        for (text, font, colour), h in zip(lines, heights):
            if text:
                self._blit(text, font, colour, midtop=(self.board_rect.centerx, y))
            y += h

    def _blit(self, text: str, font: pygame.font.Font, colour: Colour, **anchor: object) -> None:
        image = font.render(text, True, colour)
        self.surface.blit(image, image.get_rect(**anchor))
