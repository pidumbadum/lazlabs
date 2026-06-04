import sqlite3
import os
from pathlib import Path


# Путь к схеме БД — всегда рядом с этим файлом
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

# Путь к БД по умолчанию — в корне проекта (4 уровня вверх от этого файла)
DB_PATH = os.environ.get(
    "DATABASE_PATH",
    str(Path(__file__).resolve().parent.parent.parent.parent / "school.db")
)


def get_db(db_path: str = None):
    """Возвращает настроенное соединение с базой данных для текущего запроса."""
    path = db_path or DB_PATH
    Path(path).parent.mkdir(parents=True, exist_ok=True) #необходимо для того, чтобы папка с бд точно существовала
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row  # Позволяет обращаться к колонкам по имени (row['id'])
    conn.execute("PRAGMA foreign_keys = ON")  # Строгая проверка внешних ключей
    conn.execute("PRAGMA journal_mode = WAL")  # Режим Write-Ahead Log для параллельного доступа
    conn.execute("PRAGMA busy_timeout = 5000")  # Ждёт 5 сек при блокировке таблицы вместо ошибки
    return conn


def init_db(db_path: str = None):
    """Создаёт все таблицы из schema.sql при первом запуске приложения."""
    path = db_path or DB_PATH

    # Проверяем, что файл схемы существует
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(
            f"Файл схемы не найден: {SCHEMA_PATH}\n"
            f"Текущая директория: {os.getcwd()}"
        )

    conn = get_db(path)
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()

