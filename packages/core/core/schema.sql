-- Таблица учётных записей (логин, пароль, роль, ссылка на профиль)
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    login TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT CHECK(role IN ('director', 'teacher', 'student')) NOT NULL,
    linked_entity_id INTEGER
);

-- Профили преподавателей
CREATE TABLE IF NOT EXISTS teachers (
    id_teacher INTEGER PRIMARY KEY,
    name TEXT, surname TEXT,
    payout_percent REAL DEFAULT 0.0  -- Процент от стоимости занятия, получаемый учителем
);

-- Профили студентов
CREATE TABLE IF NOT EXISTS students (
    id_student INTEGER PRIMARY KEY,
    id_group INTEGER,
    name TEXT, surname TEXT,
    phone_number TEXT,
    parent_name TEXT, parent_phone TEXT, parent_email TEXT
);

-- Предметы/дисциплины
CREATE TABLE IF NOT EXISTS lessons (
    id_lesson INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    price_hour REAL NOT NULL  -- Стоимость часа занятия
);

-- Учебные группы (привязаны к учителю и предмету)
CREATE TABLE IF NOT EXISTS study_groups (
    id_group INTEGER PRIMARY KEY,
    id_teacher INTEGER,
    id_lesson INTEGER,
    group_name TEXT,
    FOREIGN KEY(id_teacher) REFERENCES teachers(id_teacher),
    FOREIGN KEY(id_lesson) REFERENCES lessons(id_lesson)
);

-- Расписание занятий
CREATE TABLE IF NOT EXISTS schedule (
    id_schedule INTEGER PRIMARY KEY,
    id_group INTEGER,
    id_teacher INTEGER,
    date TEXT,
    time TEXT,
    is_completed BOOLEAN DEFAULT 0,  -- Флаг: занятие проведено или нет
    FOREIGN KEY(id_group) REFERENCES study_groups(id_group)
);

-- Домашние/классные задания
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

-- Ответы студентов на задания
CREATE TABLE IF NOT EXISTS task_submissions (
    id_submission INTEGER PRIMARY KEY,
    id_task INTEGER,
    id_student INTEGER,
    grade INTEGER,
    submission_text TEXT,
    submission_file_path TEXT,
    submission_link TEXT,
    status TEXT DEFAULT 'pending',  -- pending/submitted/checked
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(id_task) REFERENCES tasks(id_task),
    FOREIGN KEY(id_student) REFERENCES students(id_student),
    UNIQUE(id_task, id_student)  -- Один ответ на задание от одного студента
);

-- Финансовый учёт (оплаты и остатки)
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