# From imports
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf.csrf import CSRFProtect

from config import DATABASE_PATH, SECRET_KEY, DEFAULT_PORT
from routes.api import api_bp
from routes.pages import pages_bp

# Regular imports
import os
import sqlite3


# Variables
database_path = DATABASE_PATH
database_path.parent.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY

csrf = CSRFProtect(app)

app.register_blueprint(pages_bp)
app.register_blueprint(api_bp)



# Database setup
def init_db():
    with sqlite3.connect(database_path) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS login (
                email TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT NOT NULL,
                active NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
                profile_picture TEXT
            )
        """)

def setup_default_admin():
    email = "admin@sentinel.com"

    with sqlite3.connect(database_path) as con:
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
                (email, password_hash, "James Zednik", "Administrator", True, "administrator.png"),
            )


# Main Code
@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    with sqlite3.connect(database_path) as con:
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