import json, re
from datetime import datetime, timezone
from django.contrib.auth.hashers import make_password
from pymongo import DESCENDING
from analytics.data_pipeline import REQUIRED_COLUMNS
from analytics.ml_engine import _resolve_runtime_settings, run_prediction_pipeline
from core.db import courses_col, datasets_log_col, get_cached, invalidate_cache, notifications_col, predictions_col, student_records_col, support_tickets_col, users_col


def _safe_float(val, default=0.0):
    try: return float(val)
    except (TypeError, ValueError): return default


def _action(label, icon, onclick, title, attrs, variant="default"): return {"label": label, "icon": icon, "variant": variant, "title": title, "onclick": onclick, "attrs": attrs}
def _view_action(title, payload): return {"type": "view_modal", "label": "View", "icon": "fa-solid fa-eye", "variant": "default", "title": title, "payload_json": json.dumps(payload)}


def _is_admin(teacher_user):
    return not isinstance(teacher_user, dict) or str(teacher_user.get("role") or "").strip().upper() == "ADMIN"


def _scope_key(teacher_user):
    if _is_admin(teacher_user): return "all"
    return str(teacher_user.get("user_id") or "").strip() or str(teacher_user.get("email") or "").strip().lower() or str(teacher_user.get("full_name") or "").strip().lower() or "none"


def _teacher_student_query(teacher_user=None):
    if _is_admin(teacher_user):
        return {"is_training_dataset": {"$ne": True}}
    uid = str(teacher_user.get("user_id") or "").strip()
    email = str(teacher_user.get("email") or "").strip().lower()
    tname = str(teacher_user.get("full_name") or "").strip().lower()
    assigned_codes = []
    try:
        for c in courses_col().find({}, {"_id": 0, "course_code": 1, "instructor": 1, "instructor_id": 1, "instructor_email": 1}):
            code = str(c.get("course_code") or "").strip().upper()
            if code and ((uid and str(c.get("instructor_id") or "").strip() == uid) or (email and str(c.get("instructor_email") or "").strip().lower() == email) or (tname and str(c.get("instructor") or "").strip().lower() == tname)):
                assigned_codes.append(code)
    except Exception:
        pass
    clauses = []
    if uid:
        clauses.append({"teacher_user_id": uid})
    if email:
        clauses.append({"teacher_email": {"$regex": f"^{re.escape(email)}$", "$options": "i"}})
    if assigned_codes:
        clauses.append({"course_code": {"$in": assigned_codes}})
    return {"is_training_dataset": {"$ne": True}, "$or": clauses} if clauses else {"student_id": "__NO_TEACHER_MATCH__"}


def _student_default_password(sid, full_name, bdate="", batch=""):
    first = (full_name.split()[0].lower() if full_name.split() else sid.lower()) or "student"
    clean_bdate = str(bdate or "").strip()
    if clean_bdate: return first, f"{first}@{clean_bdate}"
    trailing = sid.split("-")[-1].strip().lower() if "-" in sid else ""
    return first, f"{first}@{trailing or str(batch or '').strip().lower() or '2026'}"


def get_teacher_credentials_export_rows(teacher_user_id, teacher_email, role="TEACHER", full_name=""):
    scope = {"user_id": teacher_user_id, "email": teacher_email, "role": role, "full_name": full_name}
    rows = []
    for rec in student_records_col().find(_teacher_student_query(scope), {"_id": 0, "student_id": 1, "full_name": 1, "course_code": 1, "birth_date": 1, "batch": 1}).sort("student_id", 1):
        sid = str(rec.get("student_id") or "").strip()
        if not sid: continue
        name, bdate = str(rec.get("full_name") or sid).strip(), str(rec.get("birth_date") or "").strip()
        _, default_pw = _student_default_password(sid, name, bdate, rec.get("batch") or "")
        rows.append({"student_id": sid, "full_name": name, "course_code": str(rec.get("course_code") or "").strip().upper(), "birth_date": bdate, "login_username": sid, "default_password": default_pw})
    return rows


def classify_performance_badge(att, marks, risk_level):
    att_val, marks_val, risk = _safe_float(att), _safe_float(marks), str(risk_level or "").strip().upper()
    if risk == "HIGH" or att_val < 60.0:
        return {"text": "High Risk", "status": "danger"}
    if risk == "MEDIUM" or att_val < 75.0 or marks_val < 60.0:
        return {"text": "Needs Help", "status": "warning"}
    if att_val >= 85.0 and marks_val >= 80.0:
        return {"text": "Excellent", "status": "success"}
    return {"text": "Stable", "status": "info"}


def _load_joined_students(teacher_user=None):
    pred_map = {str(p.get("student_id") or "").strip(): p for p in predictions_col().find({}, {"_id": 0}) if p.get("student_id")}
    joined = []
    for rec in student_records_col().find(_teacher_student_query(teacher_user), {"_id": 0}).sort("student_id", 1):
        sid = str(rec.get("student_id") or "").strip()
        if not sid:
            continue
        pred = pred_map.get(sid) or {}
        att, marks = round(_safe_float(rec.get("attendance_pct")), 1), round(_safe_float(rec.get("internal_marks")), 1)
        raw_gpa = pred.get("predicted_gpa")
        risk = str(pred.get("risk_level") or "LOW").strip().upper()
        joined.append({
            "student_id": sid, "full_name": str(rec.get("full_name") or sid), "birth_date": str(rec.get("birth_date") or "").strip(),
            "batch": str(rec.get("batch") or "2026-A"), "course_code": str(rec.get("course_code") or "CS-101").upper(),
            "attendance_pct": att, "internal_marks": marks, "assignment_score": round(_safe_float(rec.get("assignment_score")), 1),
            "lms_hours_weekly": round(_safe_float(rec.get("lms_hours_weekly")), 1), "previous_gpa": round(_safe_float(rec.get("previous_gpa")), 2),
            "predicted_gpa": round(_safe_float(raw_gpa), 2) if raw_gpa is not None else None, "risk_level": risk,
            "badge": classify_performance_badge(att, marks, risk),
        })
    return joined


def _student_attrs(s):
    return {"data-student-id": s["student_id"], "data-full-name": s["full_name"], "data-birth-date": s.get("birth_date") or "", "data-batch": s["batch"], "data-course-code": s["course_code"], "data-attendance-pct": f"{s['attendance_pct']:.1f}", "data-internal-marks": f"{s['internal_marks']:.1f}", "data-assignment-score": f"{s['assignment_score']:.1f}", "data-lms-hours-weekly": f"{s['lms_hours_weekly']:.1f}", "data-previous-gpa": f"{s['previous_gpa']:.2f}"}


def _alert_attrs(s):
    return {"data-student-id": s["student_id"], "data-full-name": s["full_name"], "data-course-code": s["course_code"]}


def _delete_attrs(s):
    return {"data-student-id": s["student_id"], "data-full-name": s["full_name"]}


def provision_student_accounts(rows, teacher_user=None):
    t_uid = str((teacher_user or {}).get("user_id") or "").strip()
    t_name = str((teacher_user or {}).get("full_name") or "Teacher").strip() or "Teacher"
    now, col, creds = datetime.now(timezone.utc), users_col(), []
    for row in rows or []:
        sid, full_name, bdate = str(row.get("student_id") or "").strip(), str(row.get("full_name") or "").strip(), str(row.get("birth_date") or "").strip()
        if not (sid and full_name):
            continue
        batch_val = str(row.get("batch") or "2026-A").strip() or "2026-A"
        first_name_lower, raw_pw = _student_default_password(sid, full_name, bdate, batch_val)
        default_email = f"{re.sub(r'[^a-z0-9._-]', '', sid.lower())}@student.edupredict.edu"
        existing = col.find_one({"student_id": sid}, {"_id": 0, "email": 1, "user_id": 1}) or col.find_one({"email": default_email}, {"_id": 0, "email": 1, "user_id": 1}) or {}
        email, user_id = str(existing.get("email") or default_email).strip().lower(), str(existing.get("user_id") or f"USR-{sid}").strip()
        doc = {"student_id": sid, "user_id": user_id, "username": first_name_lower, "full_name": full_name, "birth_date": bdate, "email": email, "password_hash": make_password(raw_pw), "role": "STUDENT", "is_active": True, "approval_status": "APPROVED", "batch": batch_val, "updated_at": now}
        if t_uid:
            doc["assigned_teacher_id"] = t_uid
            doc["assigned_teacher_name"] = t_name
        col.update_one({"student_id": sid}, {"$set": doc, "$setOnInsert": {"department": "General", "created_at": now}}, upsert=True)
        creds.append({"student_id": sid, "full_name": full_name, "birth_date": bdate, "course_code": str(row.get("course_code") or "").strip().upper(), "email": email, "password": raw_pw})
    return creds


def _load_teacher_dashboard_context(teacher_user=None):
    students = _load_joined_students(teacher_user)
    total = len(students)
    badge_counts = {"Excellent": 0, "Stable": 0, "Needs Help": 0, "High Risk": 0}
    course_stats, at_risk_list = {}, []
    for s in students:
        label = s["badge"]["text"]
        badge_counts[label] = badge_counts.get(label, 0) + 1
        bucket = course_stats.setdefault(s["course_code"], {"att": 0.0, "marks": 0.0, "count": 0})
        bucket["att"] += s["attendance_pct"]
        bucket["marks"] += s["internal_marks"]
        bucket["count"] += 1
        if label in ("High Risk", "Needs Help"):
            at_risk_list.append(s)
    course_labels = sorted(course_stats.keys())
    at_risk_list.sort(key=lambda x: (0 if x["badge"]["text"] == "High Risk" else 1, x["attendance_pct"]))
    at_risk_rows = [[s["student_id"], s["full_name"], s["course_code"], f"{s['attendance_pct']:.1f}%", f"{s['internal_marks']:.1f}", s["badge"], {"actions": [_action("Update Marks", "fa-solid fa-pen-to-square", "openUpdateMarksModal(this)", f"Edit marks for {s['full_name']}", _student_attrs(s)), _action("Send Alert", "fa-solid fa-bell", "openSendAlertModal(this)", f"Send alert to {s['full_name']}", _alert_attrs(s), variant="primary")]}] for s in at_risk_list]
    courses_count = len(course_labels) if not _is_admin(teacher_user) else (courses_col().count_documents({"status": "ACTIVE"}) or len(course_labels))
    return {
        "kpis": {"total_students": total, "avg_attendance": round(sum(s["attendance_pct"] for s in students) / total, 1) if total else 0.0, "avg_marks": round(sum(s["internal_marks"] for s in students) / total, 1) if total else 0.0, "at_risk_count": len(at_risk_list), "courses_count": courses_count},
        "chart_data": {"course_summary": {"labels": course_labels, "attendance": [round(course_stats[c]["att"] / course_stats[c]["count"], 1) for c in course_labels], "marks": [round(course_stats[c]["marks"] / course_stats[c]["count"], 1) for c in course_labels]}, "badge_breakdown": {"labels": ["Excellent", "Stable", "Needs Help", "High Risk"], "counts": [badge_counts[k] for k in ("Excellent", "Stable", "Needs Help", "High Risk")]}},
        "at_risk_headers": ["Student ID", "Name", "Course", "Attendance", "Marks", "Status", "Actions"], "at_risk_rows": at_risk_rows,
    }


def get_teacher_dashboard_context(teacher_user=None):
    return get_cached(f"teacher:dashboard:{_scope_key(teacher_user)}", lambda: _load_teacher_dashboard_context(teacher_user), ttl=30.0)


def _load_teacher_students_context(batch_f, course_f, status_f, teacher_user=None):
    students = _load_joined_students(teacher_user)
    filtered = [s for s in students if (batch_f == "ALL" or s["batch"] == batch_f) and (course_f == "ALL" or s["course_code"] == course_f) and (status_f == "ALL" or s["badge"]["text"].upper() == status_f.upper())]
    rows, export_rows = [], []
    for s in filtered:
        gpa_str = f"{s['predicted_gpa']:.2f}" if s["predicted_gpa"] is not None else f"{s['previous_gpa']:.2f}"
        view_payload = {"title": s["full_name"], "subtitle": f"{s['student_id']} · {s['course_code']}", "badge": s["badge"]["text"], "items": [{"label": "Student ID", "value": s["student_id"]}, {"label": "Birth Date", "value": s.get("birth_date") or "-"}, {"label": "Course", "value": s["course_code"]}, {"label": "Marks", "value": f"{s['internal_marks']:.1f}"}, {"label": "Attendance", "value": f"{s['attendance_pct']:.1f}%"}, {"label": "Predicted GPA", "value": gpa_str}, {"label": "Risk", "value": s["badge"]["text"], "fullWidth": True}]}
        actions = [_view_action(f"View {s['full_name']}", view_payload), _action("Edit", "fa-solid fa-pen-to-square", "openUpdateMarksModal(this)", f"Edit marks for {s['full_name']}", _student_attrs(s)), _action("Alert", "fa-solid fa-bell", "openSendAlertModal(this)", f"Send alert to {s['full_name']}", _alert_attrs(s), variant="primary"), _action("Delete", "fa-solid fa-trash", "openDeleteStudentModal(this)", f"Delete {s['full_name']}", _delete_attrs(s), variant="danger")]
        rows.append([s["full_name"], f"{s['internal_marks']:.1f} / {s['attendance_pct']:.1f}%", s["badge"], {"actions": actions}])
        export_rows.append({"student_id": s["student_id"], "full_name": s["full_name"], "batch": s["batch"], "course_code": s["course_code"], "attendance_pct": f"{s['attendance_pct']:.1f}", "internal_marks": f"{s['internal_marks']:.1f}", "predicted_gpa": gpa_str, "status": s["badge"]["text"]})
    return {"filter_options": {"batches": sorted({s["batch"] for s in students if s["batch"]}), "courses": sorted({s["course_code"] for s in students if s["course_code"]}), "statuses": ["Excellent", "Stable", "Needs Help", "High Risk"]}, "student_headers": ["Student", "Marks & Att", "Risk", "Actions"], "student_rows": rows, "students_raw": filtered, "export_rows": export_rows, "birth_map": {s["student_id"]: s["birth_date"] for s in filtered if s.get("birth_date")}}


def get_teacher_students_context(batch_filter="ALL", course_filter="ALL", status_filter="ALL", teacher_user=None):
    b, c, s = str(batch_filter or "ALL").strip() or "ALL", str(course_filter or "ALL").strip() or "ALL", str(status_filter or "ALL").strip() or "ALL"
    return get_cached(f"teacher:students:{_scope_key(teacher_user)}:{b}:{c}:{s}", lambda: _load_teacher_students_context(b, c, s, teacher_user), ttl=30.0)


def _load_teacher_ingest_context(teacher_user=None):
    students = _load_joined_students(teacher_user)
    roster_rows = [[s["student_id"], s["full_name"], s["batch"], s["course_code"], f"{s['attendance_pct']:.1f}%", f"{s['internal_marks']:.1f}", f"{s['previous_gpa']:.2f}", {"actions": [_action("Update Marks", "fa-solid fa-pen-to-square", "openUpdateMarksModal(this)", f"Edit marks for {s['full_name']}", _student_attrs(s)), _action("Delete", "fa-solid fa-trash", "openDeleteStudentModal(this)", f"Delete {s['full_name']}", _delete_attrs(s), variant="danger")]}] for s in students]
    log_query = {}
    if not _is_admin(teacher_user):
        uid, name = str(teacher_user.get("user_id") or "").strip(), str(teacher_user.get("full_name") or "").strip()
        clauses = [c for c in ({"teacher_user_id": uid} if uid else None, {"uploaded_by": name} if name else None) if c]
        log_query = {"$or": clauses} if clauses else {"teacher_user_id": "__NONE__"}
    log_rows = [[str(l.get("filename") or "dataset.csv"), int(l.get("rows_processed") or 0), int(l.get("missing_values_fixed") or 0), {"text": str(l.get("status") or "COMPLETED").upper(), "status": "success" if str(l.get("status") or "COMPLETED").upper() == "COMPLETED" else "danger"}, l["uploaded_at"].strftime("%Y-%m-%d %H:%M") if hasattr(l.get("uploaded_at"), "strftime") else "-"] for l in datasets_log_col().find(log_query, {"_id": 0}).sort("uploaded_at", DESCENDING).limit(10)]
    course_codes = {str(c.get("course_code") or "").strip().upper() for c in courses_col().find({}, {"_id": 0, "course_code": 1}) if c.get("course_code")} | {s["course_code"] for s in students if s["course_code"]}
    return {
        "roster_headers": ["Student ID", "Name", "Batch", "Course", "Attendance", "Marks", "GPA", "Actions"], "roster_rows": roster_rows, "roster_raw": students,
        "log_headers": ["File Name", "Rows", "Fixed", "Status", "Uploaded"], "log_rows": log_rows, "courses_list": sorted(course_codes) or ["CS-101"],
        "students_picker": [{"student_id": s["student_id"], "full_name": s["full_name"], "birth_date": s["birth_date"], "course_code": s["course_code"], "internal_marks": s["internal_marks"], "attendance_pct": s["attendance_pct"]} for s in students],
        "birth_map": {s["student_id"]: s["birth_date"] for s in students if s.get("birth_date")}, "required_columns": REQUIRED_COLUMNS,
    }


def get_teacher_ingest_context(teacher_user=None):
    return get_cached(f"teacher:ingest:{_scope_key(teacher_user)}", lambda: _load_teacher_ingest_context(teacher_user), ttl=30.0)


def update_student_record_inline(post_data, teacher_user=None):
    raw_sid = str(post_data.get("student_id") or "").strip()
    if len(raw_sid) < 2:
        return None, "Student ID is required."
    existing = student_records_col().find_one({"student_id": raw_sid}, {"_id": 0}) or student_records_col().find_one({"student_id": raw_sid.upper()}, {"_id": 0}) or {}
    sid = str(existing.get("student_id") or raw_sid).strip()
    full_name = str(post_data.get("full_name") or post_data.get("name") or existing.get("full_name") or f"Student {sid}").strip()
    bdate = str(post_data.get("birth_date") or existing.get("birth_date") or "").strip()
    batch = str(post_data.get("batch") or existing.get("batch") or "2026-A").strip()
    course_code = str(post_data.get("course_code") or existing.get("course_code") or "CS-101").strip().upper()
    try:
        raw_att = post_data.get("attendance_pct") if post_data.get("attendance_pct") not in (None, "") else (post_data.get("attendance") or post_data.get("att") or existing.get("attendance_pct") or 80.0)
        raw_marks = post_data.get("internal_marks") if post_data.get("internal_marks") not in (None, "") else (post_data.get("marks") or post_data.get("score") or existing.get("internal_marks") or 70.0)
        att, marks = max(0.0, min(100.0, float(raw_att))), max(0.0, min(100.0, float(raw_marks)))
        assign = max(0.0, min(100.0, float(post_data.get("assignment_score") or existing.get("assignment_score") or marks)))
        lms = max(0.0, min(168.0, float(post_data.get("lms_hours_weekly") or existing.get("lms_hours_weekly") or 8.0)))
        gpa = max(0.0, min(4.0, float(post_data.get("previous_gpa") or post_data.get("gpa") or existing.get("previous_gpa") or 3.0)))
    except (TypeError, ValueError):
        return None, "Please enter valid numeric values for marks and attendance."
    doc = {"student_id": sid, "full_name": full_name, "batch": batch, "course_code": course_code, "attendance_pct": round(att, 2), "attendance_rate": round(att, 2), "internal_marks": round(marks, 2), "marks": round(marks, 2), "final_score": round(marks, 2), "assignment_score": round(assign, 2), "lms_hours_weekly": round(lms, 2), "previous_gpa": round(gpa, 2), "gpa": round(gpa, 2), "updated_at": datetime.now(timezone.utc)}
    if bdate:
        doc["birth_date"] = bdate
    if isinstance(teacher_user, dict) and str(teacher_user.get("role") or "").upper() != "ADMIN":
        doc["teacher_user_id"] = str(teacher_user.get("user_id") or "").strip()
        doc["teacher_name"] = str(teacher_user.get("full_name") or "Teacher").strip()
        doc["teacher_email"] = str(teacher_user.get("email") or "").strip().lower()
    student_records_col().update_one({"student_id": sid}, {"$set": doc}, upsert=True)
    if full_name:
        provision_student_accounts([doc], teacher_user)
    run_prediction_pipeline()
    invalidate_cache()
    return doc, None


def send_student_alert(student_id, full_name, course_code, severity, message_text, sender_name):
    sid, clean_msg = str(student_id or "").strip(), str(message_text or "").strip()
    if not sid or not clean_msg:
        return None, "Student ID and alert message are required."
    raw_sev = str(severity or "WARNING").strip().upper()
    norm_sev = {"HIGH": "DANGER", "DANGER": "DANGER", "MEDIUM": "WARNING", "WARNING": "WARNING", "LOW": "INFO", "INFO": "INFO"}.get(raw_sev, "WARNING")
    course_lbl, sender_lbl = str(course_code or "Class").strip().upper() or "Class", str(sender_name or "Teacher").strip() or "Teacher"
    doc = {"target_role": "STUDENT", "target_user_id": sid, "student_id": sid, "title": f"Teacher Alert ({course_lbl})", "message": f"{clean_msg} - {sender_lbl}", "sender_name": sender_lbl, "severity": norm_sev, "urgency": raw_sev, "is_read": False, "created_at": datetime.now(timezone.utc)}
    notifications_col().insert_one(doc)
    invalidate_cache()
    return doc, None


def delete_student_record(student_id):
    sid = str(student_id or "").strip()
    if not sid:
        return False, "Student ID is required."
    deleted = student_records_col().delete_one({"student_id": sid}).deleted_count or student_records_col().delete_one({"student_id": sid.upper()}).deleted_count
    predictions_col().delete_many({"student_id": {"$in": [sid, sid.upper()]}})
    invalidate_cache()
    return (True, None) if deleted else (False, "Student record not found.")


def _load_teacher_feedback_inbox(teacher_user=None):
    query = {"target_role": "TEACHER"}
    if not _is_admin(teacher_user):
        uid, tname = str(teacher_user.get("user_id") or "").strip(), str(teacher_user.get("full_name") or "").strip()
        clauses = [c for c in ({"target_teacher_id": uid} if uid else None, {"target_teacher_name": {"$regex": f"^{re.escape(tname)}$", "$options": "i"}} if tname else None) if c]
        query = {"target_role": "TEACHER", "$or": clauses} if clauses else {"target_role": "TEACHER", "target_teacher_id": "__NONE__"}
    rows, open_count = [], 0
    for t in support_tickets_col().find(query).sort("created_at", DESCENDING).limit(40):
        tid, st = str(t.get("ticket_id") or "").strip(), str(t.get("status") or "OPEN").strip().upper()
        open_count += int(st != "RESOLVED")
        student_name, subj, msg = str(t.get("user_name") or t.get("student_name") or t.get("user_id") or "Student").strip(), str(t.get("subject") or "Student Feedback").strip(), str(t.get("message") or "").strip()
        reply, created = str(t.get("teacher_reply") or t.get("admin_reply") or "").strip(), t.get("created_at")
        badge = {"text": "Resolved" if st == "RESOLVED" else "Open", "status": "success" if st == "RESOLVED" else "warning"}
        attrs = {"data-ticket-id": tid, "data-student-name": student_name, "data-subject": subj, "data-message": msg, "data-reply": reply}
        rows.append([tid or "-", student_name, subj, f"{msg} | Reply: {reply}" if reply else msg, badge, created.strftime("%b %d, %H:%M") if hasattr(created, "strftime") else "-", {"actions": [_action("Reply / Resolve" if st != "RESOLVED" else "Update Reply", "fa-solid fa-reply", "openReplyFeedbackModal(this)", f"Reply to {student_name}", attrs, variant="primary" if st != "RESOLVED" else "default")]}])
    return rows, open_count


def _load_teacher_alerts_scoped(teacher_user=None):
    students = _load_joined_students(teacher_user)
    at_risk = sorted([s for s in students if s["badge"]["text"] in ("High Risk", "Needs Help")], key=lambda x: (0 if x["badge"]["text"] == "High Risk" else 1, x["attendance_pct"]))
    roster_rows = [[s["student_id"], s["full_name"], s["course_code"], f"{s['attendance_pct']:.1f}%", f"{s['internal_marks']:.1f}", s["badge"], {"actions": [_action("Send Alert", "fa-solid fa-bell", "openSendAlertModal(this)", f"Send alert to {s['full_name']}", _alert_attrs(s), variant="primary")]}] for s in at_risk]
    q = {"target_role": "STUDENT", "title": {"$regex": "^Teacher Alert"}}
    if not _is_admin(teacher_user):
        uid, tname = str(teacher_user.get("user_id") or "").strip(), str(teacher_user.get("full_name") or "").strip()
        clauses = [c for c in ({"sender_user_id": uid} if uid else None, {"sender_name": {"$regex": f"^{re.escape(tname)}$", "$options": "i"}} if tname else None) if c]
        if clauses:
            q["$or"] = clauses
    history = list(notifications_col().find(q, {"_id": 0}).sort("created_at", DESCENDING).limit(30))
    history_rows = [[str(a.get("title") or "Teacher Alert"), str(a.get("student_id") or a.get("target_user_id") or "-"), str(a.get("message") or ""), {"text": str(a.get("severity") or "INFO").upper(), "status": {"DANGER": "danger", "WARNING": "warning"}.get(str(a.get("severity") or "").upper(), "info")}, {"text": "Read" if a.get("is_read") else "Unread", "status": "success" if a.get("is_read") else "warning"}, a["created_at"].strftime("%b %d, %H:%M") if hasattr(a.get("created_at"), "strftime") else "-"] for a in history]
    feedback_rows, open_fb = _load_teacher_feedback_inbox(teacher_user)
    return {
        "kpis": {"at_risk_count": len(at_risk), "high_risk_count": sum(1 for s in students if s["risk_level"] == "HIGH"), "medium_risk_count": sum(1 for s in students if s["risk_level"] == "MEDIUM"), "alerts_sent": len(history), "unread_alerts": sum(1 for a in history if not a.get("is_read")), "open_feedback_count": open_fb},
        "roster_headers": ["Student ID", "Name", "Course", "Attendance", "Marks", "Status", "Actions"], "roster_rows": roster_rows,
        "history_headers": ["Title", "Student", "Message", "Level", "Read", "Date"], "history_rows": history_rows,
        "feedback_headers": ["Ticket", "Student", "Subject", "Message", "Status", "Date", "Actions"], "feedback_rows": feedback_rows,
        "students_picker": [{"student_id": s["student_id"], "full_name": s["full_name"], "course_code": s["course_code"]} for s in students],
        "auto_alerts_enabled": bool(_resolve_runtime_settings(persist=True).get("auto_student_alerts", True)),
        "high_risk_only_count": sum(1 for s in students if s["risk_level"] == "HIGH" or s["badge"]["text"] == "High Risk"),
    }


def get_teacher_alerts_context(teacher_user=None):
    return get_cached(f"teacher:alerts:{_scope_key(teacher_user)}", lambda: _load_teacher_alerts_scoped(teacher_user), ttl=30.0)


def notify_all_high_risk_students(sender_name="Teacher", sender_user_id="", teacher_user=None):
    students = _load_joined_students(teacher_user)
    targets = [s for s in students if s["risk_level"] == "HIGH" or s["badge"]["text"] in ("High Risk", "Needs Help") or s["attendance_pct"] < 75.0]
    if not targets:
        return 0, "No high-risk or low-attendance students found in your class."
    now, sender_lbl, sender_uid, col = datetime.now(timezone.utc), str(sender_name or "Teacher").strip() or "Teacher", str(sender_user_id or "").strip(), notifications_col()
    for s in targets:
        course = str(s.get("course_code") or "Class").strip().upper() or "Class"
        doc = {"target_role": "STUDENT", "target_user_id": s["student_id"], "student_id": s["student_id"], "title": f"Teacher Alert ({course})", "message": f"Academic follow-up required in {course}: attendance {s['attendance_pct']:.1f}%, marks {s['internal_marks']:.1f}. - {sender_lbl}", "sender_name": sender_lbl, "severity": "DANGER" if (s["risk_level"] == "HIGH" or s["badge"]["text"] == "High Risk") else "WARNING", "is_read": False, "created_at": now}
        if sender_uid:
            doc["sender_user_id"] = sender_uid
        col.insert_one(doc)
    invalidate_cache()
    return len(targets), None


def reply_teacher_feedback(ticket_id, reply_text, teacher_user=None, resolve_ticket=True):
    clean_tid, clean_reply = str(ticket_id or "").strip(), str(reply_text or "").strip()
    if not clean_tid or not clean_reply:
        return False, "Ticket ID and reply message are required."
    col = support_tickets_col()
    ticket = col.find_one({"ticket_id": clean_tid, "target_role": "TEACHER"})
    if ticket is None:
        return False, "Student feedback ticket not found."
    if not _is_admin(teacher_user):
        uid, tname = str(teacher_user.get("user_id") or "").strip(), str(teacher_user.get("full_name") or "").strip().lower()
        t_tid, t_tname = str(ticket.get("target_teacher_id") or "").strip(), str(ticket.get("target_teacher_name") or "").strip().lower()
        if (uid and t_tid and uid != t_tid) and (not tname or tname != t_tname):
            return False, "You can only reply to feedback addressed to you."
    actor, now = str((teacher_user or {}).get("full_name") or "Teacher").strip() or "Teacher", datetime.now(timezone.utc)
    updates = {"admin_reply": clean_reply, "teacher_reply": clean_reply, "replied_by": actor, "replied_at": now, "updated_at": now}
    if resolve_ticket:
        updates["status"] = "RESOLVED"
    col.update_one({"_id": ticket["_id"]}, {"$set": updates})
    notifications_col().insert_one({"title": f"Teacher Reply on {clean_tid}: {str(ticket.get('subject') or 'Feedback').strip()}", "message": clean_reply, "severity": "SUCCESS", "category": "FEEDBACK_REPLY", "target_role": "STUDENT", "target_user_id": str(ticket.get("user_id") or ticket.get("student_id") or "").strip(), "ticket_id": clean_tid, "feedback_text": str(ticket.get("message") or "").strip(), "reply_text": clean_reply, "sender_name": actor, "is_read": False, "created_at": now})
    invalidate_cache()
    return True, None
