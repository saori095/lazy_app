import streamlit as st
import random
import requests
from bs4 import BeautifulSoup
import base64
import pandas as pd

def get_weekend_events():
    url = "https://www.walkerplus.com/event_list/weekend/ar1040/"
    base_url = "https://www.walkerplus.com"
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        title_elements = soup.find_all('span', class_='m-mainlist-item__ttl')
        
        events_with_links = []
        for title_element in title_elements:
            link_element = title_element.find_parent('a')
            if link_element and 'href' in link_element.attrs:
                title = title_element.get_text(strip=True)
                event_url = base_url + link_element['href']
                events_with_links.append((title, event_url))
        
        return events_with_links if events_with_links else None
        
    except requests.exceptions.RequestException as e:
        st.error(f"イベント情報の取得中にエラーが発生しました: {e}")
        return None

# MP3ファイルをbase64でエンコードして、データURIとして返す関数
def get_base64_audio_uri(file_path):
    try:
        with open(file_path, "rb") as f:
            data = f.read()
            b64 = base64.b64encode(data).decode()
            return f"data:audio/mp3;base64,{b64}"
    except FileNotFoundError:
        return None

# ローカルの画像ファイルをBase64でエンコードして返す関数
def get_base64_image_uri(file_path):
    with open(file_path, "rb") as f:
        data = f.read()
        b64 = base64.b64encode(data).decode()
        return f"data:image/jpeg;base64,{b64}"

def set_background_image_from_local(file_path):
    try:
        image_uri = get_base64_image_uri(file_path)
        st.markdown(
            f"""
            <style>
            .stApp {{
                background-image: url("{image_uri}");
                background-size: cover;
                background-position: center;
                background-repeat: no-repeat;
                background-attachment: fixed;
            }}
            </style>
            """,
            unsafe_allow_html=True
        )
    except FileNotFoundError:
        st.error(f"エラー: 指定されたファイル '{file_path}' が見つかりません。")

def set_background_image_from_local(file_path):
    """
    ローカルの画像ファイルを背景として設定します。
    ファイルパスを指定してください。
    """
    try:
        image_uri = get_base64_image_uri(file_path)
        st.markdown(
            f"""
            <style>
            .stApp {{
                background-image: url("{image_uri}");
                background-size: cover;
                background-position: center;
                background-repeat: no-repeat;
                background-attachment: fixed;
            }}
            </style>
            """,
            unsafe_allow_html=True
        )
    except FileNotFoundError:
        st.error(f"エラー: 指定されたファイル '{file_path}' が見つかりません。")

# --- アプリのメイン部分 ---

# セッションステートの初期化
if 'rewards_history' not in st.session_state:
    st.session_state.rewards_history = []

# 背景画像の設定
background_image_path = "backgroundimg.jpg"
set_background_image_from_local(background_image_path)

# 効果音のファイルパスを指定
audio_file_path = "ラッパのファンファーレ.mp3"

# CSVファイルから格言を読み込む
try:
    df = pd.read_csv("rewards.csv", encoding="utf-8", skiprows=1, header=None, names=['reward'])
    proverbs = df['reward'].tolist()
except Exception as e:
    proverbs = []
    st.error(f"格言ファイルの読み込みに失敗しました: {e}")

st.title("🎁 ご褒美ページ")
# 中央寄せのためのコンテナ
center_container = st.container()
center_container.markdown('<div class="main-content">', unsafe_allow_html=True)

with center_container:
    st.write("頑張ったご褒美に、今日の格言を表示or今週末のおでかけ先をご提案します！")
    
    if st.button("ご褒美を表示"):
        with st.spinner('ご褒美を探しています...'):
            choice = random.choice([0, 1])

            # 効果音の再生
            audio_uri = get_base64_audio_uri(audio_file_path)
            if audio_uri:
                st.markdown(f'<audio autoplay="true"><source src="{audio_uri}" type="audio/mp3"></audio>', unsafe_allow_html=True)

            if choice == 0:
                # 格言ガチャ
                if proverbs:
                    result = random.choice(proverbs)
                    st.balloons()
                    st.success(f"今日の格言は『 {result} 』です！")
                    # セッションステートに結果を追加
                    st.session_state.rewards_history.append(f"格言：{result}")
                else:
                    st.warning("格言のリストが空です。rewards.csvに項目を追加してください。")
            else:
                # おでかけ情報ガチャ
                events = get_weekend_events()
                if events:
                    result_title, result_url = random.choice(events)
                    st.balloons()
                    st.success(f"今週末のご褒美は『{result_title}』です！")
                    st.markdown(f"[リンクはこちら]({result_url})")
                    # セッションステートに結果を追加
                    st.session_state.rewards_history.append(f"おでかけ情報：{result_title}")
                else:
                    st.warning("イベント情報が見つかりませんでした。")
                    
st.markdown('</div>', unsafe_allow_html=True)

# --- 獲得したご褒美の履歴を表示するセクション ---
st.markdown("---")
st.subheader("これまでのご褒美リスト")

if st.session_state.rewards_history:
    # 新しいご褒美を一番上に表示するため、リストを逆順にする
    for item in reversed(st.session_state.rewards_history):
        st.info(item)
else:
    st.info("まだご褒美はありません。ガチャを回してみましょう！")