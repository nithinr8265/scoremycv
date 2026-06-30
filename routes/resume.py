import os
import uuid
from flask import Blueprint, request, jsonify, session
from utils.supabase_client import get_supabase
from utils.extractor import extract_text_from_pdf, extract_text_from_docx

resume_bp = Blueprint("resume", __name__)

ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
BUCKET_NAME = "resumes"

def login_required(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user"):
            return jsonify({"error": "Authentication required"}), 401
        return fn(*args, **kwargs)
    return wrapper

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@resume_bp.route("/upload", methods=["POST"])
@login_required
def upload_resume():
    user = session["user"]

    # Handle pasted text
    if request.is_json:
        data = request.get_json()
        pasted_text = data.get("text", "").strip()
        if not pasted_text:
            return jsonify({"error": "No text provided"}), 400
        if len(pasted_text) < 100:
            return jsonify({"error": "Resume text too short"}), 400

        sb = get_supabase()
        result = sb.table("resumes").insert({
            "user_id": user["id"],
            "file_name": "pasted_resume.txt",
            "file_url": None,
            "extracted_text": pasted_text[:50000],  # cap at 50k chars
        }).execute()

        if not result.data:
            return jsonify({"error": "Failed to save resume"}), 500

        return jsonify({"success": True, "resume_id": result.data[0]["id"]}), 201

    # Handle file upload
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "No file selected"}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": "Only PDF, DOCX, and TXT files are allowed"}), 400

    file_bytes = file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        return jsonify({"error": "File size exceeds 10 MB limit"}), 413

    ext = file.filename.rsplit(".", 1)[1].lower()

    # Extract text
    try:
        if ext == "pdf":
            text = extract_text_from_pdf(file_bytes)
        elif ext == "docx":
            text = extract_text_from_docx(file_bytes)
        else:
            text = file_bytes.decode("utf-8", errors="replace")
    except ValueError as e:
        return jsonify({"error": str(e)}), 422

    if len(text.strip()) < 100:
        return jsonify({"error": "Could not extract meaningful text from the file"}), 422

    # Upload to Supabase Storage
    sb = get_supabase()
    storage_path = f"{user['id']}/{uuid.uuid4()}.{ext}"
    file_url = None
    try:
        sb.storage.from_(BUCKET_NAME).upload(storage_path, file_bytes, {
            "content-type": file.content_type or "application/octet-stream"
        })
        file_url = sb.storage.from_(BUCKET_NAME).get_public_url(storage_path)
    except Exception:
        pass  # Continue even if storage fails; text is what matters

    # Save metadata to DB
    result = sb.table("resumes").insert({
        "user_id": user["id"],
        "file_name": file.filename,
        "file_url": file_url,
        "extracted_text": text[:50000],
    }).execute()

    if not result.data:
        return jsonify({"error": "Failed to save resume metadata"}), 500

    return jsonify({"success": True, "resume_id": result.data[0]["id"]}), 201
