import os
import datetime
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, g
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db, init_db, SCHEMA_SQL
from functools import wraps

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Ключ для шифрования сессий

# Настройка папки для загрузки файлов (ответы на задания)
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Дублируем схему в файл schema.sql для удобства просмотра и отладки
with open(os.path.join(os.path.dirname(__file__), "schema.sql"), "w", encoding="utf-8") as f:
    f.write(SCHEMA_SQL)

# Инициализируем БД при старте (создаёт таблицы, если их нет)
init_db()


@app.teardown_appcontext
def close_db(exception):
    """Автоматически закрывает соединение с БД после обработки запроса."""
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()


def login_required(role=None):
    """Декоратор для защиты маршрутов. Проверяет авторизацию и опционально роль."""

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


# Маршруты аутентификации и дашборд
@app.route("/login", methods=["GET", "POST"])
def login():
    """Обработка формы входа. Проверяет логин/пароль и записывает данные в сессию."""
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
    """Очищает сессию и перенаправляет на страницу входа."""
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
def index():
    """Редирект с главной страницы на логин."""
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required()
def dashboard():
    """Главная страница после входа. Рендерит шаблон в зависимости от роли."""
    role = session.get("role")
    if role == "director":
        return render_template("dashboard_director.html", user=session)
    if role == "teacher":
        return render_template("dashboard_teacher.html", user=session)
    return render_template("dashboard_student.html", user=session)


# API: Расписание
@app.route("/api/schedule")
@login_required()
def get_schedule():
    """Возвращает расписание на текущую неделю. Фильтрация зависит от роли."""
    role = session["role"]
    today = datetime.date.today()
    # Определяем понедельник и воскресенье текущей недели
    start = today - datetime.timedelta(days=today.weekday())
    end = start + datetime.timedelta(days=6)
    db = get_db()

    if role == "director":
        # Директор видит всё расписание с именами учителей и предметами
        rows = db.execute("""
            SELECT s.*, sg.group_name, t.name || ' ' || t.surname as teacher_name, l.name as lesson_name
            FROM schedule s 
            JOIN study_groups sg ON s.id_group=sg.id_group 
            JOIN teachers t ON s.id_teacher=t.id_teacher 
            JOIN lessons l ON sg.id_lesson=l.id_lesson
            WHERE s.date BETWEEN ? AND ? ORDER BY s.date, s.time
        """, (str(start), str(end))).fetchall()
    elif role == "teacher":
        # Учитель видит только свои занятия
        rows = db.execute("""
            SELECT s.*, sg.group_name, l.name as lesson_name 
            FROM schedule s 
            JOIN study_groups sg ON s.id_group=sg.id_group 
            JOIN lessons l ON sg.id_lesson=l.id_lesson
            WHERE s.date BETWEEN ? AND ? AND s.id_teacher=? ORDER BY s.date, s.time
        """, (str(start), str(end), session["linked_id"])).fetchall()
    else:
        # Студент видит расписание своей группы
        student_id = session["linked_id"]
        group = db.execute("SELECT id_group FROM students WHERE id_student=?", (student_id,)).fetchone()
        rows = db.execute("""
            SELECT s.*, l.name as lesson_name 
            FROM schedule s 
            JOIN lessons l ON sg.id_lesson=l.id_lesson 
            JOIN study_groups sg ON s.id_group=sg.id_group
            WHERE s.date BETWEEN ? AND ? AND s.id_group=?
        """, (str(start), str(end), group["id_group"])).fetchall()

    return jsonify([dict(row) for row in rows])


@app.route("/api/schedule/<int:sched_id>/complete", methods=["POST"])
@login_required("teacher")
def complete_lesson(sched_id):
    """Учитель отмечает занятие как проведённое (is_completed=1)."""
    db = get_db()
    db.execute("UPDATE schedule SET is_completed=1 WHERE id_schedule=? AND id_teacher=?",
               (sched_id, session["linked_id"]))
    db.commit()
    return jsonify({"status": "ok"})


# API: Задания и проверки
@app.route("/api/tasks")
@login_required()
def get_tasks():
    """Возвращает список заданий с фильтрацией по роли и параметрам."""
    role = session["role"]
    db = get_db()
    if role == "student":
        # Студент видит задания своей группы и статус своих ответов
        group = db.execute("SELECT id_group FROM students WHERE id_student=?", (session["linked_id"],)).fetchone()
        rows = db.execute("""
            SELECT t.*, ts.grade, ts.status as sub_status, ts.submission_text, ts.submission_file_path, ts.submission_link, l.name as lesson_name
            FROM tasks t
            LEFT JOIN task_submissions ts ON t.id_task=ts.id_task AND ts.id_student=?
            JOIN lessons l ON t.id_lesson=l.id_lesson
            WHERE t.id_group=? ORDER BY t.deadline
        """, (session["linked_id"], group["id_group"])).fetchall()
    elif role == "teacher":
        # Учитель видит свои задания с возможностью фильтрации
        group_filter = request.args.get("group")
        lesson_filter = request.args.get("lesson")
        q = "SELECT t.*, l.name as lesson_name, sg.group_name FROM tasks t JOIN lessons l ON t.id_lesson=l.id_lesson JOIN study_groups sg ON t.id_group=sg.id_group WHERE t.id_teacher=?"
        params = [session["linked_id"]]
        if group_filter: q += " AND t.id_group=?"; params.append(group_filter)
        if lesson_filter: q += " AND t.id_lesson=?"; params.append(lesson_filter)
        rows = db.execute(q, params).fetchall()
    else:
        # Директор видит все задания
        rows = db.execute(
            "SELECT t.*, l.name as lesson_name, sg.group_name FROM tasks t JOIN lessons l ON t.id_lesson=l.id_lesson JOIN study_groups sg ON t.id_group=sg.id_group ORDER BY t.deadline").fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/submit/<int:task_id>", methods=["POST"])
@login_required("student")
def submit_task(task_id):
    """Студент отправляет ответ (текст, ссылка или файл)."""
    db = get_db()
    data = request.form
    file = request.files.get("file")
    path = None
    if file and file.filename:
        path = os.path.join(app.config["UPLOAD_FOLDER"], f"{task_id}_{session['linked_id']}_{file.filename}")
        file.save(path)

    # INSERT OR REPLACE позволяет обновить ответ, если студент уже отправлял его ранее
    db.execute("""
        INSERT OR REPLACE INTO task_submissions (id_task, id_student, submission_text, submission_file_path, submission_link, status)
        VALUES (?, ?, ?, ?, ?, 'submitted') ON CONFLICT DO UPDATE SET
        submission_text=excluded.submission_text, submission_file_path=excluded.submission_file_path,
        submission_link=excluded.submission_link, status='submitted'
    """, (task_id, session["linked_id"], data.get("text"), path, data.get("link")))
    db.commit()
    return jsonify({"status": "ok"})


@app.route("/api/grade/<int:task_id>/<int:sub_id>", methods=["POST"])
@login_required("teacher")
def grade_task(task_id, sub_id):
    """Учитель выставляет оценку и меняет статус на 'checked'."""
    data = request.json
    db = get_db()
    db.execute("UPDATE task_submissions SET grade=?, status='checked' WHERE id_submission=?",
               (data.get("grade"), sub_id))
    db.commit()
    return jsonify({"status": "ok"})


@app.route("/api/submissions/<int:task_id>")
@login_required("teacher")
def get_submissions(task_id):
    """Возвращает все ответы студентов на конкретное задание."""
    db = get_db()
    rows = db.execute("""
        SELECT ts.id_submission, s.name, s.surname, ts.grade, ts.status, ts.submission_text, ts.submission_file_path, ts.submission_link
        FROM task_submissions ts JOIN students s ON ts.id_student=s.id_student WHERE ts.id_task=?
    """, (task_id,)).fetchall()
    return jsonify([dict(r) for r in rows])


# API: Управление от директора
@app.route("/api/director/users", methods=["POST"])
@login_required("director")
def create_user():
    """Создание нового пользователя (учителя или студента) директором."""
    data = request.json
    db = get_db()
    try:
        pwd_hash = generate_password_hash(data["password"])
        linked = 0
        role = data["role"]

        # Сначала создаём профиль в соответствующей таблице
        if role == "teacher":
            db.execute("INSERT INTO teachers (name, surname, payout_percent) VALUES (?, ?, ?)",
                       (data["name"], data["surname"], data.get("percent", 30)))
            linked = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        elif role == "student":
            db.execute("""
                INSERT INTO students (name, surname, id_group, phone_number, parent_name, parent_phone, parent_email)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (data["name"], data["surname"], data.get("group_id"), data.get("phone"),
                  data.get("parent_name"), data.get("parent_phone"), data.get("parent_email")))
            linked = db.execute("SELECT last_insert_rowid()").fetchone()[0]

        # Затем создаём учётную запись и привязываем к профилю
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
    """Список всех пользователей с ФИО из связанных таблиц."""
    db = get_db()
    rows = db.execute("""
        SELECT u.id, u.login, u.role,
        CASE WHEN u.role='teacher' THEN t.name || ' ' || t.surname
             WHEN u.role='student' THEN s.name || ' ' || s.surname
             ELSE 'Администратор' END as full_name
        FROM users u
        LEFT JOIN teachers t ON u.role='teacher' AND u.linked_entity_id = t.id_teacher
        LEFT JOIN students s ON u.role='student' AND u.linked_entity_id = s.id_student
        ORDER BY u.role, u.login
    """).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/director/users/<int:user_id>", methods=["DELETE"])
@login_required("director")
def delete_user(user_id):
    """Удаление пользователя и связанных записей (с защитой от самоудаления и удаления директоров)."""
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


@app.route("/api/director/groups", methods=["GET", "POST"])
@login_required("director")
def manage_groups():
    """Создание новых групп или получение списка существующих."""
    db = get_db()
    if request.method == "POST":
        data = request.json
        db.execute("INSERT INTO study_groups (group_name, id_teacher, id_lesson) VALUES (?, ?, ?)",
                   (data["group_name"], data["id_teacher"], data["id_lesson"]))
        db.commit()
        return jsonify({"status": "ok"})

    rows = db.execute("""
        SELECT g.id_group, g.group_name, t.name || ' ' || t.surname as teacher_name, l.name as lesson_name
        FROM study_groups g
        LEFT JOIN teachers t ON g.id_teacher = t.id_teacher
        LEFT JOIN lessons l ON g.id_lesson = l.id_lesson
    """).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/director/refs", methods=["GET"])
@login_required("director")
def get_refs():
    """Справочники учителей и предметов для выпадающих списков в интерфейсе."""
    db = get_db()
    teachers = db.execute("SELECT id_teacher, name, surname FROM teachers").fetchall()
    lessons = db.execute("SELECT id_lesson, name FROM lessons").fetchall()
    return jsonify({"teachers": [dict(t) for t in teachers], "lessons": [dict(l) for l in lessons]})


@app.route("/api/director/lessons", methods=["GET", "POST", "DELETE"])
@login_required("director")
def manage_lessons():
    """CRUD-операции для предметов."""
    db = get_db()
    if request.method == "POST":
        data = request.json
        db.execute("INSERT INTO lessons (name, price_hour) VALUES (?, ?)", (data["name"], data["price_hour"]))
        db.commit()
        return jsonify({"status": "ok"})
    elif request.method == "DELETE":
        lesson_id = request.args.get("id")
        if not lesson_id:
            return jsonify({"status": "error", "message": "Не указан ID"}), 400
        try:
            db.execute("DELETE FROM lessons WHERE id_lesson=?", (lesson_id,))
            db.commit()
            return jsonify({"status": "ok"})
        except sqlite3.IntegrityError:
            return jsonify({"status": "error", "message": "Нельзя удалить: предмет используется"}), 400

    rows = db.execute("SELECT * FROM lessons").fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/director/schedule", methods=["POST"])
@login_required("director")
def add_schedule():
    """Добавление занятия в расписание с проверкой на конфликты по времени/учителю/группе."""
    data = request.json
    date_str, time_str = data.get("date"), data.get("time")
    group_id, lesson_id = data.get("group_id"), data.get("lesson_id")
    if not all([date_str, time_str, group_id, lesson_id]):
        return jsonify({"status": "error", "message": "Заполните все поля"}), 400

    try:
        h, m = map(int, time_str.split(':'))
        if h < 8 or h >= 18:
            return jsonify({"status": "error", "message": "Занятия назначаются только с 08:00 до 18:00"}), 400
    except ValueError:
        return jsonify({"status": "error", "message": "Неверный формат времени"}), 400

    db = get_db()
    group = db.execute("SELECT id_teacher FROM study_groups WHERE id_group=?", (group_id,)).fetchone()
    if not group:
        return jsonify({"status": "error", "message": "Группа не найдена"}), 404

    teacher_id = group["id_teacher"]
    # Проверяем, не занято ли это время у данной группы или учителя
    conflict = db.execute("SELECT 1 FROM schedule WHERE date=? AND time=? AND (id_group=? OR id_teacher=?)",
                          (date_str, time_str, group_id, teacher_id)).fetchone()
    if conflict:
        return jsonify({"status": "error", "message": "В это время группа или учитель уже заняты"}), 400

    db.execute("INSERT INTO schedule (id_group, id_teacher, date, time) VALUES (?, ?, ?, ?)",
               (group_id, teacher_id, date_str, time_str))
    db.commit()
    return jsonify({"status": "ok"})


# API: Учительские задачи
@app.route("/api/teacher/tasks", methods=["GET", "POST"])
@login_required("teacher")
def api_teacher_tasks():
    """Учитель создаёт задания или получает список своих заданий."""
    db = get_db()
    if request.method == "POST":
        data = request.json
        if not all(k in data for k in ["group_id", "lesson_id", "title", "deadline"]):
            return jsonify({"status": "error", "message": "Заполните обязательные поля"}), 400
        db.execute("""
            INSERT INTO tasks (id_group, id_teacher, id_lesson, title, description, deadline, max_points, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'active')
        """, (data["group_id"], session["linked_id"], data["lesson_id"], data["title"],
              data.get("description", ""), data["deadline"], data.get("max_points", 100)))
        db.commit()
        return jsonify({"status": "ok"})

    group = request.args.get("group")
    lesson = request.args.get("lesson")
    q = """
        SELECT t.*, sg.group_name, l.name as lesson_name
        FROM tasks t
        JOIN study_groups sg ON t.id_group = sg.id_group
        JOIN lessons l ON t.id_lesson = l.id_lesson
        WHERE t.id_teacher = ?
    """
    params = [session["linked_id"]]
    if group: q += " AND t.id_group=?"; params.append(group)
    if lesson: q += " AND t.id_lesson=?"; params.append(lesson)
    q += " ORDER BY t.deadline DESC"
    rows = db.execute(q, params).fetchall()
    return jsonify([dict(r) for r in rows])


# API: Бухгалтерия
@app.route("/api/accounting", methods=["GET", "POST"])
@login_required("director")
def accounting_api():
    """Учёт оплат, расчёт выплат учителям и чистой прибыли."""
    db = get_db()
    if request.method == "POST":
        data = request.json
        db.execute("""
            INSERT INTO accounting (id_student, id_lesson, date, payment_amount, is_paid, classes_paid, classes_left)
            VALUES (?, ?, ?, ?, 1, ?, ?)
        """, (data["student_id"], data["lesson_id"], data["date"], data["amount"], data["classes_paid"],
              data["classes_left"]))
        db.commit()
        return jsonify({"status": "ok"})

    start, end = request.args.get("start", "2020-01-01"), request.args.get("end", "2099-12-31")
    total_paid = \
    db.execute("SELECT COALESCE(SUM(payment_amount),0) FROM accounting WHERE date BETWEEN ? AND ? AND is_paid=1",
               (start, end)).fetchone()[0]
    # Расчёт выплат учителям: цена_часа * процент_учителя за все проведённые занятия
    completed = db.execute("""
        SELECT COALESCE(SUM(l.price_hour * t.payout_percent / 100.0), 0) as payout
        FROM schedule s JOIN study_groups sg ON s.id_group=sg.id_group JOIN teachers t ON sg.id_teacher=t.id_teacher JOIN lessons l ON sg.id_lesson=l.id_lesson
        WHERE s.is_completed=1 AND s.date BETWEEN ? AND ?
    """, (start, end)).fetchone()["payout"]
    profit = total_paid - completed

    records = db.execute("""
        SELECT a.*, s.name || ' ' || s.surname as student_name, l.name as lesson_name
        FROM accounting a JOIN students s ON a.id_student=s.id_student JOIN lessons l ON a.id_lesson=l.id_lesson ORDER BY a.date DESC
    """).fetchall()
    return jsonify(
        {"records": [dict(r) for r in records], "total_paid": total_paid, "payouts": completed, "profit": profit})


#API: Уведомления
@app.route("/api/notifications")
@login_required("teacher")
def get_notifications():
    """Возвращает пропущенные занятия и новые ответы студентов для учителя."""
    db = get_db()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    teacher_id = session["linked_id"]

    missed_lessons = db.execute("""
        SELECT s.id_schedule, s.date, s.time, sg.group_name, l.name as lesson_name
        FROM schedule s JOIN study_groups sg ON s.id_group = sg.id_group JOIN lessons l ON sg.id_lesson = l.id_lesson
        WHERE s.id_teacher = ? AND (s.date || ' ' || s.time) <= ? AND s.is_completed = 0 ORDER BY s.date, s.time
    """, (teacher_id, now)).fetchall()

    new_submissions = db.execute("""
        SELECT ts.id_submission, ts.id_task, t.title as task_title, s.name || ' ' || s.surname as student_name,
        ts.submission_text, ts.submission_link, ts.submission_file_path, ts.submitted_at
        FROM task_submissions ts JOIN tasks t ON ts.id_task = t.id_task JOIN students s ON ts.id_student = s.id_student
        WHERE t.id_teacher = ? AND ts.status = 'submitted' ORDER BY ts.submitted_at DESC LIMIT 15
    """, (teacher_id,)).fetchall()

    return jsonify({"lessons": [dict(r) for r in missed_lessons], "submissions": [dict(r) for r in new_submissions]})


# Запуск приложения
if __name__ == "__main__":
    # Режим debug=True включает автоперезагрузку при изменении кода
    app.run(debug=True, port=5000)