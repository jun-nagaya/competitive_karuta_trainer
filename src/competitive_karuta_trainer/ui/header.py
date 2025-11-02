from __future__ import annotations

import random
from collections.abc import Callable

import streamlit as st

from src.competitive_karuta_trainer.adapters.session_store_streamlit import StSessionStore
from src.competitive_karuta_trainer.domain import Pair
from src.competitive_karuta_trainer.services.gameplay import start_game as _svc_start_game
from src.competitive_karuta_trainer.services.gameplay import sync_mode_pairs as _svc_sync_mode_pairs


def render_header(
    store: StSessionStore,
    reset_game: Callable[[list[Pair] | None, int | None, int | None], None],
) -> object:
    """メインヘッダー（スタートボタン + 音声プレースホルダ）を描画する。

    Args:
        reset_game: ゲーム状態を初期化するコールバック（サブセット/行列指定対応）。

    Returns:
        音声プレースホルダ（st.empty() の返り値）。
    """
    c1, c2 = st.columns([1, 9])
    with c1:
        start_disabled = len(st.session_state.pairs) == 0
        if st.button("スタート", use_container_width=False, disabled=start_disabled):
            # 現在のモードに合わせて pairs/pairs_by_id を同期
            _svc_sync_mode_pairs(store)
            all_pairs: list[Pair] = st.session_state.pairs
            subset_size = int(st.session_state.settings.get("samples", 30))
            rows = int(st.session_state.settings.get("rows", 5))
            cols = int(st.session_state.settings.get("cols", 4))
            selected_pairs = (
                random.sample(all_pairs, subset_size)
                if len(all_pairs) >= subset_size
                else all_pairs
            )
            reset_game(selected_pairs, rows, cols)
            _svc_start_game(store, selected_pairs, rows, cols)
            st.rerun()
    with c2:
        audio_placeholder = st.empty()
    return audio_placeholder
