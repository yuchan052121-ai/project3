#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# app.py
from flask import Flask, g, render_template, request, redirect, url_for, flash
import sqlite3
import hashlib
import datetime
from typing import Optional

DATABASE = "reviews.db"
PER_PAGE = 50

app = Flask(__name__)
app.secret_key = "replace-with-a-secure-random-key"  # 本番ではランダムで安全なものに変更

def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
        g._database = db
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()

def make_user_id(name: str) -> str:
    return hashlib.sha256(name.encode("utf-8")).hexdigest()[:16]

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

@app.route("/")
def index():
    courses = query_db("SELECT * FROM courses ORDER BY code")
    return render_template("index.html", courses=courses)

# 検索フォーム -> 検索結果表示
@app.route("/search/")
def search():
    q_code = request.args.get("code", "").strip()
    q_title = request.args.get("title", "").strip()
    q_area = request.args.get("area", "").strip()
    q_year = request.args.get("year", type=int)
    q_semester = request.args.get("semester", "").strip()
    q_schedule = request.args.get("schedule", "").strip()

    sql = "SELECT * FROM courses WHERE 1=1"
    params = []

    if q_code:
        sql += " AND code LIKE ?"
        params.append(f"%{q_code}%")
    if q_title:
        sql += " AND title LIKE ?"
        params.append(f"%{q_title}%")
    if q_area:
        sql += " AND area = ?"
        params.append(q_area)
    if q_year:
        sql += " AND year = ?"
        params.append(q_year)
    if q_semester:
        sql += " AND semester = ?"
        params.append(q_semester)
    if q_schedule:
        sql += " AND schedule LIKE ?"
        params.append(f"%{q_schedule}%")

    sql += " ORDER BY code"
    courses = query_db(sql, tuple(params))
    return render_template("search_results.html", courses=courses,
                           code=q_code, title=q_title, area=q_area, year=q_year,
                           semester=q_semester, schedule=q_schedule)

@app.route("/course/<int:course_id>/")
@app.route("/course/<int:course_id>/page/<int:page>/")
def course_view(course_id, page=1):
    course = query_db("SELECT * FROM courses WHERE id=?", (course_id,), one=True)
    if not course:
        return "Course not found", 404

    # filter by min recommend if provided
    min_rec = request.args.get("min_recommend", type=int)
    sql = "SELECT * FROM reviews WHERE course_id=? AND active=1"
    params = [course_id]
    if min_rec:
        sql += " AND recommend>=?"
        params.append(min_rec)
    sql += " ORDER BY created_at DESC"
    reviews = query_db(sql, tuple(params))

    total = len(reviews)
    pages = (total + PER_PAGE - 1) // PER_PAGE
    start = (page - 1) * PER_PAGE
    end = start + PER_PAGE
    page_reviews = reviews[start:end]

    return render_template("course.html", course=course, reviews=page_reviews,
                           page=page, pages=pages, total=total, has_next=end < total, has_prev=start > 0,
                           min_recommend=min_rec)

@app.route("/course/<int:course_id>/add/", methods=["GET", "POST"])
def add_review(course_id):
    course = query_db("SELECT * FROM courses WHERE id=?", (course_id,), one=True)
    if not course:
        return "Course not found", 404

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        difficulty = request.form.get("difficulty", type=int)
        recommend = request.form.get("recommend", type=int)
        attendance = 1 if request.form.get("attendance") == "on" else 0
        assessment = request.form.get("assessment", "なし")
        comment = request.form.get("comment", "").strip()

        if not name or not difficulty or not recommend:
            flash("名前・難易度・おすすめの評価を正しく入力してください。")
            return redirect(url_for("add_review", course_id=course_id))

        user_id = make_user_id(name)
        now = datetime.datetime.utcnow().isoformat()
        db = get_db()
        try:
            db.execute("""
                INSERT INTO reviews (course_id, user_id, difficulty, recommend, attendance_required, assessment, comment, created_at, active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (course_id, user_id, difficulty, recommend, attendance, assessment, comment, now))
            db.commit()
            flash("レビューを追加しました。")
        except sqlite3.IntegrityError:
            flash("同じユーザの有効なレビューが既に存在します。まず取消してください。")
        return redirect(url_for("course_view", course_id=course_id))

    return render_template("add_review.html", course=course)

@app.route("/course/<int:course_id>/cancel", methods=["POST"])
def cancel_review(course_id):
    name = request.form.get("name", "").strip()
    if not name:
        flash("名前を入力してください。")
        return redirect(url_for("course_view", course_id=course_id))

    user_id = make_user_id(name)
    db = get_db()
    cur = db.execute("SELECT id FROM reviews WHERE course_id=? AND user_id=? AND active=1 ORDER BY created_at DESC LIMIT 1",
                     (course_id, user_id))
    row = cur.fetchone()
    cur.close()

    if not row:
        flash("アクティブなレビューが見つかりません。")
        return redirect(url_for("course_view", course_id=course_id))

    # delete old active=0 records to avoid UNIQUE violation, then set active=0
    db.execute("DELETE FROM reviews WHERE course_id=? AND user_id=? AND active=0", (course_id, user_id))
    db.execute("UPDATE reviews SET active=0 WHERE id=?", (row["id"],))
    db.commit()
    flash("レビューを取消しました。")
    return redirect(url_for("course_view", course_id=course_id))

# 管理用：シラバスCSV/スクレイプからのインポート（簡易版プレースホルダ）
@app.route("/admin/import_demo")
def admin_import_demo():
    # 実際はシラバスページをスクレイピングしてINSERTする実装を入れる
    db = get_db()
    # 例：CSVから読み込む処理や、requests + BeautifulSoupで解析してINSERTする処理をここに追加
    flash("Import placeholder: implement actual syllabus import.")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

