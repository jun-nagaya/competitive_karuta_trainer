## 百人一首トレーナー

競技かるた（小倉百人一首）の学習・練習用 Streamlit アプリです。試合で迷いやすい同頭の混同候補と、どこまで読めば確定するかの「判定」を Tips に明示しています。

### 必要環境

- Python 3.11 以上
- macOS / Linux / Windows いずれも可

### すぐ使う（推奨: uv）

1) uv を入れる（未導入の場合）: https://docs.astral.sh/uv/getting-started/installation/

2) 依存を同期（ロックに従い高速セットアップ）

```bash
uv sync
```

3) 起動

```bash
uv run streamlit run main.py
```

（uv を使わない場合は、任意の仮想環境を作成し必要パッケージをインストールしてから `streamlit run main.py`）

### データ（CSV / ルール画像の取り込み）

- アップロードする ZIP の中に、次を含められます。
	- 必須: 1つの CSV（ヘッダ行に「上の句」「下の句」「上の句（ひらがな）」「下の句（ひらがな）」を含む）
	- 任意: ルール画像（PNG）
	- 任意: `config.toml`（下記設定を同梱可能）
- CSV のファイル名は固定ではなく、ヘッダ列で自動判定します（UTF-8 推奨）。
- 列「ヒント」は任意です。あれば Tips に表示します（推奨書式: 「混同候補: …。判定:『…』までで確定（n音）。」）。

最小スキーマ例:

```csv
id,上の句,下の句,上の句（ひらがな）,下の句（ひらがな）,ヒント
0,秋の田の かりほの庵の 苫をあらみ,わが衣手は 露にぬれつつ,あきのたの かりほのいほの とまをあらみ,わがころもでは つゆにぬれつつ,混同候補:『あき…』系。判定:『あきの』までで確定（3音）。
```

単品アップロードにも対応しています（CSV と PNG を個別にアップロード）。ZIP 利用を推奨します。

### 設定（TOML）

アプリ上で `config.toml` をアップロードするとタイトルやサブテキスト、盤面設定を切り替えられます。未指定は既定値で動作します。

```toml
title = "百人一首"

[pages]
tips_subheader = "決まり字などの一覧です。"
official_rule_subheader = "競技かるたの公式ルール参考画像です。"

[settings]
rows = 5
cols = 4
muted = false
sample = 30
```

### 開発メモ（任意）

```bash
# フォーマット / Lint
uv run ruff format .
uv run ruff check .

# 型チェック
uv run mypy src/

# テスト
uv run pytest -q
```

主要ディレクトリ：

- `src/competitive_karuta_trainer/app/entrypoint.py` … 画面オーケストレーション
- `src/competitive_karuta_trainer/services/` … 非 UI ロジック（ゲーム進行・データ・音声 等）
- `src/competitive_karuta_trainer/ui/` … 表示・入力コンポーネント
- `pages/` … 補助ページ（公式ルール、Tips）


