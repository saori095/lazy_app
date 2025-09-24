import streamlit as st
from openai import OpenAI
import sqlite3

# OpenAIクライアントの初期化
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# SQLiteデータベースに接続し、カーソルを取得
conn = sqlite3.connect("tasks.db")
cursor = conn.cursor()

# テーブル作成（初回のみ）
cursor.execute("""
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS subtasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_id INTEGER,
    content TEXT NOT NULL,
    estimated_time TEXT,
    is_done BOOLEAN DEFAULT 0,
    FOREIGN KEY (parent_id) REFERENCES tasks(id)
)
""")

# Streamlit UI
st.title("🚀 タスク分割 & 称賛ページ")
task = st.text_area("やることを入力してください")

if st.button("分割する", key="split_button") and task.strip():
    # GPTで分割
    prompt = f"""
あなたは優秀なタスク分割アシスタントです。
以下の作業を、ポモドーロ（25分）単位で取り組めるように、3〜5ステップに分けてください。
各ステップは、1ポモドーロ（25分）で完了できるように調整してください。
やること: {task}
"""
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    split_result = response.choices[0].message.content

    # 称賛メッセージ生成
    praise_prompt = f"""
あなたはモチベーションを高める称賛メッセージの専門家です。
以下の作業を終えた人に、短くて心に響く称賛メッセージを1つください。
作業: {task}
"""
    praise_response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": praise_prompt}],
        temperature=0.9
    )
    praise_result = praise_response.choices[0].message.content

    # 表示
    st.markdown("### 💬 称賛メッセージ")
    st.success(praise_result)
    st.balloons()

    st.markdown("### 🔹 分割されたタスク")
    st.write(split_result)

    # DB保存（親タスク）
    cursor.execute("INSERT INTO tasks (title) VALUES (?)", (task,))
    parent_id = cursor.lastrowid
    conn.commit()

    # ✅ 子タスク保存（重複除外付き）
    lines = split_result.strip().split("\n")
    for line in lines:
        clean_line = line.strip()
        if clean_line and clean_line != task:
            cursor.execute(
                "INSERT INTO subtasks (parent_id, content, estimated_time) VALUES (?, ?, ?)",
                (parent_id, clean_line, "25分")
            )
    conn.commit()



# 🔽 保存されたタスク一覧を表示（チェック付き）
cursor.execute("SELECT id, title FROM tasks ORDER BY created_at DESC")
tasks = cursor.fetchall()

for task_id, title in tasks:
    st.markdown(f"### 🧩 {title}")
    cursor.execute("SELECT id, content, is_done FROM subtasks WHERE parent_id = ?", (task_id,))
    subtasks = cursor.fetchall()
    for subtask_id, content, is_done in subtasks:
        checked = st.checkbox(content, value=bool(is_done), key=f"{subtask_id}")
        if checked != bool(is_done):
            cursor.execute("UPDATE subtasks SET is_done = ? WHERE id = ?", (int(checked), subtask_id))
            conn.commit()