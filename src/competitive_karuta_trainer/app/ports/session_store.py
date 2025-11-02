"""
アプリケーション層のポート: セッションストア

目的:
- UI 依存の具体実装（例: Streamlit の session_state）からアプリ/サービスを切り離す。
- サービス層は本ポート（Protocol）にのみ依存する。
"""

from __future__ import annotations

from typing import Any, Protocol


class SessionStore(Protocol):
    """セッション状態へのアクセス抽象。

    契約:
    - dict 風の get/set を提供する。
    - 値の型は任意（UI/サービス間の橋渡しのため）。
    """

    def get(self, key: str, default: Any = None) -> Any:  # noqa: ANN401 - UI 橋渡しのため Any 許容
        """キーに対応する値を取得する。存在しない場合は default を返す。"""

    def set(self, key: str, value: Any) -> None:  # noqa: ANN401 - UI 橋渡しのため Any 許容
        """キーに値を設定する。"""
