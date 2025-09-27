# start.py
# ポモドーロタイマー（DBイベントログ連携＋BGMは「pomodoro_*.mp3」のみ再生）

import time
import os
from pathlib import Path

import streamlit as st
from datetime import datetime
from zoneinfo import ZoneInfo

# DB 連携（Start.py 由来の処理を踏襲）
from Stats import init_db, insert_session_start, finish_session, log_event  # :contentReference[oaicite:2]{index=2}


# --- 補助関数：フォルダ内の「pomodoro_*.mp3」だけ列挙（start.py修正版の方針を移植） --- :contentReference[oaicite:3]{index=3}
def _list_bgm_prefixed(root: Path, prefix: str = "pomodoro_") -> list[str]:
    """指定フォルダ(root)内の prefix付き .mp3 のパス文字列を返す"""
    if not root.exists():
        return []
    return [str(p) for p in sorted(root.glob(f"{prefix}*.mp3"))]


def run():
    st.set_page_config(page_title="ポモドーロ", page_icon="⏳")
    st.title("⏳ ポモドーロ・タイマー（CSSドーナツ／1秒更新＋BGM）")

    # --- DB 初期化（最初に一度でOK）
    init_db()  # :contentReference[oaicite:4]{index=4}

    USER_ID = 1  # 単一ユーザー想定

    # 1) 作業時間（25/15/5）
    minutes = st.radio(
        "作業時間を選んでください（※変更するとタイマーはリセット）",
        options=[25, 15, 5],
        index=0,
        horizontal=True,
    )
    total_sec = minutes * 60

    # 2) BGM（プレフィックス方式：pomodoro_*.mp3 のみ再生対象）
    st.subheader("BGM（任意）")
    bgm_mode = st.radio(
        "ブラウザ仕様で自動再生不可：▶ を1回押してください",
        ["なし", "フォルダのMP3から選ぶ", "MP3をアップロードする"],
        index=0,
    )

    bgm_obj = None
    search_dir = Path(".").resolve()
    BGM_PREFIX = "pomodoro_"  # ここを変えれば対象BGMのプレフィックスを変更可能

    if bgm_mode == "フォルダのMP3から選ぶ":
        mp3s = _list_bgm_prefixed(search_dir, BGM_PREFIX)
        if mp3s:
            display_names = [Path(p).name for p in mp3s]
            pick_name = st.selectbox(
                f"MP3ファイル（{BGM_PREFIX}*.mp3 のみ表示）",
                options=display_names,
                index=0,
                help=str(search_dir),
            )
            if pick_name:
                bgm_obj = str(search_dir / pick_name)
        else:
            st.info(f"このフォルダに {BGM_PREFIX}*.mp3 が見つかりません：{search_dir}")

    elif bgm_mode == "MP3をアップロードする":
        st.caption(
            f"※ ファイル名は必ず **{BGM_PREFIX}** で始めてください "
            f"（例：{BGM_PREFIX}mymusic.mp3）"
        )
        up = st.file_uploader("MP3ファイルをアップロード", type=["mp3"])
        if up is not None:
            if not up.name.startswith(BGM_PREFIX):
                st.warning(f"⚠️ ファイル名が {BGM_PREFIX} で始まっていません。")
            bgm_obj = up

    if bgm_obj:
        st.audio(bgm_obj)

    # 3) 状態（記憶）
    if "running" not in st.session_state:
        st.session_state.running = False
    if "remaining" not in st.session_state:
        st.session_state.remaining = total_sec
    if "target_end" not in st.session_state:
        st.session_state.target_end = time.time() + st.session_state.remaining
    if "last_minutes" not in st.session_state:
        st.session_state.last_minutes = minutes

    # DB上のアクティブ session_id を覚える領域
    if "active_session_id" not in st.session_state:
        st.session_state.active_session_id = None
    if "started_at_utc" not in st.session_state:
        st.session_state.started_at_utc = None

    # 分数変更時はリセット
    if minutes != st.session_state.last_minutes:
        st.session_state.last_minutes = minutes
        st.session_state.running = False
        st.session_state.remaining = total_sec
        st.session_state.target_end = time.time() + total_sec
        st.info("作業時間を変更したのでリセットしました。")

    # 4) ボタン
    c1, c2, c3 = st.columns(3)
    start = c1.button("▶ 開始／再開")
    pause = c2.button("⏸ 一時停止")
    reset = c3.button("⏹ リセット")

    # --- ▶ 開始／再開 ---
    if start:
        now_utc = datetime.now(ZoneInfo("UTC"))

        if st.session_state.active_session_id is None:
            # 初回「開始」：sessions に1行作成
            sid = insert_session_start(USER_ID, now_utc)  # :contentReference[oaicite:5]{index=5}
            st.session_state.active_session_id = sid
            st.session_state.started_at_utc = now_utc
            # イベントログ
            log_event(sid, "start", now_utc)  # :contentReference[oaicite:6]{index=6}
        else:
            # 既に session がある場合は「再開」
            log_event(st.session_state.active_session_id, "resume", now_utc)  # :contentReference[oaicite:7]{index=7}

        st.session_state.running = True
        st.session_state.target_end = time.time() + st.session_state.remaining

    # --- ⏸ 一時停止 ---
    if pause and st.session_state.active_session_id is not None:
        now = time.time()
        st.session_state.remaining = max(0, int(st.session_state.target_end - now))
        st.session_state.running = False
        now_utc = datetime.now(ZoneInfo("UTC"))  # 元コードの未定義変数を補正
        log_event(st.session_state.active_session_id, "pause", now_utc)  # :contentReference[oaicite:8]{index=8}

    # --- ⏹ リセット（＝中断終了として保存） ---
    if reset and st.session_state.active_session_id is not None:
        now_utc = datetime.now(ZoneInfo("UTC"))
        # これまでの経過フォーカス秒を計算
        elapsed = int(minutes * 60 - st.session_state.remaining)
        if elapsed < 0:
            elapsed = 0
        # セッションを終了レコードとして保存
        finish_session(st.session_state.active_session_id, now_utc, elapsed)  # :contentReference[oaicite:9]{index=9}
        log_event(st.session_state.active_session_id, "reset", now_utc)  # :contentReference[oaicite:10]{index=10}

        # 既存のUIリセット
        st.session_state.running = False
        st.session_state.remaining = total_sec
        st.session_state.target_end = time.time() + total_sec
        st.session_state.active_session_id = None
        st.session_state.started_at_utc = None

    # 5) 残り秒を更新（動作中のみ）
    if st.session_state.running:
        now = time.time()
        st.session_state.remaining = max(0, int(st.session_state.target_end - now))

    # --- タイムアップ時の処理（完了保存） ---
    if st.session_state.running and st.session_state.remaining <= 0:
        st.session_state.running = False
        st.balloons()
        st.success("お疲れさまでした！")
        # 完了として sessions を確定保存＆イベント記録
        if st.session_state.active_session_id is not None:
            finished_utc = datetime.now(ZoneInfo("UTC"))
            focus_seconds = int(minutes * 60)  # 目標分そのまま
            finish_session(st.session_state.active_session_id, finished_utc, focus_seconds)  # :contentReference[oaicite:11]{index=11}
            log_event(st.session_state.active_session_id, "finish", finished_utc)  # :contentReference[oaicite:12]{index=12}
            st.session_state.active_session_id = None
            st.session_state.started_at_utc = None

    # 6) CSSドーナツ（時計回り／12時起点）
    def donut_html(done_ratio: float) -> str:
        done = min(max(done_ratio, 0.0), 1.0)
        deg = int(done * 360)      # 進捗角度（時計回り）
        percent = int(done * 100)
        size = 220                 # 円の大きさ(px)
        thickness = 32             # ドーナツの太さ(px)
        return f"""
        <div style="display:flex;flex-direction:column;align-items:center;gap:12px;">
        <div style="
            width:{size}px;height:{size}px;border-radius:50%;
            background: conic-gradient(#4CAF50 {deg}deg, #E0E0E0 0deg);
            transform:rotate(-90deg);  /* 12時(真上)から開始 */
            position:relative;
        ">
            <div style="
            position:absolute;inset:{thickness}px;border-radius:50%;
            background:white;
            display:flex;align-items:center;justify-content:center;
            font-size:24px;font-weight:600;color:#333;
            transform:rotate(90deg); /* 中央の％文字は元向きに戻す */
            ">{percent}%</div>
        </div>
        </div>
        """

    # 7) 表示
    rem = st.session_state.remaining
    done_ratio = 1 - (rem / total_sec)
    m, s = divmod(rem, 60)
    st.subheader(f"残り：{int(m)}分 {int(s)}秒")

    ph = st.empty()
    ph.markdown(donut_html(done_ratio), unsafe_allow_html=True)

    # 終了 or 1秒ごと再描画
    if st.session_state.running:
        if st.session_state.remaining <= 0:
            st.session_state.running = False
            st.balloons()
            st.success("お疲れさまでした！")
        else:
            time.sleep(1)
            st.rerun()
