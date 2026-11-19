import sqlite3

import os

from flask import Flask, jsonify, redirect, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash


app = Flask(__name__)
# Signs the session cookie; set SECRET_KEY in the environment for real use
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-me")
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")
DB_PATH = "Database.db"


def get_db():
    return sqlite3.connect(DB_PATH)


def init_db():
    with get_db() as db:
        db.execute(
            "CREATE TABLE IF NOT EXISTS login (username TEXT PRIMARY KEY, password TEXT)"
        )
        db.execute(
            "INSERT OR IGNORE INTO login (username, password) VALUES (?, ?)",
            ("admin", generate_password_hash("password")),
        )


@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "")
    password = data.get("password", "")
    with get_db() as db:
        row = db.execute(
            "SELECT password FROM login WHERE username = ?", (username,)
        ).fetchone()
    if row and check_password_hash(row[0], password):
        session["user"] = username
        return jsonify(success=True)
    return jsonify(success=False, error="Invalid username or password"), 401



@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")
    return render_template("dashboard.html")

@app.route("/discover")
def discover():
    return render_template("discover.html")



    


init_db()

if __name__ == "__main__":
    app.run(debug=True, port=8889)