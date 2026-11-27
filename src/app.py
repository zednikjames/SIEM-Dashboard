# From imports
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf.csrf import CSRFProtect
from datetime import datetime, timezone
from contextlib import closing

from config import USER_DATABASE_PATH, AUDIT_DATABASE_PATH, ARCHIVE_DATABASE_PATH, SECRET_KEY, DEFAULT_PORT
from routes.api import api_bp
from routes.pages import pages_bp

# Regular imports
import os
import sqlite3

# Variables

user_database_path = USER_DATABASE_PATH
user_database_path.parent.mkdir(parents=True, exist_ok=True)

audit_database_path = AUDIT_DATABASE_PATH
audit_database_path.parent.mkdir(parents=True, exist_ok=True)

archive_database_path = ARCHIVE_DATABASE_PATH
archive_database_path.parent.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY

csrf = CSRFProtect(app)

app.register_blueprint(pages_bp)
app.register_blueprint(api_bp)



# Database setup
def init_db():
    with sqlite3.connect(user_database_path) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS login (
                email TEXT NOT NULL PRIMARY KEY,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT NOT NULL,
                active NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
                profile_picture TEXT
            )
        """)

    with sqlite3.connect(audit_database_path) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS main_log (
                id TEXT NOT NULL PRIMARY KEY,
                timestamp TEXT NOT NULL,
                actor TEXT NOT NULL,
                action TEXT NOT NULL,
                target TEXT,
                result INTEGER NOT NULL CHECK (result IN (0, 1)),
                details TEXT
            )
        """)

        with sqlite3.connect(archive_database_path) as con:
            con.execute("""
            CREATE TABLE IF NOT EXISTS archive_log (
                id TEXT NOT NULL PRIMARY KEY,
                timestamp TEXT NOT NULL,
                actor TEXT NOT NULL,
                action TEXT NOT NULL,
                target TEXT,
                result INTEGER NOT NULL CHECK (result IN (0, 1)),
                details TEXT
            )
        """)

def setup_default_admin():
    email = "admin@sentinel.com"

    with closing(sqlite3.connect(user_database_path)) as con, con:
        existing = con.execute(
            "SELECT 1 FROM login WHERE email = ?",
            (email,),
        ).fetchone()

        if existing is None:
            password = os.environ["DEFAULT_ADMIN_PASSWORD"]
            password_hash = generate_password_hash(password)

            con.execute(
                "INSERT INTO login (email, password_hash, full_name, role, active, profile_picture) VALUES (?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(email) DO NOTHING",
                (email, password_hash, "Admin", "Administrator", True, "administrator.png"),
            )
            
# Main Code
@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    with sqlite3.connect(user_database_path) as con:
        user = con.execute(
            "SELECT password_hash FROM login WHERE email = ?",
            (email,)
        ).fetchone()

    if user is None or not check_password_hash(user[0], password): 
        return render_template(
            "login.html", error="Invalid email or password."
        ), 401

    session.clear()
    session["user_email"] = email
    return redirect(url_for('pages.overview_page'))

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/")
def index():
    return render_template('login.html')

@app.route("/favicon.ico")
def favicon():
    return app.send_static_file("favicon.ico")

init_db()
setup_default_admin()

if __name__ == "__main__":
    app.run(debug=True, port=int(DEFAULT_PORT), ssl_context=("localhost-cert.pem", "localhost-key.pem"))