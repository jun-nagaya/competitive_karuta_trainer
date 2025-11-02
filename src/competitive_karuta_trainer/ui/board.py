from __future__ import annotations

from collections.abc import Callable

import streamlit as st

from src.competitive_karuta_trainer.adapters.session_store_streamlit import StSessionStore
from src.competitive_karuta_trainer.domain import Pair
from src.competitive_karuta_trainer.services.gameplay import handle_cell_click as _svc_handle_cell_click


def render_board(on_click: Callable[[int, int], None]) -> None:
    """盤面を描画し、クリックで on_click(r, c) を呼び出す。"""
    rows_dim = int(
        st.session_state.get("active_rows", st.session_state.get("settings", {}).get("rows", 5))
    )
    cols_dim = int(
        st.session_state.get("active_cols", st.session_state.get("settings", {}).get("cols", 4))
    )
    for r in range(rows_dim):
        cols = st.columns(cols_dim)
        for c in range(cols_dim):
            card_id = st.session_state.grid[r][c]
            label = "—"
            disabled = True
            if card_id is not None:
                p: Pair | None = st.session_state.pairs_by_id.get(card_id)
                if p is not None:
                    label = p.shimo
                    disabled = False
            if cols[c].button(
                label, key=f"cell-{r}-{c}", use_container_width=True, disabled=disabled
            ):
                on_click(r, c)
                st.rerun()


def handle_click(store: StSessionStore, r: int, c: int) -> None:
    """盤面セルクリック時の処理をサービスに委譲する。"""
    _svc_handle_cell_click(store, r, c)
