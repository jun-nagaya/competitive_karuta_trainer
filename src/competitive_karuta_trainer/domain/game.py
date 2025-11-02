from __future__ import annotations

import random
from typing import Iterator, Tuple

# Grid の型は、整数の札 ID もしくは None を要素とする二次元配列
Grid = list[list[int | None]]


# 既定の行・列（後方互換のため残置。実際の処理は渡された rows/cols や grid サイズを使用）
ROWS = 5
COLS = 4
GRID_SIZE = ROWS * COLS


def init_deck(pairs) -> list[int]:
    """全ペアの id から山札（シャッフル済み）を作る。"""
    deck = [p.id for p in pairs]
    random.shuffle(deck)
    return deck


def init_grid(deck: list[int], rows: int, cols: int) -> Grid:
    """山札から下の句を取り出して rows×cols に配置。足りなければ None を埋める。"""
    grid: Grid = [[None for _ in range(cols)] for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            if deck:
                grid[r][c] = deck.pop()
            else:
                grid[r][c] = None
    return grid


def grid_positions(grid: Grid) -> Iterator[Tuple[int, int]]:
    """grid の実サイズに基づく走査位置を返す。"""
    for r, row in enumerate(grid):
        for c, _ in enumerate(row):
            yield r, c


def choose_target_from_grid(grid: Grid) -> int | None:
    """現在 grid に存在する id からランダムに選んで返す。無ければ None。"""
    choices = [grid[r][c] for r, c in grid_positions(grid) if grid[r][c] is not None]
    if not choices:
        return None
    return random.choice(choices)


def refill_cell(grid: Grid, r: int, c: int, deck: list[int]) -> None:
    """指定セルが空なら deck から1枚補充する（無ければ None のまま）。"""
    if grid[r][c] is None and deck:
        grid[r][c] = deck.pop()


def remaining_on_grid(grid: Grid) -> int:
    """grid 上に残っている札の枚数を返す。"""
    return sum(1 for r, c in grid_positions(grid) if grid[r][c] is not None)
