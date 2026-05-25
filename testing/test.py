import sys
import os
import tempfile
import sqlite3
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
import database


def _setup():
    """Настраивает тестовое окружение с временной БД."""
    app.config.update(TESTING=True, SECRET_KEY="test", UPLOAD_FOLDER=tempfile.mkdtemp())
    database.DB_PATH = tempfile.mktemp(suffix=".db")

    # Создаём schema.sql для init_db()
    schema_path = os.path.join(os.path.dirname(database.__file__), "schema.sql")
    with open(schema_path, "w", encoding="utf-8") as f:
        f.write(database.SCHEMA_SQL)

    database.init_db()
    return database.DB_PATH


def _teardown(db_path):
    """Корректно закрывает БД и удаляет файлы (важно для Windows)."""
    # Закрываем все активные соединения
    ctx = getattr(app, '_app_ctx_stack', None)
    if ctx and hasattr(ctx.top, 'db') and ctx.top.db:
        ctx.top.db.close()

    # Принудительный сборщик мусора
    import gc
    gc.collect()
    time.sleep(0.1)  # Даём ОС время освободить файл

    # Удаляем файлы БД (основной + WAL режим)
    for path in [db_path, db_path + "-wal", db_path + "-shm"]:
        if os.path.exists(path):
            try:
                os.remove(path)
            except PermissionError:
                # Повторная попытка для Windows
                time.sleep(0.3)
                try:
                    os.remove(path)
                except:
                    pass

    # Чистим schema.sql
    schema_path = os.path.join(os.path.dirname(database.__file__), "schema.sql")
    if os.path.exists(schema_path):
        os.remove(schema_path)


def test_01_db_init():
    """Проверяет создание всех таблиц при инициализации."""
    db_path = _setup()

    db = database.get_db()
    tables = [r["name"] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    expected = ["users", "teachers", "students", "lessons", "study_groups", "schedule", "tasks", "task_submissions",
                "accounting"]

    # Проверяем наличие всех таблиц
    missing = [t for t in expected if t not in tables]
    assert not missing, f"Не созданы таблицы: {missing}"

    # Проверяем количество таблиц
    assert len(tables) >= len(expected), "Создано меньше таблиц, чем ожидалось"

    db.close()  # ← Важно закрыть перед teardown!

    print(" DB Init Success")
    _teardown(db_path)

def test_02_auth_flow():
    db_path = _setup()
    client = app.test_client()

    # 1. Создаем тестового пользователя в БД
    db = database.get_db()
    db.execute("INSERT INTO users VALUES (1, 'user', ?, 'student', 0)",
               (generate_password_hash("123"),))
    db.commit()
    db.close()

    # 2. Проверяем вход (через сессию)
    # До входа сессия пуста
    with client.session_transaction() as sess:
        assert "user_id" not in sess, "Сессия должна быть пуста до входа"

    # Выполняем вход (POST-запрос)
    resp = client.post("/login", data={"login": "user", "password": "123"}, follow_redirects=False)

    # После входа должен быть редирект на dashboard (302)
    assert resp.status_code == 302, "После успешного входа должен быть редирект"

    # Проверяем сессию
    with client.session_transaction() as sess:
        assert "user_id" in sess, "После входа в сессии должен быть user_id"
        assert sess["user_id"] == 1
        assert sess["role"] == "student"

    # 3. Проверяем неверный пароль
    resp_fail = client.post("/login", data={"login": "user", "password": "wrong"}, follow_redirects=False)
    # При ошибке остаемся на /login (200 или редирект обратно)
    assert resp_fail.status_code in [200, 302]

    # 4. Проверяем выход (logout)
    client.get("/logout", follow_redirects=False)
    with client.session_transaction() as sess:
        assert "user_id" not in sess, "После выхода сессия должна очиститься"

    print("Auth Flow Success")
    _teardown(db_path)

if __name__ == "__main__":
    test_01_db_init()