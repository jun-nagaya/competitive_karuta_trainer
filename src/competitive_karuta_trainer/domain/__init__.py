"""ドメイン層（純粋ロジック/データモデル）。

提供物:
"""

from src.competitive_karuta_trainer.domain.constants import FILE_ALIASES, STREAMING_CHAR_DELAY
from src.competitive_karuta_trainer.domain.data import Pair, index_by_id
from src.competitive_karuta_trainer.domain.game import (
    Grid,
    choose_target_from_grid,
    grid_positions,
    init_deck,
    init_grid,
    refill_cell,
    remaining_on_grid,
)

__all__ = [
    # data
    "Pair",
    "index_by_id",
    # game
    "Grid",
    "init_deck",
    "init_grid",
    "grid_positions",
    "choose_target_from_grid",
    "refill_cell",
    "remaining_on_grid",
    # constants
    "STREAMING_CHAR_DELAY",
    "FILE_ALIASES",
]
