import pytest
import datetime
from werkzeug.security import generate_password_hash
from core import get_db  # импорт для test_01

# Пользователи директора
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

if __name__ == "__main__":
    pytest.main(["-v", __file__])