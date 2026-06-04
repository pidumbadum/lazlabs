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
from werkzeug.security import generate_password_hash


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
    conn = get_db(temp_db)
    yield conn
    conn.close()

@pytest.fixture
def login(client, db):
    """Фикстура: хелпер для входа пользователя."""
    def _do_login(login_name, pwd="123", role="student", linked_id=0):
        db.execute(
            "INSERT INTO users VALUES (NULL, ?, ?, ?, ?)",
            (login_name, generate_password_hash(pwd), role, linked_id)
        )
        db.commit()
        client.post("/login", data={"login": login_name, "password": pwd}, follow_redirects=True)
    return _do_login