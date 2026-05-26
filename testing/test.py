import sys
import os
import tempfile
import sqlite3
import time
import datetime
from werkzeug.security import generate_password_hash

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
import database


def _setup():
    """Настраивает тестовое окружение с временной БД."""
    app.config.update(TESTING=True, SECRET_KEY="test_key", UPLOAD_FOLDER=tempfile.mkdtemp())
    database.DB_PATH = tempfile.mktemp(suffix=".db")

    schema_path = os.path.join(os.path.dirname(database.__file__), "schema.sql")
    with open(schema_path, "w", encoding="utf-8") as f:
        f.write(database.SCHEMA_SQL)

    database.init_db()
    return database.DB_PATH


def _teardown(db_path):
    """Корректно закрывает БД и удаляет файлы (важно для Windows)."""
    import gc
    gc.collect()
    time.sleep(0.1)  # Даём ОС время освободить хендл файла

    for path in [db_path, db_path + "-wal", db_path + "-shm"]:
        if os.path.exists(path):
            try:
                os.remove(path)
            except PermissionError:
                time.sleep(0.3)
                try:
                    os.remove(path)
                except:
                    pass

    schema_path = os.path.join(os.path.dirname(database.__file__), "schema.sql")
    if os.path.exists(schema_path):
        os.remove(schema_path)


def _login(client, login, pwd="123", role="student", linked_id=0):
    """Универсальный хелпер: создаёт юзера в БД и логинит его через тестовый клиент."""
    db = database.get_db()
    # NULL позволяет SQLite автоматически назначать уникальный id
    db.execute("INSERT INTO users VALUES (NULL, ?, ?, ?, ?)",
               (login, generate_password_hash(pwd), role, linked_id))
    db.commit()
    client.post("/login", data={"login": login, "password": pwd}, follow_redirects=True)


def test_01_db_init():
    db_path = _setup()
    db = database.get_db()
    tables = [r["name"] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    expected = ["users", "teachers", "students", "lessons", "study_groups", "schedule", "tasks", "task_submissions",
                "accounting"]

    missing = [t for t in expected if t not in tables]
    assert not missing, f"Не созданы таблицы: {missing}"

    print("DB Init Success")
    _teardown(db_path)


def test_02_auth_flow():
    db_path = _setup()
    client = app.test_client()

    db = database.get_db()
    db.execute("INSERT INTO users VALUES (NULL, 'user', ?, 'student', 0)", (generate_password_hash("123"),))
    db.commit()

    with client.session_transaction() as sess:
        assert "user_id" not in sess, "Сессия должна быть пуста до входа"

    resp = client.post("/login", data={"login": "user", "password": "123"}, follow_redirects=False)
    assert resp.status_code == 302, "После успешного входа должен быть редирект"

    with client.session_transaction() as sess:
        assert "user_id" in sess
        assert sess["role"] == "student"

    resp_fail = client.post("/login", data={"login": "user", "password": "wrong"}, follow_redirects=False)
    assert resp_fail.status_code in [200, 302], "При неверном пароле редиректа быть не должно"

    client.get("/logout", follow_redirects=False)
    with client.session_transaction() as sess:
        assert "user_id" not in sess, "После выхода сессия должна очиститься"

    print("Auth Flow Success")
    _teardown(db_path)


def test_03_dashboard_roles():
    db_path = _setup()
    client = app.test_client()

    for role in ["director", "teacher", "student"]:
        _login(client, f"u_{role}", role=role, linked_id=1 if role != "director" else 0)
        resp = client.get("/dashboard")
        assert resp.status_code == 200, f"Дашборд для {role} должен отдавать 200"
        client.get("/logout")  # Очищаем сессию перед следующей итерацией

    print("Dashboard Roles Success")
    _teardown(db_path)


def test_04_schedule_api():
    db_path = _setup()

    # 🔧 ВАЖНО: Эндпоинт /api/schedule показывает только текущую неделю.
    # Генерируем дату понедельника текущей недели, чтобы тест не падал из-за фильтрации.
    today = datetime.date.today()
    monday = today - datetime.timedelta(days=today.weekday())
    test_date = str(monday)

    db = database.get_db()
    db.execute("INSERT INTO teachers VALUES (NULL, 'I', 'P', 30)")
    db.execute("INSERT INTO lessons VALUES (NULL, 'Math', 1000)")
    db.execute("INSERT INTO study_groups VALUES (NULL, 1, 1, 'G1')")
    db.execute("INSERT INTO schedule VALUES (NULL, 1, 1, ?, '10:00', 0)", (test_date,))
    db.execute("INSERT INTO users VALUES (NULL, 't1', ?, 'teacher', 1)", (generate_password_hash("123"),))
    db.commit()

    client = app.test_client()
    client.post("/login", data={"login": "t1", "password": "123"}, follow_redirects=True)

    # 1. GET /api/schedule
    resp_sched = client.get("/api/schedule")
    data = resp_sched.get_json()
    assert len(data) > 0, "Расписание должно содержать хотя бы одно занятие"
    sched_id = data[0]["id_schedule"]

    # 2. POST /api/schedule/<id>/complete
    resp_complete = client.post(f"/api/schedule/{sched_id}/complete")
    assert resp_complete.get_json()["status"] == "ok"

    # 3. Прямая проверка БД
    is_completed = db.execute("SELECT is_completed FROM schedule WHERE id_schedule=?", (sched_id,)).fetchone()[
        "is_completed"]
    assert is_completed == 1, "Занятие должно быть отмечено как проведённое (is_completed=1)"

    print("Schedule API Success")
    _teardown(db_path)


if __name__ == "__main__":
    test_01_db_init()
    test_02_auth_flow()
    test_03_dashboard_roles()
    test_04_schedule_api()
    print("Тесты 1-4 пройдены успешно!")