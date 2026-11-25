import os
import threading
import uuid
from datetime import datetime, timezone
from django.contrib.auth.hashers import check_password, make_password
from pymongo.errors import DuplicateKeyError
from core.db import (
    courses_col,
    ensure_indexes,
    get_cached,
    invalidate_cache,
    notifications_col,
    predictions_col,
    resolve_portal_branding,
    student_records_col,
    support_tickets_col,
    users_col,
)

VALID_ROLES = ("ADMIN", "TEACHER", "STUDENT", "ANALYST")
SELF_REGISTER_ROLES = ("STUDENT", "TEACHER", "ANALYST")
PROGRAM_LEVELS = (
    "School / Junior",
    "College / Intermediate",
    "BS / Undergraduate",
    "MS / Graduate",
)

_INDEXES_ENSURED = False
_INDEX_LOCK = threading.Lock()
_DEFAULT_ADMIN_ENSURED = False
_DEFAULT_ADMIN_LOCK = threading.Lock()


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
    global _DEFAULT_ADMIN_ENSURED
    if _DEFAULT_ADMIN_ENSURED:
        return None
    with _DEFAULT_ADMIN_LOCK:
        if _DEFAULT_ADMIN_ENSURED:
            return None

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
                _DEFAULT_ADMIN_ENSURED = True
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
        _DEFAULT_ADMIN_ENSURED = True
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
        "program_level": str(user_doc.get("program_level") or ""),
        "phone": str(user_doc.get("phone") or ""),
        "bio": str(user_doc.get("bio") or ""),
        "avatar_url": str(user_doc.get("avatar_url") or ""),
        "is_active": bool(user_doc.get("is_active", True)),
        "approval_status": str(user_doc.get("approval_status") or ("APPROVED" if user_doc.get("is_active", True) else "INACTIVE")).upper(),
        "theme_prefs": dict(user_doc.get("theme_prefs")) if isinstance(user_doc.get("theme_prefs"), dict) else {},
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
    approval_status = str(user_doc.get("approval_status") or "").strip().upper()
    if approval_status == "PENDING":
        return None, "Your teacher account is pending Admin approval. Please wait until an administrator approves your account."
    if approval_status == "REJECTED":
        reason = str(user_doc.get("rejection_reason") or "").strip()
        return None, (f"Your teacher account request was rejected by Admin. Reason: {reason}" if reason else "Your teacher account request was rejected by Admin.")
    if not user_doc.get("is_active", True):
        return None, "Your account is inactive. Please contact an administrator."
    if not check_password(password, user_doc.get("password_hash", "")):
        return None, "Invalid email or password."
    role = str(user_doc.get("role") or "").strip().upper()
    if role not in VALID_ROLES:
        return None, "Account role is invalid. Please contact an administrator."
    return user_doc, None


def register_user(full_name, email, password, role, department, batch, phone="", bio="", program_level=""):
    normalized_role = str(role or "").strip().upper()
    if normalized_role not in SELF_REGISTER_ROLES:
        return None, "Administrator accounts can only be created by an existing Admin."
    ensure_accounts_indexes_once()
    col = users_col()
    normalized_email = email.strip().lower()
    if col.find_one({"email": normalized_email}, {"_id": 1}) is not None:
        return None, "An account with this email already exists."

    resolved_department = department.strip() or "General"
    resolved_batch = batch.strip() or ("2026" if normalized_role == "STUDENT" else "ALL")
    raw_level = str(program_level or "").strip()
    resolved_program_level = raw_level if raw_level in PROGRAM_LEVELS else ""
    user_id = generate_unique_user_id(col)
    is_pending_teacher = normalized_role == "TEACHER"

    user_doc = {
        "user_id": user_id,
        "full_name": full_name.strip(),
        "email": normalized_email,
        "password_hash": make_password(password),
        "role": normalized_role,
        "department": resolved_department,
        "batch": resolved_batch,
        "program_level": resolved_program_level,
        "phone": str(phone or "").strip(),
        "bio": str(bio or "").strip(),
        "is_active": not is_pending_teacher,
        "approval_status": "PENDING" if is_pending_teacher else "APPROVED",
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

    if is_pending_teacher:
        try:
            notifications_col().insert_one(
                {
                    "title": "Teacher Approval Needed",
                    "message": f"{full_name.strip()} ({normalized_email}, {resolved_department}) registered as Teacher and is waiting for Admin approval.",
                    "severity": "WARNING",
                    "category": "APPROVAL",
                    "target_role": "ADMIN",
                    "is_read": False,
                    "created_at": datetime.now(timezone.utc),
                }
            )
            invalidate_cache("notifs:")
        except Exception:
            pass

    invalidate_cache("admin:")
    invalidate_cache("soon:")
    invalidate_cache("public:")
    return user_doc, None


def _safe_count(col_fn):
    try:
        return max(int(col_fn().count_documents({})), 0)
    except Exception:
        return 0


def get_public_portal_metrics():
    def _fetch():
        inst_name, current_term = resolve_portal_branding(db_connected=True)
        return {
            "institution_name": inst_name,
            "current_term": current_term,
            "users_count": _safe_count(users_col),
            "students_count": _safe_count(student_records_col),
            "teachers_count": int(users_col().count_documents({"role": "TEACHER"})) if callable(users_col) else 0,
            "courses_count": _safe_count(courses_col),
            "records_count": _safe_count(student_records_col),
            "predictions_count": _safe_count(predictions_col),
        }

    return get_cached("public:portal_metrics", _fetch, ttl=60.0)


def get_public_admin_contact():
    def _fetch():
        inst_name, current_term = resolve_portal_branding(db_connected=True)
        admin_doc = None
        try:
            admin_doc = users_col().find_one(
                {"role": "ADMIN", "is_active": True},
                {"_id": 0, "full_name": 1, "email": 1, "department": 1, "phone": 1},
            )
            if admin_doc is None:
                admin_doc = users_col().find_one(
                    {"role": "ADMIN"},
                    {"_id": 0, "full_name": 1, "email": 1, "department": 1, "phone": 1},
                )
        except Exception:
            admin_doc = None
        doc = admin_doc if isinstance(admin_doc, dict) else {}
        return {
            "institution_name": inst_name,
            "current_term": current_term,
            "full_name": str(doc.get("full_name") or "System Administrator").strip() or "System Administrator",
            "email": str(doc.get("email") or "admin@gmail.com").strip() or "admin@gmail.com",
            "department": str(doc.get("department") or "Administration").strip() or "Administration",
            "phone": str(doc.get("phone") or "").strip(),
        }

    return get_cached("public:admin_contact", _fetch, ttl=60.0)


def _generate_public_ticket_id(col):
    base = 1001 + int(col.count_documents({}))
    for offset in range(25):
        candidate = f"TCK-{base + offset}"
        if col.find_one({"ticket_id": candidate}, {"_id": 1}) is None:
            return candidate
    return f"TCK-{uuid.uuid4().hex[:6].upper()}"


def create_public_contact_ticket(name, email, subject, message):
    clean_name = str(name or "").strip()
    clean_email = str(email or "").strip().lower()
    clean_subject = str(subject or "").strip()
    clean_message = str(message or "").strip()
    if not clean_name or not clean_email or not clean_subject or not clean_message:
        return None, "All fields are required."
    try:
        col = support_tickets_col()
        ticket_id = _generate_public_ticket_id(col)
        now = datetime.now(timezone.utc)
        doc = {
            "ticket_id": ticket_id,
            "user_id": "GUEST",
            "user_name": clean_name,
            "email": clean_email,
            "role": "GUEST",
            "subject": clean_subject,
            "message": f"[Public Contact: {clean_email}] {clean_message}",
            "attachments": [],
            "status": "OPEN",
            "source": "PUBLIC_CONTACT",
            "created_at": now,
        }
        col.insert_one(doc)
        try:
            notifications_col().insert_one(
                {
                    "title": f"New Contact {ticket_id}: {clean_subject}",
                    "message": f"{clean_name} ({clean_email}): {clean_message}",
                    "severity": "WARNING",
                    "category": "TICKET",
                    "target_role": "ADMIN",
                    "ticket_id": ticket_id,
                    "is_read": False,
                    "created_at": now,
                }
            )
            invalidate_cache("notifs:")
        except Exception:
            pass
        invalidate_cache("admin:")
        return doc, None
    except Exception:
        return None, "Unable to save your inquiry right now. Please try again."
