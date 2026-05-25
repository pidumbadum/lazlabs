import os
import datetime
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, g
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db, init_db, SCHEMA_SQL
from functools import wraps

app = Flask(__name__)
app.secret_key = os.urandom(24)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Генерация schema.sql для удобства отладки
with open(os.path.join(os.path.dirname(__file__), "schema.sql"), "w", encoding="utf-8") as f:
    f.write(SCHEMA_SQL)

# Инициализация БД при первом запуске
init_db()

@app.teardown_appcontext
def close_db(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()

def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login"))
            if role and session.get("role") != role:
                flash("Доступ запрещен")
                return redirect(url_for("dashboard"))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        login = request.form["login"]
        password = request.form["password"]
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE login = ?", (login,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["role"] = user["role"]
            session["linked_id"] = user["linked_entity_id"]
            return redirect(url_for("dashboard"))
        flash("Неверный логин или пароль")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/")
def index():
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required()
def dashboard():
    role = session.get("role")
    if role == "director":
        return render_template("dashboard_director.html", user=session)
    if role == "teacher":
        return render_template("dashboard_teacher.html", user=session)
    return render_template("dashboard_student.html", user=session)


@app.route("/api/schedule")
@login_required()
def get_schedule():
    role = session["role"]
    today = datetime.date.today()
    start = today - datetime.timedelta(days=today.weekday())
    end = start + datetime.timedelta(days=6)
    db = get_db()

    if role == "director":
        rows = db.execute("""SELECT s.*, sg.group_name, t.name || ' ' || t.surname as teacher_name, l.name as lesson_name
            FROM schedule s 
            JOIN study_groups sg ON s.id_group=sg.id_group 
            JOIN teachers t ON s.id_teacher=t.id_teacher 
            JOIN lessons l ON sg.id_lesson=l.id_lesson
            WHERE s.date BETWEEN ? AND ? ORDER BY s.date, s.time""", (str(start), str(end))).fetchall()
    elif role == "teacher":
        rows = db.execute("""SELECT s.*, sg.group_name, l.name as lesson_name 
            FROM schedule s 
            JOIN study_groups sg ON s.id_group=sg.id_group 
            JOIN lessons l ON sg.id_lesson=l.id_lesson
            WHERE s.date BETWEEN ? AND ? AND s.id_teacher=? ORDER BY s.date, s.time""",
                          (str(start), str(end), session["linked_id"])).fetchall()
    else:
        student_id = session["linked_id"]
        group = db.execute("SELECT id_group FROM students WHERE id_student=?", (student_id,)).fetchone()
        rows = db.execute("""SELECT s.*, l.name as lesson_name 
            FROM schedule s 
            JOIN lessons l ON sg.id_lesson=l.id_lesson 
            JOIN study_groups sg ON s.id_group=sg.id_group
            WHERE s.date BETWEEN ? AND ? AND s.id_group=?""", (str(start), str(end), group["id_group"])).fetchall()

    return jsonify([dict(row) for row in rows])


@app.route("/api/schedule/<int:sched_id>/complete", methods=["POST"])
@login_required("teacher")
def complete_lesson(sched_id):
    db = get_db()
    db.execute("UPDATE schedule SET is_completed=1 WHERE id_schedule=? AND id_teacher=?",
               (sched_id, session["linked_id"]))
    db.commit()
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(debug=True, port=5000)