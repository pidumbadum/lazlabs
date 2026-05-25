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

    print("Commit 1: DB Init Success")
    _teardown(db_path)


if __name__ == "__main__":
    test_01_db_init()