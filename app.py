from flask import Flask, request, jsonify, render_template, session
import sqlite3
from datetime import date
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "super_secret_key"   
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
            last_record_date TEXT,
            last_life_update TEXT
        )
    """)


    conn.commit()
    conn.close()

init_db()

# ======================
# 🧠 ライフ更新ロジック　（最重要）
# ======================

def update_life(habit):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        SELECT life, total_count, last_record_date, last_life_update
        FROM habits WHERE name=?
    """, (habit,))
    row = c.fetchone()

    if row is None:
        conn.close()
        return

    life, total_count, last_date, last_life_update = row
    today = datetime.today().date()

    # 今日すでにライフ更新済みなら何もしない
    if last_life_update == str(today):
        conn.close()
        return

    if last_date:
        last_date_obj = datetime.strptime(last_date, "%Y-%m-%d").date()
        missed_days = (today - last_date_obj).days - 1

        if missed_days > 0:
            life -= missed_days

            if life <= 0:
                life = 0
                total_count = 0

    # 🔥 今日ライフ更新済みにする（ここが重要）
    c.execute("""
        UPDATE habits
        SET life=?, total_count=?, last_life_update=?
        WHERE name=?
    """, (life, total_count, str(today), habit))

    conn.commit()
    conn.close()

# --------------------
# トップページ
# --------------------
@app.route("/")
def index():
    return render_template("index.html")

#タスク追加API
@app.route("/api/add_habit", methods=["POST"])
def add_habit():
    name = request.json.get("name")

    if not name:
        return jsonify({"error": "Name required"}), 400

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    try:
        c.execute("""
            INSERT INTO habits (name, life, total_count, last_record_date)
            VALUES (?, 3, 0, NULL)
        """, (name,))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "Habit already exists"}), 400

    conn.close()
    return jsonify({"message": "Habit added"})

#タスク削除API
@app.route("/api/delete_habit", methods=["POST"])
def delete_habit():
    name = request.json.get("name")

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM habits WHERE name=?", (name,))
    conn.commit()
    conn.close()

    return jsonify({"message": "Habit deleted"})

# --------------------
# カウント追加API　実際の操作部分
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
    previous_total = total_count
    total_count += 1

    # 10の倍数をまたいだらライフ+1（最大3）
    if previous_total // 10 < total_count // 10:
        if life < 3:
            life += 1

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

    # まず全習慣取得
    c.execute("SELECT name FROM habits")
    habit_names = [row[0] for row in c.fetchall()]

    conn.close()

    # 🔥 ここで全習慣のライフ更新
    for habit in habit_names:
        update_life(habit)

    # 再取得（更新後）
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        SELECT name, life, total_count
        FROM habits
        ORDER BY id ASC
    """)
    rows = c.fetchall()

    result = []
    for name, life, total in rows:
        result.append({
            "name": name,
            "life": life,
            "total": total
        })

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

#ホストログインAPI
@app.route("/api/host_login", methods=["POST"])
def host_login():
    password = request.json.get("password")

    if password == "admin123":
        session["host"] = True
        return jsonify({"message": "Host mode enabled"})
    else:
        return jsonify({"error": "Wrong password"}), 401
    
#ホスト更新API
@app.route("/api/host_update", methods=["POST"])
def host_update():
    if not session.get("host"):
        return jsonify({"error": "Unauthorized"}), 403

    name = request.json.get("name")
    life = int(request.json.get("life"))
    total = int(request.json.get("total"))

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        UPDATE habits
        SET life=?, total_count=?
        WHERE name=?
    """, (life, total, name))

    conn.commit()
    conn.close()

    return jsonify({"message": "Updated"})
# --------------------
if __name__ == "__main__":
    app.run(debug=True)