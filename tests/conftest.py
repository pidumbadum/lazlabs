"""
Общие фикстуры для тестов Lazlabs.
"""
import pytest
import tempfile
import os
import sys

# Добавляем путь к пакетам
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'packages', 'core'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from core import init_db, get_db
from core.database import SCHEMA_PATH
from app.main import app as flask_app


@pytest.fixture
def temp_db(tmp_path):
    """Создаёт временную БД для тестов."""
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    return db_path


@pytest.fixture
def client(temp_db, monkeypatch):
    """Flask test client с временной БД."""
    # Патчим путь к БД
    import core.database
    monkeypatch.setattr(core.database, 'DB_PATH', temp_db)

    flask_app.config.update(
        TESTING=True,
        SECRET_KEY="test_key",
        UPLOAD_FOLDER=tempfile.mkdtemp()
    )

    with flask_app.test_client() as client:
        yield client


@pytest.fixture
def db(temp_db):
    """Соединение с временной БД."""
    return get_db(temp_db)

def _login(client, db, login, pwd="123", role="student", linked_id=0):
    """Хелпер: создаёт юзера и логинит его."""
    # NULL позволяет SQLite автоматически назначать уникальный id
    db.execute("INSERT INTO users VALUES (NULL, ?, ?, ?, ?)",
               (login, generate_password_hash(pwd), role, linked_id))
    db.commit()
    client.post("/login", data={"login": login, "password": pwd}, follow_redirects=True)