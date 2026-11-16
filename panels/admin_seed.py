import csv
import io
import json
import threading
from datetime import datetime, timezone
from django.contrib.auth.hashers import make_password
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError
from accounts.services import ensure_accounts_indexes_once, ensure_default_admin
import core.db as core_db
from core.db import datasets_log_col, get_cached, notifications_col, predictions_col, student_records_col, support_tickets_col, users_col

_SEED_LOCK = threading.Lock()
_ADMIN_SEED_DONE = False

DEPT_PREFIX_MAP = {
    "CS": "Computer Science", "DS": "Data Science", "AI": "Artificial Intelligence",
    "SE": "Software Engineering", "MA": "Mathematics", "DB": "Database Systems",
}

SEED_COURSES = (
    ("CS-101", "Introduction to Computer Science", "Computer Science", "2026-A", "Dr. Ayesha Khan", 3, 120),
    ("CS-204", "Data Structures & Algorithms", "Computer Science", "2025-A", "Prof. Tariq Mahmood", 4, 90),
    ("DS-301", "Applied Data Analytics", "Data Science", "2025-B", "Dr. Sana Siddiqui", 3, 75),
    ("AI-402", "Machine Learning Systems", "Artificial Intelligence", "2024-A", "Dr. Bilal Ahmed", 4, 60),
    ("SE-210", "Software Engineering Practices", "Software Engineering", "2025-A", "Engr. Nadia Farooq", 3, 85),
    ("MA-105", "Linear Algebra & Probability", "Mathematics", "2026-B", "Prof. Kamran Raza", 3, 110),
)

SEED_USERS = (
    ("USR-1001", "Dr. Ayesha Khan", "ayesha.khan@edupredict.edu", "TEACHER", "Computer Science", "ALL", None),
    ("USR-1002", "Prof. Tariq Mahmood", "tariq.mahmood@edupredict.edu", "TEACHER", "Data Science", "ALL", None),
    ("USR-1003", "Zainab Raza", "zainab.raza@edupredict.edu", "STUDENT", "Computer Science", "2026-A", "STD-2026-001"),
    ("USR-1004", "Hamza Malik", "hamza.malik@edupredict.edu", "STUDENT", "Data Science", "2025-B", "STD-2026-002"),
    ("USR-1005", "Hira Siddiqui", "hira.siddiqui@edupredict.edu", "STUDENT", "Artificial Intelligence", "2026-B", "STD-2026-003"),
    ("USR-1006", "Saad Farooq", "saad.farooq@edupredict.edu", "ANALYST", "Analytics & ML", "ALL", None),
)

SEED_TICKETS = (
    ("TKT-1001", "USR-1003", "Zainab Raza", "STUDENT", "Attendance sync mismatch for CS-101", "Weekly lab attendance percentage has not updated since Monday.", "OPEN"),
    ("TKT-1002", "USR-1001", "Dr. Ayesha Khan", "TEACHER", "Batch 2026-A roster CSV template", "Need confirmation on LMS weekly hours column before midterm upload.", "OPEN"),
    ("TKT-1003", "USR-1006", "Saad Farooq", "ANALYST", "ML pipeline retraining verification", "Random Forest risk thresholds calibrated against latest batch ingestion.", "RESOLVED"),
    ("TKT-1004", "USR-1004", "Hamza Malik", "STUDENT", "Section transfer request for DS-301", "Requesting advisor approval for morning lab slot in Applied Data Analytics.", "RESOLVED"),
)


def courses_col():
    if hasattr(core_db, "courses_col"):
        return core_db.courses_col()
    return core_db.get_collection("courses")


def _format_dt(val):
    return val.strftime("%Y-%m-%d %H:%M") if hasattr(val, "strftime") else "-"


def _serialize_value(val):
    if isinstance(val, datetime):
        return val.isoformat()
    if isinstance(val, dict):
        return {str(k): _serialize_value(v) for k, v in val.items() if k != "_id"}
    if isinstance(val, list):
        return [_serialize_value(v) for v in val]
    return val if isinstance(val, (str, int, float, bool)) or val is None else str(val)


def _infer_department_from_code(course_code):
    code = str(course_code or "").strip().upper()
    prefix = code.split("-")[0] if code else ""
    return DEPT_PREFIX_MAP.get(prefix, "General Studies")


def _safe_int(value, default, minimum, maximum):
    try:
        return max(minimum, min(maximum, int(value)))
    except (TypeError, ValueError):
        return default


def _ensure_unique_index(col, field):
    try:
        col.create_index([(field, ASCENDING)], unique=True)
    except Exception:
        pass


def ensure_admin_seed_data():
    global _ADMIN_SEED_DONE
    if _ADMIN_SEED_DONE:
        return
    with _SEED_LOCK:
        if _ADMIN_SEED_DONE:
            return
        ensure_accounts_indexes_once()
        ensure_default_admin()
        now = datetime.now(timezone.utc)
        c_col, u_col, t_col = courses_col(), users_col(), support_tickets_col()
        _ensure_unique_index(c_col, "course_code")
        _ensure_unique_index(t_col, "ticket_id")

        if c_col.count_documents({}) == 0:
            for code, title, dept, batch, inst, credits, cap in SEED_COURSES:
                if c_col.find_one({"course_code": code}, {"_id": 1}) is None:
                    c_col.insert_one({"course_code": code, "title": title, "department": dept, "batch": batch, "instructor": inst, "credits": credits, "capacity": cap, "status": "ACTIVE", "created_at": now})

        if u_col.count_documents({}) <= 1:
            pwd_hash = make_password("EduPredict@2026")
            for uid, name, email, role, dept, batch, sid in SEED_USERS:
                if u_col.find_one({"$or": [{"email": email}, {"user_id": uid}]}, {"_id": 1}) is None:
                    doc = {"user_id": uid, "full_name": name, "email": email, "password_hash": pwd_hash, "role": role, "department": dept, "batch": batch, "is_active": True, "created_at": now}
                    if sid:
                        doc["student_id"] = sid
                    try:
                        u_col.insert_one(doc)
                    except DuplicateKeyError:
                        pass

        if t_col.count_documents({}) == 0:
            for tid, uid, uname, role, subj, msg, status in SEED_TICKETS:
                if t_col.find_one({"ticket_id": tid}, {"_id": 1}) is None:
                    t_col.insert_one({"ticket_id": tid, "user_id": uid, "user_name": uname, "role": role, "subject": subj, "message": msg, "status": status, "created_at": now})
        _ADMIN_SEED_DONE = True


def _load_admin_overview_context():
    ensure_admin_seed_data()
    u_col, c_col = users_col(), courses_col()
    sr_col, p_col, t_col = student_records_col(), predictions_col(), support_tickets_col()
    student_accounts = u_col.count_documents({"role": "STUDENT"})
    student_records_count = sr_col.count_documents({})
    course_dept_map, dept_capacity = {}, {}
    for c in c_col.find({}, {"_id": 0, "course_code": 1, "department": 1, "capacity": 1}):
        code = str(c.get("course_code") or "").strip().upper()
        dept = str(c.get("department") or "General").strip()
        if code:
            course_dept_map[code] = dept
        dept_capacity[dept] = dept_capacity.get(dept, 0) + _safe_int(c.get("capacity"), 60, 0, 10000)

    dept_enrolled = {dept: 0 for dept in dept_capacity}
    att_sum, att_count = 0.0, 0
    for rec in sr_col.find({}, {"_id": 0, "course_code": 1, "attendance_pct": 1}):
        code = str(rec.get("course_code") or "").strip().upper()
        dept = course_dept_map.get(code) or _infer_department_from_code(code)
        dept_enrolled[dept] = dept_enrolled.get(dept, 0) + 1
        try:
            att_sum += float(rec.get("attendance_pct") or 0.0)
            att_count += 1
        except (TypeError, ValueError):
            pass
    if att_count == 0:
        for usr in u_col.find({"role": "STUDENT"}, {"_id": 0, "department": 1}):
            dept = str(usr.get("department") or "General").strip()
            dept_enrolled[dept] = dept_enrolled.get(dept, 0) + 1

    dept_labels = sorted(set(dept_capacity.keys()) | set(dept_enrolled.keys()))
    recent_tickets, recent_ticket_rows = [], []
    for doc in t_col.find({}, {"_id": 0}).sort("created_at", DESCENDING).limit(5):
        status_val = str(doc.get("status") or "OPEN").strip().upper()
        created_str = _format_dt(doc.get("created_at"))
        recent_tickets.append({**dict(doc), "created_at_str": created_str})
        recent_ticket_rows.append([
            str(doc.get("ticket_id") or ""),
            str(doc.get("user_name") or "User"),
            str(doc.get("subject") or ""),
            {"text": status_val, "status": "success" if status_val == "RESOLVED" else "warning"},
            created_str,
        ])

    low_risk = p_col.count_documents({"risk_level": "LOW"})
    med_risk = p_col.count_documents({"risk_level": "MEDIUM"})
    high_risk = p_col.count_documents({"risk_level": "HIGH"})
    return {
        "kpis": {
            "total_students": student_records_count if student_records_count > 0 else student_accounts,
            "student_accounts": student_accounts,
            "active_teachers": u_col.count_documents({"role": "TEACHER", "is_active": True}),
            "high_risk_count": high_risk,
            "total_predictions": p_col.count_documents({}),
            "total_users": u_col.count_documents({}),
            "active_users": u_col.count_documents({"is_active": True}),
            "open_tickets": t_col.count_documents({"status": "OPEN"}),
            "total_tickets": t_col.count_documents({}),
            "total_courses": c_col.count_documents({}),
            "active_courses": c_col.count_documents({"status": "ACTIVE"}),
            "datasets_count": datasets_log_col().count_documents({}),
            "unread_alerts": notifications_col().count_documents({"is_read": False}),
            "avg_attendance": round(att_sum / att_count, 1) if att_count > 0 else 0.0,
            "system_status": "Healthy",
        },
        "chart_data": {
            "departments": {"labels": dept_labels, "enrolled": [dept_enrolled.get(d, 0) for d in dept_labels], "capacity": [dept_capacity.get(d, 0) for d in dept_labels]},
            "risk_breakdown": {"labels": ["Low Risk", "Medium Risk", "High Risk"], "counts": [low_risk, med_risk, high_risk]},
        },
        "recent_tickets": recent_tickets,
        "recent_ticket_headers": ["Ticket ID", "User", "Subject", "Status", "Date"],
        "recent_ticket_rows": recent_ticket_rows,
    }


def get_admin_overview_context():
    return get_cached("admin:overview", _load_admin_overview_context, ttl=30.0)


def build_backup_payload(fmt="json"):
    ensure_admin_seed_data()
    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y%m%d_%H%M%S")
    data = {
        "users": [_serialize_value(d) for d in users_col().find({}, {"_id": 0, "password_hash": 0})],
        "courses": [_serialize_value(d) for d in courses_col().find({}, {"_id": 0})],
        "student_records": [_serialize_value(d) for d in student_records_col().find({}, {"_id": 0})],
        "predictions": [_serialize_value(d) for d in predictions_col().find({}, {"_id": 0})],
        "support_tickets": [_serialize_value(d) for d in support_tickets_col().find({}, {"_id": 0})],
        "datasets_log": [_serialize_value(d) for d in datasets_log_col().find({}, {"_id": 0})],
    }
    if str(fmt or "json").strip().lower() == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["collection", "record_id", "primary_label", "category", "status_or_metric", "timestamp"])
        for u in data["users"]:
            writer.writerow(["users", u.get("user_id", ""), u.get("full_name", ""), u.get("role", ""), "ACTIVE" if u.get("is_active") else "INACTIVE", u.get("created_at", "")])
        for c in data["courses"]:
            writer.writerow(["courses", c.get("course_code", ""), c.get("title", ""), c.get("department", ""), c.get("status", ""), c.get("created_at", "")])
        for s in data["student_records"]:
            writer.writerow(["student_records", s.get("student_id", ""), s.get("full_name", ""), s.get("course_code", ""), s.get("previous_gpa", ""), s.get("updated_at", "")])
        for p in data["predictions"]:
            writer.writerow(["predictions", p.get("student_id", ""), p.get("risk_level", ""), p.get("predicted_gpa", ""), p.get("dropout_risk_score", ""), p.get("generated_at", "")])
        for t in data["support_tickets"]:
            writer.writerow(["support_tickets", t.get("ticket_id", ""), t.get("subject", ""), t.get("role", ""), t.get("status", ""), t.get("created_at", "")])
        for l in data["datasets_log"]:
            writer.writerow(["datasets_log", l.get("filename", ""), l.get("uploaded_by", ""), l.get("rows_processed", 0), l.get("status", ""), l.get("uploaded_at", "")])
        return buf.getvalue(), "text/csv", f"edupredict_backup_{stamp}.csv"
    payload = {"exported_at": now.isoformat(), "counts": {k: len(v) for k, v in data.items()}, "collections": data}
    return json.dumps(payload, indent=2), "application/json", f"edupredict_backup_{stamp}.json"
