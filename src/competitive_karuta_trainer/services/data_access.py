from __future__ import annotations

from src.competitive_karuta_trainer.app.ports.session_store import SessionStore
from src.competitive_karuta_trainer.domain import Pair
from src.competitive_karuta_trainer.domain import index_by_id as _index_by_id


def get_pair(store: SessionStore, pair_id: int | None) -> Pair | None:
    """セッション（store）内のペア辞書からIDで取得する。

    pair_id が None の場合は None を返す。
    """
    if pair_id is None:
        return None
    pairs_by_id: dict[int, Pair] = store.get("pairs_by_id", {})
    return pairs_by_id.get(pair_id)


def build_index_by_id(pairs: list[Pair]) -> dict[int, Pair]:
    """`Pair` の id をキーにした辞書を返す（data.index_by_id の薄いラッパー）。"""
    return _index_by_id(pairs)


def set_pairs(store: SessionStore, pairs: list[Pair]) -> None:
    """セッションに pairs と pairs_by_id を設定する。

    - UI やコントローラ層からは本関数経由で設定することで、参照箇所の統一を図る。
    """
    store.set("pairs", pairs)
    store.set("pairs_by_id", build_index_by_id(pairs))


def get_pairs(store: SessionStore) -> list[Pair]:
    """セッションのペア一覧を返す（未設定時は空リスト）。"""
    return store.get("pairs", [])


def get_pairs_map(store: SessionStore) -> dict[int, Pair]:
    """セッションのペア辞書を返す（未設定時は空辞書）。"""
    return store.get("pairs_by_id", {})


# ---- Dataset metadata helpers ----


def set_dataset_meta(store: SessionStore, path: str, mode: str) -> None:
    """データセットの識別情報（パス/モード）をセッションに設定する。

    Args:
        path: 表示用の識別（例: uploaded://pending やファイル名等）
        mode: "kana" | "kanji" の想定
    """
    store.set("data_path", path)
    store.set("data_mode", mode)


def get_dataset_path(store: SessionStore) -> str | None:
    """データセットの識別パスを返す。未設定なら None。"""
    return store.get("data_path")


def get_dataset_mode(store: SessionStore) -> str | None:
    """データセットのモード（kana/kanji）を返す。未設定なら None。"""
    return store.get("data_mode")
