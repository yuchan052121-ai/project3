from flask import Flask, g, render_template, request, redirect, url_for, flash
import sqlite3, hashlib, datetime

app = Flask(__name__)
app.secret_key = "project3-secret"
DB = "reviews.db"
PER_PAGE = 50

def get_db():
    if "_db" not in g:
        g._db = sqlite3.connect(DB)
        g._db.row_factory = sqlite3.Row
    return g._db

@app.teardown_appcontext
def close_db(e):
    db = g.pop("_db", None)
    if db:
        db.close()

def user_id(name):
    return hashlib.sha256(name.encode()).hexdigest()[:16]

@app.route("/")
def index():
    courses = get_db().execute("SELECT * FROM courses ORDER BY code").fetchall()
    return render_template("index.html", courses=courses)

@app.route("/search/")
def search():
    args = request.args
    sql = "SELECT * FROM courses WHERE 1=1"
    params = []

    for col, key in [("code","code"),("title","title"),("year","year"),
                     ("schedule","schedule"),("area","area")]:
        if args.get(key):
            sql += f" AND {col} LIKE ?"
            params.append(f"%{args.get(key)}%")

    courses = get_db().execute(sql, params).fetchall()
    return render_template("search_results.html", courses=courses)

@app.route("/course/<int:id>/")
def course(id):
    db = get_db()
    course = db.execute("SELECT * FROM courses WHERE id=?", (id,)).fetchone()
    reviews = db.execute("""
        SELECT * FROM reviews
        WHERE course_id=? AND active=1
        ORDER BY created_at DESC
    """, (id,)).fetchall()
    return render_template("course.html", course=course, reviews=reviews)

@app.route("/course/<int:id>/add/", methods=["GET","POST"])
def add_review(id):
    if request.method == "POST":
        name = request.form["name"]
        now = datetime.datetime.now().isoformat()
        db = get_db()
        try:
            db.execute("""
                INSERT INTO reviews
                (course_id,user_id,recommend,difficulty,fun,learning,comment,created_at)
                VALUES (?,?,?,?,?,?,?,?)
            """, (
                id, user_id(name),
                int(request.form["recommend"]),
                int(request.form["difficulty"]),
                int(request.form["fun"]),
                int(request.form["learning"]),
                request.form["comment"],
                now
            ))
            db.commit()
            flash("投稿しました")
        except sqlite3.IntegrityError:
            flash("既に投稿済みです（取消してください）")
        return redirect(url_for("course", id=id))
    return render_template("add_review.html", id=id)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
