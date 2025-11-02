from __future__ import annotations

import html
import math
import uuid

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from src.competitive_karuta_trainer.domain import Pair


def render_status_and_results(target: Pair | None) -> None:
    """ステータス（残り・ミス）と終了時の結果を描画する。

    Args:
        target: 現在のターゲット。None の場合は結果表示を行う。
    """
    # このゲームの総枚数（サブセットがあればその枚数、未開始時は設定値）
    active_ids = st.session_state.get("active_pair_ids")
    planned_total = int(
        st.session_state.get("settings", {}).get("samples", len(st.session_state.pairs))
    )
    total = len(active_ids) if active_ids else planned_total
    remaining_total = max(0, total - st.session_state.score)
    c1, c2 = st.columns(2)
    with c1:
        st.metric("残り", f"{remaining_total}/{total}")
    with c2:
        st.metric("ミス", st.session_state.miss)

    if target is not None:
        return

    st.info("お疲れさまでした！ すべての札を取り終えました。")
    # 計測結果（今回のみ）
    if st.session_state.get("timing_started") and st.session_state.get("game_started_at"):
        st.subheader("計測結果")
        times: dict[int, list[float]] = st.session_state.card_times or {}
        # 今回の1枚あたり時間（このゲーム中の単回計測）
        durations: list[tuple[float, int]] = []  # (sec, pair_id)
        for pid, arr in times.items():
            if arr:
                durations.append((float(arr[-1]), pid))
        total_sec = sum(d for d, _ in durations)
        mm = int(total_sec // 60)
        ss = int(total_sec % 60)
        st.metric("総時間", f"{mm:02d}:{ss:02d}")
        if durations:
            n = len(durations)
            avg_per_card = sum(d for d, _ in durations) / n
            st.metric("平均/札", f"{avg_per_card:.2f}s")
            # 下位10%（遅い方）のみを苦手と判定
            k = max(1, math.ceil(n * 0.10))
            durations.sort(key=lambda x: x[0], reverse=True)
            weak = durations[:k]
            if weak:
                st.markdown("**苦手な札（下位10%）**")
                for sec, pid in weak:
                    p = _get_pair(pid)
                    if not p:
                        continue
                    st.write(f"• 『{p.kami}』→『{p.shimo}』 {sec:.2f}s")
            # ミスした札（降順・すべて表示）
            misses: dict[int, int] = st.session_state.get("card_misses", {})
            miss_rows = [(cnt, pid) for pid, cnt in misses.items() if cnt and cnt > 0]
            if miss_rows:
                miss_rows.sort(reverse=True, key=lambda x: x[0])
                st.markdown("**ミスした札**")
                for cnt, pid in miss_rows:
                    p = _get_pair(pid)
                    if not p:
                        continue
                    st.write(f"• 『{p.kami}』→『{p.shimo}』 ミス {cnt}回")
            # 全札の取得時間（今回使用した全札を対象）
            st.markdown("**各札の取得時間**")
            # ヒント参照（まず id をキーに、互換用に句ベースも作成）
            tips_df = st.session_state.get("kimariji_df")
            hint_by_kami: dict[str, str] = {}
            hint_by_shimo: dict[str, str] = {}
            hint_by_id: dict[int, str] = {}
            try:
                if isinstance(tips_df, pd.DataFrame) and "ヒント" in tips_df.columns:
                    if "id" in tips_df.columns:
                        for _id, h in zip(tips_df["id"], tips_df["ヒント"], strict=False):  # type: ignore[arg-type]
                            try:
                                pid = int(_id)
                            except Exception:
                                continue
                            hv = str(h).strip()
                            if hv and hv != "-":
                                hint_by_id[pid] = hv
                    for col, dst in (("上の句", hint_by_kami), ("下の句", hint_by_shimo)):
                        if col in tips_df.columns:
                            for k, h in zip(tips_df[col], tips_df["ヒント"], strict=False):  # type: ignore[arg-type]
                                hv = str(h).strip()
                                if hv and hv != "-":
                                    dst[str(k)] = hv
            except Exception:
                hint_by_kami = {}
                hint_by_shimo = {}
                hint_by_id = {}

            # 今回のゲームで使用した全ID
            active_ids: list[int] | None = st.session_state.get("active_pair_ids")
            if active_ids is None:
                active_ids = [p.id for p in st.session_state.pairs]  # type: ignore[attr-defined]
            times_map: dict[int, list[float]] = st.session_state.card_times or {}
            all_durations: list[tuple[float | None, int]] = []
            for pid in active_ids:
                arr = times_map.get(pid)
                sec_val: float | None = float(arr[-1]) if arr and len(arr) > 0 else None
                all_durations.append((sec_val, pid))
            # 計測あり→降順、未計測は末尾
            all_durations.sort(key=lambda x: (x[0] is None, -(x[0] if x[0] is not None else 0.0)))

            _render_results_table_with_inline_hints(
                all_durations,
                tips_df if isinstance(tips_df, pd.DataFrame) else None,
                hint_by_kami,
                hint_by_shimo,
                hint_by_id,
            )

            # （以前の「ヒント（今回の札のみ）」エクスパンダは簡潔化のため削除）


def _get_pair(pair_id: int | None) -> Pair | None:
    if pair_id is None:
        return None
    return st.session_state.pairs_by_id.get(pair_id)


def _esc(x: object) -> str:
    """HTMLエスケープ（None対応）

    Args:
        x: 任意の値。
    Returns:
        エスケープ済み文字列。
    """
    return html.escape(x if isinstance(x, str) else "")


def _render_upper(upper: object, key: object) -> str:
    """上の句の先頭（決まり字の長さ＝非空白文字数）までを赤字で表示する。

    - スペースは上の句の表記を維持し、カウントには含めない。
    Args:
        upper: 上の句テキスト。
        key: 決まり字テキスト。
    Returns:
        強調表示済みのHTML文字列。
    """
    text = upper if isinstance(upper, str) else ""
    k = key if isinstance(key, str) else ""
    if not text or not k:
        return _esc(text)
    target = len(k)  # 非空白の文字数でカウント
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


def _render_results_table_with_inline_hints(
    durations: list[tuple[float | None, int]],
    tips_df: pd.DataFrame | None,
    hint_by_kami: dict[str, str],
    hint_by_shimo: dict[str, str],
    hint_by_id: dict[int, str] | None = None,
) -> None:
    """「各札の取得時間」表をHTMLで描画し、ヒント列のリンクでTipsの一部をポップオーバー表示する。

    - ヒントをクリックすると、Tipsテーブルから該当行周辺のみを切り出した内容を
      画面内にポップオーバーとして表示する。
    - ポップオーバーはクリック位置付近に表示され、ウィンドウ端で折り返される。
    """
    # 列定義
    css = """
    <style>
      .res-wrap { max-height: 460px; overflow: auto; border: 1px solid #eee; border-radius: 4px; }
      .res-table { table-layout: fixed; width: 100%; border-collapse: collapse; }
      .res-table th, .res-table td { border: 1px solid #eee; padding: 6px 8px; vertical-align: top; font-size: 0.95rem; }
      .res-table th { background: #fafafa; position: sticky; top: 0; z-index: 1; }
      .res-table .hint-cell a { margin-left: 0; text-decoration: underline; }
    </style>
    """
    parts: list[str] = [css, '<div class="res-wrap">', '<table class="res-table">']
    parts.append("<colgroup>")
    parts.append('<col style="width:28%">')  # 上の句
    parts.append('<col style="width:28%">')  # 下の句
    parts.append('<col style="width:12%">')  # 時間
    parts.append('<col style="width:32%">')  # ヒント
    parts.append("</colgroup>")
    parts.append(
        "<thead><tr><th>上の句</th><th>下の句</th><th>時間(s)</th><th>ヒント</th></tr></thead>"
    )
    parts.append("<tbody>")

    # 行とオーバーレイに使うコンテンツを準備
    contents: dict[str, str] = {}
    for sec, pid in durations:
        p = _get_pair(pid)
        if not p:
            continue
        hint_val = None
        if isinstance(tips_df, pd.DataFrame):
            # id があれば最優先で使用（句の重複による取りこぼし防止）
            if hint_by_id and pid in hint_by_id:
                hint_val = hint_by_id.get(pid)
            else:
                hint_val = hint_by_kami.get(p.kami) or hint_by_shimo.get(p.shimo)
        parts.append("<tr>")
        parts.append(f"<td>{_esc(p.kami)}</td>")
        parts.append(f"<td>{_esc(p.shimo)}</td>")
        parts.append(f"<td>{('-' if sec is None else f'{sec:.2f}')}</td>")
        if hint_val and isinstance(tips_df, pd.DataFrame):
            _id = f"h{pid}"
            contents[_id] = _build_tips_window_html(
                tips_df, focus_upper=p.kami, focus_lower=p.shimo, focus_id=pid, window=20
            )
            parts.append(
                f'<td class="hint-cell"><a href="#" class="hint-link" data-id="{_id}">{_esc(hint_val)}</a></td>'
            )
        else:
            parts.append("<td>-</td>")
        parts.append("</tr>")
    parts.append("</tbody></table></div>")
    # オーバーレイと隠しコンテンツ
    overlay = _build_triggers_with_popover_html(contents)
    parts.append(overlay)
    components.html("".join(parts), height=520, width=1440, scrolling=False)


def _build_tips_window_html(
    tips_df: pd.DataFrame,
    *,
    focus_upper: str | None,
    focus_lower: str | None,
    focus_id: int | None = None,
    window: int = 20,
) -> str:
    """ヒントのウィンドウ用HTMLを構築して返す（描画は呼び出し側）。

    Returns:
        HTML 文字列。
    """
    # 既存ロジックを流用してサブテーブルを作成
    if not isinstance(tips_df, pd.DataFrame) or tips_df.empty:
        return "<div>Tips がありません。</div>"
    df = tips_df.copy()
    # 並び順: 決まり字の長さ（非空白文字数）が長いほど上、その上で五十音順（上の句）
    if "決まり字" in df.columns:

        def _count_nonspace(x: object) -> int:
            s = str(x) if isinstance(x, str) else ""
            return sum(1 for ch in s if not ch.isspace())

        df = (
            df.assign(_len=df["決まり字"].apply(_count_nonspace))
            .sort_values(["_len", "上の句"], ascending=[False, True])
            .drop(columns=["_len"], errors="ignore")
        )
    elif "上の句" in df.columns:
        df = df.sort_values(["上の句"])  # 決まり字がない場合のフォールバック
    df = df.reset_index(drop=True)
    match_idx = None
    # id があれば id を最優先
    if focus_id is not None and "id" in df.columns:
        hit = df.index[df["id"] == focus_id]
        if len(hit) > 0:
            match_idx = int(hit[0])
    if match_idx is None and focus_upper and "上の句" in df.columns:
        hit = df.index[df["上の句"] == focus_upper]
        if len(hit) > 0:
            match_idx = int(hit[0])
    if match_idx is None and focus_lower and "下の句" in df.columns:
        hit = df.index[df["下の句"] == focus_lower]
        if len(hit) > 0:
            match_idx = int(hit[0])
    n = len(df)
    if match_idx is None:
        start = 0
        end = min(n, window)
    else:
        half = max(1, window // 2)
        pos = int(match_idx)
        start = max(0, min(pos - half, n - window))
        end = min(n, start + window)
    dfw = df.iloc[start:end]

    css = """
    <style>
      .tips-wrap { max-height: 420px; overflow: auto; border: 1px solid #eee; border-radius: 4px; }
      table.table-cards { table-layout: fixed; width: 100%; border-collapse: collapse; }
      .table-cards th, .table-cards td { border: 1px solid #eee; padding: 6px 8px; vertical-align: top; font-size: 0.95rem; }
      .table-cards th { background: #fafafa; position: sticky; top: 0; z-index: 1; }
      .table-cards .upper-prefix { color: #d00; font-weight: 600; }
      .table-cards tr.hl { background: #fff6e5; }
      .table-cards th, .table-cards td { word-break: break-word; overflow-wrap: anywhere; }
    </style>
    """
    display_cols = [c for c in ["上の句", "下の句", "ヒント"] if c in dfw.columns]
    width_map = {"上の句": "32%", "下の句": "32%", "ヒント": "36%"}
    wrap_id = f"tipswrap-{uuid.uuid4().hex[:8]}"
    parts: list[str] = [
        css,
        f'<div id="{wrap_id}" class="tips-wrap">',
        '<table class="table-cards">',
    ]
    parts.append("<colgroup>")
    for c in display_cols:
        parts.append(f'<col style="width:{width_map.get(c, "auto")}">')
    parts.append("</colgroup>")
    parts.append("<thead><tr>")
    for c in display_cols:
        parts.append(f"<th>{_esc(c)}</th>")
    parts.append("</tr></thead>")
    parts.append("<tbody>")
    for idx, row in dfw.iterrows():
        klass = ' class="hl"' if match_idx is not None and idx == match_idx else ""
        parts.append(f"<tr{klass}>")
        for c in display_cols:
            if c == "上の句" and "決まり字" in dfw.columns:
                cell_html = _render_upper(row.get("上の句"), row.get("決まり字"))
            else:
                cell_html = _esc(row.get(c))
            parts.append(f"<td>{cell_html}</td>")
        parts.append("</tr>")
    parts.append("</tbody></table>")
    parts.append("</div>")
    parts.append(
        """
        <script>
        (function() {
            function centerRow(wrap) {
                const row = wrap.querySelector('tr.hl');
                if (!row) return;
                const thead = wrap.querySelector('thead');
                const headerH = thead ? thead.offsetHeight : 0;
                const view = Math.max(0, wrap.clientHeight - headerH);
                let target = row.offsetTop - headerH - (view/2) + (row.offsetHeight/2);
                target = Math.max(0, Math.min(target, wrap.scrollHeight - wrap.clientHeight));
                wrap.scrollTop = target;
            }
        const wrap = document.getElementById('"""
        + wrap_id
        + """');
            if (!wrap) return;
            requestAnimationFrame(() => centerRow(wrap));
            requestAnimationFrame(() => centerRow(wrap));
            setTimeout(() => centerRow(wrap), 60);
        })();
        </script>
        """
    )
    return "".join(parts)


def _build_triggers_with_popover_html(contents: dict[str, str]) -> str:
    """ヒント用HTMLポップオーバー（アンカー表示）を構築して返す。

    Args:
        contents: id -> HTML 本文。
    Returns:
        HTML 文字列。
    """
    css = """
        <style>
            .hidden { display: none; }
            /* ポップオーバー本体 */
            .hint-popover { position: fixed; top: 0; left: 0; display: none; z-index: 9999; background: #fff; border: 1px solid #ddd; border-radius: 8px; box-shadow: 0 6px 24px rgba(0,0,0,0.25); width: min(1200px, 92vw); max-height: 82vh; overflow: hidden; }
            .hint-popover-header { display: flex; align-items: center; justify-content: space-between; padding: 8px 10px; border-bottom: 1px solid #eee; }
            .hint-popover-title { font-weight: 600; }
            .hint-popover-close { border: none; background: transparent; font-size: 20px; cursor: pointer; line-height: 1; padding: 4px 8px; }
            .hint-popover-body { padding: 8px 10px; overflow: hidden; }
            /* 内容のテーブルラッパ（流用） */
            .tips-wrap { max-height: 420px; }
        </style>
        """
    parts: list[str] = [css]
    # 隠しコンテンツ
    for _id, content_html in contents.items():
        parts.append(f'<div id="content-{_id}" class="hidden">{content_html}</div>')
    # ポップオーバー本体とスクリプト
    parts.append(
        """
                <div id="hint-popover" class="hint-popover" role="dialog" aria-modal="false">
                    <div class="hint-popover-header">
                        <div class="hint-popover-title">ヒント</div>
                        <button class="hint-popover-close" aria-label="close">×</button>
                    </div>
                    <div id="hint-popover-body" class="hint-popover-body"></div>
                </div>
                <script>
                (function(){
                    const pop = document.getElementById('hint-popover');
                    const body = document.getElementById('hint-popover-body');
                    let lastAnchor = null;

                    function clamp(v, min, max){ return Math.max(min, Math.min(v, max)); }

                    function centerRowIn(wrap){
                        const row = wrap.querySelector('tr.hl');
                        if (!row) return;
                        const thead = wrap.querySelector('thead');
                        const headerH = thead ? thead.offsetHeight : 0;
                        const view = Math.max(0, wrap.clientHeight - headerH);
                        let target = row.offsetTop - headerH - (view/2) + (row.offsetHeight/2);
                        target = Math.max(0, Math.min(target, wrap.scrollHeight - wrap.clientHeight));
                        wrap.scrollTop = target;
                        if (Math.abs(wrap.scrollTop - target) > 2 && row.scrollIntoView) {
                            row.scrollIntoView({ block: 'center' });
                        }
                    }

                    function attemptCenter(wrap, tries){
                        if (!wrap || tries <= 0) return;
                        requestAnimationFrame(()=>{
                            centerRowIn(wrap);
                            setTimeout(()=> attemptCenter(wrap, tries-1), 50);
                        });
                    }

                    function positionNear(anchor){
                        if (!anchor) return;
                        const rect = anchor.getBoundingClientRect();
                        const vw = window.innerWidth || document.documentElement.clientWidth;
                        const vh = window.innerHeight || document.documentElement.clientHeight;
                        // いったん可視化してサイズ取得
                        pop.style.display = 'block';
                        // 適度な最大サイズに収める
                        const desiredW = Math.min(1000, Math.floor(vw * 0.9));
                        pop.style.width = desiredW + 'px';
                        const pad = 8;
                        const popW = pop.offsetWidth;
                        const popH = Math.min(pop.offsetHeight || 400, Math.floor(vh * 0.82));
                        pop.style.maxHeight = popH + 'px';
                        // 基本はアンカーの真下
                        let left = clamp(rect.left, pad, vw - popW - pad);
                        let top = rect.bottom + 8;
                        // 下がはみ出る場合は上に出す
                        if (top + popH + pad > vh) {
                            top = Math.max(pad, rect.top - 8 - popH);
                        }
                        pop.style.left = left + 'px';
                        pop.style.top = top + 'px';
                    }

                    function openById(id, anchor){
                        const src = document.getElementById('content-'+id);
                        if (!src) return;
                        body.innerHTML = src.innerHTML;
                        lastAnchor = anchor || null;
                        // 表示＆位置決め
                        positionNear(anchor);
                        // 内容のハイライト行を中央付近に
                        const wrap = body.querySelector('.tips-wrap');
                        if (wrap) attemptCenter(wrap, 5);
                        // 閉じるリスナー
                        document.addEventListener('click', onDocClick, true);
                        document.addEventListener('keydown', onKeyDown);
                        // iframe外クリック（= フォーカスが外れた）でも閉じる
                        window.addEventListener('blur', onWindowBlur);
                    }

                    function close(){
                        pop.style.display = 'none';
                        body.innerHTML = '';
                        lastAnchor = null;
                        document.removeEventListener('click', onDocClick, true);
                        document.removeEventListener('keydown', onKeyDown);
                        window.removeEventListener('blur', onWindowBlur);
                    }

                    function onDocClick(e){
                        if (!pop || pop.style.display === 'none') return;
                        const target = e.target;
                        if (!pop.contains(target)) {
                            close();
                        }
                    }

                    function onKeyDown(e){ if (e.key === 'Escape') close(); }

                    function onWindowBlur(){
                        if (!pop || pop.style.display === 'none') return;
                        // 親側（Streamlit本体）へフォーカスが移ったとみなし閉じる
                        close();
                    }

                    // テーブル内リンクをバインド
                    document.querySelectorAll('.hint-link').forEach(a=>{
                        a.addEventListener('click', (e)=>{ e.preventDefault(); openById(a.getAttribute('data-id'), a); });
                    });

                    // 右上×
                    document.querySelector('.hint-popover-close').addEventListener('click', close);

                    // リサイズで再配置
                    window.addEventListener('resize', ()=>{ if (pop.style.display !== 'none' && lastAnchor) positionNear(lastAnchor); });
                })();
                </script>
                """
    )
    return "".join(parts)
