from flask import Blueprint, render_template, session, redirect, url_for

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