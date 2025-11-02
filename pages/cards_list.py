import html

import pandas as pd
import streamlit as st

from src.competitive_karuta_trainer.services.config_loader import get_tips_subheader_text

# ページ設定
st.set_page_config(page_title="Tips", layout="wide")
st.title("Tips")
st.caption(get_tips_subheader_text())

# まずはセッションからデータセットを参照（ZIP/個別で読み込まれている場合）
df = st.session_state.get("kimariji_df")

if df is None:
    st.info(
        "『決まり字』CSV をアップロードするか、トップページで ZIP/個別ファイルからデータセットを読み込んでください。"
    )
    up = st.file_uploader("決まり字 CSV をアップロード", type=["csv"], accept_multiple_files=False)
    if not up:
        st.stop()
    try:
        df = pd.read_csv(up)
    except Exception as e:
        st.error(f"CSVの読み込みに失敗しました: {e}")
        st.stop()

# 表示前の前処理
drop_cols = [c for c in ["id", "長さ"] if c in df.columns]
if drop_cols:
    df = df.drop(columns=drop_cols)

if "優先度" in df.columns:
    _order_map = {"高": 0, "中": 1, "低": 2}
    sort_key = df["優先度"].map(_order_map).fillna(99)
    df = (
        df.assign(_優先度順=sort_key)
        .sort_values(["_優先度順", "決まり字"], ascending=[True, True])
        .drop(columns=["_優先度順", "優先度"])
    )
# 並び順: 決まり字の長さ（非空白の文字数）が長いほど上、その上で五十音順（上の句）
if "決まり字" in df.columns:

    def _count_nonspace(x: object) -> int:
        s = str(x) if isinstance(x, str) else ""
        return sum(1 for ch in s if not ch.isspace())

    df = (
        df.assign(_len=df["決まり字"].apply(_count_nonspace))
        .sort_values(["_len", "上の句"], ascending=[False, True])
        .drop(columns=["_len"], errors="ignore")
    )
else:
    # 決まり字がなければ五十音順（上の句）のみ
    if "上の句" in df.columns:
        df = df.sort_values(["上の句"])


# --- カスタムHTMLテーブルで表示 ---
def _esc(x: object) -> str:
    """HTMLエスケープ（None対応）"""
    return html.escape(x if isinstance(x, str) else "")


def _render_upper(upper: object, key: object) -> str:
    """上の句の先頭（決まり字の長さ＝非空白文字数）までを赤字で表示する。
    - スペースは上の句の表記を維持し、カウントには含めない。
    """
    text = upper if isinstance(upper, str) else ""
    k = key if isinstance(key, str) else ""
    if not text or not k:
        return _esc(text)
    target = sum(1 for ch in k if not ch.isspace())
    cnt = 0
    prefix_chars: list[str] = []
    suffix_chars: list[str] = []
    for ch in text:
        if cnt < target:
            prefix_chars.append(ch)
            if not ch.isspace():
                cnt += 1
        else:
            suffix_chars.append(ch)
    prefix = _esc("".join(prefix_chars))
    suffix = _esc("".join(suffix_chars))
    return f'<span class="upper-prefix">{prefix}</span>{suffix}'


display_cols = [c for c in ["上の句", "下の句", "ヒント"] if c in df.columns]
width_map = {"上の句": "32%", "下の句": "32%", "ヒント": "36%"}

css = """
<style>
  table.table-cards { table-layout: fixed; width: 100%; border-collapse: collapse; }
  .table-cards th, .table-cards td { border: 1px solid #eee; padding: 6px 8px; vertical-align: top; font-size: 0.95rem; }
  .table-cards th { background: #fafafa; }
  .table-cards .upper-prefix { color: #d00; font-weight: 600; }
  .table-cards th, .table-cards td { word-break: break-word; overflow-wrap: anywhere; }
</style>
"""

parts: list[str] = [css, '<table class="table-cards">']
parts.append("<colgroup>")
for c in display_cols:
    parts.append(f'<col style="width:{width_map.get(c, "auto")}">')
parts.append("</colgroup>")

parts.append("<thead><tr>")
for c in display_cols:
    parts.append(f"<th>{_esc(c)}</th>")
parts.append("</tr></thead>")

parts.append("<tbody>")
for _, row in df.iterrows():
    parts.append("<tr>")
    for c in display_cols:
        if c == "上の句" and "決まり字" in df.columns:
            cell_html = _render_upper(row.get("上の句"), row.get("決まり字"))
        else:
            cell_html = _esc(row.get(c))
        parts.append(f"<td>{cell_html}</td>")
    parts.append("</tr>")
parts.append("</tbody></table>")

st.markdown("".join(parts), unsafe_allow_html=True)
