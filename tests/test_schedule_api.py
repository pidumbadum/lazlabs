import pytest
import datetime
from werkzeug.security import generate_password_hash
from core import get_db  # импорт для test_01

#API расписания
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

#Справочники и расписание
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

if __name__ == "__main__":
    pytest.main(["-v", __file__])