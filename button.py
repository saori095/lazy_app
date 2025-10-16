import time
import pathlib
import streamlit as st
from datetime import datetime
from zoneinfo import ZoneInfo

import base64
from Stats import init_db, insert_session_start, load_all_sessions, compute_metrics,  finish_session

def run():

    # 削除
    #st.set_page_config(page_title="Big Image Button", page_icon="🖱️", layout="centered")

    # --- 画像をBase64にエンコードする関数 ---
    def image_to_base64(image_path: pathlib.Path):
        """ローカル画像をBase64エンコードされたData URI文字列に変換する"""
        if not image_path.exists():
            return None
        mime_type = "image/jpeg" 
        
        try:
            with open(image_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode()
                return f"data:{mime_type};base64,{encoded_string}"
        except Exception as e:
            st.error(f"画像の読み込み中にエラーが発生しました: {e}")
            return None
    # ----------------------------------------

    # --------------------
    # 設定
    # --------------------
    IMG_PATH = pathlib.Path("button.jpg") 

    # --------------------
    # 初期化
    # --------------------
    if "press_count" not in st.session_state:
        st.session_state.press_count = 0

    # --------------------
    # スタイル（変更なし）
    # --------------------
    st.markdown("""
    <style>
    .big-btn-wrap {
        display: grid;
        place-items: center;
    }
    a.big-img-btn {
        display: inline-block;
        border-radius: 50%; 
        overflow: hidden;
        box-shadow: 0 12px 24px rgba(0,0,0,0.18);
        transition: transform .08s ease, box-shadow .2s ease, filter .2s ease;
        outline: none;
        padding: 30px;
        backgrount-color: yellow;
    }
    a.big-img-btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 16px 32px rgba(0,0,0,0.22);
        filter: brightness(1.02);
    }
    a.big-img-btn:active {
        transform: translateY(1px) scale(.995);
    }
    a.big-img-btn img {
        max-width: 100%; 
        height: auto; 
        display: block;
        object-fit: contain;
    }
    .caption {
        margin-top: 10px;
        font-weight: 700;
        text-align: center;
        opacity: .85;
    }
    .badge {
        display: inline-block;
        background: #eee;
        border-radius: 999px;
        padding: 4px 10px;
        font-size: .9rem;
        margin-left: 8px;
    }
    div[data-testid="stMetric"] {
    display: flex;
    justify-content: center; /* コンテンツ自体を中央に寄せる */
    width: 100%; /* 親要素の幅いっぱいに広げる */
    }
    div[data-testid="stMetric"] > div {
    text-align: center; /* テキストを中央揃え */
    align-items: center; /* 垂直方向の中央揃え */
    }
    div[data-testid="stMetricLabel"] {
    justify-content: center; /* ラベルを中央揃え */
    width: 100%;
    }
    div[data-testid="stMetricValue"] {
    text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

    # 削除
    # st.set_page_config(page_title="学習ポモドーロ（連続日数）", page_icon="⏱️", layout="centered")
    # st.title("押してね❤️")

    # --------------------
    # クリック検知（変更なし）
    # --------------------
    params = st.query_params
    pressed = params.get("pressed", ["0"])[0] if isinstance(params.get("pressed"), list) else params.get("pressed", "0")

    init_db()
    USER_ID = 1

    if pressed == "1":
        # DBにセッション記録する
        started = datetime.now(tz=ZoneInfo("UTC"))
        session_id = insert_session_start(USER_ID, started)
        
        # ★ 追加: 1秒だけ focus_seconds を入れて streak対象にする
        finish_session(session_id, started, 1)
    
    # if pressed == "1":
    #     # Split ページに画面遷移するために、app.py のラジオボタンの値を変更する
    #     # app.py で st.sidebar.radio に key="current_page_selection" を設定した前提
    #     if "current_page_selection" in st.session_state:
    #         st.session_state.current_page_selection = "Split"
    #     # DBにセッション記録する
    #     started = datetime.now(tz=ZoneInfo("UTC"))
    #     session_id = insert_session_start(USER_ID, started)

        st.session_state.press_count = st.session_state.get("press_count", 0) + 1
        #st.success(f"✅ ボタンが押されました！（通算 {st.session_state.press_count} 回, session_id={session_id}）")

        # 【重要】URLパラメータをクリアして、次のリロードで 'pressed=1' のロジックが実行されないようにする
        #st.query_params.clear()

        # 画面遷移のために Streamlit を再実行 (リダイレクト) させる
        #st.experimental_rerun()

    # --------------------
    # 画像ボタンの描画 (Base64適用)
    # --------------------

    st.markdown(
    """
    <h1 style="text-align: center; margin-bottom: 20px;">押してね❤️</h1>
    """, 
    unsafe_allow_html=True
    )

    # 1. Base64文字列に変換
    img_src = image_to_base64(IMG_PATH) # ★ img_src に Base64文字列を代入

    if not img_src:
        st.info("button.jpg を同じフォルダに置いてください。")
        # Base64変換に失敗した場合、HTMLをレンダリングしないか、代替のテキストを表示
        st.stop() # 処理を中断してエラー表示を防ぐ

    # 幅いっぱい（max_widthで制御）
    max_width = 350
    stamp = int(time.time())  # キャッシュ回避
    st.markdown(
        f"""
        <div class="big-btn-wrap">
        <a class="big-img-btn" 
            href="?pressed=1&t={stamp}"
            style="cursor: pointer; display:inline-block;">
            <img src="{img_src}" width="{max_width}" style="border-radius: 50%;"> 
        </a>
        </div>
        """,
        unsafe_allow_html=True
    )

    # 連続日数を表示
    df = load_all_sessions(USER_ID)
    metrics = compute_metrics(df)
    st.metric("連続日数", f"{metrics['streak_days']} 日")

    # # DB初期化
    # init_db()

    # # 単一ユーザー想定
    # USER_ID = 1

    # if st.button("押して記録！"):
    #     # UTC時刻でセッション開始を記録
    #     started = datetime.now(tz=ZoneInfo("UTC"))
    #     session_id = insert_session_start(USER_ID, started)
    #     st.success(f"セッションを記録しました！ (session_id={session_id})")

    # # データ取得 & 指標計算
    # df = load_all_sessions(USER_ID)
    # metrics = compute_metrics(df)

    # # 連続日数だけ表示
    # st.metric("連続日数", f"{metrics['streak_days']} 日")