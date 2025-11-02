from __future__ import annotations

import time

from src.competitive_karuta_trainer.app.ports.session_store import SessionStore
from src.competitive_karuta_trainer.services.audio import get_target_audio_bytes


def maybe_get_scheduled_autoplay(store: SessionStore) -> tuple[bool, bytes | None, str | None]:
    """スケジュールされた自動再生を非ブロッキングで実行し、結果を返す。

    Returns:
        (attempted, audio_bytes, player_id)
        attempted: 条件が揃い自動再生を試みたか（未到来なら False）
        audio_bytes: 取得できた音声（失敗時は None）
        player_id: プレーヤー要素のID（音声ありのとき）
    副作用:
        実行した場合は autoplay_at を None に戻す（成功/失敗問わず）。
    注意:
        time.sleep は使用せず、現在時刻が autoplay_at を過ぎている場合のみ実行する。
    """
    target_id = store.get("target_id")
    autoplay_at = store.get("autoplay_at")
    if not (
        target_id is not None
        and not store.get("muted", False)
        and store.get("timing_started")
        and autoplay_at is not None
    ):
        return False, None, None

    # 時刻未到来なら、同一レンダリング内での遅延再生を可能にする
    now = time.time()
    if now < float(autoplay_at):
        # 残り時間を ms で記録し、音声を先に用意して返す
        defer_ms = int(max(0.0, (float(autoplay_at) - now)) * 1000)
        audio_bytes = get_target_audio_bytes(store)
        # スケジュールは消費済みにする
        store.set("autoplay_at", None)
        store.set("autoplay_min_delay", None)
        store.set("autoplay_defer_ms", defer_ms)
        if audio_bytes:
            return True, audio_bytes, f"player-{target_id}"
        return True, None, None

    # 到来したので即時実行（最低遅延はスケジュール側で設定済み想定）
    audio_bytes = get_target_audio_bytes(store)
    # 終了処理
    store.set("autoplay_at", None)
    # 一度使った最小遅延設定はクリア（存在すれば）
    store.set("autoplay_min_delay", None)
    store.set("autoplay_defer_ms", 0)
    if audio_bytes:
        return True, audio_bytes, f"player-{target_id}"
    return True, None, None
