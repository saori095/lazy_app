import streamlit as st
import random
import requests
from bs4 import BeautifulSoup
import base64
import pandas as pd

def run():

    # Webサイトから週末のイベント情報とURLを取得する関数
    def get_weekend_events():
        url = "https://www.walkerplus.com/event_list/weekend/ar1040/"
        base_url = "https://www.walkerplus.com"
        try:
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # イベント名が含まれるspanタグを見つける
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
            st.error(f"イベント情報の取得に失敗しました: {e}")
            return [("イベント情報が見つかりませんでした", "#")]
        except Exception as e:
            st.error(f"おでかけ情報の解析中にエラーが発生しました: {e}")
            return [("イベント情報が見つかりませんでした", "#")]

    # base64エンコードされたオーディオURIを生成する関数
    def get_base64_audio_uri(file_path):
        try:
            with open(file_path, "rb") as f:
                data = f.read()
                b64 = base64.b64encode(data).decode()
            return f"data:audio/mp3;base64,{b64}"
        except FileNotFoundError:
            st.warning(f"効果音ファイルが見つかりません: {file_path}")
        except Exception as e:
            st.error(f"効果音の読み込み中にエラーが発生しました: {e}")
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
        except Exception as e:
            st.error(f"背景画像の設定中にエラーが発生しました: {e}")

    # 履歴機能追加 Session Stateの初期化（ご褒美履歴を保持するリスト）
    if 'reward_history' not in st.session_state:
        st.session_state['reward_history'] = []

    # 背景画像の設定
    background_image_path = "backgroundimg.jpg"
    set_background_image_from_local(background_image_path)

    # 効果音ファイルパス
    audio_file_path = "ラッパのファンファーレ.mp3"

    # 格言をCSVファイルから読み込む
    try:
        df = pd.read_csv("rewards.csv", encoding="utf-8", skiprows=1, header=None, names=['reward'])
        proverbs = df['reward'].tolist()
    except Exception as e:
        proverbs = []
        st.error(f"格言ファイルの読み込みに失敗しました: {e}")

    st.title("🎁 ご褒美ページ")
    st.markdown('<div class="main-content">', unsafe_allow_html=True)

    st.write("頑張ったご褒美に、今日の格言を表示or今週末のおでかけ先をご提案します！")

    if st.button("ご褒美を表示"):
        with st.spinner('ご褒美を探しています...'):
            # どのガチャを引くかランダムに選択（0:格言, 1:おでかけ情報）
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
                    st.success(f"今日の格言は『 **{result}** 』です！")
                    
                    # 履歴への追加
                    st.session_state.reward_history.append(f"格言：『{result}』")

                else:
                    st.warning("格言のリストが空です。rewards.csvに項目を追加してください。")
            else:
                # おでかけ情報ガチャ
                events = get_weekend_events()
                
                # イベントが取得できた場合
                if events and events != [("イベント情報が見つかりませんでした", "#")]:
                    result_title, result_url = random.choice(events)
                    st.balloons()
                    st.success(f"今週末は『{result_title}』にお出かけしませんか？")
                    st.markdown(f"[イベントの詳細を見る]({result_url})")

                    # 履歴への追加
                    st.session_state.reward_history.append(f"おでかけ：『{result_title}』")
                else:
                    st.warning("おでかけ情報が見つかりませんでした。")

    st.markdown('</div>', unsafe_allow_html=True)

    # 履歴の表示
    st.markdown("---") # 区切り線
    st.subheader("📚 ご褒美獲得履歴")

    if st.session_state.reward_history:
        # 最新のものが上にくるように逆順で表示
        for i, reward in enumerate(reversed(st.session_state.reward_history)):
            st.write(f"{reward}")
    else:
        st.write("まだご褒美の獲得履歴はありません。")