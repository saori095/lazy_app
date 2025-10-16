import streamlit as st
from openai import OpenAI
import sqlite3
import random
import time
from datetime import datetime

def run():
    # --- 初期設定・DB接続 ---
    try:
        client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    except Exception as e:
        st.error("OpenAI APIキーが設定されていません。st.secretsを確認してください。")
        st.stop()

    def get_db_connection():
        conn = sqlite3.connect("tasks.db")
        conn.row_factory = sqlite3.Row
        return conn

    def setup_database():
        with get_db_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS subtasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    parent_id INTEGER,
                    content TEXT NOT NULL,
                    estimated_time TEXT,
                    is_done BOOLEAN DEFAULT 0,
                    FOREIGN KEY (parent_id) REFERENCES tasks(id)
                )
            """)
            conn.commit()

    def generate_split_tasks(task_text):
        prompt = f"""
あなたは超優秀な行動心理学者であり、タスク分割のアシスタントです。
先延ばししがちな人が「TECH0の宿題」のような面倒な課題に、楽な気持ちで取り組めるように手助けをします。

以下のルールに従って、ユーザーのタスクを分割してください。

1. 最初のステップは、思考が不要な「5秒で終わる行動」にする。
2. タスク全体を「理解」「計画」「実装」「見直し」の4段階に分ける。
3. 各ステップはポモドーロ（25分）で取り組める粒度にする。
4. 詰まった時の「もし詰まったら：〜する」形式の提案を含める。
5. 全体で3〜5ステップの具体的なアクションプランを提示する。

やること: {task_text}
"""
        try:
            response = client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            st.error(f"タスク分割中にエラーが発生しました: {e}")
            return None

    def generate_praise_message(task_text, style):
        style_instruction_dict = {
            "普通に": "標準語で、短くて心に響くように褒めてください。",
            "博多弁で": "あたたかい博多弁で、親しみを込めて褒めてください。",
            "熱血コーチ風に": "熱血なスポーツコーチのように情熱的に褒めてください。",
            "炭治郎風に": "竈門炭治郎のように、優しく誠実な言葉で、相手の努力を心から讃えてください。",
            "善逸風に": "我妻善逸のように、感情豊かで泣きながらでも相手を全力で褒めてください。",
            "煉獄さん風に": "煉獄杏寿郎のように、力強く、魂を燃やすような言葉で褒めてください。"
        }
        style_instruction = style_instruction_dict.get(style, "標準語で褒めてください。")

        praise_prompt = f"""
あなたはモチベーションを高める称賛メッセージの専門家です。
以下の作業を終えた人に、{style_instruction}
作業: {task_text}
"""
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": praise_prompt}],
                temperature=0.9
            )
            return response.choices[0].message.content
        except Exception as e:
            st.error(f"称賛メッセージ生成中にエラーが発生しました: {e}")
            return "素晴らしい！お疲れ様でした！"

    def get_time_based_praise():
        hour = datetime.now().hour
        weekday = datetime.now().strftime("%A")
        praise = []

        if weekday == "Saturday":
            praise.append("土曜日に頑張るなんて偉い！みんなが休んでる時に一歩前進！")
        elif weekday == "Sunday":
            praise.append("日曜日に取り組むなんて素晴らしい！週明けが楽しみですね！")
        elif weekday in ["Monday", "Friday"]:
            praise.append(f"{weekday}に動き出すあなた、かっこいい！")

        if hour < 6:
            praise.append("早朝から動いてるなんて、まさに意識高い系！")
        elif hour < 12:
            praise.append("午前中にスタートできるあなた、最高です！")
        elif hour < 18:
            praise.append("午後の集中タイムに取り組む姿勢、素敵です！")
        else:
            praise.append("夜遅くまで頑張ってるなんて…本当に尊敬します！")

        return random.choice(praise)

    def get_progress_based_praise():
        with get_db_connection() as conn:
            count = conn.execute("SELECT COUNT(*) FROM subtasks WHERE is_done = 1").fetchone()[0]

        if count >= 10:
            return f"これまでに {count} 個のタスクを完了！継続力が素晴らしいです！"
        elif count >= 5:
            return f"{count} 個の達成、お見事！この調子でどんどん進みましょう！"
        elif count >= 1:
            return f"すでに {count} 個も進めてる！ちゃんと積み重ねてますね！"
        else:
            return "最初の一歩、ここから始まります！"

    def save_and_display_tasks(task, split_result, praise_result, praise_style):
        st.markdown("### あなたへの称賛メッセージ（タスク完了時用）")
        st.success(praise_result)
        st.balloons()

        st.markdown("### あなた専用の攻略プラン")
        st.markdown(split_result)

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO tasks (title) VALUES (?)", (task,))
            parent_id = cursor.lastrowid

            lines = split_result.strip().split("\n")
            for line in lines:
                clean_line = line.strip()
                if clean_line.startswith(("1.", "2.", "3.", "4.", "5.", "-", "・", "ステップ")):
                    parts = clean_line.split(":", 1)
                    clean_line = parts[1].strip() if len(parts) > 1 else clean_line.lstrip("12345.- ・ステップ").strip()

                if clean_line:
                    time_estimate = "25分"
                    if "5秒" in clean_line or "10秒" in clean_line:
                        time_estimate = "5-10秒"

                    cursor.execute(
                        "INSERT INTO subtasks (parent_id, content, estimated_time) VALUES (?, ?, ?)",
                        (parent_id, clean_line, time_estimate)
                    )
            conn.commit()

    def display_task_list():
        st.divider()
        st.subheader("今すぐ取り組むタスク一覧")

        with get_db_connection() as conn:
            tasks = conn.execute("SELECT id, title FROM tasks ORDER BY created_at DESC").fetchall()

            if not tasks:
                st.info("まだタスクがありません。上の入力欄からタスクを追加してみましょう！")
                return

            for task_record in tasks:
                st.markdown(f"### {task_record['title']}")
                subtasks = conn.execute(
                    "SELECT id, content, is_done FROM subtasks WHERE parent_id = ? ORDER BY id ASC",
                    (task_record['id'],)
                ).fetchall()

                first_subtask_handled = False
                for subtask_record in subtasks:
                    is_done = bool(subtask_record['is_done'])

                    if not is_done and not first_subtask_handled:
                        label = f"**{subtask_record['content']}** (まずこれだけ！)"
                        first_subtask_handled = True
                    else:
                        label = subtask_record['content']

                    checked = st.checkbox(label, value=is_done, key=f"subtask_{subtask_record['id']}")

                    if checked != is_done:
                        conn.execute(
                            "UPDATE subtasks SET is_done = ? WHERE id = ?",
                            (int(checked), subtask_record['id'])
                        )
                        conn.commit()

                        if checked and first_subtask_handled:
                            praise_messages = [
                                "すばらしい一歩を踏み出しましたね！",
                                "えらい！よく始めました！",
                                "ナイス！その調子！",
                                "やったね！壁を越えたよ！",
                                "素晴らしい！行動に移したことが何より大事！",
                                "いいね！その一歩が未来を変える！",
                                "最高！もう始められた時点で勝ちだよ！",
                                "その勇気、尊敬します！",
                                "一歩踏み出すって、簡単じゃない。よくやった！",
                                "スタートを切ったあなたはもう成功者です！",
                                get_time_based_praise(),
                                get_progress_based_praise()
                            ]
                            st.success(random.choice(praise_messages))
                            st.toast("タスク完了！おめでとう！")
                            time.sleep(2)

                        st.rerun()

    # --- メイン画面の表示 ---
    st.set_page_config(page_title="タスク分割", page_icon="📝")
    st.title("💎タスク分割 & 称賛ページ")

    setup_database()

    task = st.text_area("大きなタスクを1つ入力してください（例: TECH0の宿題を終わらせる）", height=100)
    praise_style = st.selectbox(
        "どんな風に褒められたい？",
        ("普通に", "博多弁で", "熱血コーチ風に", "炭治郎風に", "善逸風に", "煉獄さん風に")
    )

    if st.button("タスクを分割する", key="split_button", type="primary") and task.strip():
        with st.spinner("あなた専用プランを作成中です..."):
            split_result = generate_split_tasks(task)
            praise_result = generate_praise_message(task, praise_style)

            if split_result and praise_result:
                save_and_display_tasks(task, split_result, praise_result, praise_style)
                st.rerun()

    display_task_list()

# --- 実行トリガー ---
if __name__ == "__main__":
    run()
