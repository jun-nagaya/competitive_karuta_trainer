"""
共通定数
- コメントは現状の目的・契約・使い方のみを記載する。
"""

# ミュート時の文字ストリーミング表示の1文字あたり遅延秒
STREAMING_CHAR_DELAY: float = 0.1

# データセットに期待するファイル（論理名 -> 許容ベース名の候補リスト）
FILE_ALIASES: dict[str, list[str]] = {
    "kana": ["hyakunin_issyu.csv"],
    "kanji": ["hyakunin_issyu_kanji.csv"],
    "kimariji": ["kimariji.csv"],
    "rule": ["official_rule.png"],
}
