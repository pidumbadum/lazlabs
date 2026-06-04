import pytest
import datetime
from werkzeug.security import generate_password_hash
from core import get_db  # импорт для test_01

# Инициализация БД
def test_01_db_init(temp_db):
    """Проверка создания всех таблиц."""
    db = get_db(temp_db)
    tables = [r["name"] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    expected = ["users", "teachers", "students", "lessons", "study_groups", "schedule", "tasks", "task_submissions",
                "accounting"]

    missing = [t for t in expected if t not in tables]
    assert not missing, f"Не созданы таблицы: {missing}"

# Логика добавления директора
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