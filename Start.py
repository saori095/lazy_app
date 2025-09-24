# main.py
# Matplotlibを使わず、CSSのconic-gradientで時計回りドーナツを描画
import time
import os
import streamlit as st

st.set_page_config(page_title="ポモドーロ", page_icon="⏳")
st.title("⏳ ポモドーロ・タイマー（CSSドーナツ／1秒更新＋BGM）")

# 1) 作業時間（25/15/5）
minutes = st.radio(
    "作業時間を選んでください（※変更するとタイマーはリセット）",
    options=[25, 15, 5],
    index=0,
    horizontal=True,
)
total_sec = minutes * 60

# 2) BGM（MP3）
st.subheader("BGM（任意）")
bgm_mode = st.radio(
    "ブラウザ仕様で自動再生不可：▶ を1回押してください",
    ["なし", "フォルダのMP3から選ぶ", "MP3をアップロードする"],
    index=0,
)
bgm_obj = None
if bgm_mode == "フォルダのMP3から選ぶ":
    mp3s = [f for f in os.listdir(".") if f.lower().endswith(".mp3")]
    if mp3s:
        pick = st.selectbox("MP3ファイルを選択", mp3s)
        if pick:
            bgm_obj = pick
    else:
        st.info("このフォルダに .mp3 が見つかりません。")
elif bgm_mode == "MP3をアップロードする":
    up = st.file_uploader("MP3ファイルをアップロード", type=["mp3"])
    if up is not None:
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

if start:
    st.session_state.running = True
    st.session_state.target_end = time.time() + st.session_state.remaining

if pause:
    now = time.time()
    st.session_state.remaining = max(0, int(st.session_state.target_end - now))
    st.session_state.running = False

if reset:
    st.session_state.running = False
    st.session_state.remaining = total_sec
    st.session_state.target_end = time.time() + total_sec

# 5) 残り秒を更新（動作中のみ）
if st.session_state.running:
    now = time.time()
    st.session_state.remaining = max(0, int(st.session_state.target_end - now))

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
