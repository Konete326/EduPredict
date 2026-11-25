from datetime import datetime, timezone
from pymongo import DESCENDING, UpdateOne
from analytics.data_pipeline import REQUIRED_COLUMNS
from analytics.ml_engine import run_prediction_pipeline
from core.db import (
    courses_col,
    datasets_log_col,
    get_cached,
    invalidate_cache,
    notifications_col,
    predictions_col,
    student_records_col,
)


def _safe_float(val, default=0.0):
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _action(label, icon, onclick, title, attrs, variant="default"):
    return {"label": label, "icon": icon, "variant": variant, "title": title, "onclick": onclick, "attrs": attrs}


def classify_performance_badge(att, marks, risk_level):
    att_val = _safe_float(att, 0.0)
    marks_val = _safe_float(marks, 0.0)
    risk = str(risk_level or "").strip().upper()
    if risk == "HIGH" or att_val < 60.0:
        return {"text": "High Risk", "status": "danger"}
    if risk == "MEDIUM" or att_val < 75.0 or marks_val < 60.0:
        return {"text": "Needs Help", "status": "warning"}
    if att_val >= 85.0 and marks_val >= 80.0:
        return {"text": "Excellent", "status": "success"}
    return {"text": "Stable", "status": "info"}


def _load_joined_students():
    pred_map = {}
    for pred in predictions_col().find({}, {"_id": 0}):
        sid = str(pred.get("student_id") or "").strip()
        if sid:
            pred_map[sid] = pred

    joined = []
    for rec in student_records_col().find({}, {"_id": 0}).sort("student_id", 1):
        sid = str(rec.get("student_id") or "").strip()
        if not sid:
            continue
        pred = pred_map.get(sid) or {}
        att = round(_safe_float(rec.get("attendance_pct"), 0.0), 1)
        marks = round(_safe_float(rec.get("internal_marks"), 0.0), 1)
        assign = round(_safe_float(rec.get("assignment_score"), 0.0), 1)
        lms = round(_safe_float(rec.get("lms_hours_weekly"), 0.0), 1)
        prev_gpa = round(_safe_float(rec.get("previous_gpa"), 0.0), 2)
        raw_pred_gpa = pred.get("predicted_gpa")
        pred_gpa = round(_safe_float(raw_pred_gpa), 2) if raw_pred_gpa is not None else None
        risk_level = str(pred.get("risk_level") or "LOW").strip().upper()
        badge = classify_performance_badge(att, marks, risk_level)
        joined.append({
            "student_id": sid,
            "full_name": str(rec.get("full_name") or sid),
            "batch": str(rec.get("batch") or "2026-A"),
            "course_code": str(rec.get("course_code") or "CS-101").upper(),
            "attendance_pct": att,
            "internal_marks": marks,
            "assignment_score": assign,
            "lms_hours_weekly": lms,
            "previous_gpa": prev_gpa,
            "predicted_gpa": pred_gpa,
            "risk_level": risk_level,
            "badge": badge,
        })
    return joined


def _student_attrs(s):
    return {
        "data-student-id": s["student_id"],
        "data-full-name": s["full_name"],
        "data-batch": s["batch"],
        "data-course-code": s["course_code"],
        "data-attendance-pct": f"{s['attendance_pct']:.1f}",
        "data-internal-marks": f"{s['internal_marks']:.1f}",
        "data-assignment-score": f"{s['assignment_score']:.1f}",
        "data-lms-hours-weekly": f"{s['lms_hours_weekly']:.1f}",
        "data-previous-gpa": f"{s['previous_gpa']:.2f}",
    }


def _alert_attrs(s):
    return {
        "data-student-id": s["student_id"],
        "data-full-name": s["full_name"],
        "data-course-code": s["course_code"],
    }


def _delete_attrs(s):
    return {"data-student-id": s["student_id"], "data-full-name": s["full_name"]}


def _load_teacher_dashboard_context():
    students = _load_joined_students()
    total = len(students)
    avg_att = round(sum(s["attendance_pct"] for s in students) / total, 1) if total else 0.0
    avg_marks = round(sum(s["internal_marks"] for s in students) / total, 1) if total else 0.0

    badge_counts = {"Excellent": 0, "Stable": 0, "Needs Help": 0, "High Risk": 0}
    course_stats = {}
    at_risk_list = []

    for s in students:
        label = s["badge"]["text"]
        badge_counts[label] = badge_counts.get(label, 0) + 1
        code = s["course_code"]
        bucket = course_stats.setdefault(code, {"att": 0.0, "marks": 0.0, "count": 0})
        bucket["att"] += s["attendance_pct"]
        bucket["marks"] += s["internal_marks"]
        bucket["count"] += 1
        if label in ("High Risk", "Needs Help"):
            at_risk_list.append(s)

    course_labels = sorted(course_stats.keys())
    course_att = [round(course_stats[c]["att"] / course_stats[c]["count"], 1) for c in course_labels]
    course_marks = [round(course_stats[c]["marks"] / course_stats[c]["count"], 1) for c in course_labels]

    at_risk_list.sort(key=lambda x: (0 if x["badge"]["text"] == "High Risk" else 1, x["attendance_pct"]))
    at_risk_headers = ["Student ID", "Name", "Course", "Attendance", "Marks", "Status", "Actions"]
    at_risk_rows = []
    for s in at_risk_list:
        actions = [
            _action("Update Marks", "fa-solid fa-pen-to-square", "openUpdateMarksModal(this)", f"Edit marks for {s['full_name']}", _student_attrs(s)),
            _action("Send Alert", "fa-solid fa-bell", "openSendAlertModal(this)", f"Send alert to {s['full_name']}", _alert_attrs(s), variant="primary"),
        ]
        at_risk_rows.append([
            s["student_id"], s["full_name"], s["course_code"],
            f"{s['attendance_pct']:.1f}%", f"{s['internal_marks']:.1f}", s["badge"], {"actions": actions},
        ])

    courses_count = courses_col().count_documents({"status": "ACTIVE"})
    if courses_count == 0:
        courses_count = len(course_labels)

    return {
        "kpis": {
            "total_students": total,
            "avg_attendance": avg_att,
            "avg_marks": avg_marks,
            "at_risk_count": len(at_risk_list),
            "courses_count": courses_count,
        },
        "chart_data": {
            "course_summary": {"labels": course_labels, "attendance": course_att, "marks": course_marks},
            "badge_breakdown": {
                "labels": ["Excellent", "Stable", "Needs Help", "High Risk"],
                "counts": [badge_counts["Excellent"], badge_counts["Stable"], badge_counts["Needs Help"], badge_counts["High Risk"]],
            },
        },
        "at_risk_headers": at_risk_headers,
        "at_risk_rows": at_risk_rows,
    }


def get_teacher_dashboard_context():
    return get_cached("teacher:dashboard", _load_teacher_dashboard_context, ttl=30.0)


def _load_teacher_students_context(batch_f, course_f, status_f):
    students = _load_joined_students()
    batches = sorted({s["batch"] for s in students if s["batch"]})
    courses = sorted({s["course_code"] for s in students if s["course_code"]})
    statuses = ["Excellent", "Stable", "Needs Help", "High Risk"]

    filtered = []
    for s in students:
        if batch_f != "ALL" and s["batch"] != batch_f:
            continue
        if course_f != "ALL" and s["course_code"] != course_f:
            continue
        if status_f != "ALL" and s["badge"]["text"].upper() != status_f.upper():
            continue
        filtered.append(s)

    headers = ["Student ID", "Name", "Batch", "Course", "Attendance", "Marks", "Pred GPA", "Status", "Actions"]
    rows, export_rows = [], []
    for s in filtered:
        actions = [
            _action("Update Marks", "fa-solid fa-pen-to-square", "openUpdateMarksModal(this)", f"Edit marks for {s['full_name']}", _student_attrs(s)),
            _action("Send Alert", "fa-solid fa-bell", "openSendAlertModal(this)", f"Send alert to {s['full_name']}", _alert_attrs(s), variant="primary"),
            _action("Delete", "fa-solid fa-trash", "openDeleteStudentModal(this)", f"Delete {s['full_name']}", _delete_attrs(s), variant="danger"),
        ]
        gpa_str = f"{s['predicted_gpa']:.2f}" if s["predicted_gpa"] is not None else f"{s['previous_gpa']:.2f}"
        rows.append([
            s["student_id"], s["full_name"], s["batch"], s["course_code"],
            f"{s['attendance_pct']:.1f}%", f"{s['internal_marks']:.1f}", gpa_str, s["badge"], {"actions": actions},
        ])
        export_rows.append({
            "student_id": s["student_id"], "full_name": s["full_name"], "batch": s["batch"],
            "course_code": s["course_code"], "attendance_pct": f"{s['attendance_pct']:.1f}",
            "internal_marks": f"{s['internal_marks']:.1f}", "predicted_gpa": gpa_str, "status": s["badge"]["text"],
        })

    return {
        "filter_options": {"batches": batches, "courses": courses, "statuses": statuses},
        "student_headers": headers,
        "student_rows": rows,
        "students_raw": filtered,
        "export_rows": export_rows,
    }


def get_teacher_students_context(batch_filter="ALL", course_filter="ALL", status_filter="ALL"):
    b = str(batch_filter or "ALL").strip() or "ALL"
    c = str(course_filter or "ALL").strip() or "ALL"
    s = str(status_filter or "ALL").strip() or "ALL"
    return get_cached(f"teacher:students:{b}:{c}:{s}", lambda: _load_teacher_students_context(b, c, s), ttl=30.0)


def _load_teacher_ingest_context():
    students = _load_joined_students()
    roster_headers = ["Student ID", "Name", "Batch", "Course", "Attendance", "Marks", "GPA", "Actions"]
    roster_rows = []
    for s in students:
        actions = [
            _action("Update Marks", "fa-solid fa-pen-to-square", "openUpdateMarksModal(this)", f"Edit marks for {s['full_name']}", _student_attrs(s)),
            _action("Delete", "fa-solid fa-trash", "openDeleteStudentModal(this)", f"Delete {s['full_name']}", _delete_attrs(s), variant="danger"),
        ]
        roster_rows.append([
            s["student_id"], s["full_name"], s["batch"], s["course_code"],
            f"{s['attendance_pct']:.1f}%", f"{s['internal_marks']:.1f}", f"{s['previous_gpa']:.2f}", {"actions": actions},
        ])

    log_headers = ["File Name", "Rows", "Fixed", "Status", "Uploaded"]
    log_rows = []
    for log in datasets_log_col().find({}, {"_id": 0}).sort("uploaded_at", DESCENDING).limit(10):
        st = str(log.get("status") or "COMPLETED").upper()
        dt = log.get("uploaded_at")
        log_rows.append([
            str(log.get("filename") or "dataset.csv"),
            int(log.get("rows_processed") or 0),
            int(log.get("missing_values_fixed") or 0),
            {"text": st, "status": "success" if st == "COMPLETED" else "danger"},
            dt.strftime("%Y-%m-%d %H:%M") if hasattr(dt, "strftime") else "-",
        ])

    course_codes = {str(c.get("course_code") or "").strip().upper() for c in courses_col().find({}, {"_id": 0, "course_code": 1}) if c.get("course_code")}
    course_codes.update(s["course_code"] for s in students if s["course_code"])
    students_picker = [{"student_id": s["student_id"], "full_name": s["full_name"], "course_code": s["course_code"]} for s in students]
    return {
        "roster_headers": roster_headers,
        "roster_rows": roster_rows,
        "roster_raw": students,
        "log_headers": log_headers,
        "log_rows": log_rows,
        "courses_list": sorted(course_codes) or ["CS-101"],
        "students_picker": students_picker,
        "required_columns": REQUIRED_COLUMNS,
    }


def get_teacher_ingest_context():
    return get_cached("teacher:ingest", _load_teacher_ingest_context, ttl=30.0)


def update_student_record_inline(post_data):
    sid = str(post_data.get("student_id") or "").strip().upper()
    if len(sid) < 2:
        return None, "Student ID is required."
    existing = student_records_col().find_one({"student_id": sid}, {"_id": 0}) or {}
    full_name = str(post_data.get("full_name") or post_data.get("name") or existing.get("full_name") or f"Student {sid}").strip()
    batch = str(post_data.get("batch") or existing.get("batch") or "2026-A").strip()
    course_code = str(post_data.get("course_code") or existing.get("course_code") or "CS-101").strip().upper()

    try:
        raw_att = post_data.get("attendance_pct") if post_data.get("attendance_pct") not in (None, "") else (post_data.get("attendance") or post_data.get("att") or post_data.get("attendance_rate") or existing.get("attendance_pct") or 80.0)
        raw_marks = post_data.get("internal_marks") if post_data.get("internal_marks") not in (None, "") else (post_data.get("marks") or post_data.get("score") or post_data.get("final_score") or existing.get("internal_marks") or 70.0)
        att = max(0.0, min(100.0, float(raw_att)))
        marks = max(0.0, min(100.0, float(raw_marks)))
        assign = max(0.0, min(100.0, float(post_data.get("assignment_score") or existing.get("assignment_score") or marks)))
        lms = max(0.0, min(168.0, float(post_data.get("lms_hours_weekly") or existing.get("lms_hours_weekly") or 8.0)))
        gpa = max(0.0, min(4.0, float(post_data.get("previous_gpa") or post_data.get("gpa") or existing.get("previous_gpa") or 3.0)))
    except (TypeError, ValueError):
        return None, "Please enter valid numeric values for marks and attendance."

    doc = {
        "student_id": sid, "full_name": full_name, "batch": batch, "course_code": course_code,
        "attendance_pct": round(att, 2), "attendance_rate": round(att, 2),
        "internal_marks": round(marks, 2), "marks": round(marks, 2), "final_score": round(marks, 2),
        "assignment_score": round(assign, 2), "lms_hours_weekly": round(lms, 2),
        "previous_gpa": round(gpa, 2), "gpa": round(gpa, 2), "updated_at": datetime.now(timezone.utc),
    }
    student_records_col().update_one({"student_id": sid}, {"$set": doc}, upsert=True)
    run_prediction_pipeline()
    invalidate_cache()
    return doc, None


def send_student_alert(student_id, full_name, course_code, severity, message_text, sender_name):
    sid = str(student_id or "").strip().upper()
    clean_msg = str(message_text or "").strip()
    if not sid or not clean_msg:
        return None, "Student ID and alert message are required."
    raw_sev = str(severity or "WARNING").strip().upper()
    sev_map = {"HIGH": "DANGER", "DANGER": "DANGER", "MEDIUM": "WARNING", "WARNING": "WARNING", "LOW": "INFO", "INFO": "INFO"}
    norm_sev = sev_map.get(raw_sev, "WARNING")
    course_lbl = str(course_code or "Class").strip().upper() or "Class"
    sender_lbl = str(sender_name or "Teacher").strip() or "Teacher"
    doc = {
        "target_role": "STUDENT",
        "target_user_id": sid,
        "student_id": sid,
        "title": f"Teacher Alert ({course_lbl})",
        "message": f"{clean_msg} - {sender_lbl}",
        "sender_name": sender_lbl,
        "severity": norm_sev,
        "urgency": raw_sev,
        "is_read": False,
        "created_at": datetime.now(timezone.utc),
    }
    notifications_col().insert_one(doc)
    invalidate_cache()
    return doc, None


def delete_student_record(student_id):
    sid = str(student_id or "").strip().upper()
    if not sid:
        return False, "Student ID is required."
    deleted = student_records_col().delete_one({"student_id": sid}).deleted_count
    predictions_col().delete_many({"student_id": sid})
    invalidate_cache()
    return (True, None) if deleted else (False, "Student record not found.")
