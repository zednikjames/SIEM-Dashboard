# Normal Imports
import sqlite3
import os
import configparser
import secrets

# From Imports
from pathlib import Path
from flask import Flask, jsonify, redirect, render_template, request, send_file, session
from werkzeug.security import check_password_hash, generate_password_hash


config = configparser.ConfigParser()
config.read('server.ini')

HOST = config.get("server", "host")
PORT = config.get("server", "host_port")
DB_PATH = "Database.db"
project_root = Path(__file__).resolve().parent.parent

# Main Application
app = Flask(__name__, template_folder=str(project_root / "templates"), static_folder=str(project_root / "static"))
# Signs the session cookie; set SECRET_KEY in the environment for real use
app.secret_key = os.environ["SECRET_KEY"]
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")

# Database Setup
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

# API references
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

@app.route("/api/discover/log")
def log():
    return send_file(r"C:\Users\james\OneDrive\Desktop\SIEM Dashboard\recvived-logs\log.txt", mimetype="text/plain")

@app.route("/api/discover/recieve", methods=['POST'])
def recieve():
    if "file" not in request.files:
        return {"message": "No file provided"}, 400
    file = request.files['file']
    file.save(f"C:\\Users\\james\\OneDrive\\Desktop\\SIEM Dashboard\\Forwarded-Logs\\{file.filename}")
    return jsonify(success=True)

@app.route("/api/generate_token", methods=['POST', 'GET'])
def generate_token():
    data = request.get_json() or {}
    name = data.get("name")
    
    if not isinstance(name, str) or not name.strip():
        return jsonify(error="Name must be a non-empty string"), 400

    if config.has_option('generated_tokens', name):
        return jsonify(error="Token name already exists"), 400

    if len(name) > 50:
        return jsonify(error="Name too long (max 50 characters)"), 400

    token = secrets.token_urlsafe(32)

    config.set('generated_tokens', name, token)

    with open('server.ini', "w") as configfile:
        config.write(configfile)

    return jsonify({"generated_token": token})

# Default routes
@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/")
def index():
    if "user" not in session:
        return redirect("/login")
    return render_template("index.html")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/discover")
def discover():
    return render_template("discover.html")

@app.route("/settings")
def settings():
    return render_template("settings.html")

init_db()

if __name__ == "__main__":
    app.run(debug=True, host=HOST, port=int(PORT))