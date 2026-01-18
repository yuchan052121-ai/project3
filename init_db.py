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

    recommend INTEGER CHECK(recommend BETWEEN 1 AND 5),
    difficulty INTEGER CHECK(difficulty BETWEEN 1 AND 5),
    fun INTEGER CHECK(fun BETWEEN 1 AND 5),
    learning INTEGER CHECK(learning BETWEEN 1 AND 5),

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
