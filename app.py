#!/usr/bin/env python
# coding: utf-8

from flask import Flask, g, render_template, request, redirect, url_for, flash
import sqlite3
import hashlib
import datetime
import sys
import os
import re 
import numpy as np

# 1. パス設定とインポート
sys.path.append(os.path.join(os.path.dirname(__file__), 'recommender'))
from recommend_algo import TopicBasedRecommender

# 2. 定数・グローバル変数
DATABASE = "reviews.db"
PER_PAGE = 50
recommender_engine = None

app = Flask(__name__)
app.secret_key = "secure-tsukuba-key" # セッション管理用の鍵

# --- 追加: 学籍番号の形式チェック関数 ---
def is_valid_student_id(student_id):
    """半角数字9桁であるかチェックする"""
    return bool(re.fullmatch(r'\d{9}', student_id))

# 3. 推薦エンジンの初期化（エラー回避ロジック）
def get_recommender():
    global recommender_engine
    if recommender_engine is None:
        print("推薦エンジンを初期化中...")
        try:
            recommender_engine = TopicBasedRecommender(df_grad=None, num_topics=6)
            recommender_engine.assign_info_to_courses()
            recommender_engine.train_lda()
            print("推薦エンジンの準備が完了しました。")
        except Exception as e:
            print(f"エンジン初期化エラー: {e}")
            recommender_engine = None
    return recommender_engine

# 4. データベース管理
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

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def make_user_id(name: str) -> str:
    """学籍番号をハッシュ化して16文字のIDにする"""
    return hashlib.sha256(name.encode("utf-8")).hexdigest()[:16]

# 5. ルート定義（メイン機能）
@app.route("/")
def index():
    courses = query_db("SELECT * FROM courses ORDER BY code")
    return render_template("index.html", courses=courses)

@app.route("/search/")
def search():
    q_title = request.args.get("title", "").strip()
    q_year = request.args.get("year", type=int)
    q_semester = request.args.get("semester", "").strip()

    sql = "SELECT * FROM courses WHERE 1=1"
    params = []

    if q_title:
        sql += " AND title LIKE ?"
        params.append(f"%{q_title}%")
    if q_year:
        sql += " AND year = ?"
        params.append(q_year)
    if q_semester:
        sql += " AND semester = ?"
        params.append(q_semester)

    sql += " ORDER BY code"
    courses = query_db(sql, tuple(params))
    return render_template("search_results.html", courses=courses, title=q_title)

@app.route("/course/<int:course_id>/")
def course_view(course_id):
    course = query_db("SELECT * FROM courses WHERE id=?", (course_id,), one=True)
    if not course:
        return "授業が見つかりません", 404

    reviews = query_db("SELECT * FROM reviews WHERE course_id=? AND active=1 ORDER BY created_at DESC", (course_id,))
    return render_template("course.html", course=course, reviews=reviews)

@app.route("/course/<int:course_id>/add/", methods=["GET", "POST"])
def add_review(course_id):
    course = query_db("SELECT * FROM courses WHERE id=?", (course_id,), one=True)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        diff = request.form.get("difficulty", type=int)
        rec = request.form.get("recommend", type=int)
        comment = request.form.get("comment", "").strip()

        if not name or not rec:
            flash("学籍番号とおすすめ度は必須です。")
            return redirect(url_for("add_review", course_id=course_id))
        
        if not is_valid_student_id(name):
            flash("学籍番号は9桁の半角数字で入力してください。")
            return redirect(url_for("add_review", course_id=course_id))

        user_id = make_user_id(name)
        db = get_db()
        db.execute("""
            INSERT INTO reviews (course_id, user_id, difficulty, recommend, comment, created_at, active)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        """, (course_id, user_id, diff, rec, comment, datetime.datetime.now().isoformat()))
        db.commit()
        flash("レビューを投稿しました。")
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
    db.execute("UPDATE reviews SET active=0 WHERE course_id=? AND user_id=? AND active=1", (course_id, user_id))
    db.commit()
    
    flash("レビューを取り消しました。")
    return redirect(url_for("course_view", course_id=course_id))

# 6. 推薦ロジック
@app.route("/recommendations", methods=["GET", "POST"])
def show_recommendations():
    recommendations = []
    user_name = ""
    user_analysis = []

    if request.method == "POST":
        user_name = request.form.get("name", "").strip()
        
        if not user_name:
            flash("学籍番号を入力してください。")
            return redirect(url_for("show_recommendations"))
        if not is_valid_student_id(user_name):
            flash("学籍番号は9桁の半角数字で入力してください。")
            return redirect(url_for("show_recommendations"))

        user_id = make_user_id(user_name)
        db = get_db()
        rows = db.execute("""
            SELECT c.title, r.recommend 
            FROM reviews r 
            JOIN courses c ON r.course_id = c.id 
            WHERE r.user_id = ? AND r.active = 1
        """, (user_id,)).fetchall()

        if not rows:
            flash(f"学籍番号 {user_name} さんのレビューがありません。先に投稿してください。")
        else:
            engine = get_recommender()
            try:
                user_rated_titles = [row['title'] for row in rows]
                user_ratings_dict = {row['title']: row['recommend'] for row in rows}

                # --- Colabと同一の配列マッピング ---
                final_ratings = np.zeros(len(engine.df_combined))
                for i, title in enumerate(engine.df_combined['授業科目名']):
                    if title in user_ratings_dict:
                        final_ratings[i] = user_ratings_dict[title]

                # プロファイルの学習実行
                engine.update_user_profile(final_ratings)
                
                # 推薦リストの取得
                all_recs = engine.get_social_recommendations_as_dict(top_n=50)
                
                # 既に評価した授業を除外（※Colabと挙動を合わせるなら除外しない選択もありますが、実用上は除外を推奨）
                recommendations = [
                    c for c in all_recs 
                    if c['授業科目名'] not in user_rated_titles
                ][:10]
                
                # --- 分析結果(％)の作成 ---
                for i, percent in enumerate(engine.user_profile_percent):
                    user_analysis.append({
                        'topic': engine._number_to_char(i),
                        'percent': percent
                    })
                
                # 表示用にnan対策
                for rec in recommendations:
                    for key in rec:
                        if str(rec[key]).lower() == 'nan':
                            rec[key] = ""
                                        
            except Exception as e:
                flash(f"推薦中にエラーが発生しました: {e}")

    return render_template("recommendations.html", recs=recommendations, user_name=user_name, analysis=user_analysis)


if __name__ == "__main__":
    with app.app_context():
        get_recommender()
    app.run(host="0.0.0.0", port=5000, debug=True)
# finish