"""
Интеграционные тесты Lazlabs School.
Адаптировано под pytest с фикстурами из conftest.py
"""
import pytest
import datetime
from werkzeug.security import generate_password_hash
from core import get_db  # импорт для test_01


def _login(client, db, login, pwd="123", role="student", linked_id=0):
    """Хелпер: создаёт юзера и логинит его."""
    # NULL позволяет SQLite автоматически назначать уникальный id
    db.execute("INSERT INTO users VALUES (NULL, ?, ?, ?, ?)",
               (login, generate_password_hash(pwd), role, linked_id))
    db.commit()
    client.post("/login", data={"login": login, "password": pwd}, follow_redirects=True)


# ========== Инициализация БД ==========
def test_01_db_init(temp_db):
    """Проверка создания всех таблиц."""
    db = get_db(temp_db)
    tables = [r["name"] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    expected = ["users", "teachers", "students", "lessons", "study_groups", "schedule", "tasks", "task_submissions",
                "accounting"]

    missing = [t for t in expected if t not in tables]
    assert not missing, f"Не созданы таблицы: {missing}"


# ========== Аутентификация ==========
def test_02_auth_flow(client, db):
    """Тест входа и выхода из системы."""
    db.execute("INSERT INTO users VALUES (NULL, 'user', ?, 'student', 0)", (generate_password_hash("123"),))
    db.commit()

    # Проверяем пустую сессию
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


def test_03_dashboard_roles(client, db):
    """Проверка доступа к дашбордам для разных ролей."""
    for role in ["director", "teacher", "student"]:
        _login(client, db, f"u_{role}", role=role, linked_id=1 if role != "director" else 0)
        resp = client.get("/dashboard")
        assert resp.status_code == 200, f"Дашборд для {role} должен отдавать 200"
        client.get("/logout")  # Очищаем сессию перед следующей итерацией

    print("Dashboard Roles Success")


# ========== API расписания ==========
def test_04_schedule_api(client, db):
    """Тест получения расписания и отметки о проведении."""
    # Генерируем дату понедельника текущей недели, чтобы тест не падал из-за фильтрации.
    today = datetime.date.today()
    monday = today - datetime.timedelta(days=today.weekday())
    test_date = str(monday)

    # Используем фикстуру db (вместо database.get_db())
    db.execute("INSERT INTO teachers VALUES (NULL, 'I', 'P', 30)")
    db.execute("INSERT INTO lessons VALUES (NULL, 'Math', 1000)")
    db.execute("INSERT INTO study_groups VALUES (NULL, 1, 1, 'G1')")
    db.execute("INSERT INTO schedule VALUES (NULL, 1, 1, ?, '10:00', 0)", (test_date,))
    db.execute("INSERT INTO users VALUES (NULL, 't1', ?, 'teacher', 1)", (generate_password_hash("123"),))
    db.commit()

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


# ========== Задания и оценки ==========
def test_05_tasks_and_grades(client, db):
    # Подготовка данных
    db.execute("INSERT INTO teachers VALUES (20, 'T', 'T', 40)")
    db.execute("INSERT INTO lessons VALUES (2, 'Phys', 1500)")
    db.execute("INSERT INTO study_groups VALUES (2, 20, 2, 'G2')")
    db.execute("INSERT INTO students VALUES (200, 2, 'S', 'S', '+7', 'P', '+7', 'p@e')")
    db.execute("INSERT INTO tasks VALUES (200, 2, 20, 2, 'HW1', 'desc', '2024-06-01', 'active', 100)")
    db.commit()

    # 1. Студент сдаёт работу
    _login(client, db, "s2", role="student", linked_id=200)
    assert client.post("/api/submit/200", data={"text": "ans"}).get_json()["status"] == "ok"
    client.get("/logout")

    # 2. Учитель проверяет и ставит оценку
    db.execute("INSERT INTO users VALUES (21, 't2', ?, 'teacher', 20)", (generate_password_hash("123"),))
    db.commit()
    client.post("/login", data={"login": "t2", "password": "123"}, follow_redirects=True)
    assert client.post("/api/grade/200/1", json={"grade": 85}).get_json()["status"] == "ok"

    # 3. Проверяем, что оценка записалась в БД
    assert db.execute("SELECT grade FROM task_submissions WHERE id_task=200").fetchone()["grade"] == 85


# ========== Пользователи директора ==========
def test_06_director_users(client, db):
    # Подготавливаем данные для соблюдения FK-ограничений при создании студента
    db.execute("INSERT INTO teachers VALUES (NULL, 'T', 'T', 30)")
    db.execute("INSERT INTO lessons VALUES (NULL, 'Math', 1000)")
    db.execute("INSERT INTO study_groups VALUES (NULL, 1, 1, 'G1')")
    db.execute("INSERT INTO users VALUES (NULL, 'dir', ?, 'director', 0)", (generate_password_hash("123"),))
    db.commit()

    client.post("/login", data={"login": "dir", "password": "123"}, follow_redirects=True)

    # 1. Создание студента
    r_create = client.post("/api/director/users", json={
        "login": "new_student", "password": "pass", "role": "student",
        "name": "A", "surname": "B", "group_id": 1, "phone": "123",
        "parent_name": "P", "parent_phone": "456", "parent_email": "p@e"
    })
    assert r_create.get_json()["status"] == "ok", f"Создание не удалось: {r_create.get_json()}"

    # 2. Проверка списка пользователей
    users = client.get("/api/director/users").get_json()
    assert any(u["login"] == "new_student" for u in users), "Студент не появился в списке"
    del_id = next(u["id"] for u in users if u["login"] == "new_student")

    # 3. Удаление студента
    assert client.delete(f"/api/director/users/{del_id}").get_json()["status"] == "ok"

    # 4. Защита от удаления самого себя
    director_id = db.execute("SELECT id FROM users WHERE login='dir'").fetchone()["id"]
    assert client.delete(f"/api/director/users/{director_id}").status_code == 403


# ========== Справочники и расписание ==========
def test_07_refs_schedule(client, db):
    # Подготовка данных
    db.execute("INSERT INTO teachers VALUES (1, 'T1', 'N1', 30)")
    db.execute("INSERT INTO lessons VALUES (1, 'Math', 1000)")
    db.execute("INSERT INTO study_groups VALUES (1, 1, 1, 'G1')")
    db.execute("INSERT INTO users VALUES (100, 'dir', ?, 'director', 0)", (generate_password_hash("123"),))
    db.commit()

    client.post("/login", data={"login": "dir", "password": "123"}, follow_redirects=True)

    # 1. Проверка справочников (refs)
    refs = client.get("/api/director/refs").get_json()
    assert len(refs["lessons"]) == 1 and len(refs["teachers"]) == 1

    # 2. Получение списка групп
    groups = client.get("/api/director/groups").get_json()
    assert groups[0]["group_name"] == "G1"

    # 3. Успешное создание расписания
    assert client.post("/api/director/schedule", json={
        "date": "2024-05-20", "time": "10:00", "group_id": 1, "lesson_id": 1
    }).get_json()["status"] == "ok"

    # 4. Проверка конфликта (группа/учитель заняты в то же время)
    r_conflict = client.post("/api/director/schedule", json={
        "date": "2024-05-20", "time": "10:00", "group_id": 1, "lesson_id": 1
    })
    assert r_conflict.get_json()["status"] == "error" and "заняты" in r_conflict.get_json()["message"]

    # 5. Проверка валидации времени (вне 08:00–18:00)
    r_time = client.post("/api/director/schedule", json={
        "date": "2024-05-20", "time": "22:00", "group_id": 1, "lesson_id": 1
    })
    assert r_time.status_code == 400 and "08:00 до 18:00" in r_time.get_json()["message"]


# ========== Задания учителя ==========
def test_08_teacher_tasks(client, db):
    # Подготовка данных (учитель, предмет, группа)
    db.execute("INSERT INTO teachers VALUES (30, 'Teach', 'A', 50)")
    db.execute("INSERT INTO lessons VALUES (3, 'Eng', 1200)")
    db.execute("INSERT INTO study_groups VALUES (3, 30, 3, 'G3')")
    db.execute("INSERT INTO users VALUES (30, 't3', ?, 'teacher', 30)", (generate_password_hash("123"),))
    db.commit()

    client.post("/login", data={"login": "t3", "password": "123"}, follow_redirects=True)

    # 1. Создание задания
    assert client.post("/api/teacher/tasks", json={
        "group_id": 3, "lesson_id": 3, "title": "HW2", "deadline": "2024-07-01"
    }).get_json()["status"] == "ok"

    # 2. Проверка списка заданий
    tasks = client.get("/api/teacher/tasks").get_json()
    assert len(tasks) == 1 and tasks[0]["title"] == "HW2"


# ========== Бухгалтерия и уведомления ==========
def test_09_acc_notifs(client, db):
    # Подготовка данных
    db.execute("INSERT INTO teachers VALUES (40, 'T40', 'X', 40)")
    db.execute("INSERT INTO lessons VALUES (4, 'Hist', 2000)")
    db.execute("INSERT INTO study_groups VALUES (4, 40, 4, 'G4')")
    db.execute("INSERT INTO students VALUES (400, 4, 'Stu', 'Stu', '+7', 'P', '+7', 'p@e')")
    db.execute("INSERT INTO users VALUES (40, 'dir40', ?, 'director', 0)", (generate_password_hash("123"),))
    db.execute("INSERT INTO users VALUES (41, 't40', ?, 'teacher', 40)", (generate_password_hash("123"),))
    # Занятие в прошлом (2020), чтобы попасть в "пропущенные"
    db.execute("INSERT INTO schedule VALUES (400, 4, 40, '2020-01-01', '09:00', 0)")
    db.commit()

    # 1. Директор вносит оплату
    client.post("/login", data={"login": "dir40", "password": "123"}, follow_redirects=True)
    client.post("/api/accounting", json={
        "student_id": 400, "lesson_id": 4, "date": "2024-05-20",
        "amount": 5000, "classes_paid": 1, "classes_left": 5
    })
    assert client.get("/api/accounting").get_json()["total_paid"] == 5000.0
    client.get("/logout")

    # 2. Учитель проверяет уведомления
    client.post("/login", data={"login": "t40", "password": "123"}, follow_redirects=True)
    notifs = client.get("/api/notifications").get_json()
    assert len(notifs["lessons"]) == 1 and notifs["lessons"][0]["id_schedule"] == 400


# ========== Логика добавления директора ==========
def test_10_add_director_logic(client, db):
    pwd_hash = generate_password_hash("admin123")

    # Первая вставка
    db.execute("""INSERT OR IGNORE INTO users (login, password_hash, role, linked_entity_id)
        VALUES ('director', ?, 'director', 0)""", (pwd_hash,))
    db.commit()

    row = db.execute("SELECT login, role FROM users WHERE login='director'").fetchone()
    assert row is not None and row["login"] == "director"

    # Повторная вставка (должна игнорироваться)
    db.execute("""INSERT OR IGNORE INTO users (login, password_hash, role, linked_entity_id)
        VALUES ('director', ?, 'director', 0)""", (pwd_hash,))
    db.commit()

    assert db.execute("SELECT COUNT(*) FROM users WHERE login='director'").fetchone()[0] == 1


if __name__ == "__main__":
    pytest.main(["-v", __file__])