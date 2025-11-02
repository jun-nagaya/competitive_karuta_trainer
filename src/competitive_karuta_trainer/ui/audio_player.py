from __future__ import annotations

import base64
from typing import Any

import streamlit as st

from src.competitive_karuta_trainer.adapters.session_store_streamlit import StSessionStore
from src.competitive_karuta_trainer.services.audio import get_target_audio_bytes


def render_audio_player(placeholder: Any, store: StSessionStore, target_id: int | None) -> None:
    """音声プレーヤーを表示する。

    条件:
    - 計測開始済み (timing_started)
    - ターゲット ID が存在
    - ミュートではない

    音声取得ロジックは `audio.get_target_audio_bytes()` に委譲する。
    """
    if not (
        st.session_state.get("timing_started")
        and target_id is not None
        and not st.session_state.muted
    ):
        return
    audio_bytes = get_target_audio_bytes(store)
    if audio_bytes:
        player_id = f"player-{target_id}"
        b64 = base64.b64encode(audio_bytes).decode("utf-8")
        html = f'<audio id="{player_id}" src="data:audio/mp3;base64,{b64}" controls></audio>'
        placeholder.markdown(html, unsafe_allow_html=True)
    else:
        placeholder.caption("音声を準備しています…")


def build_autoplay_html(audio_bytes: bytes, player_id: str, defer_ms: int = 0) -> str:
    """自動再生用の HTML を生成する（autoplay + JS の play() フォールバック）。

    defer_ms: 再生開始をミリ秒単位で遅延させる（0 なら即時）。
    """
    b64 = base64.b64encode(audio_bytes).decode("utf-8")
    tpl = (
        (
            """
                <div>
                    <audio id="__ID__" src="data:audio/mp3;base64,__SRC__" controls autoplay></audio>
                    <button id="__ID___btn" style="display:none;margin-left:8px;">▶ 再生</button>
                </div>
                <script>
                (function(){
                    var a = document.getElementById("__ID__");
                    var b = document.getElementById("__ID___btn");
                    function tryPlay(){
                        if (!a || !a.play) return;
                        try { a.currentTime = 0; } catch(e) {}
                        var p = a.play();
                        if (p && p.catch) { p.catch(function(){ b.style.display='inline-block'; }); }
                    }
                    var deferMs = __DEFER__;
                    if (deferMs && deferMs > 0) {
                        setTimeout(tryPlay, deferMs);
                    } else {
                        tryPlay();
                    }
                    if (b) {
                        b.addEventListener('click', function(){ b.style.display='none'; tryPlay(); });
                    }
                })();
                </script>
                """
        )
        .replace("__ID__", player_id)
        .replace("__SRC__", b64)
        .replace("__DEFER__", str(int(max(0, defer_ms))))
    )
    return tpl


def render_html(placeholder: Any, html: str) -> None:
    """汎用 HTML をプレースホルダに描画する。"""
    placeholder.markdown(html, unsafe_allow_html=True)
