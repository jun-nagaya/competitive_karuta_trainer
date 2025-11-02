"""Streamlit セッション状態アダプタ。

目的:
- UI 層でのみ `st.session_state` を扱うための薄い抽象を提供する。
- アプリ層ポート `SessionStore` の実装を提供する。

使い方:
- UI コードで `StSessionStore` を生成し、サービス関数へ渡す。
"""

from __future__ import annotations

from typing import Any

from src.competitive_karuta_trainer.app.ports.session_store import SessionStore


class StSessionStore(SessionStore):
    """Streamlit 実装の SessionStore。"""

    def get(self, key: str, default: Any = None) -> Any:  # noqa: ANN401 - UI 橋渡しのため Any 許容
        import streamlit as st

        return st.session_state.get(key, default)

    def set(self, key: str, value: Any) -> None:  # noqa: ANN401 - UI 橋渡しのため Any 許容
        import streamlit as st

        st.session_state[key] = value
