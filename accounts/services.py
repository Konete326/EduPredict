import os
import threading
import uuid
from datetime import datetime, timezone
from django.contrib.auth.hashers import check_password, make_password
from pymongo.errors import DuplicateKeyError
from core.db import ensure_indexes, student_records_col, users_col

VALID_ROLES = ("ADMIN", "TEACHER", "STUDENT", "ANALYST")

_INDEXES_ENSURED = False
_INDEX_LOCK = threading.Lock()


def ensure_accounts_indexes_once():
    global _INDEXES_ENSURED
    if _INDEXES_ENSURED:
        return True
    with _INDEX_LOCK:
        if _INDEXES_ENSURED:
            return True
        if ensure_indexes():
            _INDEXES_ENSURED = True
            return True
        return False


def ensure_default_admin():
    admin_email = (os.getenv("ADMIN_EMAIL") or "admin@gmail.com").strip().lower() or "admin@gmail.com"
    admin_password = os.getenv("ADMIN_PASSWORD") or "admin123"
    admin_full_name = (os.getenv("ADMIN_FULL_NAME") or "System Administrator").strip() or "System Administrator"

    ensure_accounts_indexes_once()
    col = users_col()
    existing = col.find_one({"email": admin_email})
    if existing is None:
        admin_doc = {
            "user_id": "USR-1000",
            "full_name": admin_full_name,
            "email": admin_email,
            "password_hash": make_password(admin_password),
            "role": "ADMIN",
            "department": "Administration",
            "batch": "ALL",
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
        }
        try:
            col.insert_one(admin_doc)
            return admin_doc
        except DuplicateKeyError:
            existing = col.find_one({"email": admin_email})
            if existing is None:
                raise

    updates = {}
    if existing.get("role") != "ADMIN":
        updates["role"] = "ADMIN"
    if existing.get("is_active") is not True:
        updates["is_active"] = True
    if not check_password(admin_password, existing.get("password_hash", "")):
        updates["password_hash"] = make_password(admin_password)
    if updates:
        col.update_one({"_id": existing["_id"]}, {"$set": updates})
        existing.update(updates)
    return existing


def serialize_session_user(user_doc):
    role = str(user_doc.get("role") or "").strip().upper()
    session_user = {
        "user_id": str(user_doc.get("user_id") or ""),
        "full_name": str(user_doc.get("full_name") or ""),
        "email": str(user_doc.get("email") or "").strip().lower(),
        "role": role,
        "department": str(user_doc.get("department") or ""),
        "batch": str(user_doc.get("batch") or ""),
        "is_active": bool(user_doc.get("is_active", True)),
    }
    student_id = user_doc.get("student_id")
    if role == "STUDENT":
        session_user["student_id"] = str(student_id or session_user["user_id"])
    elif student_id:
        session_user["student_id"] = str(student_id)
    return session_user


def generate_unique_user_id(col):
    base = 1001 + col.count_documents({})
    for offset in range(25):
        candidate = f"USR-{base + offset}"
        if col.find_one({"user_id": candidate}, {"_id": 1}) is None:
            return candidate
    return f"USR-{uuid.uuid4().hex[:6].upper()}"


def generate_unique_student_id(records_col, user_id):
    year = datetime.now(timezone.utc).year
    suffix = str(user_id).split("-")[-1]
    candidate = f"STD-{year}-{suffix}"
    if records_col.find_one({"student_id": candidate}, {"_id": 1}) is None:
        return candidate
    return f"STD-{year}-{uuid.uuid4().hex[:4].upper()}"


def authenticate_user(email, password):
    ensure_default_admin()
    user_doc = users_col().find_one({"email": email.strip().lower()})
    if user_doc is None:
        return None, "Invalid email or password."
    if not user_doc.get("is_active", True):
        return None, "Your account is inactive. Please contact an administrator."
    if not check_password(password, user_doc.get("password_hash", "")):
        return None, "Invalid email or password."
    role = str(user_doc.get("role") or "").strip().upper()
    if role not in VALID_ROLES:
        return None, "Account role is invalid. Please contact an administrator."
    return user_doc, None


def register_user(full_name, email, password, role, department, batch):
    ensure_accounts_indexes_once()
    col = users_col()
    normalized_email = email.strip().lower()
    if col.find_one({"email": normalized_email}, {"_id": 1}) is not None:
        return None, "An account with this email already exists."

    normalized_role = role.strip().upper()
    resolved_department = department.strip() or "General"
    resolved_batch = batch.strip() or ("2026" if normalized_role == "STUDENT" else "ALL")
    user_id = generate_unique_user_id(col)

    user_doc = {
        "user_id": user_id,
        "full_name": full_name.strip(),
        "email": normalized_email,
        "password_hash": make_password(password),
        "role": normalized_role,
        "department": resolved_department,
        "batch": resolved_batch,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    }

    student_id = None
    if normalized_role == "STUDENT":
        records_col = student_records_col()
        student_id = generate_unique_student_id(records_col, user_id)
        user_doc["student_id"] = student_id

    try:
        col.insert_one(user_doc)
    except DuplicateKeyError:
        return None, "An account with this email already exists."

    if normalized_role == "STUDENT" and student_id:
        records_col = student_records_col()
        if records_col.find_one({"student_id": student_id}, {"_id": 1}) is None:
            records_col.insert_one(
                {
                    "student_id": student_id,
                    "full_name": full_name.strip(),
                    "batch": resolved_batch,
                    "course_code": "CS-101",
                    "attendance_pct": 85.0,
                    "internal_marks": 75.0,
                    "assignment_score": 80.0,
                    "lms_hours_weekly": 10.0,
                    "previous_gpa": 3.2,
                    "updated_at": datetime.now(timezone.utc),
                }
            )

    return user_doc, None
