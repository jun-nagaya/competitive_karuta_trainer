from __future__ import annotations

import pathlib
import re
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class Pair:
    """札のペア（上の句/下の句）。

    現状の契約:
    - id: 0 始まりの連番（読み込み順）
    - kami: 上の句（簡易正規化済み）
    - shimo: 下の句（簡易正規化済み）
    """

    id: int
    kami: str  # 上の句
    shimo: str  # 下の句


def _normalize_text(s: str) -> str:
    """軽量な正規化を行う。

    - 全角スペースを半角に変換
    - 連続空白を1つに圧縮
    - 前後空白を除去
    - 句読点は保持する
    """
    if s is None:
        return ""
    # 全角スペース→半角
    s = s.replace("　", " ")
    # 前後空白トリム
    s = s.strip()
    # 連続空白を単一空白に
    s = re.sub(r"\s+", " ", s)
    return s


def load_pairs(csv_path: str | pathlib.Path) -> list[Pair]:
    """CSV から (id, 上の句, 下の句) を読み込み、正規化した `Pair` のリストを返す。

    契約:
    - 入力: ローカルパスまたは http(s) URL を受け付ける。
    - 想定カラム: 上の句, 下の句（列名の前後空白は無視）
    - 欠損や2列未満の行はスキップ
    - 重複 (kami, shimo) は1件に統合
    - 文字コードは UTF-8 を想定
    """
    src = str(csv_path)
    is_url = src.startswith("http://") or src.startswith("https://")
    path = pathlib.Path(src) if not is_url else None
    if not is_url:
        assert path is not None
        if not path.exists():
            raise FileNotFoundError(f"CSV not found: {path}")

        # engine='python' は区切りゆらぎへの寛容度が高い
        df = pd.read_csv(path, header=0, sep=",", engine="python", dtype=str, encoding="utf-8")
    else:
        # URL から直接読み込む
        df = pd.read_csv(src, header=0, sep=",", engine="python", dtype=str, encoding="utf-8")
    # カラム名の空白を除去
    df.rename(columns={c: c.strip() for c in df.columns}, inplace=True)

    # 列名の候補に対応
    col_kami = next((c for c in df.columns if c.replace(" ", "") in ("上の句", "上の句")), None)
    col_shimo = next((c for c in df.columns if c.replace(" ", "") in ("下の句", "下の句")), None)
    if col_kami is None or col_shimo is None:
        # 列名が判別できない場合は先頭2列を使う
        if len(df.columns) >= 2:
            col_kami, col_shimo = df.columns[:2]
        else:
            raise ValueError("CSV の列が不足しています（上の句/下の句）。")

    records: list[Pair] = []
    seen: set[tuple[str, str]] = set()
    # まずは標準CSV解釈の行から作成
    for _, row in df.iterrows():
        kami_raw = row.get(col_kami)
        shimo_raw = row.get(col_shimo)
        if pd.isna(kami_raw) or pd.isna(shimo_raw):
            # 列が欠損している行はスキップ
            continue
        kami = _normalize_text(str(kami_raw))
        shimo = _normalize_text(str(shimo_raw))
        if not kami or not shimo:
            continue
        key = (kami, shimo)
        if key in seen:
            continue
        seen.add(key)
        records.append(Pair(id=len(records), kami=kami, shimo=shimo))

    # 追加のフォールバック: 行テキストを直接読み、区切りが「,」で無い場合は最初の「、」で分割
    # 既存の records に無いものを補完
    # URL の場合は生テキスト読取のフォールバックは実施しない
    data_lines: list[str] = []
    if not is_url:
        assert path is not None
        with path.open("r", encoding="utf-8") as f:
            lines = f.read().splitlines()
        if lines:
            # ヘッダーをスキップ
            data_lines = lines[1:]

    for line in data_lines:
        if not line.strip():
            continue
        # 既にCSVで読めている行はほぼ同一だが、安全のため同じロジックで正規化
        if "," in line:
            parts = line.split(",", 1)
        elif "、" in line:
            parts = line.split("、", 1)
        else:
            continue
        if len(parts) != 2:
            continue
        kami = _normalize_text(parts[0])
        shimo = _normalize_text(parts[1])
        if not kami or not shimo:
            continue
        key = (kami, shimo)
        if key in seen:
            continue
        seen.add(key)
        records.append(Pair(id=len(records), kami=kami, shimo=shimo))

    if not records:
        raise ValueError("CSV から有効な上の句/下の句ペアを読み込めませんでした。")

    return records


def index_by_id(pairs: list[Pair]) -> dict[int, Pair]:
    """`Pair` の id をキーにした辞書を作成して返す。"""
    return {p.id: p for p in pairs}
