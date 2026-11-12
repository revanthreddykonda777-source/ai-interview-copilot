from collections import defaultdict
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, g, abort
import hashlib
import hmac
import sqlite3
import os
import re
import secrets
import time
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from backend.db import create_database, DEFAULT_DB_PATH
from backend.services.resume_parser import extract_text
from backend.services.skill_extractor import extract_skills
from backend.services.answer_evaluator import evaluate_answer as coach_evaluator
from backend.services.question_generator import generate_interview_questions

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(BASE_DIR, "frontend", "templates")
STATIC_DIR = os.path.join(BASE_DIR, "frontend", "static")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
SECRET_FILE_PATH = os.path.join(BASE_DIR, "data", ".flask_secret")

load_dotenv(os.path.join(BASE_DIR, ".env"))


def _get_or_create_secret_key():
    env_key = (os.getenv("FLASK_SECRET_KEY") or "").strip()
    if env_key:
        return env_key
    os.makedirs(os.path.dirname(SECRET_FILE_PATH), exist_ok=True)
    if os.path.exists(SECRET_FILE_PATH):
        with open(SECRET_FILE_PATH, "r", encoding="utf-8") as fh:
            stored = fh.read().strip()
            if stored:
                return stored
    generated = secrets.token_hex(32)
    with open(SECRET_FILE_PATH, "w", encoding="utf-8") as fh:
        fh.write(generated)
    try:
        os.chmod(SECRET_FILE_PATH, 0o600)
    except OSError:
        pass
    return generated


app = Flask(
    __name__,
    template_folder=TEMPLATE_DIR,
    static_folder=STATIC_DIR,
    static_url_path="/static",
)
app.secret_key = _get_or_create_secret_key()
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true",
    MAX_CONTENT_LENGTH=5 * 1024 * 1024,  # 5 MB max upload
)

PASSWORD_HASH_METHOD = "scrypt"
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128
EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_RATE_BUCKETS = defaultdict(list)


def _client_ip():
    return request.remote_addr or "unknown"


def _is_rate_limited(bucket_name, limit, window_seconds):
    now = time.time()
    key = f"{bucket_name}:{_client_ip()}"
    timestamps = [t for t in _RATE_BUCKETS[key] if now - t < window_seconds]
    if len(timestamps) >= limit:
        _RATE_BUCKETS[key] = timestamps
        return True
    timestamps.append(now)
    _RATE_BUCKETS[key] = timestamps
    return False


def get_csrf_token():
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_hex(32)
        session["csrf_token"] = token
    return token


@app.context_processor
def inject_security_context():
    return {"csrf_token": get_csrf_token}


@app.before_request
def verify_csrf():
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        expected = session.get("csrf_token") or ""
        provided = (
            request.headers.get("X-CSRFToken")
            or request.form.get("csrf_token")
            or ""
        )
        if not expected or not provided or not hmac.compare_digest(provided, expected):
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"success": False, "error": "Invalid or missing CSRF token."}), 403
            abort(403, description="Invalid or missing CSRF token. Please refresh and try again.")


@app.after_request
def apply_security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(self), geolocation=()")
    return response


@app.errorhandler(413)
def handle_large_upload(err):
    flash("Uploaded file is too large. Maximum allowed size is 5 MB.", "error")
    return redirect(url_for("resume"))


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DEFAULT_DB_PATH)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    error = None
    if request.method == "POST":
        if _is_rate_limited("login", limit=15, window_seconds=300):
            return render_template("login.html", error="Too many login attempts. Please wait a few minutes and try again."), 429
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

        pwd_match = False
        if user and isinstance(user["password"], str) and user["password"].startswith(("scrypt:", "pbkdf2:")):
            try:
                pwd_match = check_password_hash(user["password"], password)
            except Exception:
                pwd_match = False

        if user and pwd_match:
            session.clear()
            session["user_id"] = user["id"]
            session["fullname"] = user["fullname"]
            session["role"] = user["role"] if "role" in user.keys() and user["role"] else "user"
            session["csrf_token"] = secrets.token_hex(32)
            return redirect(url_for("dashboard"))
        error = "Invalid email or password. Please try again."
    return render_template("login.html", error=error)

@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    error = None
    if request.method == "POST":
        if _is_rate_limited("register", limit=10, window_seconds=600):
            return render_template("register.html", error="Too many registration attempts. Please try again later."), 429
        fullname = request.form.get("fullname", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not fullname or not email or not password:
            error = "All fields are required."
        elif len(fullname) > 100 or not EMAIL_REGEX.match(email):
            error = "Please provide a valid name and email address."
        elif len(password) < MIN_PASSWORD_LENGTH:
            error = f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
        elif len(password) > MAX_PASSWORD_LENGTH:
            error = f"Password must be at most {MAX_PASSWORD_LENGTH} characters."
        else:
            db = get_db()
            if db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone():
                error = "An account with that email already exists."
            else:
                hashed_password = generate_password_hash(password, method=PASSWORD_HASH_METHOD)
                db.execute("INSERT INTO users (fullname, email, password, role) VALUES (?, ?, ?, 'user')",
                           (fullname, email, hashed_password))
                db.commit()
                flash("Account created! Please log in.", "success")
                return redirect(url_for("login"))
    return render_template("register.html", error=error)

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    error = None
    info = None
    if request.method == "POST":
        if _is_rate_limited("forgot_password", limit=5, window_seconds=300):
            return render_template("forgot_password.html", error="Too many reset requests. Please wait a few minutes."), 429
        email = request.form.get("email", "").strip().lower()
        if not email or not EMAIL_REGEX.match(email):
            error = "Please enter a valid email address."
        else:
            db = get_db()
            user = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
            if user:
                raw_token = secrets.token_urlsafe(32)
                token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
                expires_at = int(time.time()) + 900  # 15 minutes
                db.execute(
                    "UPDATE users SET reset_token_hash = ?, reset_token_expires = ? WHERE id = ?",
                    (token_hash, expires_at, user["id"]),
                )
                db.commit()
                reset_link = url_for("reset_password", token=raw_token, _external=True)
                print(f"[SECURITY] One-time password reset link generated for user_id={user['id']}: {reset_link}")
            info = "If an account matches that email, a time-limited reset link has been generated (check the server console in local mode)."
    return render_template("forgot_password.html", error=error, info=info)

@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    token = (request.args.get("token") or request.form.get("token") or "").strip()
    if not token:
        flash("A valid, non-expired password reset link is required.", "error")
        return redirect(url_for("forgot_password"))

    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    now = int(time.time())
    db = get_db()
    user = db.execute(
        "SELECT id FROM users WHERE reset_token_hash = ? AND reset_token_expires > ?",
        (token_hash, now),
    ).fetchone()
    if not user:
        return render_template("reset_password.html", token="", error="This reset link is invalid or has expired. Please request a new one."), 400

    error = None
    if request.method == "POST":
        if _is_rate_limited("reset_password", limit=5, window_seconds=300):
            return render_template("reset_password.html", token=token, error="Too many attempts. Please wait a few minutes."), 429
        new_pwd = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        if not new_pwd or not confirm:
            error = "Both fields are required."
        elif len(new_pwd) < MIN_PASSWORD_LENGTH:
            error = f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
        elif len(new_pwd) > MAX_PASSWORD_LENGTH:
            error = f"Password must be at most {MAX_PASSWORD_LENGTH} characters."
        elif new_pwd != confirm:
            error = "Passwords do not match."
        else:
            hashed_password = generate_password_hash(new_pwd, method=PASSWORD_HASH_METHOD)
            db.execute(
                "UPDATE users SET password = ?, reset_token_hash = NULL, reset_token_expires = NULL WHERE id = ?",
                (hashed_password, user["id"]),
            )
            db.commit()
            session.clear()
            flash("Password reset successfully! Please log in.", "success")
            return redirect(url_for("login"))
    return render_template("reset_password.html", token=token, error=error)

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


def _delete_user_uploads(uid):
    prefix = f"{uid}_"
    if not os.path.isdir(UPLOAD_DIR):
        return
    for name in os.listdir(UPLOAD_DIR):
        if name.startswith(prefix):
            try:
                os.remove(os.path.join(UPLOAD_DIR, name))
            except OSError:
                pass


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template(
        "dashboard.html",
        fullname=session.get("fullname", "User"),
        role=session.get("role", "user"),
    )


@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    uid = session["user_id"]
    user = db.execute(
        "SELECT id, fullname, email, password, role, resume_feedback FROM users WHERE id = ?",
        (uid,),
    ).fetchone()
    if not user:
        session.clear()
        return redirect(url_for("login"))

    error = None
    if request.method == "POST":
        action = (request.form.get("action") or "").strip()

        if action == "update_name":
            new_name = (request.form.get("fullname") or "").strip()
            if not new_name or len(new_name) > 100:
                error = "Please enter a valid full name (1-100 characters)."
            else:
                db.execute("UPDATE users SET fullname = ? WHERE id = ?", (new_name, uid))
                db.commit()
                session["fullname"] = new_name
                flash("Profile name updated.", "success")
                return redirect(url_for("profile"))

        elif action == "change_password":
            current_pwd = request.form.get("current_password") or ""
            new_pwd = request.form.get("new_password") or ""
            confirm_pwd = request.form.get("confirm_password") or ""
            if not check_password_hash(user["password"], current_pwd):
                error = "Current password is incorrect."
            elif len(new_pwd) < MIN_PASSWORD_LENGTH or len(new_pwd) > MAX_PASSWORD_LENGTH:
                error = f"New password must be between {MIN_PASSWORD_LENGTH} and {MAX_PASSWORD_LENGTH} characters."
            elif new_pwd != confirm_pwd:
                error = "New passwords do not match."
            else:
                hashed = generate_password_hash(new_pwd, method=PASSWORD_HASH_METHOD)
                db.execute("UPDATE users SET password = ? WHERE id = ?", (hashed, uid))
                db.commit()
                flash("Password updated securely.", "success")
                return redirect(url_for("profile"))

        elif action == "clear_resume":
            db.execute(
                "UPDATE users SET resume_text = NULL, resume_skills = NULL, resume_feedback = NULL, target_role = NULL WHERE id = ?",
                (uid,),
            )
            db.execute("DELETE FROM questions WHERE topic_id = ?", (f"resume_{uid}",))
            db.commit()
            session.pop("resume_skills", None)
            _delete_user_uploads(uid)
            flash("Saved resume analysis, tailored questions, and uploaded files removed.", "success")
            return redirect(url_for("profile"))

        elif action == "delete_account":
            confirm_pwd = request.form.get("confirm_password") or ""
            if not check_password_hash(user["password"], confirm_pwd):
                error = "Password verification failed. Account was not deleted."
            else:
                db.execute("DELETE FROM bookmarks WHERE user_id = ?", (uid,))
                db.execute("DELETE FROM question_attempts WHERE user_id = ?", (uid,))
                db.execute("DELETE FROM coach_attempts WHERE user_id = ?", (uid,))
                db.execute("DELETE FROM sessions WHERE user_id = ?", (uid,))
                db.execute("DELETE FROM questions WHERE topic_id = ?", (f"resume_{uid}",))
                db.execute("DELETE FROM users WHERE id = ?", (uid,))
                db.commit()
                _delete_user_uploads(uid)
                session.clear()
                flash("Your account and associated data have been permanently deleted.", "success")
                return redirect(url_for("register"))

    return render_template(
        "profile.html",
        fullname=user["fullname"],
        email=user["email"],
        role=user["role"],
        has_resume=bool(user["resume_feedback"]),
        error=error,
    )

@app.route("/resume")
def resume():
    if "user_id" not in session:
        return redirect(url_for("login"))
    db = get_db()
    row = db.execute("SELECT resume_feedback, target_role FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    has_analysis = bool(row and row["resume_feedback"])
    saved_target_role = row["target_role"] if row and row["target_role"] else ""
    return render_template("resume.html", has_analysis=has_analysis, saved_target_role=saved_target_role)


def _compute_jd_match(found_skills, job_description):
    if not job_description or not job_description.strip():
        return [], [], min(len(found_skills) * 10, 100)
    jd_skills = extract_skills(job_description)
    if not jd_skills:
        return [], [], min(len(found_skills) * 10, 100)
    found_lower = {s.lower() for s in found_skills}
    matched = [s for s in jd_skills if s.lower() in found_lower]
    missing = [s for s in jd_skills if s.lower() not in found_lower]
    pct = round((len(matched) / len(jd_skills)) * 100)
    return matched, missing, pct


ALLOWED_RESUME_EXTENSIONS = {".pdf", ".docx"}

@app.route("/upload_resume", methods=["POST"])
def upload_resume():
    from backend.ai.router import evaluate_resume

    if "user_id" not in session:
        return redirect(url_for("login"))

    file = request.files.get("resume")
    job_description = (request.form.get("job_description") or "").strip()[:5000]

    if not file or file.filename == "":
        flash("No file selected. Please choose a PDF or DOCX resume to upload.", "error")
        return redirect(url_for("resume"))

    raw_ext = os.path.splitext(file.filename)[1].lower()
    filename = secure_filename(file.filename)
    ext = os.path.splitext(filename)[1].lower() or raw_ext
    if ext not in ALLOWED_RESUME_EXTENSIONS:
        flash("Unsupported file type. Please upload a PDF or DOCX resume.", "error")
        return redirect(url_for("resume"))

    header = file.stream.read(5)
    file.stream.seek(0)
    if ext == ".pdf" and header != b"%PDF-":
        flash("Invalid PDF file. Please upload a valid PDF document.", "error")
        return redirect(url_for("resume"))
    if ext == ".docx" and not header.startswith(b"PK\x03\x04"):
        flash("Invalid DOCX file. Please upload a valid Word document.", "error")
        return redirect(url_for("resume"))

    uid = session["user_id"]
    _delete_user_uploads(uid)
    safe_stem = os.path.splitext(filename)[0] or "resume"
    stored_name = f"{uid}_{safe_stem}{ext}"
    filepath = os.path.join(UPLOAD_DIR, stored_name)
    file.save(filepath)

    text = extract_text(filepath)
    if not text or not text.strip():
        flash("We couldn't read any text from that file. Please try a different PDF or DOCX.", "error")
        return redirect(url_for("resume"))

    found_skills = extract_skills(text)
    session["resume_skills"] = [s.lower() for s in found_skills]
    matched_skills, missing_jd_skills, match_pct = _compute_jd_match(found_skills, job_description)

    jd_prompt_section = ""
    if job_description:
        jd_prompt_section = f"""
Target Job Description:
\"\"\"
{job_description[:2500]}
\"\"\"

Also evaluate Role Fit & Missing Keywords specifically against this Target Job Description.
"""

    prompt = f"""you are an expert ATS Resume Reviewer,

Analyze the following resume.

1.Resume Score out of 100
2.ATS Compatiblity
3.Strengths
4.Weakness
5.Missing Skills
6.Improvement Suggesstions
7.Final verdict
{jd_prompt_section}
Resume:

{text[:15000]}
"""

    try:
        feedback = evaluate_resume(prompt)
    except Exception as e:
        print("Resume analysis AI error:", e)
        feedback = "AI feedback is temporarily unavailable. Please try again later."

    db = get_db()
    db.execute(
        "UPDATE users SET resume_text = ?, resume_skills = ?, resume_feedback = ?, target_role = ? WHERE id = ?",
        (text, ",".join(session["resume_skills"]), feedback, job_description, session["user_id"])
    )
    db.commit()

    questions = []
    try:
        generated = generate_interview_questions(text, skills=found_skills, job_description=job_description)
        topic_id = f"resume_{session['user_id']}"

        rows = []
        for q in generated:
            if not isinstance(q, dict):
                continue
            question_text = (q.get("question") or "").strip()
            answer_text = (q.get("answer") or "").strip()
            if not question_text or not answer_text:
                continue
            rows.append((
                topic_id,
                q.get("difficulty") or "Intermediate",
                q.get("type") or "theoretical",
                question_text,
                answer_text,
                (q.get("hint") or "").strip() or "Think about the core concept behind this question."
            ))

        if rows:
            db.execute("DELETE FROM questions WHERE topic_id = ?", (topic_id,))
            db.executemany(
                "INSERT INTO questions (topic_id, difficulty, type, question, answer, hint) VALUES (?, ?, ?, ?, ?, ?)",
                rows
            )
            db.commit()

            questions = db.execute(
                "SELECT id, question, answer, hint, difficulty, type FROM questions WHERE topic_id = ?",
                (topic_id,)
            ).fetchall()
    except Exception as e:
        print("Question generation error:", e)
        flash("Resume analyzed, but we couldn't auto-generate interview questions this time.", "error")

    return render_template(
        "analysis.html",
        skills=found_skills,
        resume_text=text,
        feedback=feedback,
        questions=questions,
        job_description=job_description,
        matched_skills=matched_skills,
        missing_jd_skills=missing_jd_skills,
        match_pct=match_pct,
    )


@app.route("/analysis")
def analysis():
    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    user = db.execute(
        "SELECT resume_text, resume_skills, resume_feedback, target_role FROM users WHERE id = ?",
        (session["user_id"],)
    ).fetchone()

    if not user or not user["resume_text"]:
        flash("Upload a resume first to view your ATS analysis and tailored questions.", "error")
        return redirect(url_for("resume"))

    found_skills = [s.strip() for s in (user["resume_skills"] or "").split(",") if s.strip()]
    job_description = user["target_role"] or ""
    matched_skills, missing_jd_skills, match_pct = _compute_jd_match(found_skills, job_description)
    topic_id = f"resume_{session['user_id']}"
    questions = db.execute(
        "SELECT id, question, answer, hint, difficulty, type FROM questions WHERE topic_id = ?",
        (topic_id,)
    ).fetchall()

    return render_template(
        "analysis.html",
        skills=found_skills,
        resume_text=user["resume_text"],
        feedback=user["resume_feedback"] or "",
        questions=questions,
        job_description=job_description,
        matched_skills=matched_skills,
        missing_jd_skills=missing_jd_skills,
        match_pct=match_pct,
    )

@app.route("/api/questions/<topic_id>")
def get_questions(topic_id):
    db = get_db()
    difficulty = request.args.get("difficulty", "All")
    qtype = request.args.get("type", "All")

    if topic_id == "bookmarked":
        if "user_id" not in session:
            return jsonify([])
        query = """
            SELECT q.id, q.question, q.answer, q.hint, q.difficulty, q.type
            FROM bookmarks b
            JOIN questions q ON b.question_id = q.id
            WHERE b.user_id = ?
        """
        params = [session["user_id"]]
        if difficulty != "All":
            query += " AND q.difficulty = ?"
            params.append(difficulty)
        if qtype != "All":
            query += " AND q.type = ?"
            params.append(qtype)
        query += " ORDER BY b.created_at DESC"
        questions = db.execute(query, params).fetchall()
    elif topic_id == "missed":
        if "user_id" not in session:
            return jsonify([])
        query = """
            SELECT q.id, q.question, q.answer, q.hint, q.difficulty, q.type
            FROM question_attempts qa
            JOIN questions q ON qa.question_id = q.id
            WHERE qa.user_id = ?
              AND qa.id IN (
                  SELECT MAX(id) FROM question_attempts
                  WHERE user_id = ?
                  GROUP BY question_id
              )
              AND qa.passed = 0
        """
        params = [session["user_id"], session["user_id"]]
        if difficulty != "All":
            query += " AND q.difficulty = ?"
            params.append(difficulty)
        if qtype != "All":
            query += " AND q.type = ?"
            params.append(qtype)
        query += " ORDER BY qa.created_at DESC"
        questions = db.execute(query, params).fetchall()
    else:
        if topic_id == "resume_tailored":
            if "user_id" not in session:
                return jsonify([])
            topic_id = f"resume_{session['user_id']}"
        elif topic_id.startswith("resume_"):
            if "user_id" not in session or topic_id != f"resume_{session['user_id']}":
                return jsonify({"error": "Unauthorized"}), 403

        query = "SELECT id, question, answer, hint, difficulty, type FROM questions WHERE topic_id = ?"
        params = [topic_id]

        if difficulty != "All":
            query += " AND difficulty = ?"
            params.append(difficulty)

        if qtype != "All":
            if qtype == "coding" and topic_id.startswith("resume_"):
                query += " AND type IN ('coding', 'practical')"
            else:
                query += " AND type = ?"
                params.append(qtype)

        questions = db.execute(query, params).fetchall()

    return jsonify([{
        "id": q["id"],
        "question": q["question"],
        "answer": q["answer"],
        "hint": q["hint"],
        "difficulty": q["difficulty"],
        "type": q["type"]
    } for q in questions])

@app.route("/api/user_info")
def user_info():
    if "user_id" not in session:
        return jsonify({
            "logged_in": False,
            "resume_skills": [],
            "bookmark_count": 0,
            "missed_count": 0,
            "has_analysis": False,
        })

    db = get_db()
    uid = session["user_id"]
    user = db.execute(
        "SELECT fullname, email, resume_skills, resume_feedback FROM users WHERE id = ?",
        (uid,)
    ).fetchone()

    skills = []
    if user and user["resume_skills"]:
        skills = [s.strip() for s in user["resume_skills"].split(",") if s.strip()]

    bookmark_row = db.execute(
        "SELECT COUNT(*) AS cnt FROM bookmarks WHERE user_id = ?", (uid,)
    ).fetchone()
    missed_row = db.execute(
        """
        SELECT COUNT(*) AS cnt FROM question_attempts
        WHERE user_id = ?
          AND id IN (SELECT MAX(id) FROM question_attempts WHERE user_id = ? GROUP BY question_id)
          AND passed = 0
        """,
        (uid, uid),
    ).fetchone()

    return jsonify({
        "logged_in": True,
        "fullname": user["fullname"] if user else "",
        "email": user["email"] if user else "",
        "resume_skills": skills,
        "bookmark_count": bookmark_row["cnt"] if bookmark_row else 0,
        "missed_count": missed_row["cnt"] if missed_row else 0,
        "has_analysis": bool(user and user["resume_feedback"]),
    })


@app.route("/api/bookmarks", methods=["GET", "POST"])
def api_bookmarks():
    if "user_id" not in session:
        if request.method == "GET":
            return jsonify({"bookmark_ids": []})
        return jsonify({"success": False, "error": "Please sign in to save bookmarks."}), 401

    db = get_db()
    uid = session["user_id"]

    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        try:
            question_id = int(data.get("question_id"))
        except (TypeError, ValueError):
            return jsonify({"success": False, "error": "Invalid question_id"}), 400
        if not db.execute("SELECT id FROM questions WHERE id = ?", (question_id,)).fetchone():
            return jsonify({"success": False, "error": "Question not found"}), 404
        existing = db.execute(
            "SELECT id FROM bookmarks WHERE user_id = ? AND question_id = ?",
            (uid, question_id),
        ).fetchone()
        if existing:
            db.execute("DELETE FROM bookmarks WHERE id = ?", (existing["id"],))
            bookmarked = False
        else:
            db.execute(
                "INSERT OR IGNORE INTO bookmarks (user_id, question_id) VALUES (?, ?)",
                (uid, question_id),
            )
            bookmarked = True
        db.commit()
    else:
        bookmarked = None

    rows = db.execute(
        "SELECT question_id FROM bookmarks WHERE user_id = ? ORDER BY created_at DESC",
        (uid,),
    ).fetchall()
    return jsonify({
        "success": True,
        "bookmarked": bookmarked,
        "bookmark_ids": [r["question_id"] for r in rows],
    })


@app.route("/api/record_attempt", methods=["POST"])
def api_record_attempt():
    if "user_id" not in session:
        return jsonify({"success": True, "saved": False})

    data = request.get_json(silent=True) or {}
    try:
        question_id = int(data.get("question_id"))
        score = max(0, min(100, int(data.get("score") or 0)))
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "Invalid question_id or score"}), 400
    topic_id = (data.get("topic_id") or "").strip()[:64]
    passed = 1 if data.get("passed") else 0

    if not question_id or not topic_id:
        return jsonify({"success": False, "error": "Missing question_id or topic_id"}), 400

    db = get_db()
    if not db.execute("SELECT id FROM questions WHERE id = ?", (question_id,)).fetchone():
        return jsonify({"success": False, "error": "Question not found"}), 404
    db.execute(
        "INSERT INTO question_attempts (user_id, question_id, topic_id, passed, score) VALUES (?, ?, ?, ?, ?)",
        (session["user_id"], question_id, topic_id, passed, score),
    )
    db.commit()
    return jsonify({"success": True, "saved": True})

PASS_SCORE_THRESHOLD = 60

def _extract_score(text):
    match = re.search(r"score\s*:?\s*(\d{1,3})\s*(?:/\s*100)?", text, re.IGNORECASE)
    if match:
        return max(0, min(100, int(match.group(1))))
    return None

def _parse_coach_sections(text):
    headings = [
        ("feedback", r"Feedback"),
        ("strengths", r"Strengths"),
        ("weaknesses", r"Weaknesses"),
        ("suggestions", r"Suggestions for Improvement"),
        ("ideal_answer", r"Ideal Answer"),
    ]
    pattern = re.compile(
        r"^(?:" + "|".join(label for _, label in headings) + r")\s*:",
        re.IGNORECASE | re.MULTILINE,
    )
    matches = list(pattern.finditer(text or ""))
    if not matches:
        return None

    sections = {}
    for idx, match in enumerate(matches):
        header_raw = match.group(0).rstrip(":").strip().lower()
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        for key, label in headings:
            if header_raw == label.lower():
                sections[key] = body
                break
    return sections or None


def _save_coach_attempt(question, user_answer, score, feedback):
    if "user_id" not in session:
        return
    db = get_db()
    db.execute(
        "INSERT INTO coach_attempts (user_id, question, user_answer, score, feedback) VALUES (?, ?, ?, ?, ?)",
        (session["user_id"], question[:1000], user_answer[:4000], max(0, min(100, int(score))), feedback[:8000]),
    )
    db.commit()


def _recent_coach_attempts(limit=5):
    if "user_id" not in session:
        return []
    db = get_db()
    return db.execute(
        "SELECT id, question, score, feedback, created_at FROM coach_attempts WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (session["user_id"], limit),
    ).fetchall()


@app.route("/evaluate_answer", methods=["POST"])
def evaluate_answer():
    from backend.ai.router import evaluate_resume

    if _is_rate_limited("ai_eval", limit=30, window_seconds=60):
        if request.is_json:
            return jsonify({"success": False, "error": "Rate limit exceeded. Please wait a moment."}), 429
        return render_template("answer_coach.html", ai_feedback="Rate limit exceeded. Please wait a moment.", recent_attempts=_recent_coach_attempts()), 429

    is_json_req = request.is_json
    if is_json_req:
        data = request.get_json(silent=True) or {}
        question = (data.get("question") or "").strip()[:2000]
        correct_answer = (data.get("correct_answer") or "").strip()[:4000]
        user_answer = (data.get("user_answer") or "")[:8000]
    else:
        question = (request.form.get("question") or "Explain what Machine Learning is.").strip()[:2000]
        correct_answer = (request.form.get("correct_answer") or "").strip()[:4000]
        user_answer = (request.form.get("user_answer") or "")[:8000]

    if not user_answer.strip():
        if is_json_req:
            return jsonify({"success": False, "error": "Answer is empty."}), 400
        return render_template(
            "answer_coach.html",
            ai_feedback="Error: Answer is empty.",
            question=question,
            correct_answer=correct_answer,
            user_answer=user_answer,
            recent_attempts=_recent_coach_attempts(),
        ), 400

    expected_block = correct_answer if correct_answer else "No fixed reference provided; judge against standard interview best practices, technical precision, and structured clarity."
    coding_note = (
        "\nIf the question involves code, SQL, or algorithms, also check time/space complexity and edge cases."
        if any(k in question.lower() for k in ("code", "algorithm", "complexity", "sql", "query", "function", "implement"))
        else ""
    )

    prompt = f"""You are an expert Technical Interview Coach.

Compare the candidate's answer with the expected answer for the given question.

Question:
{question}

Expected Answer:
{expected_block}

Candidate Answer:
{user_answer}

Evaluate the candidate's answer like a real interviewer based on:
1.Technical Accuracy
2.Completeness
3.Clarity
4.Relevance to the question
5.Communication Skills{coding_note}

Return exactly in this format:

Score: __/100

Feedback:

Strengths:

Weaknesses:

Suggestions for Improvement:

Ideal Answer:
"""
    try:
        feedback = evaluate_resume(prompt)
        score = _extract_score(feedback)
        if score is None:
            basic = coach_evaluator(user_answer, correct_answer or question)
            score = basic["score"]
        _save_coach_attempt(question, user_answer, score, feedback)
        if not is_json_req:
            return render_template(
                "answer_coach.html",
                ai_feedback=feedback,
                coach_score=score,
                coach_sections=_parse_coach_sections(feedback),
                question=question,
                correct_answer=correct_answer,
                user_answer=user_answer,
                recent_attempts=_recent_coach_attempts(),
            )
        return jsonify({
            "success": True,
            "score": score,
            "correct": score >= PASS_SCORE_THRESHOLD,
            "feedback": feedback,
            "mode": "AI"
        })
    except Exception as e:
        print("AI Error (both Gemini and Ollama failed):", e)
        basic = coach_evaluator(user_answer, correct_answer or question)
        basic_feedback = f"{basic['feedback']} {basic['tips']}"
        _save_coach_attempt(question, user_answer, basic["score"], basic_feedback)
        if not is_json_req:
            return render_template(
                "answer_coach.html",
                ai_feedback=basic_feedback,
                coach_score=basic["score"],
                coach_sections=None,
                question=question,
                correct_answer=correct_answer,
                user_answer=user_answer,
                recent_attempts=_recent_coach_attempts(),
            )
        return jsonify({
            "success": True,
            "score": basic["score"],
            "correct": basic["score"] >= PASS_SCORE_THRESHOLD,
            "feedback": basic_feedback,
            "mode": "Basic"
        })

@app.route("/api/save_session", methods=["POST"])
def save_session():
    if "user_id" not in session:
        return jsonify({"success": False, "error": "Not logged in"}), 401

    data = request.get_json(silent=True) or {}
    topic_id = str(data.get("topic_id") or "").strip()[:64]
    try:
        score = int(data.get("score", 0))
        total = int(data.get("total", 0))
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "Invalid score or total"}), 400

    if not topic_id or total <= 0 or score < 0 or score > total:
        return jsonify({"success": False, "error": "Invalid session payload"}), 400

    db = get_db()
    db.execute("INSERT INTO sessions (user_id, topic_id, score, total) VALUES (?, ?, ?, ?)",
               (session["user_id"], topic_id, score, total))
    db.commit()

    return jsonify({"success": True})

@app.route("/api/chat", methods=["POST"])
def api_chat():
    from backend.ai.router import evaluate_resume

    if _is_rate_limited("ai_chat", limit=30, window_seconds=60):
        return jsonify({"success": False, "error": "Rate limit exceeded. Please wait a moment."}), 429

    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()[:2000]
    if not message:
        return jsonify({"success": False, "error": "Message is empty."}), 400

    prompt = (
        "You are AI Interview Copilot, a concise, helpful technical and behavioral interview coach. "
        "Answer the candidate's question clearly in 2-5 sentences.\n\n"
        f"Candidate: {message}"
    )
    try:
        reply = evaluate_resume(prompt).strip()
        return jsonify({"success": True, "reply": reply, "mode": "AI"})
    except Exception as e:
        print("Chat AI error:", e)
        return jsonify({
            "success": True,
            "reply": "Use the STAR method (Situation, Task, Action, Result) for behavioral questions, and state trade-offs clearly for technical questions.",
            "mode": "Fallback"
        })

@app.route("/api/follow_up", methods=["POST"])
def api_follow_up():
    from backend.ai.router import evaluate_resume

    if _is_rate_limited("ai_follow_up", limit=30, window_seconds=60):
        return jsonify({"success": False, "error": "Rate limit exceeded. Please wait a moment."}), 429

    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()[:2000]
    user_answer = (data.get("user_answer") or "").strip()[:8000]
    if not user_answer:
        return jsonify({"success": False, "error": "Answer is empty."}), 400

    prompt = (
        "You are a Technical Interviewer. Based on the interview question and the candidate's answer below, "
        "ask ONE concise, probing follow-up question (1-2 sentences max) to test deeper understanding.\n\n"
        f"Original Question: {question}\n"
        f"Candidate Answer: {user_answer}\n\n"
        "Follow-up Question:"
    )
    try:
        follow_up = evaluate_resume(prompt).strip()
        return jsonify({"success": True, "follow_up": follow_up, "mode": "AI"})
    except Exception as e:
        print("Follow-up AI error:", e)
        return jsonify({
            "success": True,
            "follow_up": "Can you walk through a real-world edge case or trade-off with that approach?",
            "mode": "Fallback"
        })

@app.route("/progress")
def progress():
    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    uid = session["user_id"]
    rows = db.execute(
        """
        SELECT id, topic_id, score, total, date
        FROM sessions
        WHERE user_id = ?
        ORDER BY date DESC, id DESC
        LIMIT 50
        """,
        (uid,),
    ).fetchall()

    total_sessions = len(rows)
    percentages = [round((r["score"] / r["total"]) * 100) for r in rows if r["total"] > 0]
    avg_score = round(sum(percentages) / len(percentages)) if percentages else 0
    best_score = max(percentages) if percentages else 0

    topic_rows = db.execute(
        """
        SELECT topic_id,
               COUNT(*) AS attempts,
               SUM(score) AS sum_score,
               SUM(total) AS sum_total
        FROM sessions
        WHERE user_id = ? AND total > 0
        GROUP BY topic_id
        ORDER BY attempts DESC
        """,
        (uid,),
    ).fetchall()

    topic_stats = []
    for tr in topic_rows:
        acc = round((tr["sum_score"] / tr["sum_total"]) * 100) if tr["sum_total"] else 0
        topic_stats.append({
            "topic_id": tr["topic_id"],
            "label": tr["topic_id"].replace("_", " ").title(),
            "sessions": tr["attempts"],
            "accuracy": acc,
        })

    bookmark_count = db.execute(
        "SELECT COUNT(*) AS cnt FROM bookmarks WHERE user_id = ?", (uid,)
    ).fetchone()["cnt"]
    missed_count = db.execute(
        """
        SELECT COUNT(*) AS cnt FROM question_attempts
        WHERE user_id = ?
          AND id IN (SELECT MAX(id) FROM question_attempts WHERE user_id = ? GROUP BY question_id)
          AND passed = 0
        """,
        (uid, uid),
    ).fetchone()["cnt"]

    coach_attempts = _recent_coach_attempts(limit=10)

    return render_template(
        "progress.html",
        fullname=session.get("fullname", "User"),
        sessions=rows,
        coach_attempts=coach_attempts,
        total_sessions=total_sessions,
        avg_score=avg_score,
        best_score=best_score,
        topic_stats=topic_stats,
        bookmark_count=bookmark_count,
        missed_count=missed_count,
    )

@app.route("/admin")
def admin():
    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    current_user = db.execute("SELECT role FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    if not current_user or current_user["role"] != "admin":
        abort(403, description="Admin privileges required.")

    sessions = db.execute("""
        SELECT sessions.id, users.fullname, sessions.topic_id,
               sessions.score, sessions.total, sessions.date
        FROM sessions
        JOIN users ON sessions.user_id = users.id
        ORDER BY sessions.date DESC
        LIMIT 50
    """).fetchall()

    return render_template("admin.html", sessions=sessions)

@app.route("/answer-coach")
def answer_coach():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("answer_coach.html", recent_attempts=_recent_coach_attempts())


@app.errorhandler(403)
def handle_forbidden(err):
    if request.is_json or request.path.startswith("/api/"):
        return jsonify({"success": False, "error": getattr(err, "description", "Forbidden")}), 403
    return render_template("error.html", code=403, title="Access Denied", message=getattr(err, "description", "You do not have permission to access this resource.")), 403


@app.errorhandler(404)
def handle_not_found(err):
    if request.is_json or request.path.startswith("/api/"):
        return jsonify({"success": False, "error": "Resource not found"}), 404
    return render_template("error.html", code=404, title="Page Not Found", message="The page you requested does not exist or has moved."), 404


@app.errorhandler(500)
def handle_server_error(err):
    if request.is_json or request.path.startswith("/api/"):
        return jsonify({"success": False, "error": "Internal server error"}), 500
    return render_template("error.html", code=500, title="Something Went Wrong", message="An unexpected error occurred on the server. Please try again."), 500

@app.route("/faq")
def faq():
    return render_template("faq.html")

@app.route("/privacy")
def privacy():
    return render_template("privacy.html")

@app.route("/statements")
@app.route("/terms")
def statements():
    return render_template("statements.html")

os.makedirs(UPLOAD_DIR, exist_ok=True)

# Ensure database tables exist on startup
create_database()

if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")