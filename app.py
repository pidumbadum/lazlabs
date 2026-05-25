import os
import datetime
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, g
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db, init_db, SCHEMA_SQL
from functools import wraps

app = Flask(__name__)
app.secret_key = os.urandom(24)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Генерация schema.sql для удобства отладки
with open(os.path.join(os.path.dirname(__file__), "schema.sql"), "w", encoding="utf-8") as f:
    f.write(SCHEMA_SQL)

# Инициализация БД при первом запуске
init_db()

@app.teardown_appcontext
def close_db(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()

@app.route("/")
def index():
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True, port=5000)