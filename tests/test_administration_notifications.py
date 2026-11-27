import os
import re
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from flask import Flask
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import check_password_hash


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
with patch.dict(os.environ, {"USER_DATABASE_PATH": "unused.db", "AUDIT_DATABASE_PATH": "unused-audit.db",
                            "ARCHIVE_DATABASE_PATH": "unused-archive.db", "SECRET_KEY": "test", "PORT": "5000"}):
    from routes import api
    from routes.pages import pages_bp


class AdministrationNotificationsTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        database = Path(self.directory.name) / "test.db"
        self.database = database
        database_patch = patch.object(api, "USER_DATABASE_PATH", database)
        database_patch.start()
        self.addCleanup(database_patch.stop)
        self.audit_database = Path(self.directory.name) / "audit.db"
        audit_patch = patch.object(api, "AUDIT_DATABASE_PATH", self.audit_database)
        audit_patch.start()
        self.addCleanup(audit_patch.stop)
        with closing(sqlite3.connect(database)) as con, con:
            con.execute(
                "CREATE TABLE login (email TEXT PRIMARY KEY, password_hash TEXT NOT NULL, "
                "full_name TEXT NOT NULL, role TEXT NOT NULL, "
                "active NOT NULL DEFAULT 1 CHECK (active IN (0, 1)), profile_picture TEXT)"
            )
            con.execute(
                "INSERT INTO login (email, password_hash, full_name, role, profile_picture) "
                "VALUES (?, ?, ?, ?, NULL)",
                ("admin@sentinel.com", "hash", "Admin", "Administrator"),
            )
        with closing(sqlite3.connect(self.audit_database)) as con, con:
            con.execute(
                "CREATE TABLE main_log (id TEXT NOT NULL PRIMARY KEY, timestamp TEXT NOT NULL, "
                "actor TEXT NOT NULL, action TEXT NOT NULL, target TEXT, "
                "result INTEGER NOT NULL CHECK (result IN (0, 1)), details TEXT)"
            )
        self.app = Flask(
            __name__,
            template_folder=str(ROOT / "src" / "templates"),
            static_folder=str(ROOT / "src" / "static"),
        )
        self.app.secret_key = "test-key"
        CSRFProtect(self.app)
        self.app.register_blueprint(api.api_bp)
        self.app.register_blueprint(pages_bp)
        self.app.add_url_rule("/", endpoint="index", view_func=lambda: "login")
        self.app.add_url_rule("/logout", endpoint="logout", view_func=lambda: "", methods=["POST"])
        self.client = self.app.test_client()
        with self.client.session_transaction() as session:
            session["user_email"] = "admin@sentinel.com"
        page = self.client.get("/settings/administration").get_data(as_text=True)
        self.token = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)

    def test_json_success_and_duplicate(self):
        data = {"csrf_token": self.token, "email": "new@example.com",
                "password": "test-password", "name": "New User", "role": "Analyst"}
        response = self.client.post("/api/create_user", data=data, headers={"Accept": "application/json"})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json["message"], "User has been created")
        with closing(sqlite3.connect(self.database)) as con:
            role, active = con.execute(
                "SELECT role, active FROM login WHERE email = ?", ("new@example.com",)
            ).fetchone()
        self.assertEqual((role, active), ("Analyst", 1))
        response = self.client.post("/api/create_user", data=data, headers={"Accept": "application/json"})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json["error"], "User already exists")
        with closing(sqlite3.connect(self.audit_database)) as con:
            events = con.execute(
                "SELECT actor, action, target, result, details FROM main_log ORDER BY rowid"
            ).fetchall()
        self.assertEqual(events, [
            ("admin@sentinel.com", "user.created", "new@example.com", 1, "User has been created"),
            ("admin@sentinel.com", "user.created", "new@example.com", 0, "User already exists"),
        ])

    def test_audit_failure_rolls_back_user_creation(self):
        data = {"csrf_token": self.token, "email": "new@example.com",
                "password": "test-password", "name": "New User", "role": "Analyst"}
        original_log = api.write_user_creation_log
        def fail_success_log(con, actor, target, result, details):
            if result:
                raise sqlite3.OperationalError("test failure")
            return original_log(con, actor, target, result, details)

        with patch.object(api, "write_user_creation_log", side_effect=fail_success_log):
            with self.assertLogs(self.app.logger, level="ERROR"):
                response = self.client.post("/api/create_user", data=data,
                                            headers={"Accept": "application/json"})
        self.assertEqual(response.status_code, 500)
        with closing(sqlite3.connect(self.database)) as con:
            self.assertIsNone(con.execute(
                "SELECT email FROM login WHERE email = ?", ("new@example.com",)
            ).fetchone())
        with closing(sqlite3.connect(self.audit_database)) as con:
            event = con.execute(
                "SELECT result, details FROM main_log WHERE target = ?", ("new@example.com",)
            ).fetchone()
        self.assertEqual(event, (0, "Database error; outcome not confirmed"))

    def test_notification_forms_use_distinct_ids_and_endpoints(self):
        page = self.client.get("/settings/administration").get_data(as_text=True)
        self.assertRegex(page, r'<form[^>]*action="/api/create_user"[^>]*id="create-user-form"')
        self.assertRegex(page, r'<form[^>]*action="/api/modify_user"[^>]*id="modify-user-form"')

    def test_invalid_and_csrf_errors(self):
        response = self.client.post("/api/create_user", data={"csrf_token": self.token},
                                    headers={"Accept": "application/json"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["error"], "Email cannot be empty!")
        self.assertEqual(self.client.post("/api/create_user", data={}).status_code, 400)

    def test_regular_form_still_redirects(self):
        response = self.client.post("/api/create_user", data={
            "csrf_token": self.token, "email": "other@example.com",
            "password": "test-password", "name": "Other", "role": "Analyst",
        })
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["Location"], "/settings/administration")

    def test_non_administrator_cannot_create_user(self):
        with self.client.session_transaction() as session:
            session["user_email"] = "other@example.com"
        response = self.client.post("/api/create_user", data={"csrf_token": self.token},
                                    headers={"Accept": "application/json"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json["error"], "Insufficient permission")

    def test_modify_user_updates_password_status_and_optional_role(self):
        with closing(sqlite3.connect(self.database)) as con, con:
            con.execute(
                "INSERT INTO login (email, password_hash, full_name, role) VALUES (?, ?, ?, ?)",
                ("user@example.com", "old-hash", "User", "Analyst"),
            )
        data = {"csrf_token": self.token, "email": " user@example.com ",
                "password": "new-password", "status": " False ", "role": "  "}
        response = self.client.post("/api/modify_user", data=data,
                                    headers={"Accept": "application/json"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["message"], "User has been updated")
        with closing(sqlite3.connect(self.database)) as con:
            password_hash, active, role = con.execute(
                "SELECT password_hash, active, role FROM login WHERE email = ?",
                ("user@example.com",),
            ).fetchone()
        self.assertTrue(check_password_hash(password_hash, "new-password"))
        self.assertEqual((active, role), (0, "Analyst"))

        data.update(status="true", role=" Administrator ")
        response = self.client.post("/api/modify_user", data=data)
        self.assertEqual(response.status_code, 303)
        with closing(sqlite3.connect(self.database)) as con:
            active, role = con.execute(
                "SELECT active, role FROM login WHERE email = ?", ("user@example.com",)
            ).fetchone()
        self.assertEqual((active, role), (1, "Administrator"))

    def test_modify_user_rejects_bad_input_and_missing_user(self):
        data = {"csrf_token": self.token, "email": "missing@example.com",
                "password": "password", "status": "maybe", "role": "Analyst"}
        response = self.client.post("/api/modify_user", data=data)
        self.assertEqual(response.status_code, 400)
        data["password"] = ""
        self.assertEqual(self.client.post("/api/modify_user", data=data).status_code, 400)
        data["password"] = "password"
        data["status"] = ""
        self.assertEqual(self.client.post("/api/modify_user", data=data).status_code, 400)
        data["status"] = "true"
        response = self.client.post("/api/modify_user", data=data)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.client.post("/api/modify_user", data={}).status_code, 400)
        with self.client.session_transaction() as session:
            session["user_email"] = "missing@example.com"
        self.assertEqual(self.client.post("/api/modify_user", data=data).status_code, 403)


if __name__ == "__main__":
    unittest.main()
