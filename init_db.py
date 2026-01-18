import sqlite3

conn = sqlite3.connect("reviews.db")
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE,
    title TEXT,
    area TEXT,
    year TEXT,
    schedule TEXT
);
""")

c.execute("""
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER,
    user_id TEXT,

    recommend INTEGER,
    difficulty INTEGER,
    fun INTEGER,
    learning INTEGER,

    attendance_required INTEGER,
    assessment TEXT,
    comment TEXT,
    created_at TEXT,
    active INTEGER DEFAULT 1,

    UNIQUE(course_id, user_id, active)
);
""")

conn.commit()
conn.close()
print("DB initialized")
