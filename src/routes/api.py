import sqlite3

from flask import Blueprint, jsonify, request, session
from config import DATABASE_PATH, PROFILE_PICTURE_FOLDER

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