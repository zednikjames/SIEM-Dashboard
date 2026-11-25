import sqlite3
from contextlib import closing

from flask import Blueprint, jsonify, request, session, redirect, url_for
from config import DATABASE_PATH, PROFILE_PICTURE_FOLDER
from werkzeug.security import generate_password_hash

api_bp = Blueprint("api", __name__, url_prefix="/api")

@api_bp.route("/get_user_info")
def get_user_info():
    email = session.get("user_email")
    if email is None:
        return jsonify({"error": "Not signed in"}), 401

    with sqlite3.connect(DATABASE_PATH) as con:
        role = con.execute("SELECT role FROM login WHERE email = ?", (email,)).fetchone()
        fullname = con.execute("SELECT full_name FROM login WHERE email = ?", (email,)).fetchone()
        profile_picture = con.execute("SELECT profile_picture FROM login WHERE email = ?", (email,)).fetchone()

    if role is None:
        return jsonify({"error": "Role not found"}), 404
    
    return jsonify({
            "role": role[0],
            "fullname": fullname[0],
            "profile_picture": profile_picture[0]
        })

@api_bp.route("/return_users")
def return_users():
    email = session.get("user_email")
    if email is None:
        return jsonify({"error": "Not signed in"}), 401

    with closing(sqlite3.connect(DATABASE_PATH)) as con, con:
        role = con.execute("SELECT role FROM login WHERE email = ?", (email,)).fetchone()
    
        if role is None or role[0] != "Administrator":
            return jsonify({"error": "Insufficient permission"}), 403

    with closing(sqlite3.connect(DATABASE_PATH)) as con:
        users = con.execute(
            "SELECT full_name, email, role, active FROM login"
            ).fetchall()

    return jsonify([
    {
        "full_name": user[0],
        "email": user[1],
        "role": user[2],
        "active": bool(user[3]),
    }
        for user in users
    ])


@api_bp.route("/create_user", methods=['POST', 'GET'])
def create_user():
    email = session.get("user_email")
    if email is None:
        return jsonify({"error": "Not signed in"}), 401

    with closing(sqlite3.connect(DATABASE_PATH)) as con, con:
        role = con.execute("SELECT role FROM login WHERE email = ?", (email,)).fetchone()

        if role is None or role[0] != "Administrator":
            return jsonify({"error": "Insufficient permission"}), 403

    with closing(sqlite3.connect(DATABASE_PATH)) as con, con:
        data = request.form

        email_address = data.get("email")
        password = data.get("password")
        name = data.get("name")
        given_role = data.get("role")

        if not isinstance(email_address, str) or not email_address.strip():
            return jsonify(error="Email cannot be empty!"), 400
        if not isinstance(password, str) or not password:
            return jsonify(error="Password cannot be empty!"), 400
        if not isinstance(name, str) or not name.strip():
            return jsonify(error="Name cannot be empty!"), 400
        if not isinstance(given_role, str) or not given_role.strip():
            return jsonify(error="Role cannot be empty!"), 400

        cursor = con.execute(
            """
            INSERT INTO login (email, password_hash, full_name, role, active, profile_picture)
            VALUES (?, ?, ?, ?, ?, NULL)
            ON CONFLICT(email) DO NOTHING
            """,
            (email_address.strip(), generate_password_hash(password), name.strip(), given_role, True),
        )
        if cursor.rowcount == 0:
            return jsonify(error="User already exists"), 409

    if request.accept_mimetypes.best == "application/json":
        return jsonify(message="User has been created"), 201
    return redirect(url_for("pages.administration_settings"), code=303)


@api_bp.route("/modify_user", methods=['POST'])
def modify_user():
    email = session.get("user_email")
    if email is None:
        return jsonify({"error": "Not signed in"}), 401

    with closing(sqlite3.connect(DATABASE_PATH)) as con, con:
        role = con.execute("SELECT role FROM login WHERE email = ?", (email,)).fetchone()

        if role is None or role[0] != "Administrator":
            return jsonify({"error": "Insufficient permission"}), 403

        data = request.form

        existing_email = data.get("email")
        modify_password = data.get("password")
        modify_status = data.get("status", "").strip().lower()
        modify_role = data.get("role", "").strip()

        if not isinstance(existing_email, str) or not existing_email.strip():
            return jsonify(error="Email cannot be empty!"), 400
        if not isinstance(modify_password, str) or not modify_password:
            return jsonify(error="Password cannot be empty!"), 400
        if modify_status not in ("true", "false"):
            return jsonify(error="Status must be True or False"), 400

        cursor = con.execute(
            """
            UPDATE login
            SET password_hash = ?, active = ?, role = COALESCE(NULLIF(?, ''), role)
            WHERE email = ?
            """,
            (generate_password_hash(modify_password), modify_status == "true",
             modify_role, existing_email.strip()),
        )
        if cursor.rowcount == 0:
            return jsonify(error="User not found"), 404

    if request.accept_mimetypes.best == "application/json":
        return jsonify(message="User has been updated"), 200
    return redirect(url_for("pages.administration_settings"), code=303)