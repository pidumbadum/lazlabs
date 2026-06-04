import pytest
import datetime
from werkzeug.security import generate_password_hash
from core import get_db  # импорт для test_01

#Задания и оценки
def test_05_tasks_and_grades(client, db, login):
    # Подготовка данных
    db.execute("INSERT INTO teachers VALUES (20, 'T', 'T', 40)")
    db.execute("INSERT INTO lessons VALUES (2, 'Phys', 1500)")
    db.execute("INSERT INTO study_groups VALUES (2, 20, 2, 'G2')")
    db.execute("INSERT INTO students VALUES (200, 2, 'S', 'S', '+7', 'P', '+7', 'p@e')")
    db.execute("INSERT INTO tasks VALUES (200, 2, 20, 2, 'HW1', 'desc', '2024-06-01', 'active', 100)")
    db.commit()

    # 1. Студент сдаёт работу
    login("s2", role="student", linked_id=200)
    assert client.post("/api/submit/200", data={"text": "ans"}).get_json()["status"] == "ok"
    client.get("/logout")

    # 2. Учитель проверяет и ставит оценку
    db.execute("INSERT INTO users VALUES (21, 't2', ?, 'teacher', 20)", (generate_password_hash("123"),))
    db.commit()
    client.post("/login", data={"login": "t2", "password": "123"}, follow_redirects=True)
    assert client.post("/api/grade/200/1", json={"grade": 85}).get_json()["status"] == "ok"

    # 3. Проверяем, что оценка записалась в БД
    assert db.execute("SELECT grade FROM task_submissions WHERE id_task=200").fetchone()["grade"] == 85

#Задания учителя
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

if __name__ == "__main__":
    pytest.main(["-v", __file__])