"""
決まり字（最短識別接頭辞）の算出サービス。

目的:
- かなデータ（`Pair` のリスト）から、各札の下の句に対する最短の一意接頭辞（決まり字）を算出する。

契約:
- 入力は「かな」の `Pair` リスト（`Pair.kami`/`Pair.shimo` にひらがなが入っている想定）。
- 下の句を対象とし、空白や句読点は決まり字判定から除外する（UI 上の強調のために原文側の位置も返す）。
- 出力は `pandas.DataFrame` で、少なくとも以下の列を持つ。
    - id: int
    - 下の句（ひらがな）: str  … 入力の原文（正規化後）
    - 決まり字: str  … 空白・句読点を除いた最短一意接頭辞
    - 決まり字（文字数）: int  … 決まり字の文字数（上記と同じ基準）
    - 決まり字（原文末位置）: int  … 原文におけるハイライト終端の文字位置（0-origin, Python のスライス終端）

使い方:
- `compute_kimariji_df(pairs_kana)` を呼び出して `DataFrame` を取得する。
"""

from __future__ import annotations

import re
from collections.abc import Iterable

import pandas as pd

from src.competitive_karuta_trainer.domain.data import Pair

_PUNCTUATION_PATTERN = re.compile(r"[\s、。．，,。！？!？『』「」（）()・·…‥]+")


def _strip_for_kimariji(s: str) -> str:
    """決まり字判定用に空白・主要な句読点を除去する。"""
    if not s:
        return ""
    return _PUNCTUATION_PATTERN.sub("", s)


def _original_prefix_end_index(original: str, required_len: int) -> int:
    """原文文字列において、空白・句読点を除外したカウントで `required_len` 文字に達する終端位置を返す。

    例: original="あ き の", required_len=2 → 'あ','き' で 2 文字、'き' の直後のインデックスを返す。
    original の長さ未満で required_len に達しない場合は len(original) を返す。
    """
    if required_len <= 0:
        return 0
    cnt = 0
    for i, ch in enumerate(original):
        if _PUNCTUATION_PATTERN.match(ch):
            continue
        cnt += 1
        if cnt >= required_len:
            return i + 1
    return len(original)


def _compute_unique_lengths(stripped_list: list[str]) -> list[int]:
    """除外済み文字列群に対する最短一意接頭辞の長さを返す（各要素ごと）。"""
    uniq_len: list[int] = [0] * len(stripped_list)
    for i, s in enumerate(stripped_list):
        if not s:
            uniq_len[i] = 0
            continue
        n = 1
        while n <= len(s):
            prefix = s[:n]
            conflict = False
            for j, t in enumerate(stripped_list):
                if i == j:
                    continue
                if t.startswith(prefix):
                    conflict = True
                    break
            if not conflict:
                uniq_len[i] = n
                break
            n += 1
        if uniq_len[i] == 0:
            uniq_len[i] = len(s)
    return uniq_len


def compute_kimariji_for_texts(
    original_list: Iterable[str], *, original_label: str
) -> pd.DataFrame:
    """原文文字列の配列から決まり字情報を算出し、DataFrame を返す。

    Args:
        original_list: 元の文字列（スペース・句読点を含む）。
        original_label: 返却列での元文の列名（例: "上の句（ひらがな）"）。
    Returns:
        DataFrame（列: original_label, 決まり字, 決まり字（文字数）, 決まり字（原文末位置））
    """
    originals = list(original_list)
    stripped_list: list[str] = [_strip_for_kimariji(s) for s in originals]
    uniq_len = _compute_unique_lengths(stripped_list)
    rows: list[dict[str, object]] = []
    for original, klen in zip(originals, uniq_len, strict=True):
        end_pos = _original_prefix_end_index(original, klen)
        kimari_original = original[:end_pos]
        rows.append(
            {
                original_label: original,
                "決まり字": kimari_original,
                "決まり字（文字数）": klen,
                "決まり字（原文末位置）": end_pos,
            }
        )
    return pd.DataFrame(rows)


def compute_kimariji_df(pairs_kana: Iterable[Pair]) -> pd.DataFrame:
    """かな `Pair` 群から（下の句に対する）決まり字情報を算出して返す。"""
    pairs = list(pairs_kana)
    original_list: list[str] = [p.shimo for p in pairs]
    df = compute_kimariji_for_texts(original_list, original_label="下の句（ひらがな）")
    # id 付与（入力順に対応）
    df.insert(0, "id", [p.id for p in pairs])
    return df
