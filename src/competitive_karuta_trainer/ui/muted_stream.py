from __future__ import annotations

import time
from html import escape as html_escape

import streamlit as st

from src.competitive_karuta_trainer.domain import STREAMING_CHAR_DELAY, Pair


def render_muted_stream(target: Pair | None) -> None:
    """ミュート時の上の句をストリーミング表示する。

    仕様:
    - 無音モードかつ target がある場合に、上の句を1文字ずつ描画する。
    - 自動リフレッシュが無くても進行するよう、1実行内でストリームを完結させる。
    - 同じターゲットでは二重にストリームしない（完了後は全文静的表示）。
    """
    # スタート後（計測開始）かつ無音モード、ターゲットがある場合のみストリーム開始
    if not (
        st.session_state.get("timing_started", False)
        and st.session_state.muted
        and target is not None
    ):
        return

    holder = st.empty()
    current_tid = st.session_state.get("target_id")
    already = st.session_state.get("last_streamed_target_id") == current_tid

    # 既に完了していれば再表示しない
    if already:
        return

    # ストリーミング実行（非ブロッキングに近い体感で、短時間のみブロック）
    text_full = target.kami
    total = len(text_full)
    st.session_state.last_streamed_target_id = current_tid
    # 最低1文字目は即時表示
    for i in range(1, total + 1):
        # 途中でターゲットが変わったら中断
        if st.session_state.get("target_id") != current_tid:
            return
        text = text_full[:i]
        holder.markdown(
            f'<div style="text-align:center;font-size:1.8rem;line-height:1.8;">{html_escape(text)}</div>',
            unsafe_allow_html=True,
        )
        if i < total:
            time.sleep(float(STREAMING_CHAR_DELAY))
