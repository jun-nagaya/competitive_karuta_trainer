from __future__ import annotations

import math
import time

import pandas as pd
import streamlit as st

from src.competitive_karuta_trainer.domain import Pair


def render_status_and_results(target: Pair | None) -> None:
    """ステータス（残り・ミス）と終了時の結果を描画する。

    Args:
        target: 現在のターゲット。None の場合は結果表示を行う。
    """
    # このゲームの総枚数（サブセットがあればその枚数、未開始時は設定値）
    active_ids = st.session_state.get("active_pair_ids")
    planned_total = int(
        st.session_state.get("settings", {}).get("samples", len(st.session_state.pairs))
    )
    total = len(active_ids) if active_ids else planned_total
    remaining_total = max(0, total - st.session_state.score)
    c1, c2 = st.columns(2)
    with c1:
        st.metric("残り", f"{remaining_total}/{total}")
    with c2:
        st.metric("ミス", st.session_state.miss)

    if target is not None:
        return

    st.info("お疲れさまでした！ すべての札を取り終えました。")
    # 計測結果（今回のみ）
    if st.session_state.get("timing_started") and st.session_state.get("game_started_at"):
        elapsed = time.time() - st.session_state.game_started_at
        mm = int(elapsed // 60)
        ss = int(elapsed % 60)
        st.subheader("計測結果")
        st.metric("総時間", f"{mm:02d}:{ss:02d}")
        times: dict[int, list[float]] = st.session_state.card_times or {}
        # 今回の1枚あたり時間（このゲーム中の単回計測）
        durations: list[tuple[float, int]] = []  # (sec, pair_id)
        for pid, arr in times.items():
            if arr:
                durations.append((float(arr[-1]), pid))
        if durations:
            n = len(durations)
            avg_per_card = sum(d for d, _ in durations) / n
            st.metric("平均/札", f"{avg_per_card:.2f}s")
            # 下位10%（遅い方）のみを苦手と判定
            k = max(1, math.ceil(n * 0.10))
            durations.sort(key=lambda x: x[0], reverse=True)
            weak = durations[:k]
            if weak:
                st.markdown("**苦手な札（下位10%）**")
                for sec, pid in weak:
                    p = _get_pair(pid)
                    if not p:
                        continue
                    st.write(f"• 『{p.kami}』→『{p.shimo}』 {sec:.2f}s")
            # ミスした札（降順・すべて表示）
            misses: dict[int, int] = st.session_state.get("card_misses", {})
            miss_rows = [(cnt, pid) for pid, cnt in misses.items() if cnt and cnt > 0]
            if miss_rows:
                miss_rows.sort(reverse=True, key=lambda x: x[0])
                st.markdown("**ミスした札**")
                for cnt, pid in miss_rows:
                    p = _get_pair(pid)
                    if not p:
                        continue
                    st.write(f"• 『{p.kami}』→『{p.shimo}』 ミス {cnt}回")
            # 全札の取得時間（今回）
            st.markdown("**各札の取得時間**")
            rows = []
            for sec, pid in sorted(durations, key=lambda x: x[0], reverse=True):
                p = _get_pair(pid)
                if not p:
                    continue
                rows.append(
                    {
                        "上の句": p.kami,
                        "下の句": p.shimo,
                        "時間(s)": f"{sec:.2f}",
                    }
                )
            if rows:
                df = pd.DataFrame(rows)
                st.dataframe(df, hide_index=True, use_container_width=True)


def _get_pair(pair_id: int | None) -> Pair | None:
    if pair_id is None:
        return None
    return st.session_state.pairs_by_id.get(pair_id)
