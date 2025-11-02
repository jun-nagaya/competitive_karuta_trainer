from __future__ import annotations

import streamlit as st

from src.competitive_karuta_trainer.adapters.session_store_streamlit import StSessionStore
from src.competitive_karuta_trainer.services.gameplay import on_muted_toggle as _svc_on_muted_toggle


def render_sidebar(store: StSessionStore) -> None:
    """サイドバーの設定 UI を描画する。

    - データ未読込時は一部コントロールを無効化する。
    - ミュート切替は常に反映する（プレイ中でも可）。
    - ページリンクは利用可能な場合のみ表示する。
    """
    with st.sidebar:
        st.subheader("ゲーム設定")
        # データ未読込時は枚数/行列/モードを無効化する
        controls_disabled = (
            st.session_state.get("timing_started", False) or len(st.session_state.pairs) == 0
        )
        # ミュート切替はプレイ中でも許可（初回はデータ未読込時のみ無効）
        mute_disabled = len(st.session_state.pairs) == 0
        max_samples = max(1, len(st.session_state.pairs))
        # データ未読込時は widget state を分離して、既定値が 1 に固定される問題を回避
        samples_key = "samples_enabled" if not controls_disabled else "samples_disabled"
        samples = st.number_input(
            "プレイ枚数",
            min_value=1,
            max_value=max_samples,
            value=min(
                max_samples,
                max(1, st.session_state.get("settings", {}).get("samples", 30)),
            ),
            step=1,
            disabled=controls_disabled,
            key=samples_key,
        )
        rows_in = st.number_input(
            "行数",
            min_value=2,
            max_value=8,
            value=st.session_state.get("settings", {}).get("rows", 5),
            step=1,
            disabled=controls_disabled,
        )
        cols_in = st.number_input(
            "列数",
            min_value=2,
            max_value=8,
            value=st.session_state.get("settings", {}).get("cols", 4),
            step=1,
            disabled=controls_disabled,
        )
        mode_label = st.radio(
            "文字モード",
            options=["かな", "漢字"],
            index=0 if st.session_state.get("settings", {}).get("mode", "kana") == "kana" else 1,
            disabled=controls_disabled,
            horizontal=True,
        )
        st.markdown(
            '<div style="font-size:0.9rem; color:#31333F; font-weight:400; margin-bottom:4px;">無音モード</div>',
            unsafe_allow_html=True,
        )
        current_muted = st.session_state.get("settings", {}).get("muted", False)
        new_muted = st.toggle("", value=current_muted, disabled=mute_disabled)

        # 設定を保存（データ未読込時は枚数/行列/モードのみ更新しない）
        if not controls_disabled:
            if "settings" not in st.session_state:
                st.session_state.settings = {}
            st.session_state.settings.update(
                {
                    "mode": "kana" if mode_label == "かな" else "kanji",
                    "samples": int(samples),
                    "rows": int(rows_in),
                    "cols": int(cols_in),
                }
            )
        # ミュート設定は常に反映（プレイ中でも切替可）
        _svc_on_muted_toggle(store, bool(new_muted))

        # ページ移動リンク（Streamlit が対応している場合はサイドバーに表示）
        # 環境により自動のページ切替UIが表示されますが、見つけやすいよう明示リンクを併設します。
        try:
            # 新しめの Streamlit では page_link が提供される
            if hasattr(st.sidebar, "page_link"):
                st.divider()
                # 公式ルールページ
                st.page_link("pages/official_rule.py", label="公式ルール")
                # 札一覧
                st.page_link("pages/cards_list.py", label="Tips")
        except Exception:
            # 未対応環境ではデフォルトのページ切替UIを利用してもらう
            st.info("ページ切替は画面左上のページメニューから行えます。")
