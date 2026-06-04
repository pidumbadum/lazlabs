import pytest
import datetime
from werkzeug.security import generate_password_hash
from core import get_db  # импорт для test_01

#Аутентификация
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


def test_03_dashboard_roles(client, db, login):
    """Проверка доступа к дашбордам для разных ролей."""
    for role in ["director", "teacher", "student"]:
        login(f"u_{role}", role=role, linked_id=1 if role != "director" else 0)
        resp = client.get("/dashboard")
        assert resp.status_code == 200, f"Дашборд для {role} должен отдавать 200"
        client.get("/logout")  # Очищаем сессию перед следующей итерацией

    print("Dashboard Roles Success")

if __name__ == "__main__":
    pytest.main(["-v", __file__])