import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), "school.db")

# Проверяем, создана ли БД. Если нет, просим сначала запустить app.py для инициализации схемы.
if not os.path.exists(DB_PATH):
    print(" Файл school.db не найден. Сначала запустите app.py и остановите его (Ctrl+C).")
    exit()

conn = sqlite3.connect(DB_PATH)
# Хэшируем пароль безопасным способом (не храним в открытом виде)
pwd_hash = generate_password_hash("admin123")

# Добавляем запись в таблицу users с ролью 'director'
# linked_entity_id = 0, так как у директора нет отдельной таблицы профиля
conn.execute("""INSERT OR IGNORE INTO users (login, password_hash, role, linked_entity_id)
VALUES ('director', ?, 'director', 0)""", (pwd_hash,))

conn.commit()
conn.close()

print(" Директор успешно создан!")
print(" Логин: director")
print(" Пароль: admin123")