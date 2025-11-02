from __future__ import annotations

import time
from collections.abc import Iterable

from src.competitive_karuta_trainer.app.ports.session_store import SessionStore
from src.competitive_karuta_trainer.domain import Pair, choose_target_from_grid, index_by_id, refill_cell

# UI コンポーネントからのイベント（クリック、開始、ミュート切替等）を受け取り、
# セッション状態の更新とドメイン操作を一箇所に集約する。
# 本モジュールは UI フレームワークに依存しない。状態アクセスは SessionStore 経由で行う。


def handle_cell_click(store: SessionStore, r: int, c: int) -> None:
    """盤面セルクリック時の処理を行う。

    振る舞い:
    - 正解: スコア加算、補充、次ターゲット選定、計時更新、自動再生のスケジュール。
    - 不正解: ミス加算、当該ターゲットのミス回数を更新。
    """
    grid: list[list[int | None]] = store.get("grid")
    if not grid:
        return
    card_id = grid[r][c]
    target_id = store.get("target_id")
    if card_id is None or target_id is None:
        return

    if card_id == target_id:
        # 正解
        now_ts = time.time()
        # 計測（ターゲット経過時間）
        if store.get("timing_started") and store.get("target_started_at"):
            duration = max(0.0, now_ts - float(store.get("target_started_at")))
            times: dict[int, list[float]] = store.get("card_times", {})
            arr = times.get(int(target_id))
            if arr is None:
                times[int(target_id)] = [duration]
            else:
                arr.append(duration)
            store.set("card_times", times)

        store.set("score", int(store.get("score", 0)) + 1)
        # 札を取り除いて補充
        grid[r][c] = None
        deck: list[int] = store.get("deck", [])
        refill_cell(grid, r, c, deck)
        store.set("grid", grid)
        next_target = choose_target_from_grid(grid)
        store.set("target_id", next_target)
        # 次ターゲットの計測開始
        if store.get("timing_started") and next_target is not None:
            store.set("target_started_at", now_ts)
        # 自動再生スケジュール（最小遅延 2.0s）
        store.set("autoplay_at", time.time() + 2.0)
        store.set("autoplay_min_delay", 2.0)
    else:
        # 不正解
        store.set("miss", int(store.get("miss", 0)) + 1)
        cm: dict[int, int] = store.get("card_misses", {})
        tid = int(target_id)
        cm[tid] = int(cm.get(tid, 0)) + 1
        store.set("card_misses", cm)


def sync_mode_pairs(store: SessionStore) -> None:
    """現在の設定モード（かな/漢字）に合わせて使用ペアを同期する。

    - `pairs_kana`/`pairs_kanji` が存在する場合に限り、`pairs` と `pairs_by_id` を更新する。
    - `data_mode` も併せて更新する。
    """
    pairs_kana = store.get("pairs_kana")
    pairs_kanji = store.get("pairs_kanji")
    if pairs_kana is None and pairs_kanji is None:
        return
    mode = (store.get("settings", {}) or {}).get("mode", "kana")
    src = pairs_kana if mode == "kana" else pairs_kanji
    if src is None:
        return
    pairs: list[Pair] = list(src)
    store.set("pairs", pairs)
    store.set("pairs_by_id", index_by_id(pairs))
    store.set("data_mode", mode)


def start_game(store: SessionStore, selected_pairs: Iterable[Pair], rows: int, cols: int) -> None:
    """ゲーム開始時の計時・スケジュール等の初期化を行う。

    前提:
    - 盤面構築やターゲット選定は別途完了している（例: reset_game() 済み）。
    """
    now_ts = time.time()
    store.set("timing_started", True)
    store.set("game_started_at", now_ts)
    store.set("target_started_at", now_ts)
    store.set("card_times", {})
    store.set("card_misses", {})
    store.set("last_streamed_target_id", None)
    # 起動直後も音声が流れるよう自動再生を短い遅延でスケジュール
    store.set("autoplay_at", now_ts + 0.2)
    store.set("autoplay_min_delay", 0.2)
    # 使用札ID一覧（明示設定）
    try:
        ids = [p.id for p in selected_pairs]  # type: ignore[attr-defined]
    except Exception:
        ids = None
    store.set("active_pair_ids", ids)


def on_muted_toggle(store: SessionStore, new_muted: bool) -> None:
    """ミュート切替時の副作用（設定更新・再生スケジュール）を処理する。"""
    desired = bool(new_muted)
    current = bool(store.get("muted", False))
    # 状態に変化がなければ何もしない
    if current == desired:
        return

    settings = store.get("settings", {}) or {}
    settings["muted"] = desired
    store.set("settings", settings)
    store.set("muted", desired)
    # トグル時のみストリーム状態をリセット
    store.set("last_streamed_target_id", None)
    # プレイ中にミュート解除されたら、直ちに再生を試みる
    if not desired and store.get("timing_started") and store.get("target_id") is not None:
        now = time.time()
        store.set("autoplay_at", now + 0.1)
        store.set("autoplay_min_delay", 0.1)
