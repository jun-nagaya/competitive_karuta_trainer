"""
データセット読み込みサービス（Streamlit 非依存）
- ZIP バイト列からの読込
- 個別ファイル（ベース名->バイト列）の読込
- ファイル名エイリアス解決

戻り値の契約:
    (pairs_kana: list[Pair], pairs_kanji: list[Pair], kimariji_df: pandas.DataFrame, rule_image_bytes: bytes)
"""

from __future__ import annotations

import io
import os
import tempfile
import zipfile
from typing import Any  # noqa: F401  # 将来的な拡張で使用予定（インターフェイス維持）

import pandas as pd

from src.competitive_karuta_trainer.domain import FILE_ALIASES, Pair
from src.competitive_karuta_trainer.domain.data import load_pairs
from src.competitive_karuta_trainer.services.config_loader import set_runtime_config, set_runtime_toml_bytes


def _zip_members_by_basename(zf: zipfile.ZipFile) -> dict[str, str]:
    """Zip 内のメンバーをベース名で引ける辞書にする（重複時は最初を優先）。"""
    out: dict[str, str] = {}
    for name in zf.namelist():
        base = os.path.basename(name)
        if base and base not in out:
            out[base] = name
    return out


def resolve_required_files(
    name_map: dict[str, str],
) -> tuple[dict[str, str], list[str]]:
    """ベース名->実体の辞書から、必要ファイルの実体を解決する。

    Args:
        name_map: ベース名 -> 実体（Zip内フルパスやキー）
    Returns:
        (resolved_map, missing_keys)
        resolved_map: 論理名(kana/kanji/kimariji/rule) -> 実体
        missing_keys: 解決できなかった論理名
    """
    resolved: dict[str, str] = {}
    missing: list[str] = []
    for key, candidates in FILE_ALIASES.items():
        found = None
        for cand in candidates:
            if cand in name_map:
                found = name_map[cand]
                break
        if found is None:
            missing.append(key)
        else:
            resolved[key] = found
    return resolved, missing


def _read_pairs_from_bytes(content: bytes) -> list[Pair]:
    """CSV バイト列を一時ファイルに落として load_pairs で読み込む。"""
    with tempfile.NamedTemporaryFile("wb", suffix=".csv", delete=False) as tf:
        tf.write(content)
        tmp = tf.name
    try:
        return load_pairs(tmp)
    finally:
        try:
            os.remove(tmp)
        except Exception:
            pass


def load_from_zip_bytes(
    data: bytes,
) -> tuple[list[Pair], list[Pair], pd.DataFrame, bytes]:
    """Zip バイト列からデータセットを読み込む。"""
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        name_map = _zip_members_by_basename(zf)
        resolved, missing_keys = resolve_required_files(name_map)
        if missing_keys:
            details = [f"{k}: {', '.join(FILE_ALIASES[k])}" for k in missing_keys]
            raise ValueError("Zip に必要ファイルが不足しています: " + "; ".join(details))

        def read_member_as_pairs(member_fullname: str) -> list[Pair]:
            with zf.open(member_fullname) as f:
                return _read_pairs_from_bytes(f.read())

        kana_pairs = read_member_as_pairs(resolved["kana"])
        kanji_pairs = read_member_as_pairs(resolved["kanji"])
        with zf.open(resolved["kimariji"]) as f:
            kimariji_df = pd.read_csv(io.BytesIO(f.read()))
        with zf.open(resolved["rule"]) as f:
            rule_img_bytes = f.read()
        # 任意の config.toml が含まれていれば取り込む
        try:
            base_map = _zip_members_by_basename(zf)
            cfg_member = base_map.get("config.toml")
            if cfg_member:
                with zf.open(cfg_member) as f:
                    set_runtime_toml_bytes(f.read())
            else:
                set_runtime_config(None)
        except Exception:
            set_runtime_config(None)
        return kana_pairs, kanji_pairs, kimariji_df, rule_img_bytes


def load_from_multi_bytes(
    by_name_bytes: dict[str, bytes],
) -> tuple[list[Pair], list[Pair], pd.DataFrame, bytes]:
    """個別ファイル（ベース名->バイト列）からデータセットを読み込む。"""
    resolved, missing_keys = resolve_required_files({k: k for k in by_name_bytes.keys()})
    if missing_keys:
        details = [f"{k}: {', '.join(FILE_ALIASES[k])}" for k in missing_keys]
        raise ValueError("不足ファイル: " + "; ".join(details))

    kana = _read_pairs_from_bytes(by_name_bytes[resolved["kana"]])
    kanji = _read_pairs_from_bytes(by_name_bytes[resolved["kanji"]])
    tips_df = pd.read_csv(io.BytesIO(by_name_bytes[resolved["kimariji"]]))
    rule_img = by_name_bytes[resolved["rule"]]

    if not kana or not kanji or tips_df.empty or not rule_img:
        raise ValueError("ファイルの内容が不正です。")

    # 任意の config.toml が含まれていれば取り込む
    try:
        if "config.toml" in by_name_bytes:
            set_runtime_toml_bytes(by_name_bytes["config.toml"])
        else:
            set_runtime_config(None)
    except Exception:
        set_runtime_config(None)

    return kana, kanji, tips_df, rule_img
