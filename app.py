import os
from flask import Flask
from flask_mail import Mail
from dotenv import load_dotenv

load_dotenv()

from routes.auth import auth_bp
from routes.resume import resume_bp
from routes.analysis import analysis_bp
from routes.report import report_bp
from routes.admin import admin_bp
from utils.supabase_client import init_supabase



app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-in-prod")

# Mail config (Supabase SMTP / Gmail)
app.config["MAIL_SERVER"] = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
app.config["MAIL_PORT"] = int(os.environ.get("MAIL_PORT", 587))
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = os.environ.get("MAIL_DEFAULT_SENDER")

mail = Mail(app)

# Register blueprints
app.register_blueprint(auth_bp, url_prefix="/auth")
app.register_blueprint(resume_bp, url_prefix="/resume")
app.register_blueprint(analysis_bp, url_prefix="/analysis")
app.register_blueprint(report_bp, url_prefix="/report")
app.register_blueprint(admin_bp, url_prefix="/admin")

# Main routes
from flask import render_template, session, redirect, url_for

@app.route("/")
def index():
    if session.get("user"):
        return redirect(url_for("dashboard"))
    return render_template("landing.html")

@app.route("/dashboard")
def dashboard():
    if not session.get("user"):
        return redirect(url_for("index"))
    return render_template("dashboard.html", user=session["user"])

@app.route("/upload")
def upload_page():
    if not session.get("user"):
        return redirect(url_for("index"))
    return render_template("upload.html", user=session["user"])

@app.route("/history")
def history_page():
    if not session.get("user"):
        return redirect(url_for("index"))
    return render_template("history.html", user=session["user"])

@app.route("/profile")
def profile_page():
    if not session.get("user"):
        return redirect(url_for("index"))
    return render_template("profile.html", user=session["user"])

@app.route("/result/<analysis_id>")
def result_page(analysis_id):
    if not session.get("user"):
        return redirect(url_for("index"))
    return render_template("result.html", user=session["user"], analysis_id=analysis_id)

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "False") == "True", port=5000)
