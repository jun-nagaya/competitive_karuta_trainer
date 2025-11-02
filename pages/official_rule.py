"""
公式ルールページ
- セッション内の画像（ZIP/個別で読み込まれたもの）があれば表示します。
- 画像が無い場合は何も表示せず、ページ（タイトル・キャプション）のみを示します。
"""

import base64

import streamlit as st

from src.competitive_karuta_trainer.services.config_loader import get_official_rule_subheader_text

# ページ設定
st.set_page_config(page_title="公式ルール", layout="wide")
st.title("公式ルール")
st.caption(get_official_rule_subheader_text())

img_bytes: bytes | None = st.session_state.get("rule_image_bytes")

if img_bytes is None:
    # 画像が無い場合はなにも表示しない（ページ遷移は可能）
    st.stop()

try:
    b64 = base64.b64encode(img_bytes).decode("utf-8")
    html = f"""
    <div style="width:100%; display:flex; justify-content:center;">
        <img src="data:image/*;base64,{b64}" alt="公式ルール"
             style="height:95vh; max-width:100%; width:auto; object-fit:contain;" />
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
except Exception as e:
    st.error(f"画像の読み込みに失敗しました: {e}")
