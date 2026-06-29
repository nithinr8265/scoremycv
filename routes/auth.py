import os
import bcrypt
from flask import Blueprint, request, jsonify, session, redirect, url_for
from utils.supabase_client import get_supabase
from utils.jwt_util import create_token, decode_token, create_reset_token

auth_bp = Blueprint("auth", __name__)

# ── Signup ─────────────────────────────────────────────────────────────────────
@auth_bp.route("/signup", methods=["POST"])
def signup():
    data = request.get_json()
    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not name or not email or not password:
        return jsonify({"error": "All fields are required"}), 400
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    sb = get_supabase()
    # Check if email exists
    existing = sb.table("users").select("id").eq("email", email).execute()
    if existing.data:
        return jsonify({"error": "Email already registered"}), 409

    # Hash password
    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    # Insert user
    result = sb.table("users").insert({
        "name": name,
        "email": email,
        "password_hash": pw_hash,
        "role": "user"
    }).execute()

    if not result.data:
        return jsonify({"error": "Failed to create account"}), 500

    user = result.data[0]
    token = create_token(user["id"], user["email"])
    session["user"] = {"id": user["id"], "name": user["name"], "email": user["email"], "role": "user"}
    return jsonify({"success": True, "token": token, "user": session["user"]}), 201


# ── Login ──────────────────────────────────────────────────────────────────────
@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    sb = get_supabase()
    result = sb.table("users").select("*").eq("email", email).execute()
    if not result.data:
        return jsonify({"error": "Invalid email or password"}), 401

    user = result.data[0]
    if not user.get("password_hash"):
        return jsonify({"error": "Please use Google login for this account"}), 401

    if not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
        return jsonify({"error": "Invalid email or password"}), 401

    token = create_token(user["id"], user["email"], user.get("role", "user"))
    session["user"] = {"id": user["id"], "name": user["name"], "email": user["email"], "role": user.get("role", "user")}
    return jsonify({"success": True, "token": token, "user": session["user"]}), 200


# ── Logout ─────────────────────────────────────────────────────────────────────
@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True}), 200


# ── Forgot Password ────────────────────────────────────────────────────────────
@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    data = request.get_json()
    email = data.get("email", "").strip().lower()
    if not email:
        return jsonify({"error": "Email is required"}), 400

    sb = get_supabase()
    result = sb.table("users").select("id").eq("email", email).execute()
    # Always return success to prevent email enumeration
    if result.data:
        token = create_reset_token(email)
        reset_url = f"{os.environ.get('APP_URL', 'http://localhost:5000')}/auth/reset-password?token={token}"
        # Send email via Flask-Mail (imported in app.py, use current_app)
        from flask import current_app
        from flask_mail import Message
        try:
            from app import mail
            msg = Message(
                subject="Reset your ScoreMyCV password",
                recipients=[email],
                html=f"""
                <h2>Password Reset</h2>
                <p>Click the link below to reset your password. This link expires in 1 hour.</p>
                <a href="{reset_url}" style="background:#2563eb;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;">Reset Password</a>
                <p>If you didn't request this, ignore this email.</p>
                """
            )
            mail.send(msg)
        except Exception:
            pass  # Log in production

    return jsonify({"success": True, "message": "If that email exists, a reset link has been sent"}), 200


# ── Reset Password ─────────────────────────────────────────────────────────────
@auth_bp.route("/reset-password", methods=["POST"])
def reset_password():
    data = request.get_json()
    token = data.get("token", "")
    new_password = data.get("password", "")

    if not token or not new_password:
        return jsonify({"error": "Token and new password are required"}), 400
    if len(new_password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    try:
        payload = decode_token(token)
        if payload.get("purpose") != "reset":
            raise ValueError("Invalid token purpose")
        email = payload["email"]
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    pw_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    sb = get_supabase()
    sb.table("users").update({"password_hash": pw_hash}).eq("email", email).execute()
    return jsonify({"success": True, "message": "Password updated successfully"}), 200


# ── Google OAuth callback (handled via Supabase Auth) ─────────────────────────
@auth_bp.route("/google/callback", methods=["POST"])
def google_callback():
    data = request.get_json()
    access_token = data.get("access_token")
    if not access_token:
        return jsonify({"error": "Access token required"}), 400

    sb = get_supabase()
    try:
        user_resp = sb.auth.get_user(access_token)
        supabase_user = user_resp.user
        email = supabase_user.email
        name = supabase_user.user_metadata.get("full_name", email.split("@")[0])
        google_id = supabase_user.id

        # Upsert user in our users table
        existing = sb.table("users").select("*").eq("email", email).execute()
        if existing.data:
            user = existing.data[0]
            sb.table("users").update({"google_id": google_id, "name": name}).eq("email", email).execute()
        else:
            result = sb.table("users").insert({
                "name": name,
                "email": email,
                "google_id": google_id,
                "role": "user"
            }).execute()
            user = result.data[0]

        token = create_token(user["id"], email)
        session["user"] = {"id": user["id"], "name": name, "email": email, "role": user.get("role", "user")}
        return jsonify({"success": True, "token": token, "user": session["user"]}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 401


# ── Auth pages (GET) ──────────────────────────────────────────────────────────
@auth_bp.route("/login", methods=["GET"])
def login_page():
    from flask import render_template
    return render_template("login.html")

@auth_bp.route("/signup", methods=["GET"])
def signup_page():
    from flask import render_template
    return render_template("signup.html")

@auth_bp.route("/forgot-password", methods=["GET"])
def forgot_password_page():
    from flask import render_template
    return render_template("forgot_password.html")

@auth_bp.route("/reset-password", methods=["GET"])
def reset_password_page():
    from flask import render_template
    token = request.args.get("token", "")
    return render_template("reset_password.html", token=token)

@auth_bp.route("/google/redirect", methods=["GET"])
def google_redirect():
    supabase_url = os.environ.get("SUPABASE_URL", "")
    app_url = os.environ.get("APP_URL", "http://localhost:5000")
    redirect_to = f"{app_url}/auth/google/callback-page"
    return redirect(f"{supabase_url}/auth/v1/authorize?provider=google&redirect_to={redirect_to}")

@auth_bp.route("/google/callback-page", methods=["GET"])
def google_callback_page():
    from flask import render_template
    return render_template("google_callback.html")
