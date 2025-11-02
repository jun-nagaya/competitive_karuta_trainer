from __future__ import annotations

from src.competitive_karuta_trainer.app.ports.session_store import SessionStore
from src.competitive_karuta_trainer.domain import Pair, choose_target_from_grid, init_deck, init_grid
from src.competitive_karuta_trainer.services import data_access
from src.competitive_karuta_trainer.services.config_loader import load_default_settings_values


def initialize_state(store: SessionStore) -> None:
    """アプリ起動時に必要なセッション状態を初期化する。

    既に存在するキーは上書きせず、未定義のときのみ初期値を設定する。
    データ未読込時は空のペアリストで初期盤面を構築する。
    """
    if store.get("pairs") is None:
        pairs: list[Pair] = []
        data_access.set_pairs(store, pairs)
        # 設定（サイドバーで変更可能）
        _defaults = load_default_settings_values()
        store.set(
            "settings",
            {
                # 初期のプレイ枚数（TOML で上書き可能）
                "samples": int(_defaults.get("samples", 30)),
                "rows": int(_defaults.get("rows", 5)),
                "cols": int(_defaults.get("cols", 4)),
                "muted": bool(_defaults.get("muted", False)),
                "mode": "kana",  # 'kana' or 'kanji'
            },
        )
        # 初期盤面を構築
        deck = init_deck(pairs)
        store.set("deck", deck)
        settings = store.get("settings", {})
        rows = int(settings.get("rows", 5))
        cols = int(settings.get("cols", 4))
        grid = init_grid(deck, rows, cols)
        store.set("grid", grid)
        store.set("active_rows", rows)
        store.set("active_cols", cols)
        store.set("target_id", choose_target_from_grid(grid))
        # 情報表示用のデータ識別
        data_access.set_dataset_meta(store, "uploaded://pending", "kana")
        store.set("score", 0)
        store.set("miss", 0)
        store.set("muted", bool(settings.get("muted", False)))
        # 自動再生予定時刻（取得後に遅延して再生）
        store.set("autoplay_at", None)
        # ミュート時の上の句ストリーミング制御
        store.set("last_streamed_target_id", None)

    # 計測関連（未定義時のみ初期化）
    if store.get("timing_started") is None:
        store.set("timing_started", False)
    if store.get("game_started_at") is None:
        store.set("game_started_at", None)
    if store.get("target_started_at") is None:
        store.set("target_started_at", None)
    if store.get("card_times") is None:
        store.set("card_times", {})
    if store.get("card_misses") is None:
        store.set("card_misses", {})
    # 音声キャッシュ
    if store.get("audio_cache") is None:
        store.set("audio_cache", {})


def reset_game(
    store: SessionStore,
    pairs_subset: list[Pair] | None = None,
    rows: int | None = None,
    cols: int | None = None,
) -> None:
    """ゲーム状態をリセットし、新しいデッキと盤面を構築する。

    引数が指定されればそれを優先し、未指定のときは現在の設定値を用いる。
    セッション状態（スコア・ミス・計測・キャッシュ等）をゲーム開始時の状態に揃える。
    """
    pairs = pairs_subset if pairs_subset is not None else (store.get("pairs") or [])
    settings = store.get("settings", {})
    rows_val = int(rows) if rows is not None else int(settings.get("rows", 5))
    cols_val = int(cols) if cols is not None else int(settings.get("cols", 4))
    deck = init_deck(pairs)
    store.set("deck", deck)
    grid = init_grid(deck, rows_val, cols_val)
    store.set("grid", grid)
    store.set("target_id", choose_target_from_grid(grid))
    store.set("score", 0)
    store.set("miss", 0)
    store.set("audio_cache", {})
    store.set("last_streamed_target_id", None)
    # このゲームで使う札ID一覧
    try:
        store.set("active_pair_ids", [p.id for p in pairs])  # type: ignore[attr-defined]
    except Exception:
        store.set("active_pair_ids", None)
    # 盤面サイズ（今回のゲーム中は固定）
    store.set("active_rows", rows_val)
    store.set("active_cols", cols_val)
    # 計測関連のリセット
    store.set("timing_started", False)
    store.set("game_started_at", None)
    store.set("target_started_at", None)
    store.set("card_times", {})
    store.set("card_misses", {})
