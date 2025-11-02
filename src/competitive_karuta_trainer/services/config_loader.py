from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING, Any


class _RuntimeStore:
    config: dict[str, Any] | None = None


_RUNTIME_STORE = _RuntimeStore()


def set_runtime_config(cfg: dict[str, Any] | None) -> None:
    """実行時（アップロード）で与えられた設定を保持する。None で解除。"""
    _RUNTIME_STORE.config = cfg if isinstance(cfg, dict) else None


def set_runtime_toml_bytes(data: bytes) -> None:
    """アップロードされた TOML バイト列から実行時設定を反映する。"""
    try:
        text = data.decode("utf-8")
        cfg = tomllib.loads(text)
        set_runtime_config(cfg if isinstance(cfg, dict) else None)
    except Exception:
        set_runtime_config(None)


def _get_config() -> dict[str, Any]:
    """現在有効な設定を返す。

    方針: デフォルトではローカルの TOML を読み込まない。
    - アップロードによって与えられたランタイム設定（_RUNTIME_CONFIG）があればそれを返す。
    - それ以外は空辞書を返し、各呼び出し側で default 値にフォールバックさせる。
    """
    if isinstance(_RUNTIME_STORE.config, dict):
        return _RUNTIME_STORE.config
    return {}


def get_app_title(default: str = "百人一首") -> str:
    cfg = _get_config()
    title = cfg.get("title")
    if isinstance(title, str) and title.strip():
        return title.strip()
    return default


def get_tips_subheader_text(default: str = "決まり字などの一覧です。") -> str:
    cfg = _get_config()
    pages = cfg.get("pages") or {}
    if isinstance(pages, dict):
        v = pages.get("tips_subheader")
        if isinstance(v, str) and v.strip():
            return v.strip()
    return default


def get_official_rule_subheader_text(default: str = "") -> str:
    cfg = _get_config()
    pages = cfg.get("pages") or {}
    if isinstance(pages, dict):
        v = pages.get("official_rule_subheader")
        if isinstance(v, str) and v.strip():
            return v.strip()
    return default


def load_default_settings_values() -> dict[str, int | bool]:
    result: dict[str, int | bool] = {}
    cfg = _get_config()
    settings = cfg.get("settings")
    if isinstance(settings, dict):
        # ゲーム設定の既定値（TOML からの読み込み）。
        # 不正な型の場合は各呼び出し側でコード既定値へフォールバックする。
        if isinstance(settings.get("samples"), int):
            result["samples"] = int(settings["samples"])
        if isinstance(settings.get("rows"), int):
            result["rows"] = int(settings["rows"])
        if isinstance(settings.get("cols"), int):
            result["cols"] = int(settings["cols"])
        if isinstance(settings.get("muted"), bool):
            result["muted"] = bool(settings["muted"])
    return result


if TYPE_CHECKING:
    from src.competitive_karuta_trainer.app.state import Settings as _SettingsType


def load_default_settings() -> _SettingsType:
    from src.competitive_karuta_trainer.app.state import Settings  # 局所インポートで循環回避

    values = load_default_settings_values()
    return Settings(
        rows=int(values.get("rows", Settings.rows)),
        cols=int(values.get("cols", Settings.cols)),
        muted=bool(values.get("muted", Settings.muted)),
    )
