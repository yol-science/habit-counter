from flask import Flask, request, jsonify, render_template
import sqlite3
from datetime import date

app = Flask(__name__)
DB_NAME = "counter.db"

# --------------------
# DB初期化
# --------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity TEXT,
            record_date TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

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
    today = str(date.today())

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO records (activity, record_date) VALUES (?,?)",
              (activity, today))
    conn.commit()
    conn.close()

    return jsonify({"message": "added"})

# --------------------
# 今日の合計取得API
# --------------------
@app.route("/api/today")
def today_total():
    today = str(date.today())
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        SELECT activity, COUNT(*) 
        FROM records 
        WHERE record_date=?
        GROUP BY activity
    """, (today,))
    data = dict(c.fetchall())
    conn.close()
    return jsonify(data)

# --------------------
# 累計取得API
# --------------------
@app.route("/api/total")
def total():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        SELECT activity, COUNT(*) 
        FROM records
        GROUP BY activity
    """)
    data = dict(c.fetchall())
    conn.close()
    return jsonify(data)

# --------------------
if __name__ == "__main__":
    app.run(debug=True)