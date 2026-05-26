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

@app.route("/api/tasks")
@login_required()
def get_tasks():
    role = session["role"]
    db = get_db()
    if role == "student":
        group = db.execute("SELECT id_group FROM students WHERE id_student=?", (session["linked_id"],)).fetchone()
        rows = db.execute("""SELECT t.*, ts.grade, ts.status as sub_status, ts.submission_text, ts.submission_file_path, ts.submission_link, l.name as lesson_name
            FROM tasks t
            LEFT JOIN task_submissions ts ON t.id_task=ts.id_task AND ts.id_student=?
            JOIN lessons l ON t.id_lesson=l.id_lesson
            WHERE t.id_group=? ORDER BY t.deadline""", (session["linked_id"], group["id_group"])).fetchall()
    elif role == "teacher":
        group_filter = request.args.get("group")
        lesson_filter = request.args.get("lesson")
        q = "SELECT t.*, l.name as lesson_name, sg.group_name FROM tasks t JOIN lessons l ON t.id_lesson=l.id_lesson JOIN study_groups sg ON t.id_group=sg.id_group WHERE t.id_teacher=?"
        params = [session["linked_id"]]
        if group_filter: q += " AND t.id_group=? "; params.append(group_filter)
        if lesson_filter: q += " AND t.id_lesson=? "; params.append(lesson_filter)
        rows = db.execute(q, params).fetchall()
    else:
        rows = db.execute("SELECT t.*, l.name as lesson_name, sg.group_name FROM tasks t JOIN lessons l ON t.id_lesson=l.id_lesson JOIN study_groups sg ON t.id_group=sg.id_group ORDER BY t.deadline").fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/api/submit/<int:task_id>", methods=["POST"])
@login_required("student")
def submit_task(task_id):
    db = get_db()
    data = request.form
    file = request.files.get("file")
    path = None
    if file and file.filename:
        path = os.path.join(app.config["UPLOAD_FOLDER"], f"{task_id}_{session['linked_id']}_{file.filename}")
        file.save(path)
    db.execute("""INSERT OR REPLACE INTO task_submissions (id_task, id_student, submission_text, submission_file_path, submission_link, status)
        VALUES (?, ?, ?, ?, ?, 'submitted') ON CONFLICT DO UPDATE SET
        submission_text=excluded.submission_text, submission_file_path=excluded.submission_file_path,
        submission_link=excluded.submission_link, status='submitted'""",
        (task_id, session["linked_id"], data.get("text"), path, data.get("link")))
    db.commit()
    return jsonify({"status": "ok"})

@app.route("/api/grade/<int:task_id>/<int:sub_id>", methods=["POST"])
@login_required("teacher")
def grade_task(task_id, sub_id):
    data = request.json
    db = get_db()
    db.execute("UPDATE task_submissions SET grade=?, status='checked' WHERE id_submission=?",
        (data.get("grade"), sub_id))
    db.commit()
    return jsonify({"status": "ok"})

@app.route("/api/submissions/<int:task_id>")
@login_required("teacher")
def get_submissions(task_id):
    db = get_db()
    rows = db.execute("""SELECT ts.id_submission, s.name, s.surname, ts.grade, ts.status, ts.submission_text, ts.submission_file_path, ts.submission_link
        FROM task_submissions ts JOIN students s ON ts.id_student=s.id_student WHERE ts.id_task=?""", (task_id,)).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/api/director/users", methods=["POST"])
@login_required("director")
def create_user():
    data = request.json
    db = get_db()
    try:
        pwd_hash = generate_password_hash(data["password"])
        linked = 0
        role = data["role"]
        if role == "teacher":
            db.execute("INSERT INTO teachers (name, surname, payout_percent) VALUES (?, ?, ?)",
                       (data["name"], data["surname"], data.get("percent", 30)))
            linked = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        elif role == "student":
            db.execute("""INSERT INTO students (name, surname, id_group, phone_number, parent_name, parent_phone, parent_email) 
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                       (data["name"], data["surname"], data.get("group_id"), data.get("phone"),
                        data.get("parent_name"), data.get("parent_phone"), data.get("parent_email")))
            linked = db.execute("SELECT last_insert_rowid()").fetchone()[0]

        db.execute("INSERT INTO users (login, password_hash, role, linked_entity_id) VALUES (?, ?, ?, ?)",
                   (data["login"], pwd_hash, role, linked))
        db.commit()
        return jsonify({"status": "ok"})
    except sqlite3.IntegrityError:
        db.rollback()
        return jsonify({"status": "error", "message": "Этот логин уже занят. Придумайте другой."}), 400


@app.route("/api/director/users", methods=["GET"])
@login_required("director")
def get_users_list():
    db = get_db()
    rows = db.execute("""SELECT u.id, u.login, u.role,
        CASE WHEN u.role='teacher' THEN t.name || ' ' || t.surname
             WHEN u.role='student' THEN s.name || ' ' || s.surname
             ELSE 'Администратор' END as full_name
        FROM users u
        LEFT JOIN teachers t ON u.role='teacher' AND u.linked_entity_id = t.id_teacher
        LEFT JOIN students s ON u.role='student' AND u.linked_entity_id = s.id_student
        ORDER BY u.role, u.login""").fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/director/users/<int:user_id>", methods=["DELETE"])
@login_required("director")
def delete_user(user_id):
    if user_id == session.get("user_id"):
        return jsonify({"status": "error", "message": "Нельзя удалить свой собственный аккаунт"}), 403

    db = get_db()
    user = db.execute("SELECT role, linked_entity_id FROM users WHERE id=?", (user_id,)).fetchone()
    if not user:
        return jsonify({"status": "error", "message": "Пользователь не найден"}), 404
    if user["role"] == "director":
        return jsonify({"status": "error", "message": "Удаление директоров запрещено"}), 403

    try:
        if user["role"] == "student":
            db.execute("DELETE FROM task_submissions WHERE id_student=?", (user["linked_entity_id"],))
            db.execute("DELETE FROM accounting WHERE id_student=?", (user["linked_entity_id"],))
            db.execute("DELETE FROM students WHERE id_student=?", (user["linked_entity_id"],))
        elif user["role"] == "teacher":
            db.execute("DELETE FROM teachers WHERE id_teacher=?", (user["linked_entity_id"],))
        db.execute("DELETE FROM users WHERE id=?", (user_id,))
        db.commit()
        return jsonify({"status": "ok"})
    except sqlite3.IntegrityError:
        return jsonify({"status": "error", "message": "Нельзя удалить: есть зависимые записи"}), 400

if __name__ == "__main__":
    app.run(debug=True, port=5000)