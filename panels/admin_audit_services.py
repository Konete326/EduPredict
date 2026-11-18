import csv
import io
import threading
import uuid
from datetime import datetime, timezone
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError
from core.db import (
    check_db_health, courses_col, datasets_log_col, get_cached, get_collection,
    invalidate_cache, notifications_col, support_tickets_col, users_col,
)
from panels.admin_seed import _format_dt, _safe_int

VALID_LOG_CATEGORIES = ("USERS", "COURSES", "TICKETS", "DATA", "SYSTEM")
VALID_LOG_SEVERITIES = ("INFO", "WARNING", "DANGER", "SUCCESS")
CAT_STATUS_MAP = {"USERS": "info", "COURSES": "success", "TICKETS": "warning", "DATA": "info", "SYSTEM": "info"}
SEV_STATUS_MAP = {"INFO": "info", "SUCCESS": "success", "WARNING": "warning", "DANGER": "danger"}
LOG_HEADERS = ["Log ID", "Actor", "Role", "Category", "Activity Summary", "Level", "Timestamp"]
SETTING_HEADERS = ["Setting Name", "Group", "Current Value", "Default Value", "Status", "Updated"]
BASELINE_AUDIT_LOGS = (
    ("LOG-1001", "System Admin", "ADMIN", "SYSTEM", "PORTAL_BOOT", "EduPredict academic portal audit trail initialized.", "INFO", "SYSTEM"),
    ("LOG-1002", "Saad Farooq", "ANALYST", "DATA", "PIPELINE_READY", "Automated ML evaluation and dropout risk pipeline verified.", "SUCCESS", "SYSTEM"),
    ("LOG-1003", "Dr. Ayesha Khan", "TEACHER", "COURSES", "ROSTER_SYNC", "CS-101 course roster and attendance threshold synced.", "INFO", "SYSTEM"),
    ("LOG-1004", "System Admin", "ADMIN", "SYSTEM", "SECURITY_CHECK", "Role-based access guards active across all 4 portal panels.", "WARNING", "SYSTEM"),
)
DEFAULT_PORTAL_SETTINGS = {
    "institution_name": "EduPredict Academic Portal", "current_term": "Fall 2026", "default_batch": "2026-A",
    "passing_gpa": 2.0, "min_attendance_pct": 75, "high_risk_threshold": 70, "medium_risk_threshold": 35,
    "anomaly_drop_pct": 25, "auto_student_alerts": True, "auto_teacher_alerts": True,
    "updated_by": "System Admin", "updated_at_str": "",
}
INT_SETTING_RANGES = (("min_attendance_pct", 0, 100, "Minimum attendance"), ("high_risk_threshold", 10, 100, "High risk limit"), ("medium_risk_threshold", 5, 95, "Medium risk limit"), ("anomaly_drop_pct", 5, 90, "Sudden drop limit"))
_AUDIT_LOCK = threading.Lock()
_AUDIT_SEED_DONE = False


def activity_logs_col():
    return get_collection("activity_logs")


def system_settings_col():
    return get_collection("system_settings")


def _clean_category(category_filter):
    clean = str(category_filter or "ALL").strip().upper()
    return clean if clean == "ALL" or clean in VALID_LOG_CATEGORIES else "ALL"


def _safe_float(value, default, minimum, maximum):
    try:
        return round(max(minimum, min(maximum, float(value))), 2)
    except (TypeError, ValueError):
        return default


def _parse_bool(post_data, key):
    raw = post_data.get(key)
    return bool(raw) if raw is None or isinstance(raw, bool) else str(raw).strip().lower() in ("true", "1", "yes", "on")


def _dt_sort_value(val):
    if isinstance(val, str) and val.strip():
        try:
            val = datetime.fromisoformat(val.strip().replace("Z", "+00:00"))
        except ValueError:
            return 0.0
    if isinstance(val, datetime):
        return (val.replace(tzinfo=timezone.utc) if val.tzinfo is None else val.astimezone(timezone.utc)).timestamp()
    return 0.0


def _ensure_audit_seed_data():
    global _AUDIT_SEED_DONE
    if _AUDIT_SEED_DONE:
        return
    with _AUDIT_LOCK:
        if _AUDIT_SEED_DONE:
            return
        a_col, s_col = activity_logs_col(), system_settings_col()
        for col, field in ((a_col, "log_id"), (s_col, "setting_key")):
            try:
                col.create_index([(field, ASCENDING)], unique=True)
            except Exception:
                pass
        if a_col.count_documents({}) == 0:
            now = datetime.now(timezone.utc)
            for log_id, actor, role, cat, act, summ, sev, src in BASELINE_AUDIT_LOGS:
                if a_col.find_one({"log_id": log_id}, {"_id": 1}) is None:
                    try:
                        a_col.insert_one({"log_id": log_id, "actor": actor, "role": role, "category": cat, "action": act, "summary": summ, "severity": sev, "source": src, "created_at": now})
                    except DuplicateKeyError:
                        pass
        _AUDIT_SEED_DONE = True


def _generate_unique_log_id(col):
    base = 1001 + _safe_int(col.count_documents({}), 0, 0, 1000000)
    for offset in range(30):
        candidate = f"LOG-{base + offset}"
        if col.find_one({"log_id": candidate}, {"_id": 1}) is None:
            return candidate
    return f"LOG-{uuid.uuid4().hex[:6].upper()}"


def _fetch_sorted_docs(col, projection, sort_field, limit=50):
    cursor = col.find({}, projection)
    if isinstance(cursor, (list, tuple)):
        return list(cursor)[:limit]
    if hasattr(cursor, "sort"):
        cursor = cursor.sort(sort_field, DESCENDING)
    if isinstance(cursor, (list, tuple)):
        return list(cursor)[:limit]
    if hasattr(cursor, "limit"):
        limited = cursor.limit(limit)
        items = list(limited)
        if items or limited is cursor:
            return items
    return list(cursor)[:limit]


def _normalize_log_entry(doc, fallback_id="LOG-0000", fallback_source="SYSTEM"):
    cat, sev, created_at = str(doc.get("category") or "SYSTEM").strip().upper(), str(doc.get("severity") or "INFO").strip().upper(), doc.get("created_at")
    return {
        "log_id": str(doc.get("log_id") or fallback_id), "actor": str(doc.get("actor") or "System Admin").strip() or "System Admin",
        "role": str(doc.get("role") or "SYSTEM").strip().upper(), "category": cat if cat in VALID_LOG_CATEGORIES else "SYSTEM",
        "action": str(doc.get("action") or "EVENT").strip().upper(), "summary": str(doc.get("summary") or "").strip(),
        "severity": sev if sev in VALID_LOG_SEVERITIES else "INFO", "source": str(doc.get("source") or fallback_source).strip().upper(),
        "created_at": created_at, "created_at_str": _format_dt(created_at),
    }


def _collect_platform_logs():
    items = []
    for u in _fetch_sorted_docs(users_col(), {"_id": 0, "password_hash": 0}, "created_at", limit=15):
        uid, name, urole, active = str(u.get("user_id") or "USR"), str(u.get("full_name") or u.get("email") or "Portal User"), str(u.get("role") or "USER").strip().upper(), bool(u.get("is_active", True))
        items.append(_normalize_log_entry({"log_id": f"EVT-{uid}", "actor": name, "role": urole, "category": "USERS", "action": "USER_ACTIVE" if active else "USER_INACTIVE", "summary": f"Account {'active' if active else 'deactivated'} for {name} ({urole}, {u.get('department') or 'General'}).", "severity": "SUCCESS" if active else "WARNING", "source": "PLATFORM", "created_at": u.get("created_at")}))
    for c in _fetch_sorted_docs(courses_col(), {"_id": 0}, "created_at", limit=15):
        code, status = str(c.get("course_code") or "COURSE").strip().upper(), str(c.get("status") or "ACTIVE").strip().upper()
        items.append(_normalize_log_entry({"log_id": f"CRS-{code}", "actor": str(c.get("instructor") or "Academic Admin"), "role": "ADMIN", "category": "COURSES", "action": f"COURSE_{status}", "summary": f"Course {code} ({c.get('title') or code}) in {c.get('department') or 'General'} is {status.lower()}.", "severity": "INFO" if status == "ACTIVE" else "WARNING", "source": "PLATFORM", "created_at": c.get("updated_at") or c.get("created_at")}))
    for t in _fetch_sorted_docs(support_tickets_col(), {"_id": 0}, "created_at", limit=15):
        tid, status = str(t.get("ticket_id") or "TKT"), str(t.get("status") or "OPEN").strip().upper()
        items.append(_normalize_log_entry({"log_id": tid if tid.startswith("TKT-") else f"TKT-{tid}", "actor": str(t.get("user_name") or "Portal User"), "role": str(t.get("role") or "USER").strip().upper(), "category": "TICKETS", "action": f"TICKET_{status}", "summary": f"Help ticket {tid} ({status.title()}): {t.get('subject') or 'Support inquiry'}", "severity": "SUCCESS" if status == "RESOLVED" else "WARNING", "source": "PLATFORM", "created_at": t.get("updated_at") or t.get("created_at")}))
    for idx, d in enumerate(_fetch_sorted_docs(datasets_log_col(), {"_id": 0}, "uploaded_at", limit=15), start=1):
        status, rows_n, fixed_n = str(d.get("status") or "COMPLETED").strip().upper(), _safe_int(d.get("rows_processed"), 0, 0, 1000000), _safe_int(d.get("missing_values_fixed"), 0, 0, 1000000)
        items.append(_normalize_log_entry({"log_id": f"DAT-{1000 + idx}", "actor": str(d.get("uploaded_by") or "Data Analyst"), "role": "ANALYST", "category": "DATA", "action": "DATASET_UPLOAD", "summary": f"Dataset {d.get('filename') or 'dataset.csv'} processed ({rows_n} rows, {fixed_n} imputed) - {status}.", "severity": "SUCCESS" if status == "COMPLETED" else "DANGER", "source": "PLATFORM", "created_at": d.get("uploaded_at") or d.get("created_at")}))
    return items


def record_audit_log(actor, role, category, action, summary, severity="INFO", source="SYSTEM"):
    clean_summary = str(summary or "").strip()
    if not clean_summary:
        return None
    col, clean_cat, clean_sev = activity_logs_col(), str(category or "SYSTEM").strip().upper(), str(severity or "INFO").strip().upper()
    doc = {
        "log_id": _generate_unique_log_id(col), "actor": str(actor or "System Admin").strip() or "System Admin",
        "role": str(role or "ADMIN").strip().upper() or "ADMIN", "category": clean_cat if clean_cat in VALID_LOG_CATEGORIES else "SYSTEM",
        "action": str(action or "EVENT").strip().upper() or "EVENT", "summary": clean_summary,
        "severity": clean_sev if clean_sev in VALID_LOG_SEVERITIES else "INFO", "source": str(source or "SYSTEM").strip().upper() or "SYSTEM",
        "created_at": datetime.now(timezone.utc),
    }
    col.insert_one(doc)
    invalidate_cache()
    return doc


def _load_activity_logs(clean_cat):
    _ensure_audit_seed_data()
    all_logs = [_normalize_log_entry(d) for d in _fetch_sorted_docs(activity_logs_col(), {"_id": 0}, "created_at", limit=60)] + _collect_platform_logs()
    all_logs.sort(key=lambda x: (_dt_sort_value(x.get("created_at")), 1 if x.get("source") == "MANUAL" else 0), reverse=True)
    counts = {"ALL": 0, "USERS": 0, "COURSES": 0, "TICKETS": 0, "DATA": 0, "SYSTEM": 0}
    for item in all_logs:
        counts["ALL"] += 1
        if item["category"] in counts:
            counts[item["category"]] += 1
    log_kpis = {"total_events": len(all_logs), "admin_actions": sum(1 for x in all_logs if x["role"] == "ADMIN" or x["source"] == "MANUAL"), "data_ml_events": sum(1 for x in all_logs if x["category"] == "DATA"), "security_events": sum(1 for x in all_logs if x["severity"] in ("WARNING", "DANGER") or x["category"] == "SYSTEM")}
    logs = all_logs if clean_cat == "ALL" else [x for x in all_logs if x["category"] == clean_cat]
    rows = [[x["log_id"], x["actor"], {"text": x["role"], "status": "info"}, {"text": x["category"], "status": CAT_STATUS_MAP.get(x["category"], "info")}, x["summary"], {"text": x["severity"], "status": SEV_STATUS_MAP.get(x["severity"], "info")}, x["created_at_str"]] for x in logs]
    return logs, counts, log_kpis, list(LOG_HEADERS), rows


def list_activity_logs(category_filter="ALL"):
    clean_cat = _clean_category(category_filter)
    return get_cached(f"admin:logs:{clean_cat}", lambda: _load_activity_logs(clean_cat), ttl=30.0)


def get_default_admin_logs_context(selected_category="ALL"):
    return {"logs": [], "category_counts": {"ALL": 0, "USERS": 0, "COURSES": 0, "TICKETS": 0, "DATA": 0, "SYSTEM": 0}, "log_kpis": {"total_events": 0, "admin_actions": 0, "data_ml_events": 0, "security_events": 0}, "log_headers": list(LOG_HEADERS), "log_rows": [], "selected_category": selected_category}


def export_activity_logs_csv(category_filter="ALL"):
    clean_cat = _clean_category(category_filter)
    logs, _, _, _, _ = list_activity_logs(clean_cat)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Log ID", "Actor", "Role", "Category", "Action", "Activity Summary", "Level", "Source", "Timestamp"])
    for item in logs:
        writer.writerow([item["log_id"], item["actor"], item["role"], item["category"], item["action"], item["summary"], item["severity"], item["source"], item["created_at_str"]])
    return buf.getvalue(), "text/csv", f"edupredict_activity_logs_{clean_cat.lower()}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"


def clear_manual_audit_logs(actor_name="System Admin"):
    deleted = _safe_int(getattr(activity_logs_col().delete_many({"source": "MANUAL"}), "deleted_count", 0), 0, 0, 1000000)
    record_audit_log(actor_name, "ADMIN", "SYSTEM", "CLEAR_MANUAL_LOGS", f"Cleared {deleted} manual activity note(s).", severity="INFO", source="SYSTEM")
    invalidate_cache()
    return deleted


def _alerts_label(cfg):
    return f"Student: {'On' if cfg['auto_student_alerts'] else 'Off'}, Teacher: {'On' if cfg['auto_teacher_alerts'] else 'Off'}"


def _build_settings_context(raw_doc, db_connected=True):
    doc, d = (raw_doc if isinstance(raw_doc, dict) else {}), DEFAULT_PORTAL_SETTINGS
    s = {
        "institution_name": str(doc.get("institution_name") or d["institution_name"]).strip() or d["institution_name"],
        "current_term": str(doc.get("current_term") or d["current_term"]).strip() or d["current_term"],
        "default_batch": str(doc.get("default_batch") or d["default_batch"]).strip() or d["default_batch"],
        "passing_gpa": _safe_float(doc.get("passing_gpa"), d["passing_gpa"], 0.0, 4.0),
        "auto_student_alerts": bool(doc["auto_student_alerts"]) if "auto_student_alerts" in doc else d["auto_student_alerts"],
        "auto_teacher_alerts": bool(doc["auto_teacher_alerts"]) if "auto_teacher_alerts" in doc else d["auto_teacher_alerts"],
        "updated_by": str(doc.get("updated_by") or d["updated_by"]).strip() or d["updated_by"],
        "updated_at_str": _format_dt(doc.get("updated_at")) if doc.get("updated_at") else str(doc.get("updated_at_str") or ""),
        **{k: _safe_int(doc.get(k), d[k], low, high) for k, low, high, _ in INT_SETTING_RANGES},
    }
    settings_kpis = {"current_term": s["current_term"], "default_batch": s["default_batch"], "min_attendance_pct": s["min_attendance_pct"], "passing_gpa": s["passing_gpa"], "high_risk_threshold": s["high_risk_threshold"], "medium_risk_threshold": s["medium_risk_threshold"], "alerts_status": "Enabled" if (s["auto_student_alerts"] or s["auto_teacher_alerts"]) else "Paused", "db_status": "Connected" if db_connected else "Offline"}
    updated_label = s["updated_at_str"] or "Default"
    specs = (
        ("Portal Name", "General", s["institution_name"], d["institution_name"], s["institution_name"] != d["institution_name"]),
        ("Term & Batch", "Academic", f"{s['current_term']} ({s['default_batch']})", f"{d['current_term']} ({d['default_batch']})", s["current_term"] != d["current_term"] or s["default_batch"] != d["default_batch"]),
        ("Passing GPA", "Academic", f"{s['passing_gpa']:.1f}", f"{d['passing_gpa']:.1f}", abs(s["passing_gpa"] - d["passing_gpa"]) > 0.001),
        ("Minimum Attendance", "Academic", f"{s['min_attendance_pct']}%", f"{d['min_attendance_pct']}%", s["min_attendance_pct"] != d["min_attendance_pct"]),
        ("High Risk Limit", "Risk Limits", f"{s['high_risk_threshold']}%", f"{d['high_risk_threshold']}%", s["high_risk_threshold"] != d["high_risk_threshold"]),
        ("Medium Risk Limit", "Risk Limits", f"{s['medium_risk_threshold']}%", f"{d['medium_risk_threshold']}%", s["medium_risk_threshold"] != d["medium_risk_threshold"]),
        ("Sudden Drop Limit", "Anomaly Rules", f"{s['anomaly_drop_pct']}%", f"{d['anomaly_drop_pct']}%", s["anomaly_drop_pct"] != d["anomaly_drop_pct"]),
        ("Auto Alerts", "Notifications", _alerts_label(s), _alerts_label(d), (s["auto_student_alerts"], s["auto_teacher_alerts"]) != (d["auto_student_alerts"], d["auto_teacher_alerts"])),
    )
    setting_rows = [[n, g, cv, dv, {"text": "Custom" if chg else "Default", "status": "info" if chg else "success"}, updated_label] for n, g, cv, dv, chg in specs]
    return {"settings_data": s, "settings_kpis": settings_kpis, "setting_headers": list(SETTING_HEADERS), "setting_rows": setting_rows}


def get_default_portal_settings_context():
    return _build_settings_context({}, db_connected=False)


def get_portal_settings():
    def _load():
        _ensure_audit_seed_data()
        return _build_settings_context(system_settings_col().find_one({"setting_key": "portal_config"}, {"_id": 0}), db_connected=bool(check_db_health().get("connected", False)))
    return get_cached("admin:settings", _load, ttl=30.0)


def _save_settings_doc(values, actor_name, action, summary, severity):
    now, clean_actor = datetime.now(timezone.utc), str(actor_name or "System Admin").strip() or "System Admin"
    payload = {**values, "setting_key": "portal_config", "updated_by": clean_actor, "updated_at": now, "updated_at_str": _format_dt(now)}
    system_settings_col().update_one({"setting_key": "portal_config"}, {"$set": payload}, upsert=True)
    record_audit_log(clean_actor, "ADMIN", "SYSTEM", action, summary, severity=severity, source="SYSTEM")
    invalidate_cache()
    return payload, None


def update_portal_settings(post_data, actor_name="System Admin"):
    base, existing = dict(DEFAULT_PORTAL_SETTINGS), system_settings_col().find_one({"setting_key": "portal_config"}, {"_id": 0})
    if isinstance(existing, dict):
        base.update({k: existing[k] for k in DEFAULT_PORTAL_SETTINGS if k in existing})
    text_vals = {k: str(post_data.get(k) if k in post_data else base[k]).strip() for k in ("institution_name", "current_term", "default_batch")}
    if not all(text_vals.values()):
        return None, "Portal name, current term, and default batch are required."
    try:
        gpa = round(float(post_data.get("passing_gpa") if "passing_gpa" in post_data else base["passing_gpa"]), 2)
        ints = {k: int(post_data.get(k) if k in post_data else base[k]) for k, _, _, _ in INT_SETTING_RANGES}
    except (TypeError, ValueError):
        return None, "Enter valid numbers for GPA, attendance, and risk limits."
    if not (0.0 <= gpa <= 4.0):
        return None, "Passing GPA must be between 0.0 and 4.0."
    for key, low, high, label in INT_SETTING_RANGES:
        if not (low <= ints[key] <= high):
            return None, f"{label} must be between {low} and {high}."
    if ints["medium_risk_threshold"] >= ints["high_risk_threshold"]:
        return None, "Medium risk threshold must be lower than high risk threshold."
    values = {**text_vals, "passing_gpa": gpa, **ints, "auto_student_alerts": _parse_bool(post_data, "auto_student_alerts"), "auto_teacher_alerts": _parse_bool(post_data, "auto_teacher_alerts")}
    return _save_settings_doc(values, actor_name, "UPDATE_SETTINGS", f"Updated portal settings ({text_vals['current_term']}, {text_vals['default_batch']}, min attendance {ints['min_attendance_pct']}%).", "SUCCESS")


def reset_portal_settings(actor_name="System Admin"):
    return _save_settings_doc(dict(DEFAULT_PORTAL_SETTINGS), actor_name, "RESET_SETTINGS", "Restored portal settings to default values.", "WARNING")
