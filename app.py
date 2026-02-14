from flask import Flask, request, jsonify, render_template
import sqlite3
from datetime import date
from datetime import datetime

app = Flask(__name__)
DB_NAME = "counter.db"

# --------------------
# DB初期化
# --------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            life INTEGER,
            total_count INTEGER,
            last_record_date TEXT
        )
    """)

    habits = ["exercise", "study", "meditation"]

    for habit in habits:
        c.execute("""
            INSERT OR IGNORE INTO habits
            (name, life, total_count, last_record_date)
            VALUES (?, 3, 0, NULL)
        """, (habit,))

    conn.commit()
    conn.close()

init_db()

# ======================
# 🧠 ライフ更新ロジック
# ======================

def update_life(habit):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT life, total_count, last_record_date FROM habits WHERE name=?", (habit,))
    row = c.fetchone()

    if row is None:
        conn.close()
        return

    life, total_count, last_date = row

    if last_date:
        last_date_obj = datetime.strptime(last_date, "%Y-%m-%d").date()
        today = datetime.today().date()
        diff = (today - last_date_obj).days

        if diff > 0:
            life -= diff

            if life <= 0:
                life = 0
                total_count = 0

            c.execute("""
                UPDATE habits
                SET life=?, total_count=?
                WHERE name=?
            """, (life, total_count, habit))

            conn.commit()

    conn.close()


# --------------------
# トップページ
# --------------------
@app.route("/")
def index():
    return render_template("index.html")

# --------------------
# カウント追加API
# --------------------
@app.route("/api/add", methods=["POST"])
def add_count():
    activity = request.json.get("activity")
    today = datetime.today().date()

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # ライフ更新
    update_life(activity)

    c.execute("SELECT life, total_count, last_record_date FROM habits WHERE name=?", (activity,))
    row = c.fetchone()

    if row is None:
        conn.close()
        return jsonify({"error": "Habit not found"}), 400

    life, total_count, last_date = row

    # すでに今日カウントしているか？
    if last_date == str(today):
        conn.close()
        return jsonify({"message": "Already counted today", "life": life, "total": total_count})

    # ライフが0ならカウント不可
    if life <= 0:
        conn.close()
        return jsonify({"message": "Life is zero. Reset required.", "life": life, "total": total_count})

    # カウント実行
    total_count += 1
    life = 3

    c.execute("""
        UPDATE habits
        SET total_count=?, life=?, last_record_date=?
        WHERE name=?
    """, (total_count, life, str(today), activity))

    conn.commit()
    conn.close()

    return jsonify({"message": "Count added", "life": life, "total": total_count})

# --------------------
# 今日の合計取得API
# --------------------
@app.route("/api/today")
def today_total():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT name, life, total_count FROM habits")
    rows = c.fetchall()

    result = {}
    for name, life, total in rows:
        result[name] = {
            "life": life,
            "total": total
        }

    conn.close()
    return jsonify(result)
# --------------------
# 累計取得API
# --------------------
@app.route("/api/total")
def total():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT name, total_count FROM habits")
    rows = c.fetchall()

    result = {name: total for name, total in rows}

    conn.close()
    return jsonify(result)
# --------------------
if __name__ == "__main__":
    app.run(debug=True)