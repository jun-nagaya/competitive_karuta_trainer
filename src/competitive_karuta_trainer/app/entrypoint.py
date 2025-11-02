import streamlit as st

from src.competitive_karuta_trainer.adapters.session_store_streamlit import StSessionStore
from src.competitive_karuta_trainer.services import app_state, data_access
from src.competitive_karuta_trainer.services.audio_playback import maybe_get_scheduled_autoplay
from src.competitive_karuta_trainer.services.config_loader import get_app_title, set_runtime_config
from src.competitive_karuta_trainer.ui.audio_player import (
    build_autoplay_html,
    render_audio_player,
    render_html,
)
from src.competitive_karuta_trainer.ui.board import handle_click, render_board
from src.competitive_karuta_trainer.ui.header import render_header
from src.competitive_karuta_trainer.ui.landing import render_upload_ui
from src.competitive_karuta_trainer.ui.muted_stream import render_muted_stream
from src.competitive_karuta_trainer.ui.sidebar import render_sidebar
from src.competitive_karuta_trainer.ui.status import render_status_and_results


def main():
    # ページ設定は「アップロード前は常に既定タイトル」に固定する。
    # Streamlit の仕様上 set_page_config は最初に 1 度だけ呼ぶ必要があるため、
    # ここでは固定の既定タイトルを使い、データ読込後の見出しは別途動的に描画する。
    default_title = "百人一首トレーナー"
    st.set_page_config(page_title=default_title, layout="wide")

    try:
        store = StSessionStore()
        app_state.initialize_state(store)
    except Exception as e:
        st.error(f"データ読み込みに失敗しました: {e}")
        return

    # データの有無でタイトルとランタイム設定の扱いを分岐
    # - データ未読込: ランタイム設定（アップロード TOML 由来）は破棄し、既定タイトルを表示
    # - データ読込済: ランタイム設定を反映したタイトルを表示
    data_loaded = len(st.session_state.pairs) > 0
    if not data_loaded:
        # 履歴（ランタイム設定）が残らないようにクリアする
        try:
            set_runtime_config(None)
        except Exception:
            # タイトル描画に支障が出ないように握りつぶす
            pass
        st.title(default_title)
    else:
        st.title(get_app_title(default_title))

    # サイドバー: 設定 UI
    render_sidebar(store)

    # ランディング: データ未読込ならメインエリアをアップロード画面にする
    if len(st.session_state.pairs) == 0:
        # アップロード画面ではゲームUIを表示しない
        render_upload_ui(reset_game=lambda pairs: app_state.reset_game(store, pairs))
        return

    # ここから下はデータ読込済み時のゲームUI
    # ヘッダー操作（スタート + 音声プレーヤー置き場）
    audio_placeholder = render_header(
        store,
        reset_game=lambda pairs, rows, cols: app_state.reset_game(store, pairs, rows, cols),
    )

    # リセット時に自動で計測を開始するため、専用の計測開始ボタンは設置しない

    # ステータス表示と終了時の結果、ミュート時の上の句ストリーム
    target = data_access.get_pair(store, store.get("target_id"))
    render_status_and_results(target)
    render_muted_stream(target)

    # 音声プレースホルダ
    render_audio_player(
        audio_placeholder,
        store,
        store.get("target_id"),
    )

    # 盤面
    st.divider()
    render_board(lambda r, c: handle_click(store, r, c))

    # スケジュールされた自動再生（サービスで判定し、UIで描画）
    attempted, audio_bytes, player_id = maybe_get_scheduled_autoplay(store)
    if attempted:
        if audio_bytes and player_id:
            defer_ms = int(store.get("autoplay_defer_ms") or 0)
            store.set("autoplay_defer_ms", None)  # 消費
            html = build_autoplay_html(audio_bytes, player_id, defer_ms)
            render_html(audio_placeholder, html)
        else:
            st.warning("音声生成に失敗しました（ネットワーク状況等をご確認ください）。")
