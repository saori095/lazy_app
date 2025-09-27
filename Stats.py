import os
import sqlite3
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

# =========================
# 基本設定
# =========================
APP_TZ = ZoneInfo("Asia/Tokyo")
DB_DIR = os.path.join(".", "data")
DB_PATH = os.path.join(DB_DIR, "study.db")

os.makedirs(DB_DIR, exist_ok=True)

# =========================
# DBユーティリティ
# =========================
def get_conn():
    # check_same_thread=False で Streamlit の複数スレッドでも安全に
    return sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES, check_same_thread=False)

def init_db():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id        INTEGER NOT NULL DEFAULT 1,
            started_at_utc TEXT NOT NULL,
            finished_at_utc TEXT,
            focus_seconds  INTEGER NOT NULL DEFAULT 0,
            note           TEXT
        );
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_started ON sessions(user_id, started_at_utc);")
        conn.commit()

def insert_session_start(user_id: int, started_at_utc: datetime):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO sessions (user_id, started_at_utc) VALUES (?, ?)",
            (user_id, started_at_utc.isoformat()),
        )
        conn.commit()
        return cur.lastrowid

def finish_session(session_id: int, finished_at_utc: datetime, focus_seconds: int):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE sessions SET finished_at_utc = ?, focus_seconds = ? WHERE session_id = ?",
            (finished_at_utc.isoformat(), max(0, int(focus_seconds)), session_id),
        )
        conn.commit()

def load_all_sessions(user_id: int) -> pd.DataFrame:
    with get_conn() as conn:
        df = pd.read_sql_query(
            "SELECT * FROM sessions WHERE user_id = ? ORDER BY started_at_utc ASC",
            conn,
            params=(user_id,),
        )
    # 文字列→datetime
    if not df.empty:
        df["started_at_utc"] = pd.to_datetime(df["started_at_utc"], utc=True)
        df["finished_at_utc"] = pd.to_datetime(df["finished_at_utc"], utc=True, errors="coerce")
    return df

# =========================
# 指標計算（Asia/Tokyoでの日付を基準）
# =========================
def _to_local(dt_utc: pd.Timestamp) -> pd.Timestamp:
    return dt_utc.tz_convert(APP_TZ)

def compute_metrics(df: pd.DataFrame):
    if df.empty:
        return {
            "total_seconds": 0,
            "last7_seconds": 0,
            "streak_days": 0,
            "by_day": pd.DataFrame(),
        }

    # ローカルタイムに変換
    df = df.copy()
    df["started_local"] = df["started_at_utc"].dt.tz_convert(APP_TZ)
    df["finished_local"] = df["finished_at_utc"].dt.tz_convert(APP_TZ)

    # 学習秒数は focus_seconds（未終了は0のまま）
    df["focus_seconds"] = df["focus_seconds"].fillna(0).astype(int)

    # 日単位の集計（ローカル日付）
    df["local_date"] = df["started_local"].dt.date
    by_day = df.groupby("local_date", as_index=False)["focus_seconds"].sum()

    # 総学習時間
    total_seconds = int(by_day["focus_seconds"].sum())

    # 直近7日（今日含む）の学習時間
    today_local = datetime.now(APP_TZ).date()
    seven_days_ago = today_local - timedelta(days=6)
    last7 = by_day[(by_day["local_date"] >= seven_days_ago) & (by_day["local_date"] <= today_local)]
    last7_seconds = int(last7["focus_seconds"].sum())

    # 連続日数（今日も学習していれば今日から、していなければ昨日から）
    learned_days = set(by_day[by_day["focus_seconds"] > 0]["local_date"].tolist())
    # 連続の起点は「今日 or 昨日」。今日に学習がなければ昨日から数える
    start_date = today_local if today_local in learned_days else (today_local - timedelta(days=1))
    streak = 0
    cur = start_date
    while cur in learned_days:
        streak += 1
        cur = cur - timedelta(days=1)

    return {
        "total_seconds": total_seconds,
        "last7_seconds": last7_seconds,
        "streak_days": streak,
        "by_day": by_day.sort_values("local_date"),
    }

def fmt_hms(total_seconds: int) -> str:
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    if h > 0:
        return f"{h}時間{m}分{s}秒"
    elif m > 0:
        return f"{m}分{s}秒"
    else:
        return f"{s}秒"

# =========================
# Streamlit UI
# =========================
st.set_page_config(page_title="学習ポモドーロ（記録＆指標）", page_icon="⏱️", layout="centered")
st.title("⏱️ 学習ポモドーロ（記録＆指標）")

init_db()

# シンプルに単一ユーザー（将来ログインに置換可）
USER_ID = 1

# セッション状態
if "active_session_id" not in st.session_state:
    st.session_state.active_session_id = None
if "started_at_utc" not in st.session_state:
    st.session_state.started_at_utc = None

# ==== ステータス表示 ====
df = load_all_sessions(USER_ID)
metrics = compute_metrics(df)

col1, col2, col3 = st.columns(3)
col1.metric("連続日数", f"{metrics['streak_days']} 日")
col2.metric("直近7日の学習", fmt_hms(metrics["last7_seconds"]))
col3.metric("総学習時間", fmt_hms(metrics["total_seconds"]))

st.caption("※ タイムゾーンは Asia/Tokyo で日付判定しています。")

# ==== 操作パネル ====
st.subheader("ポモドーロ操作")
DEFAULT_FOCUS_MIN = 25
DEFAULT_BREAK_MIN = 5

with st.form("control"):
    focus_min = st.number_input("集中（分）", min_value=5, max_value=120, value=DEFAULT_FOCUS_MIN, step=5)
    note = st.text_input("メモ（任意）", value="")
    submitted = st.form_submit_button("▶ 開始（Start）", disabled=st.session_state.active_session_id is not None)

if submitted and st.session_state.active_session_id is None:
    started = datetime.now(tz=ZoneInfo("UTC"))
    session_id = insert_session_start(USER_ID, started)
    st.session_state.active_session_id = session_id
    st.session_state.started_at_utc = started
    st.toast("セッションを開始しました。集中していきましょう！💪", icon="✅")

# アクティブ中の表示と停止ボタン
if st.session_state.active_session_id is not None:
    started_local = _to_local(pd.Timestamp(st.session_state.started_at_utc))
    elapsed = (datetime.now(tz=ZoneInfo("UTC")) - st.session_state.started_at_utc).total_seconds()
    st.info(f"進行中：{started_local.strftime('%Y-%m-%d %H:%M:%S')} 開始 / 経過 {fmt_hms(int(elapsed))}")
    if st.button("■ 終了（Finish）", type="primary"):
        finished_utc = datetime.now(tz=ZoneInfo("UTC"))
        focus_seconds = int((finished_utc - st.session_state.started_at_utc).total_seconds())
        finish_session(st.session_state.active_session_id, finished_utc, focus_seconds)
        # メモがあれば更新（note列を簡易更新）
        if note:
            with get_conn() as conn:
                conn.execute("UPDATE sessions SET note = ? WHERE session_id = ?", (note, st.session_state.active_session_id))
                conn.commit()
        st.session_state.active_session_id = None
        st.session_state.started_at_utc = None
        st.success("セッションを保存しました。おつかれさま！🎉")
        # 指標を更新
        df = load_all_sessions(USER_ID)
        metrics = compute_metrics(df)

st.divider()

# ==== 履歴テーブル ====
st.subheader("学習履歴（直近）")
if df.empty:
    st.write("まだ記録がありません。上でセッションを開始してみましょう。")
else:
    # 表示用にローカルタイムへ変換
    show = df.copy()
    show["started_local"] = show["started_at_utc"].dt.tz_convert(APP_TZ).dt.strftime("%Y-%m-%d %H:%M:%S")
    show["finished_local"] = show["finished_at_utc"].dt.tz_convert(APP_TZ).dt.strftime("%Y-%m-%d %H:%M:%S")
    show["focus_time"] = show["focus_seconds"].apply(fmt_hms)
    show = show[["session_id", "started_local", "finished_local", "focus_time", "note"]].sort_values("session_id", ascending=False)
    st.dataframe(show, use_container_width=True)

# ==== 日次サマリ ====
if not metrics["by_day"].empty:
    st.subheader("日次サマリ")
    day = metrics["by_day"].copy()
    day["date"] = pd.to_datetime(day["local_date"])
    day["hours"] = (day["focus_seconds"] / 3600).round(2)
    st.bar_chart(day.set_index("date")["hours"])
    st.caption("棒グラフ：各日の学習時間（時間）")
