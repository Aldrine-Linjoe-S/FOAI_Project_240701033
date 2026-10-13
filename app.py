"""CareerCompass AI — Flask application."""
import json
import os
import secrets
import sqlite3
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import (Flask, abort, flash, g, jsonify, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

from database import connect_db, init_db
from recommendation_engine import CAREERS, all_careers, career_by_slug, recommend

BASE_DIR = Path(__file__).resolve().parent

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(SECRET_KEY=os.environ.get("CAREERCOMPASS_SECRET", "dev-only-change-me"),
        DATABASE=str(Path(app.instance_path) / "careercompass.sqlite3"),
        SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")
    if test_config: app.config.update(test_config)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    with app.app_context(): init_db(app.config["DATABASE"])
    app.add_template_filter(lambda value: {"Beginner": 1, "Intermediate": 2, "Advanced": 3}.get(value, 0), "level_value")

    def db():
        if "db" not in g: g.db = connect_db(app.config["DATABASE"])
        return g.db
    @app.teardown_appcontext
    def close_db(error=None):
        connection = g.pop("db", None)
        if connection is not None: connection.close()

    @app.before_request
    def load_user():
        g.user = None
        if session.get("user_id"):
            g.user = db().execute("SELECT id,name,email FROM users WHERE id=?", (session["user_id"],)).fetchone()
            if g.user is None: session.clear()
        if "csrf_token" not in session: session["csrf_token"] = secrets.token_urlsafe(32)

    @app.context_processor
    def inject_helpers(): return {"csrf_token": lambda: session.get("csrf_token", "")}

    @app.before_request
    def csrf_protect():
        if request.method == "POST":
            sent = request.form.get("csrf_token", "")
            if not sent or not secrets.compare_digest(sent, session.get("csrf_token", "")):
                abort(400, description="This form expired. Please reload the page and try again.")

    def login_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if g.user is None:
                flash("Please sign in to continue.", "info")
                return redirect(url_for("login", next=request.path))
            return view(*args, **kwargs)
        return wrapped

    def latest_assessment():
        row = db().execute("SELECT * FROM assessments WHERE user_id=? ORDER BY created_at DESC,id DESC LIMIT 1", (g.user["id"],)).fetchone()
        if not row: return None, None, None
        return row, json.loads(row["answers"]), json.loads(row["results"])

    @app.route("/")
    def home(): return render_template("index.html", careers=CAREERS[:4])

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if g.user: return redirect(url_for("dashboard"))
        if request.method == "POST":
            name = request.form.get("name", "").strip()[:80]
            email = request.form.get("email", "").strip().lower()[:254]
            password = request.form.get("password", "")
            if not name or "@" not in email or len(password) < 8:
                flash("Enter your name, a valid email, and a password with at least 8 characters.", "danger")
            else:
                try:
                    cur = db().execute("INSERT INTO users(name,email,password_hash) VALUES(?,?,?)", (name,email,generate_password_hash(password)))
                    db().commit(); session.clear(); session["user_id"] = cur.lastrowid; session["csrf_token"] = secrets.token_urlsafe(32)
                    flash("Your account is ready. Let’s discover your next steps.", "success")
                    return redirect(url_for("dashboard"))
                except sqlite3.IntegrityError: flash("That email is already registered. Try signing in.", "warning")
        return render_template("auth.html", mode="register")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if g.user: return redirect(url_for("dashboard"))
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            user = db().execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
            if user and check_password_hash(user["password_hash"], request.form.get("password", "")):
                session.clear(); session["user_id"] = user["id"]; session["csrf_token"] = secrets.token_urlsafe(32)
                flash("Welcome back.", "success")
                next_url = request.args.get("next", "")
                if next_url.startswith("/") and not next_url.startswith("//"): return redirect(next_url)
                return redirect(url_for("dashboard"))
            flash("Email or password wasn’t recognized.", "danger")
        return render_template("auth.html", mode="login")

    @app.route("/logout", methods=["POST"])
    def logout():
        session.clear(); flash("You’re signed out.", "info"); return redirect(url_for("home"))

    @app.route("/dashboard")
    @login_required
    def dashboard():
        row, answers, results = latest_assessment()
        history = db().execute("SELECT id,created_at,results FROM assessments WHERE user_id=? ORDER BY created_at DESC,id DESC LIMIT 6", (g.user["id"],)).fetchall()
        history_data = [{"date": h["created_at"][:10], "score": json.loads(h["results"])[0]["score"] if json.loads(h["results"]) else 0} for h in reversed(history)]
        return render_template("dashboard.html", result=results[0] if results else None, results=results or [], answers=answers or {}, history=history, history_data=history_data)

    @app.route("/assessment", methods=["GET", "POST"])
    @login_required
    def assessment():
        if request.method == "POST":
            answers = {"education":request.form.get("education",""), "subjects":request.form.getlist("subjects"),
                "performance":request.form.get("performance",""), "skill_levels":{}, "interests":request.form.getlist("interests"),
                "strengths":request.form.getlist("strengths"), "work_styles":request.form.getlist("work_styles"),
                "career_directions":request.form.getlist("career_directions"), "hours_per_week":request.form.get("hours_per_week",""),
                "learning_style":request.form.get("learning_style",""), "goal":request.form.get("goal","").strip()[:500]}
            for skill in request.form.getlist("skill_names"):
                level = request.form.get("level_" + skill, "")
                if level in ("Beginner", "Intermediate", "Advanced"): answers["skill_levels"][skill] = level
            if not answers["education"] or not (answers["interests"] or answers["skill_levels"] or answers["strengths"]):
                flash("Please complete your education level and at least one skills, interests, or strengths selection.", "danger")
                return render_template("assessment.html", answers=answers, careers=CAREERS)
            results = recommend(answers)
            cur = db().execute("INSERT INTO assessments(user_id,answers,results) VALUES(?,?,?)", (g.user["id"],json.dumps(answers),json.dumps(results)))
            db().commit(); return redirect(url_for("results", assessment_id=cur.lastrowid))
        _, answers, _ = latest_assessment()
        return render_template("assessment.html", answers=answers or {}, careers=CAREERS)

    def assessment_record(assessment_id):
        row = db().execute("SELECT * FROM assessments WHERE id=? AND user_id=?", (assessment_id,g.user["id"])).fetchone()
        if row is None: abort(404)
        return row, json.loads(row["answers"]), json.loads(row["results"])

    @app.route("/results")
    @app.route("/results/<int:assessment_id>")
    @login_required
    def results(assessment_id=None):
        if assessment_id is not None: row, answers, matches = assessment_record(assessment_id)
        else:
            row, answers, matches = latest_assessment()
            if row is None: return redirect(url_for("assessment"))
        return render_template("results.html", assessment=row, answers=answers, matches=matches)

    @app.route("/careers")
    def careers():
        query = request.args.get("q", "").strip().lower()
        category = request.args.get("category", "")
        skills = request.args.getlist("skill")
        items = all_careers()
        if query: items = [c for c in items if query in (c["name"]+" "+c["summary"]+" "+" ".join(c["skills"])).lower()]
        if category: items = [c for c in items if c["category"] == category]
        if skills: items = [c for c in items if set(skills) & set(c["skills"])]
        return render_template("careers.html", careers=items, categories=sorted({c["category"] for c in CAREERS}), query=query, category=category)

    @app.route("/careers/<slug>")
    def career_detail(slug):
        career = career_by_slug(slug)
        if career is None: abort(404)
        return render_template("career_detail.html", career=career)

    @app.route("/roadmap/<slug>", methods=["GET", "POST"])
    @login_required
    def roadmap(slug):
        career = career_by_slug(slug)
        if career is None: abort(404)
        if request.method == "POST":
            if request.form.get("action") == "reset":
                db().execute("DELETE FROM roadmap_progress WHERE user_id=? AND career_slug=?", (g.user["id"],slug))
            else:
                checked = set(request.form.getlist("task_id"))
                for i, stage in enumerate(career["roadmap"]):
                    for j in range(3):
                        task = f"{i}-{j}"
                        done = int(task in checked)
                        db().execute("INSERT INTO roadmap_progress(user_id,career_slug,task_id,completed) VALUES(?,?,?,?) ON CONFLICT(user_id,career_slug,task_id) DO UPDATE SET completed=excluded.completed,updated_at=CURRENT_TIMESTAMP", (g.user["id"],slug,task,done))
            db().commit(); flash("Roadmap progress updated.", "success"); return redirect(url_for("roadmap",slug=slug))
        rows = db().execute("SELECT task_id,completed FROM roadmap_progress WHERE user_id=? AND career_slug=?", (g.user["id"],slug)).fetchall()
        state = {r["task_id"]: bool(r["completed"]) for r in rows}
        total = 3 * len(career["roadmap"])
        done = sum(state.get(f"{i}-{j}",False) for i,stage in enumerate(career["roadmap"]) for j in range(len(stage)))
        return render_template("roadmap.html", career=career, progress=state, total=total, done=done, percent=round(100*done/total) if total else 0)

    @app.route("/skills")
    @login_required
    def skills():
        _, answers, results = latest_assessment()
        chosen = request.args.get("career", "")
        career = career_by_slug(chosen) if chosen else (results[0] if results else None)
        levels = (answers or {}).get("skill_levels", {})
        have = {s for s,l in levels.items() if l in ("Intermediate","Advanced")}
        gaps = [{"name":s,"level":levels.get(s,"Not selected"),"priority":"High" if s in (career or {}).get("skills",[])[:2] else "Medium"} for s in (career or {}).get("skills",[]) if s not in have]
        return render_template("skills.html", career=career, answers=answers or {}, careers=CAREERS, gaps=gaps)

    @app.route("/history")
    @login_required
    def history():
        rows = db().execute("SELECT id,created_at,results FROM assessments WHERE user_id=? ORDER BY created_at DESC,id DESC", (g.user["id"],)).fetchall()
        records = [{"id":r["id"],"created_at":r["created_at"],"results":json.loads(r["results"])} for r in rows]
        chart = [{"date":r["created_at"][:10],"score":r["results"][0]["score"] if r["results"] else 0} for r in reversed(records)]
        return render_template("history.html", records=records, chart=chart)

    @app.errorhandler(400)
    def bad_request(error): return render_template("error.html", code=400, message=getattr(error,"description","The request could not be completed.")),400
    @app.errorhandler(404)
    def not_found(error): return render_template("error.html", code=404, message="We couldn’t find that page. Try exploring careers instead."),404
    @app.errorhandler(500)
    def server_error(error): return render_template("error.html", code=500, message="Something went wrong. Please try again."),500
    return app

app = create_app()
if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "1") == "1")
