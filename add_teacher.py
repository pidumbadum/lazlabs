import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), "school.db")

if not os.path.exists(DB_PATH):
    print(" Файл school.db не найден. Сначала запустите app.py и остановите его (Ctrl+C).")
    exit()

conn = sqlite3.connect(DB_PATH)
pwd_hash = generate_password_hash("teacher123")

# 1. Создаём запись в таблице teachers с базовыми данными и процентом выплат
conn.execute("""
INSERT INTO teachers (name, surname, payout_percent)
VALUES ('Иван', 'Иванов', 50.0)
""")
# Получаем ID только что созданного преподавателя
teacher_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

# 2. Создаём учётную запись в users и привязываем её к teacher_id через linked_entity_id
# INSERT OR IGNORE предотвратит ошибку, если логин уже существует
conn.execute("""INSERT OR IGNORE INTO users (login, password_hash, role, linked_entity_id)
VALUES ('teacher', ?, 'teacher', ?)""", (pwd_hash, teacher_id))

conn.commit()
conn.close()

print(" Учитель успешно создан!")
print(" Логин: teacher")
print(" Пароль: teacher123")
print(" ФИО: Иван Иванов")
print(" Процент от занятий: 50%")