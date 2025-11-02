"""
データセット読み込みサービス（Streamlit 非依存）
- ZIP バイト列からの読込
- 個別ファイル（ベース名->バイト列）の読込
- ファイル名エイリアス解決

戻り値の契約:
    (pairs_kana: list[Pair], pairs_kanji: list[Pair], kimariji_df: pandas.DataFrame, rule_image_bytes: bytes)

破壊的変更: 従来の3分割CSV（hyakunin_issyu.csv / hyakunin_issyu_kanji.csv / kimariji.csv）は
サポートを終了。以後は「単一CSV + ルール画像（PNG）」のみを受け付ける。
CSV のファイル名は固定しない（内容の列ヘッダで判定する）。
"""

from __future__ import annotations

import io
import os
import tempfile
import zipfile
from collections.abc import Callable
from typing import Any  # noqa: F401  # 将来的な拡張で使用予定（インターフェイス維持）

import pandas as pd

from src.competitive_karuta_trainer.domain import Pair
from src.competitive_karuta_trainer.domain.data import load_pairs
from src.competitive_karuta_trainer.services.config_loader import (
    set_runtime_config,
    set_runtime_toml_bytes,
)
from src.competitive_karuta_trainer.services.kimariji import compute_kimariji_for_texts


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
    read_bytes: Callable[[str], bytes],
) -> tuple[dict[str, str], list[str]]:
    """ベース名->実体の辞書から、必要ファイル（CSV/PNG）を自動検出する。

    - CSV: 列ヘッダに「上の句」「下の句」「上の句（ひらがな）」「下の句（ひらがな）」を全て含むものを優先。
    - PNG: 拡張子 .png の最初の1件（任意）。

    Args:
        name_map: ベース名 -> 実体（Zip内フルパスやキー 等）
        read_bytes: 実体から bytes を読み出すコールバック（引数は実体）
    Returns:
        (resolved_map, missing_keys)
    resolved_map: {"csv": 実体, "rule": 実体?}
    missing_keys: ["csv"] だけを返す（PNG は任意のため欠如しても含めない）
    """
    csv_candidate = None
    # CSV を探索（中身を確認して判定）
    for base, real in sorted(name_map.items()):
        if not base.lower().endswith(".csv"):
            continue
        try:
            b = read_bytes(real)
            df = pd.read_csv(io.BytesIO(b))
            cols = set(df.columns)
            need = {"上の句", "下の句", "上の句（ひらがな）", "下の句（ひらがな）"}
            if need.issubset(cols):
                csv_candidate = real
                break
        except Exception:
            continue

    rule_candidate = None
    for base, real in sorted(name_map.items()):
        if base.lower().endswith(".png"):
            rule_candidate = real
            break

    resolved: dict[str, str] = {}
    missing: list[str] = []
    if csv_candidate is None:
        missing.append("csv")
    else:
        resolved["csv"] = csv_candidate
    if rule_candidate is not None:
        resolved["rule"] = rule_candidate
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
) -> tuple[list[Pair], list[Pair], pd.DataFrame, bytes | None]:
    """Zip バイト列からデータセットを読み込む（単一CSV + PNG を自動検出）。"""
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        name_map = _zip_members_by_basename(zf)
        resolved, missing_keys = resolve_required_files(
            name_map, read_bytes=lambda member: zf.read(member)
        )
        if missing_keys:
            # CSV は必須、PNG は任意
            raise ValueError("Zip に必要ファイルが不足しています: " + ", ".join(missing_keys))

        with zf.open(resolved["csv"]) as f:
            df = pd.read_csv(io.BytesIO(f.read()))
        # かな・漢字を明示列指定で抽出（重複列名の混入を防ぐ）
        kana_src_cols = [c for c in ("上の句（ひらがな）", "下の句（ひらがな）") if c in df.columns]
        if len(kana_src_cols) != 2:
            raise ValueError(
                "CSV に『上の句（ひらがな）』『下の句（ひらがな）』列が見つかりません。"
            )
        kana_df = df[kana_src_cols].rename(
            columns={"上の句（ひらがな）": "上の句", "下の句（ひらがな）": "下の句"}
        )
        kanji_src_cols = [c for c in ("上の句", "下の句") if c in df.columns]
        if len(kanji_src_cols) != 2:
            raise ValueError("CSV に『上の句』『下の句』列が見つかりません。")
        kanji_df = df[kanji_src_cols]
        # 決まり字（上の句かな）を算出して df に付与
        if "上の句（ひらがな）" in df.columns:
            km_df = compute_kimariji_for_texts(
                df["上の句（ひらがな）"].tolist(), original_label="上の句（ひらがな）"
            )
            if len(km_df) == len(df):
                df = df.copy()
                df["_決まり字"] = km_df["決まり字"].values
        # CSV バイト化して既存ロジックに通す
        kana_csv = kana_df.to_csv(index=False).encode("utf-8")
        kanji_csv = kanji_df.to_csv(index=False).encode("utf-8")
        kana_pairs = _read_pairs_from_bytes(kana_csv)
        kanji_pairs = _read_pairs_from_bytes(kanji_csv)
        # Tips は「ひらがな」の上の句/下の句をベースに作成し、id で参照できるようにする
        tips_src_cols = [c for c in ("上の句（ひらがな）", "下の句（ひらがな）") if c in df.columns]
        has_hint = "ヒント" in df.columns
        if has_hint:
            tips_src_cols.append("ヒント")
        kimariji_df = (
            df[tips_src_cols]
            .rename(
                columns={
                    "上の句（ひらがな)": "上の句",
                    "上の句（ひらがな）": "上の句",
                    "下の句（ひらがな)": "下の句",
                    "下の句（ひらがな）": "下の句",
                }
            )
            .copy()
            if tips_src_cols
            else pd.DataFrame()
        )
        if not kimariji_df.empty:
            # kana_pairs と同じ並びなので 0..N-1 を id として付与
            kimariji_df.insert(0, "id", list(range(len(kimariji_df))))
        if "_決まり字" in df.columns and not kimariji_df.empty:
            kimariji_df = kimariji_df.copy()
            kimariji_df["決まり字"] = df["_決まり字"].values

        rule_img_bytes: bytes | None = None
        if "rule" in resolved:
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
) -> tuple[list[Pair], list[Pair], pd.DataFrame, bytes | None]:
    """個別ファイル（ベース名->バイト列）からデータセットを読み込む（単一CSV + PNG を自動検出）。"""
    resolved, missing_keys = resolve_required_files(
        {k: k for k in by_name_bytes.keys()}, read_bytes=lambda k: by_name_bytes[k]
    )
    if missing_keys:
        # CSV は必須、PNG は任意
        raise ValueError("不足ファイル: " + ", ".join(missing_keys))

    df = pd.read_csv(io.BytesIO(by_name_bytes[resolved["csv"]]))
    kana_src_cols = [c for c in ("上の句（ひらがな）", "下の句（ひらがな）") if c in df.columns]
    if len(kana_src_cols) != 2:
        raise ValueError("CSV に『上の句（ひらがな）』『下の句（ひらがな）』列が見つかりません。")
    kana_df = df[kana_src_cols].rename(
        columns={"上の句（ひらがな）": "上の句", "下の句（ひらがな）": "下の句"}
    )
    kanji_src_cols = [c for c in ("上の句", "下の句") if c in df.columns]
    if len(kanji_src_cols) != 2:
        raise ValueError("CSV に『上の句』『下の句』列が見つかりません。")
    kanji_df = df[kanji_src_cols]
    # 決まり字（上の句かな）
    if "上の句（ひらがな）" in df.columns:
        km_df = compute_kimariji_for_texts(
            df["上の句（ひらがな）"].tolist(), original_label="上の句（ひらがな）"
        )
        if len(km_df) == len(df):
            df = df.copy()
            df["_決まり字"] = km_df["決まり字"].values
    kana_csv = kana_df.to_csv(index=False).encode("utf-8")
    kanji_csv = kanji_df.to_csv(index=False).encode("utf-8")
    kana = _read_pairs_from_bytes(kana_csv)
    kanji = _read_pairs_from_bytes(kanji_csv)
    # Tips（かな基準 + id 付与）
    tips_src_cols = [c for c in ("上の句（ひらがな）", "下の句（ひらがな）") if c in df.columns]
    if "ヒント" in df.columns:
        tips_src_cols.append("ヒント")
    tips_df = (
        df[tips_src_cols]
        .rename(
            columns={
                "上の句（ひらがな)": "上の句",
                "上の句（ひらがな）": "上の句",
                "下の句（ひらがな)": "下の句",
                "下の句（ひらがな）": "下の句",
            }
        )
        .copy()
        if tips_src_cols
        else pd.DataFrame()
    )
    if not tips_df.empty:
        tips_df.insert(0, "id", list(range(len(tips_df))))
    if "_決まり字" in df.columns and not tips_df.empty:
        tips_df = tips_df.copy()
        tips_df["決まり字"] = df["_決まり字"].values

    rule_img: bytes | None = None
    if "rule" in resolved:
        rule_img = by_name_bytes[resolved["rule"]]

    if not kana or not kanji:
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
