import streamlit as st

# 4つの run() を、別名で読み込む
from Start import run as run_start
from Split import run as run_split
from Stats import run as run_stats
from rewards import run as run_rewards
from button import run as run_button


st.set_page_config(page_title="Lazy_app", page_icon="⏱️", layout="centered")

# ----------------------------
# 最初にページを判定
# ----------------------------
#page = st.query_params.get("page", "button")  # ← デフォルトを button に変更


# ----------------------------
# button ページだけ特別扱い
# ----------------------------
# if page == "button":
#     run_button()
#     st.stop() 

#st.title("⏱️ Lazy_app")

# page = st.query_params.get("page", "start")

# st.sidebar.header("メニュー")
# page = st.sidebar.radio(
#     "画面をえらぶ",
#     ["ホーム","ポモドーロ・タイマー", "タスク分割", "ダッシュボード", "ご褒美"],
#     index=0
# )

# # メニューで選ばれた run() を呼ぶだけ
# if page == "ホーム":
#     run_button()
# elif page == "ポモドーロターマー":
#     run_start()
# elif page == "タスク分割":
#     run_split()
# elif page == "ダッシュボード":
#     run_stats()
# else:
#     run_rewards()


PAGES = {
    "ホーム": run_button,
    "ポモドーロタイマー": run_start,
    "タスク分割": run_split,
    "ダッシュボード": run_stats,
    "ご褒美": run_rewards,
}

# 1) URLを“唯一の正”にする
params = st.query_params
current = params.get("page", "ホーム")
if current not in PAGES:
    current = "ホーム"

st.sidebar.header("メニュー")

# 2) ラジオは URL の現在値をそのまま表示（key で状態を保持）
options = list(PAGES.keys())
page = st.sidebar.radio(
    "画面をえらぶ",
    options,
    index=options.index(current),
    key="nav_radio",
)

# 3) 値が変わった時だけ URL を更新 → 即 rerun（無限ループ防止）
if page != current:
    st.query_params["page"] = page
    st.rerun()

# 4) 実行
PAGES[current]()
