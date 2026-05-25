import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "school.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn

def init_db():
    conn = get_db()
    with open(os.path.join(os.path.dirname(__file__), "schema.sql"), "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    login TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT CHECK(role IN ('director', 'teacher', 'student')) NOT NULL,
    linked_entity_id INTEGER
);
CREATE TABLE IF NOT EXISTS teachers (
    id_teacher INTEGER PRIMARY KEY,
    name TEXT, surname TEXT,
    payout_percent REAL DEFAULT 0.0
);
CREATE TABLE IF NOT EXISTS students (
    id_student INTEGER PRIMARY KEY,
    id_group INTEGER,
    name TEXT, surname TEXT,
    phone_number TEXT,
    parent_name TEXT, parent_phone TEXT, parent_email TEXT
);
CREATE TABLE IF NOT EXISTS lessons (
    id_lesson INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    price_hour REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS study_groups (
    id_group INTEGER PRIMARY KEY,
    id_teacher INTEGER,
    id_lesson INTEGER,
    group_name TEXT,
    FOREIGN KEY(id_teacher) REFERENCES teachers(id_teacher),
    FOREIGN KEY(id_lesson) REFERENCES lessons(id_lesson)
);
CREATE TABLE IF NOT EXISTS schedule (
    id_schedule INTEGER PRIMARY KEY,
    id_group INTEGER,
    id_teacher INTEGER,
    date TEXT,
    time TEXT,
    is_completed BOOLEAN DEFAULT 0,
    FOREIGN KEY(id_group) REFERENCES study_groups(id_group)
);
CREATE TABLE IF NOT EXISTS tasks (
    id_task INTEGER PRIMARY KEY,
    id_group INTEGER,
    id_teacher INTEGER,
    id_lesson INTEGER,
    title TEXT,
    description TEXT,
    deadline TEXT,
    status TEXT DEFAULT 'active',
    max_points INTEGER,
    FOREIGN KEY(id_group) REFERENCES study_groups(id_group)
);
CREATE TABLE IF NOT EXISTS task_submissions (
    id_submission INTEGER PRIMARY KEY,
    id_task INTEGER,
    id_student INTEGER,
    grade INTEGER,
    submission_text TEXT,
    submission_file_path TEXT,
    submission_link TEXT,
    status TEXT DEFAULT 'pending',
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(id_task) REFERENCES tasks(id_task),
    FOREIGN KEY(id_student) REFERENCES students(id_student),
    UNIQUE(id_task, id_student)
);
CREATE TABLE IF NOT EXISTS accounting (
    id_operation INTEGER PRIMARY KEY,
    id_student INTEGER,
    id_lesson INTEGER,
    date TEXT,
    payment_amount REAL,
    is_paid BOOLEAN DEFAULT 0,
    classes_paid INTEGER,
    classes_left INTEGER,
    FOREIGN KEY(id_student) REFERENCES students(id_student)
);
"""