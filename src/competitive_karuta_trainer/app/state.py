"""アプリケーションの状態モデル定義。

目的:
- UI とドメインの境界で用いる明示的な状態構造を提供する。
- サービス層は AppState を入力・出力し、副作用を局所化する。

使い方:
- UI でセッションから AppState を復元し描画に渡す。
- ユーザー操作はサービス関数に渡し、新しい AppState を受け取って保存する。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.competitive_karuta_trainer.domain import Grid, Pair


@dataclass
class Settings:
    """画面構成や動作に関する設定。

    現状の契約:
    - rows/cols は盤面の初期行・列数を表す。
    - muted は音声再生のミュート状態を示す。
    """

    rows: int = 5
    cols: int = 4
    muted: bool = False


@dataclass
class AppState:
    """アプリケーション全体の状態。

    現状の契約:
    - pairs/pairs_by_id は問題データを保持する。
    - deck は残り札の ID 群を保持する。
    - grid は盤面の配置を表す。
    - target_id は現在のターゲット札 ID。
    - autoplay_at は自動再生の予定時刻（epoch 秒）。
    - card_times はカード別の所要時間ログ。
    - settings は現在有効な UI 設定を保持する。
    """

    # データ
    pairs: list[Pair] = field(default_factory=list)
    pairs_by_id: dict[int, Pair] = field(default_factory=dict)

    # 盤面
    deck: list[int] = field(default_factory=list)
    grid: Grid | None = None
    active_rows: int = 5
    active_cols: int = 4

    # 進行
    target_id: int | None = None
    score: int = 0
    miss: int = 0

    # オーディオ/ストリーミング
    muted: bool = False
    autoplay_at: float | None = None  # epoch seconds
    last_streamed_target_id: int | None = None

    # 計時/記録
    timing_started: bool = False
    target_started_at: float | None = None
    card_times: dict[int, list[float]] = field(default_factory=dict)

    # 設定
    settings: Settings = field(default_factory=lambda: _load_settings_from_text())

    def __post_init__(self) -> None:
        """設定デフォルトの反映（初期 active_* を Settings に同期）。"""
        # active_rows/cols がクラス既定値から変わっていない場合のみ同期
        if self.active_rows == 5:
            self.active_rows = self.settings.rows
        if self.active_cols == 4:
            self.active_cols = self.settings.cols


def _load_settings_from_text() -> Settings:
    """外部テキストから Settings を読み込む（フォールバックあり）。"""
    try:
        from src.competitive_karuta_trainer.services.config_loader import load_default_settings

        return load_default_settings()
    except Exception:
        # 何らかの読み込み失敗時はコード既定値
        return Settings()
