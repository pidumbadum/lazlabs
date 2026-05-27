import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), "school.db")

if not os.path.exists(DB_PATH):
    print(" Файл school.db не найден. Сначала запустите app.py и остановите его (Ctrl+C).")
    exit()

conn = sqlite3.connect(DB_PATH)
pwd_hash = generate_password_hash("admin123")

conn.execute("""INSERT OR IGNORE INTO users (login, password_hash, role, linked_entity_id)
    VALUES ('director', ?, 'director', 0)""", (pwd_hash,))

conn.commit()
conn.close()

print("Директор успешно создан!")
print(" Логин: director")
print(" Пароль: admin123")