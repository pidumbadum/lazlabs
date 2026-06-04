import pytest
import datetime
from werkzeug.security import generate_password_hash
from core import get_db  # импорт для test_01

# Бухгалтерия и уведомления
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

if __name__ == "__main__":
    pytest.main(["-v", __file__])