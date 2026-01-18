#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# app.py
from flask import Flask, g, render_template, request, redirect, url_for, flash
import sqlite3
import hashlib
import datetime

DATABASE = "reviews.db"
PER_PAGE = 50

app = Flask(__name__)
app.secret_key = "replace-with-a-secure-random-key"  # 本番では必ず変更

# -----------------------------
# DB 接続
# -----------------------------
def get_db():
    if "_database" not in g:
        g._database = sqlite3.connect(DATABASE)
        g._database.row_factory = sqlite3.Row
    return g._database

@app.teardown_appcontext
def close_connection(exception):
    db = g.pop("_database", None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rows = cur.fetchall()
    cur.close()
    return (rows[0] if rows else None) if one else rows

# -----------------------------
# ユーザー識別（簡易）
# -----------------------------
def make_user_id(name: str) -> str:
    return hashlib.sha256(name.encode("utf-8")).hexdigest()[:16]

# -----------------------------
# トップページ
# -----------------------------
@app.route("/")
def index():
    courses = query_db("SELECT * FROM courses ORDER BY code")
    return render_template("index.html", courses=courses)

# -----------------------------
# 検索
# -----------------------------
@app.route("/search/")
def search():
    q_code = request.args.get("code", "").strip()
    q_title = request.args.get("title", "").strip()
    q_area = request.args.get("area", "").strip()
    q_year = request.args.get("year", "").strip()
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
        sql += " AND year LIKE ?"
        params.append(f"%{q_year}%")
    if q_schedule:
        sql += " AND schedule LIKE ?"
        params.append(f"%{q_schedule}%")

    sql += " ORDER BY code"

    courses = query_db(sql, tuple(params))
    return render_template(
        "search_results.html",
        courses=courses,
        code=q_code,
        title=q_title,
        area=q_area,
        year=q_year,
        schedule=q_schedule,
    )

# -----------------------------
# 授業詳細 + 口コミ一覧
# -----------------------------
@app.route("/course/<int:course_id>/")
@app.route("/course/<int:course_id>/page/<int:page>/")
def course_view(course_id, page=1):
    course = query_db("SELECT * FROM courses WHERE id=?", (course_id,), one=True)
    if not course:
        return "Course not found", 404

    min_rec = request.args.get("min_recommend", type=int)

    sql = "SELECT * FROM reviews WHERE course_id=? AND active=1"
    params = [course_id]

    if min_rec:
        sql += " AND recommend >= ?"
        params.append(min_rec)

    sql += " ORDER BY created_at DESC"
    reviews = query_db(sql, tuple(params))

    total = len(reviews)
    pages = (total + PER_PAGE - 1) // PER_PAGE
    start = (page - 1) * PER_PAGE
    end = start + PER_PAGE
    page_reviews = reviews[start:end]

    return render_template(
        "course.html",
        course=course,
        reviews=page_reviews,
        page=page,
        pages=pages,
        total=total,
        has_next=end < total,
        has_prev=start > 0,
        min_recommend=min_rec,
    )

# -----------------------------
# 口コミ投稿
# -----------------------------
@app.route("/course/<int:course_id>/add/", methods=["GET", "POST"])
def add_review(course_id):
    course = query_db("SELECT * FROM courses WHERE id=?", (course_id,), one=True)
    if not course:
        return "Course not found", 404

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        recommend = request.form.get("recommend", type=int)
        difficulty = request.form.get("difficulty", type=int)
        fun = request.form.get("fun", type=int)
        learning = request.form.get("learning", type=int)
        attendance = 1 if request.form.get("attendance") == "on" else 0
        assessment = request.form.get("assessment", "").strip()
        comment = request.form.get("comment", "").strip()

        if not name or not all([recommend, difficulty, fun, learning]):
            flash("名前と4項目すべての評価（1〜5）を入力してください。")
            return redirect(url_for("add_review", course_id=course_id))

        user_id = make_user_id(name)
        now = datetime.datetime.utcnow().isoformat()
        db = get_db()

        try:
            db.execute("""
                INSERT INTO reviews (
                    course_id, user_id,
                    recommend, difficulty, fun, learning,
                    attendance_required, assessment,
                    comment, created_at, active
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (
                course_id, user_id,
                recommend, difficulty, fun, learning,
                attendance, assessment,
                comment, now
            ))
            db.commit()
            flash("レビューを追加しました。")
        except sqlite3.IntegrityError:
            flash("同じユーザーの有効なレビューが既に存在します。取消後に再投稿してください。")

        return redirect(url_for("course_view", course_id=course_id))

    return render_template("add_review.html", course=course)

# -----------------------------
# 口コミ取消
# -----------------------------
@app.route("/course/<int:course_id>/cancel", methods=["POST"])
def cancel_review(course_id):
    name = request.form.get("name", "").strip()
    if not name:
        flash("名前を入力してください。")
        return redirect(url_for("course_view", course_id=course_id))

    user_id = make_user_id(name)
    db = get_db()

    row = query_db("""
        SELECT id FROM reviews
        WHERE course_id=? AND user_id=? AND active=1
        ORDER BY created_at DESC LIMIT 1
    """, (course_id, user_id), one=True)

    if not row:
        flash("有効なレビューが見つかりません。")
        return redirect(url_for("course_view", course_id=course_id))

    db.execute("DELETE FROM reviews WHERE course_id=? AND user_id=? AND active=0", (course_id, user_id))
    db.execute("UPDATE reviews SET active=0 WHERE id=?", (row["id"],))
    db.commit()

    flash("レビューを取り消しました。")
    return redirect(url_for("course_view", course_id=course_id))

# -----------------------------
# 起動
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
