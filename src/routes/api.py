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

ADMIN_ROLE = "System Administrator"


# Functions
def is_system_administrator(email):
    with closing(sqlite3.connect(USER_DATABASE_PATH)) as con:
        user = con.execute(
            "SELECT role, active FROM login WHERE email = ?", (email,)
        ).fetchone()
    return user is not None and user[0] == ADMIN_ROLE and bool(user[1])


def write_user_creation_log(con, user_id, actor, target, result, details):
    con.execute(
        """
        INSERT INTO audit.main_log
            (id, user_id, timestamp, actor, action, target, result, details)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid.uuid4()),
            user_id,
            datetime.now(timezone.utc).isoformat(),
            actor,
            "user.created",
            target,
            result,
            details,
        ),
    )


def write_user_modification(con, user_id, actor, target, result, details):
    con.execute(
        """
        INSERT INTO audit.main_log
            (id, user_id, timestamp, actor, action, target, result, details)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid.uuid4()),
            user_id,
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

    if not is_system_administrator(email):
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
    actor_email = session.get("user_email")
    if actor_email is None:
        return jsonify({"error": "Not signed in"}), 401

    data = request.form
    email = data.get("email")
    password = data.get("password")
    name = data.get("name")
    role = data.get("roles", "").strip()
    permissions = data.getlist("permissions")

    allowed_roles = {
        ADMIN_ROLE,
        r"SOC Manager \ Team Lead",
        "Tier 2 SOC Analyst",
        "Tier 1 SOC Analyst",
        "Incident Responder",
        "Threat Hunter",
        "Read-Only User",
    }
    allowed_permissions = {"alerts.view", "alerts.modify"}

    if not email:
        return jsonify(error="Email cannot be empty"), 400
    if not password:
        return jsonify(error="Password cannot be empty"), 400
    if not name:
        return jsonify(error="Name cannot be empty"), 400
    if role not in allowed_roles:
        return jsonify(error="Invalid role"), 400
    if not set(permissions).issubset(allowed_permissions):
        return jsonify(error="Invalid permission"), 400
    if len(permissions) != len(set(permissions)):
        return jsonify(error="Duplicate permission"), 400

    actor_id = None

    try:
        with closing(sqlite3.connect(USER_DATABASE_PATH)) as con, con:
            con.execute("PRAGMA foreign_keys = ON")
            con.execute("ATTACH DATABASE ? AS audit", (str(AUDIT_DATABASE_PATH),))

            actor = con.execute(
                "SELECT user_id, role, active FROM login WHERE email = ?",
                (actor_email,),
            ).fetchone()

            if actor is None or actor[1] != ADMIN_ROLE or not actor[2]:
                return jsonify(error="Insufficient permission"), 403

            actor_id = actor[0]
            new_user_id = str(uuid.uuid4())

            cursor = con.execute(
                """
                INSERT INTO login
                    (user_id, email, password_hash, full_name, role, active, profile_picture)
                VALUES (?, ?, ?, ?, ?, ?, NULL)
                ON CONFLICT(email) DO NOTHING
                 """,
                (new_user_id, email, generate_password_hash(password), name.strip(), role, True),
            )

            if cursor.rowcount == 0:
                write_user_creation_log(
                    con, actor_id, actor_email, email, False, "User already exists"
                )
                return jsonify(error="User already exists"), 409

            con.executemany(
                "INSERT INTO permissions (user_id, permission_key) VALUES (?, ?)",
                [(new_user_id, permission) for permission in permissions],
            )

            write_user_creation_log(
                con, actor_id, actor_email, email, True, "User has been created"
            )

    except sqlite3.Error:
        current_app.logger.exception("Database error while creating user")

        # The first transaction has rolled back. Try logging the failure separately.
        if actor_id is not None:
            try:
                with closing(sqlite3.connect(USER_DATABASE_PATH)) as con, con:
                    con.execute(
                        "ATTACH DATABASE ? as audit", (str(AUDIT_DATABASE_PATH),)
                    )
                    write_user_creation_log(
                        con, actor_id, actor_email, email, False,
                        "Database error; outcome not confirmed",
                    )
            except sqlite3.Error:
                current_app.logger.exception("Could not write user creation audit event")

        return jsonify(error="Could not create user"), 500

    if request.accept_mimetypes.best == "application/json":
        return jsonify(message="User has been created"), 201
    return redirect(url_for("pages.administration_settings"), code=303)


@api_bp.route("/modify_user", methods=['POST'])
def modify_user():
    actor_email = session.get("user_email")
    if actor_email is None:
        return jsonify(error="Not signed in"), 401

    data = request.form
    target = data.get("email", "").strip()
    password = data.get("password", "")
    status = data.get("status", "").strip().lower()
    role = data.get("roles", "").strip()

    allowed_roles = {
        ADMIN_ROLE,
        r"SOC Manager \ Team Lead",
        "Tier 2 SOC Analyst",
        "Tier 1 SOC Analyst",
        "Incident Responder",
        "Threat Hunter",
        "Read-Only User",
    }

    if not target:
        return jsonify(error="Email connect be empty"), 400
    if not password:
        return jsonify(error="Password cannot be empty"), 400
    if status not in ("true", "false"):
        return jsonify(error="Status must be True or False"), 400
    if role and role not in allowed_roles:
        return jsonify(error="Invalid role"), 400

    actor_id = None

    try:
        with closing(sqlite3.connect(USER_DATABASE_PATH)) as con, con:
            con.execute(
                "ATTACH DATABASE ? as audit",
                (str(AUDIT_DATABASE_PATH),),
            )

            actor = con.execute(
                "SELECT user_id, role, active FROM login WHERE email = ?",
                (actor_email,),
            ).fetchone()

            if actor is None or actor[1] != ADMIN_ROLE or not actor[2]:
                return jsonify(error="Insufficient permission"), 403

            actor_id = actor[0]

            cursor = con.execute(
                """
                UPDATE login
                SET password_hash = ?,
                    active = ?,
                    role = COALESCE(NULLIF(?, ''), role)
                WHERE email = ?
                """,
                (generate_password_hash(password), status == "true", role, target),
            )

            if cursor.rowcount == 0:
                write_user_modification(
                    con, actor_id, actor_email, target, False, "User does not exist"
                )
                return jsonify(error="User does not exist"), 404

            write_user_modification(
                con, actor_id, actor_email, target, True, "User has been modified"
            )
    except sqlite3.Error:
        current_app.logger.exception("Database error while modifying user")

        if actor_id is not None:
            try:
                with closing(sqlite3.connect(USER_DATABASE_PATH)) as con, con:
                    con.execute(
                        "ATTACH DATABASE ? AS audit",
                        (str(AUDIT_DATABASE_PATH),),
                    )
                    write_user_modification(
                        con, actor_id, actor_email, target, False,
                        "Database error; outcome not confirmed",
                    )
            except sqlite3.Error:
                current_app.logger.exception("Could not write user modification audit event")

        return jsonify(error="Could not modify user"), 500

    if request.accept_mimetypes.best == "application/json":
        return jsonify(message="User has been updated"), 200
    return redirect(url_for("pages.administration_settings"), code=303)

@api_bp.route('/return_logs')
def return_logs():
    email = session.get("user_email")
    if email is None:
        return jsonify({"error": "Not signed in"}), 401
    
    if not is_system_administrator(email):
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