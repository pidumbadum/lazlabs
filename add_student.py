import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), "school.db")

if not os.path.exists(DB_PATH):
    print(" Файл school.db не найден. Сначала запустите app.py и остановите его (Ctrl+C).")
    exit()

conn = sqlite3.connect(DB_PATH)
pwd_hash = generate_password_hash("student123")

# 1. Создаём профиль студента
# id_group = NULL позволяет скрипту работать даже если в БД ещё нет созданных групп
conn.execute("""
INSERT INTO students (id_group, name, surname, phone_number, parent_name, parent_phone, parent_email)
VALUES (NULL, 'Петр', 'Петров', '+79001234567', 'Мария Петрова', '+79009876543', 'parent@example.com')
""")
student_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

# 2. Создаём учётную запись и привязываем к студенту
conn.execute("""INSERT OR IGNORE INTO users (login, password_hash, role, linked_entity_id)
VALUES ('student', ?, 'student', ?)""", (pwd_hash, student_id))

conn.commit()
conn.close()

print(" Студент успешно создан!")
print(" Логин: student")
print(" Пароль: student123")
print(" ФИО: Петр Петров")
print(" Телефон: +79001234567")
print(" Родитель: Мария Петрова")
print("Примечание: Группа не назначена (id_group=NULL). Назначьте её через админку директора.")