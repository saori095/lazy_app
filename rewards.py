import streamlit as st
import random
import requests
from bs4 import BeautifulSoup
import base64

# Webサイトから週末のイベント情報とURLを取得する関数
def get_weekend_events():
    url = "https://www.walkerplus.com/event_list/weekend/ar1040/"
    base_url = "https://www.walkerplus.com"
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 修正箇所: イベント名が含まれるspanタグをまず見つける
        title_elements = soup.find_all('span', class_='m-mainlist-item__ttl')
        
        events_with_links = []
        for title_element in title_elements:
            # spanタグの親要素であるaタグを取得
            link_element = title_element.find_parent('a')
            if link_element and 'href' in link_element.attrs:
                title = title_element.get_text(strip=True)
                # 相対URLを絶対URLに変換
                event_url = base_url + link_element['href']
                events_with_links.append((title, event_url))
        
        return events_with_links if events_with_links else [("イベント情報が見つかりませんでした", "#")]
        
    except requests.exceptions.RequestException as e:
        st.error(f"イベント情報の取得中にエラーが発生しました: {e}")
        return [("イベント情報の取得に失敗しました", "#")]

# MP3ファイルをbase64でエンコードして、データURIとして返す関数
def get_base64_audio_uri(file_path):
    with open(file_path, "rb") as f:
        data = f.read()
        b64 = base64.b64encode(data).decode()
        return f"data:audio/mp3;base64,{b64}"

# ローカルの画像ファイルをBase64でエンコードして返す関数
def get_base64_image_uri(file_path):
    with open(file_path, "rb") as f:
        data = f.read()
        b64 = base64.b64encode(data).decode()
        return f"data:image/jpeg;base64,{b64}"

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

# 使用例:
# このスクリプトと同じディレクトリに画像ファイル（例: 'background.jpg'）を配置してください
background_image_path = "backgroundimg.jpg"
set_background_image_from_local(background_image_path)

# Streamlitアプリのメイン部分
st.title("🎁 ご褒美ページ")

# 効果音のファイルパスを指定
audio_file_path = "ラッパのファンファーレ.mp3"

# ガチャを回すボタン
if st.button("ガチャを回す！"):
    events = get_weekend_events()
    
    # 取得したイベントリストからランダムに1つ選択
    result_title, result_url = random.choice(events)
    
    st.balloons()

    # 追加: base64でエンコードした効果音を再生
    audio_uri = get_base64_audio_uri(audio_file_path)
    st.markdown(
        f"""
        <audio autoplay="true">
            <source src="{audio_uri}" type="audio/mp3">
        </audio>
        """,
        unsafe_allow_html=True,
        )
    
    # Markdown形式でハイパーリンクとして表示
    st.success(f"今週末のご褒美は『{result_title}』です！")
    st.markdown(f"[リンクはこちら]({result_url})")