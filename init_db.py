import sqlite3

DB = "reviews.db"

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # courses（Excel連携）
    c.execute("""
    CREATE TABLE IF NOT EXISTS courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE,
        title TEXT,
        year TEXT,        -- 標準履修年次（文字列のまま）
        schedule TEXT,    -- 時間割
        area TEXT         -- 専攻区分
    )
    """)

    # reviews（4項目星評価）
    c.execute("""
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_id INTEGER,
        user_id TEXT,

        recommend INTEGER CHECK(recommend BETWEEN 1 AND 5),
        difficulty INTEGER CHECK(difficulty BETWEEN 1 AND 5),
        fun INTEGER CHECK(fun BETWEEN 1 AND 5),
        learning INTEGER CHECK(learning BETWEEN 1 AND 5),

        comment TEXT,
        created_at TEXT,
        active INTEGER DEFAULT 1,

        UNIQUE(course_id, user_id, active)
    )
    """)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("DB initialized")
