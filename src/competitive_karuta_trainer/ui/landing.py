from __future__ import annotations

import os
from collections.abc import Callable

import streamlit as st

from src.competitive_karuta_trainer.domain import Pair, index_by_id
from src.competitive_karuta_trainer.services import dataset_loader
from src.competitive_karuta_trainer.services.config_loader import load_default_settings_values


def render_upload_ui(reset_game: Callable[[list[Pair]], None]) -> None:
    """ランディングのアップロード UI を描画する。

    使用者は、呼び出し元で `len(st.session_state.pairs) == 0` のときに
    本関数を呼び出し、その直後に return すること。

    Args:
        reset_game: データ読み込み後にゲーム状態を初期化するコールバック。
    """
    st.header("データセットをアップロード")
    st.markdown(
        """
        単一CSV形式のみ対応しています。
        - 必須: CSV 1 枚
        - 任意: 公式ルール画像（PNG）、設定（config.toml）
        """
    )
    mode = st.radio(
        "方法",
        options=["ZIP（推奨）", "個別ファイル（CSV 必須、PNG/TOML 任意）"],
        horizontal=True,
    )
    err_holder = st.empty()

    if mode.startswith("ZIP"):
        up_zip = st.file_uploader(
            "data フォルダを zip にしたファイル",
            type=["zip"],
            accept_multiple_files=False,
        )
        if st.button("読み込む", type="primary", key="main_btn_load_zip"):
            try:
                if not up_zip:
                    raise ValueError("ZIP ファイルが選択されていません。")
                kana, kanji, tips_df, rule_img = dataset_loader.load_from_zip_bytes(
                    up_zip.getvalue()
                )
                st.session_state.pairs_kana = kana
                st.session_state.pairs_kanji = kanji
                st.session_state.kimariji_df = tips_df
                st.session_state.rule_image_bytes = rule_img
                selected_mode = st.session_state.get("settings", {}).get("mode", "kana")
                use_pairs = kana if selected_mode == "kana" else kanji
                st.session_state.pairs = use_pairs
                st.session_state.pairs_by_id = index_by_id(use_pairs)
                st.session_state.data_path = "uploaded-zip://local"
                st.session_state.data_mode = selected_mode
                if "settings" not in st.session_state:
                    st.session_state.settings = {}
                _defaults = load_default_settings_values()
                for _k in ("samples", "rows", "cols", "muted"):
                    if _k in _defaults:
                        st.session_state.settings[_k] = _defaults[_k]
                st.session_state.muted = bool(st.session_state.settings.get("muted", False))
                st.session_state.last_streamed_target_id = None
                reset_game(use_pairs)
                st.success("データセットを読み込みました。")
                st.rerun()
            except Exception as e:
                err_holder.error(f"読み込みに失敗しました: {e}")
    else:
        ups = st.file_uploader(
            "必須: CSV / 任意: PNG, config.toml",
            type=["csv", "png", "toml"],
            accept_multiple_files=True,
        )
        if st.button("読み込む", type="primary", key="main_btn_load_multi"):
            try:
                files = ups or []
                by_name_bytes: dict[str, bytes] = {
                    os.path.basename(f.name): f.getvalue() for f in files
                }
                kana, kanji, tips_df, rule_img = dataset_loader.load_from_multi_bytes(by_name_bytes)
                st.session_state.pairs_kana = kana
                st.session_state.pairs_kanji = kanji
                st.session_state.kimariji_df = tips_df
                st.session_state.rule_image_bytes = rule_img
                selected_mode = st.session_state.get("settings", {}).get("mode", "kana")
                use_pairs = kana if selected_mode == "kana" else kanji
                st.session_state.pairs = use_pairs
                st.session_state.pairs_by_id = index_by_id(use_pairs)
                st.session_state.data_path = "uploaded-multi://local"
                st.session_state.data_mode = selected_mode
                if "settings" not in st.session_state:
                    st.session_state.settings = {}
                _defaults = load_default_settings_values()
                for _k in ("samples", "rows", "cols", "muted"):
                    if _k in _defaults:
                        st.session_state.settings[_k] = _defaults[_k]
                st.session_state.muted = bool(st.session_state.settings.get("muted", False))
                st.session_state.last_streamed_target_id = None
                reset_game(use_pairs)
                st.success("データセットを読み込みました")
                st.rerun()
            except Exception as e:
                err_holder.error(f"読み込みに失敗しました: {e}")
