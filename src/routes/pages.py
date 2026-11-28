from flask import Blueprint, render_template, session, redirect, url_for, abort
from routes.api import is_system_administrator

pages_bp = Blueprint("pages", __name__)

@pages_bp.route("/overview")
def overview_page():
    if "user_email" not in session:
        return redirect(url_for("index"))
    return render_template("overview.html")

@pages_bp.route("/incidents")
def incidents_page():
    if "user_email" not in session:
        return redirect(url_for("index"))
    return render_template("incidents.html")

@pages_bp.route("/alerts")
def alerts_page():
    if "user_email" not in session:
        return redirect(url_for("index"))
    return render_template("alerts.html")

@pages_bp.route("/search")
def search_page():
    if "user_email" not in session:
        return redirect(url_for("index"))
    return render_template("search.html")

@pages_bp.route("/assets")
def assets_page():
    if "user_email" not in session:
        return redirect(url_for("index"))
    return render_template("assets.html")

@pages_bp.route("/investigations")
def investigations_page():
    if "user_email" not in session:
        return redirect(url_for("index"))
    return render_template("investigations.html")

@pages_bp.route("/reports")
def reports_page():
    if "user_email" not in session:
        return redirect(url_for("index"))
    return render_template("reports.html")

@pages_bp.route("/settings")
def settings_page():
    if "user_email" not in session:
        return redirect(url_for("index"))
    return render_template("settings.html")

# Setting Pages

@pages_bp.route("/settings/general")
def general_settings():
    if "user_email" not in session:
        return redirect(url_for("index"))

    return render_template("setting-pages/general-settings.html")

@pages_bp.route("/settings/security")
def security_settings():
    if "user_email" not in session:
        return redirect(url_for("index"))

    return render_template("setting-pages/security-settings.html")

@pages_bp.route("/settings/notifications")
def notifications_settings():
    if "user_email" not in session:
        return redirect(url_for("index"))

    return render_template("setting-pages/notifications-settings.html")

@pages_bp.route("/settings/data-sources")
def data_sources_settings():
    if "user_email" not in session:
        return redirect(url_for("index"))

    return render_template("setting-pages/data-sources-settings.html")

@pages_bp.route("/settings/administration")
def administration_settings():
    if "user_email" not in session:
        return redirect(url_for("index"))
    if not is_system_administrator(session["user_email"]):
        abort(403)

    return render_template("setting-pages/administration-settings.html")