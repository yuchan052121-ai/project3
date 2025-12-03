#!/usr/bin/env python
# coding: utf-8

# In[1]:


# init_db.py
import sqlite3
import datetime

DB = "reviews.db"

def init_db(path=DB):
    conn = sqlite3.connect(path)
    c = conn.cursor()

    # courses テーブル（シラバス情報に合わせてフィールドを拡張）
    c.execute("""
    CREATE TABLE IF NOT EXISTS courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE,
        title TEXT,
        area TEXT,            -- 専攻区分（例: 基礎, 社会経済システム, 経営工学, 都市計画, その他）
        year INTEGER,         -- 標準履修年次（例: 1,2,3,4）
        semester TEXT,        -- 実施学期（例: 前期, 後期, 通年）
        schedule TEXT,        -- 曜時限（例: 月1, 火3-4）
        credits REAL,
        syllabus_url TEXT
    )
    """)

    # reviews テーブル
    c.execute("""
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_id INTEGER,
        user_id TEXT,
        difficulty INTEGER CHECK(difficulty>=1 AND difficulty<=5),   -- 単位取得難易度
        recommend INTEGER CHECK(recommend>=1 AND recommend<=5),     -- おすすめ度
        attendance_required INTEGER DEFAULT 0,  -- 出席確認の有無 (0/1)
        assessment TEXT,      -- "テスト" / "レポート" / "両方" / "なし"
        comment TEXT,
        created_at TIMESTAMP,
        active INTEGER DEFAULT 1,
        UNIQUE(course_id, user_id, active)
    )
    """)

    conn.commit()
    return conn

def seed_sample_courses(conn):
    c = conn.cursor()
    sample = [
        ("SES101", "社会経済入門", "基礎", 1, "前期", "月1", 2, None),
        ("ENG201", "経営工学基礎", "経営工学", 2, "前期", "火2-3", 2, None),
        ("URP301", "都市計画論", "都市計画", 3, "後期", "水4", 2, None),
        ("STAT220", "統計学入門", "基礎", 2, "前期", "木3", 2, None),
    ]
    for code, title, area, year, sem, sched, credits, url in sample:
        try:
            c.execute("""
                INSERT INTO courses (code, title, area, year, semester, schedule, credits, syllabus_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (code, title, area, year, sem, sched, credits, url))
        except sqlite3.IntegrityError:
            pass
    conn.commit()

if __name__ == "__main__":
    conn = init_db()
    seed_sample_courses(conn)
    print("Initialized DB as reviews.db with sample courses.")
    conn.close()

