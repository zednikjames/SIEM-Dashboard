# From imports
from contextlib import closing
from flask import current_app
from flask import Blueprint, jsonify, request, session, redirect, url_for
from config import USER_DATABASE_PATH, AUDIT_DATABASE_PATH, PROFILE_PICTURE_FOLDER
from werkzeug.security import generate_password_hash
from datetime import datetime, timezone

# Regular imports
import uuid
import sqlite3

api_bp = Blueprint("api", __name__, url_prefix="/api")


# Functions
def write_user_creation_log(con, actor, target, result, details):
    con.execute(
        """
        INSERT INTO audit.main_log
            (id, timestamp, actor, action, target, result, details)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid.uuid4()),
            datetime.now(timezone.utc).isoformat(),
            actor,
            "user.created",
            target,
            result,
            details,
        ),
    )


def write_user_modification(con, actor, target, result, details):
    con.execute(
        """
        INSERT INTO audit.main_log
            (id, timestamp, actor, action, target, result, details)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid.uuid4()),
            datetime.now(timezone.utc).isoformat(),
            actor,
            "user.modified",
            target,
            result,
            details,
        ),
    )




# API Calls
@api_bp.route("/get_user_info")
def get_user_info():
    email = session.get("user_email")
    if email is None:
        return jsonify({"error": "Not signed in"}), 401

    with sqlite3.connect(USER_DATABASE_PATH) as con:
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

    with closing(sqlite3.connect(USER_DATABASE_PATH)) as con, con:
        role = con.execute("SELECT role FROM login WHERE email = ?", (email,)).fetchone()
    
        if role is None or role[0] != "Administrator":
            return jsonify({"error": "Insufficient permission"}), 403

    with closing(sqlite3.connect(USER_DATABASE_PATH)) as con:
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

    with closing(sqlite3.connect(USER_DATABASE_PATH)) as con, con:
        role = con.execute("SELECT role FROM login WHERE email = ?", (email,)).fetchone()

        if role is None or role[0] != "Administrator":
            return jsonify({"error": "Insufficient permission"}), 403

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

        target = email_address.strip()

        try:
            with closing(sqlite3.connect(USER_DATABASE_PATH)) as con, con:
                con.execute(
                    "ATTACH DATABASE ? AS audit",
                    (str(AUDIT_DATABASE_PATH),),
                )

                cursor = con.execute(
                    """
                    INSERT INTO login
                        (email, password_hash, full_name, role, active, profile_picture)
                    VALUES (?, ?, ?, ?, ?, NULL)
                    ON CONFLICT(email) DO NOTHING
                    """,
                    (target, generate_password_hash(password), name.strip(), given_role, True),
                )

                if cursor.rowcount == 0:
                    write_user_creation_log(con, email, target, False, "User already exists")
                    return jsonify(error="User already exists"), 409

                write_user_creation_log(con, email, target, True, "User has been created")

        except sqlite3.Error:
            current_app.logger.exception("Database error while creating user")

            # The first transaction has rolled back. Try logging the failure separately.
            try:
                with closing(sqlite3.connect(USER_DATABASE_PATH)) as con, con:
                    con.execute(
                        "ATTACH DATABASE ? AS audit",
                        (str(AUDIT_DATABASE_PATH),),
                    )
                    write_user_creation_log(
                        con, email, target, False, "Database error; outcome not confirmed"
                    )
            except sqlite3.Error:
                current_app.logger.exception("Could not write user creation audit event")
            return jsonify(error="Could not create user"), 500

    if request.accept_mimetypes.best == "application/json":
        return jsonify(message="User has been created"), 201
    return redirect(url_for("pages.administration_settings"), code=303)


@api_bp.route("/modify_user", methods=['POST'])
def modify_user():
    email = session.get("user_email")
    if email is None:
        return jsonify({"error": "Not signed in"}), 401

    with closing(sqlite3.connect(USER_DATABASE_PATH)) as con, con:
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

    target = existing_email.strip()

    try:
        with closing(sqlite3.connect(USER_DATABASE_PATH)) as con, con:
            con.execute(
                "ATTACH DATABASE ? AS audit",
                (str(AUDIT_DATABASE_PATH),)
            )

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
                write_user_modification(con, email, target, False, "User doesn't exist")
                return jsonify(error="User doesn't exist"), 404
            write_user_modification(con, email, target, True, "User has been modified")

    except sqlite3.Error:
        current_app.logger.exception("Database error while modifying user")

        try:
            with closing(sqlite3.connect(USER_DATABASE_PATH)) as con, con:
                con.execute(
                    "ATTACH DATABASE ? AS audit",
                    (str(AUDIT_DATABASE_PATH),),
                )
                write_user_modification(
                    con, email, target, False, "Database error; outcome not confirmed"
                )
        except sqlite3.Error:
            current_app.logger.exception("Could not modifiy user audit event")
        return jsonify(error="Could not modify user"), 500

    if request.accept_mimetypes.best == "application/json":
        return jsonify(message="User has been updated"), 200
    return redirect(url_for("pages.administration_settings"), code=303)

@api_bp.route('/return_logs')
def return_logs():
    email = session.get("user_email")
    if email is None:
        return jsonify({"error": "Not signed in"}), 401
    
    with closing(sqlite3.connect(USER_DATABASE_PATH)) as con, con:
        role = con.execute("SELECT role FROM login WHERE email = ?", (email,)).fetchone()
        
        if role is None or role[0] != "Administrator":
            return jsonify({"error": "Insufficient permission"}), 403

    with closing(sqlite3.connect(AUDIT_DATABASE_PATH)) as con:
        logs = con.execute("SELECT id, timestamp, actor, action, target, result, details FROM main_log").fetchall()

    return jsonify([
        {
            "event_id": log[0],
            "timestamp": log[1],
            "actor": log[2],
            "action": log[3],
            "target": log[4],
            "result": bool(log[5]),
            "details": log[6],
        }
        for log in logs
    ])