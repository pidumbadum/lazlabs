import sys
import os
from werkzeug.security import generate_password_hash

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'packages', 'core'))
from core import get_db, init_db
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