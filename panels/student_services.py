from pymongo import DESCENDING
from analytics.ml_engine import _resolve_runtime_settings
from core.db import (
    courses_col,
    get_cached,
    notifications_col,
    predictions_col,
    student_records_col,
)
from panels.student_alert_services import (
    _alert_targets,
    _load_recent_alerts,
    get_student_alerts_context,
    mark_alert_read,
)


def _safe_float(val, default=0.0):
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _empty_record(student_id):
    return {
        "student_id": student_id,
        "full_name": "",
        "batch": "",
        "records": [],
        "courses": [],
        "avg_attendance": 0.0,
        "avg_marks": 0.0,
        "avg_assignment": 0.0,
        "lms_hours_weekly": 0.0,
        "previous_gpa": 0.0,
        "predicted_gpa": None,
        "risk_level": "PENDING",
        "risk_score": None,
        "is_anomaly": False,
        "anomaly_reason": "",
        "recommendation": "",
        "generated_at": None,
    }


def _fetch_student_docs(student_id):
    records = list(student_records_col().find({"student_id": student_id}, {"_id": 0}).sort("updated_at", DESCENDING))
    prediction = predictions_col().find_one({"student_id": student_id}, {"_id": 0, "generated_at": -1})
    return records, prediction


def _fetch_batch_docs(batch, course_codes=None):
    clean_courses = [c for c in (course_codes or []) if c]
    query = {"batch": batch} if batch else ({"course_code": {"$in": clean_courses}} if clean_courses else {})
    return list(student_records_col().find(query, {"_id": 0, "student_id": 1, "course_code": 1, "attendance_pct": 1, "internal_marks": 1, "assignment_score": 1}))


def _course_class_stats(batch, docs=None):
    stats = {}
    iterable = docs if docs is not None else student_records_col().find({"batch": batch} if batch else {}, {"_id": 0, "course_code": 1, "attendance_pct": 1, "internal_marks": 1, "assignment_score": 1})
    for rec in iterable:
        code = str(rec.get("course_code") or "").strip().upper()
        if not code:
            continue
        bucket = stats.setdefault(code, {"att": 0.0, "marks": 0.0, "assign": 0.0, "count": 0})
        bucket["att"] += _safe_float(rec.get("attendance_pct"))
        bucket["marks"] += _safe_float(rec.get("internal_marks"))
        bucket["assign"] += _safe_float(rec.get("assignment_score"))
        bucket["count"] += 1
    class_stats = {}
    for code, bucket in stats.items():
        n = bucket["count"]
        class_stats[code] = {
            "attendance": round(bucket["att"] / n, 1),
            "marks": round(bucket["marks"] / n, 1),
            "assignment": round(bucket["assign"] / n, 1),
            "count": n,
        }
    return class_stats


def _batch_rank(student_id, batch, student_avg_marks, docs=None):
    if batch is None:
        return None
    iterable = docs if docs is not None else student_records_col().find({"batch": batch} if batch else {}, {"_id": 0, "student_id": 1, "internal_marks": 1})
    peer_totals = {}
    for rec in iterable:
        sid = str(rec.get("student_id") or "").strip()
        if not sid:
            continue
        bucket = peer_totals.setdefault(sid, [0.0, 0])
        bucket[0] += _safe_float(rec.get("internal_marks"))
        bucket[1] += 1
    if not peer_totals:
        return None
    my_score = _safe_float(student_avg_marks)
    better = sum(1 for sid, (s, c) in peer_totals.items() if sid != student_id and (s / max(c, 1)) > my_score)
    return {"rank": better + 1, "total": len(peer_totals)}


def _build_tips(record, prediction, class_avg_marks, class_avg_att, min_att=75.0):
    tips = []
    att = record["avg_attendance"]
    marks = record["avg_marks"]
    risk = record["risk_level"]
    lms = record["lms_hours_weekly"]
    class_att = class_avg_att or 0.0

    if att < float(min_att):
        weekly_lectures = 5
        target_att = min(100, int(round(float(min_att))) + 10)
        needed = max(0, int(round((float(target_att) - att) / max(weekly_lectures, 1) * 10)))
        tips.append({
            "icon": "fa-solid fa-calendar-check",
            "status": "danger" if att < 60.0 else "warning",
            "title": f"Raise your attendance above {target_att}%",
            "text": f"You are at {att:.1f}%. Attending the next {max(1, needed)} lectures will push you over {target_att}%.",
        })
    elif att >= min(100.0, max(90.0, float(min_att) + 10.0)):
        tips.append({
            "icon": "fa-solid fa-medal",
            "status": "success",
            "title": "Attendance is excellent",
            "text": f"You are at {att:.1f}%, well above the class average of {class_att:.1f}%. Keep it up!",
        })
    if marks < class_avg_marks - 3:
        tips.append({
            "icon": "fa-solid fa-book-open",
            "status": "warning",
            "title": "Marks are below class average",
            "text": f"Your average is {marks:.1f} vs class {class_avg_marks:.1f}. Revise this week's topics and ask your teacher for practice work.",
        })
    if lms < 5.0:
        tips.append({
            "icon": "fa-solid fa-clock",
            "status": "warning",
            "title": "Increase weekly study time",
            "text": f"You study about {lms:.1f} hours per week. Aim for 6-8 hours to see steady grade gains.",
        })
    if risk == "HIGH":
        tips.append({
            "icon": "fa-solid fa-hands-holding-circle",
            "status": "danger",
            "title": "Extra support recommended",
            "text": "Your current risk is High. Message your teacher from the Alerts page and set a weekly catch-up plan.",
        })
    if not tips:
        tips.append({
            "icon": "fa-solid fa-circle-check",
            "status": "success",
            "title": "You are on track",
            "text": "Attendance and marks look healthy. Keep your routine and stay ahead of deadlines.",
        })
    return tips


def _build_insight(record, rank):
    risk = record["risk_level"]
    att = record["avg_attendance"]
    gpa = record["predicted_gpa"]
    if risk == "PENDING":
        summary = "Your prediction is not ready yet. Once your teacher uploads marks, your personal insight will appear here."
        status = "info"
    elif risk == "HIGH":
        summary = "You are at high dropout risk right now. Focus on attendance first, then talk to your teacher about a catch-up plan."
        status = "danger"
    elif risk == "MEDIUM":
        summary = "You are doing okay but slipping in some areas. Small weekly improvements will move you back on track."
        status = "warning"
    else:
        summary = "Great work! Your attendance and marks predict a strong final result. Keep your current routine."
        status = "success"
    points = []
    if att:
        points.append(f"Attendance: {att:.1f}%")
    if gpa is not None:
        points.append(f"Predicted GPA: {gpa:.2f}")
    if rank:
        points.append(f"Class standing: #{rank['rank']} of {rank['total']}")
    if record["anomaly_reason"]:
        points.append(f"Flag: {record['anomaly_reason']}")
    if record["recommendation"]:
        points.append(f"Advice: {record['recommendation']}")
    return {"summary": summary, "status": status, "points": points}


def _load_student_overview(student_id, user_id, role):
    portal_settings = _resolve_runtime_settings(persist=True)
    min_att = float(portal_settings.get("min_attendance_pct", 75.0))
    excellent_att = min(100.0, max(85.0, min_att + 5.0))
    record = _empty_record(student_id)
    records, prediction = _fetch_student_docs(student_id)
    if records:
        primary = records[0]
        record["full_name"] = str(primary.get("full_name") or "")
        record["batch"] = str(primary.get("batch") or "")
        course_rows = []
        for rec in records:
            course_rows.append({
                "course_code": str(rec.get("course_code") or "").upper(),
                "attendance_pct": round(_safe_float(rec.get("attendance_pct")), 1),
                "internal_marks": round(_safe_float(rec.get("internal_marks")), 1),
                "assignment_score": round(_safe_float(rec.get("assignment_score")), 1),
                "lms_hours_weekly": round(_safe_float(rec.get("lms_hours_weekly")), 1),
            })
        record["courses"] = course_rows
        n = len(course_rows) or 1
        record["avg_attendance"] = round(sum(c["attendance_pct"] for c in course_rows) / n, 1)
        record["avg_marks"] = round(sum(c["internal_marks"] for c in course_rows) / n, 1)
        record["avg_assignment"] = round(sum(c["assignment_score"] for c in course_rows) / n, 1)
        record["lms_hours_weekly"] = course_rows[0]["lms_hours_weekly"]
        record["previous_gpa"] = round(_safe_float(primary.get("previous_gpa")), 2)

    if prediction:
        raw_gpa = prediction.get("predicted_gpa")
        record["predicted_gpa"] = round(_safe_float(raw_gpa), 2) if raw_gpa is not None else None
        record["risk_level"] = str(prediction.get("risk_level") or "PENDING").upper()
        record["risk_score"] = prediction.get("dropout_risk_score")
        record["is_anomaly"] = bool(prediction.get("is_anomaly"))
        record["anomaly_reason"] = str(prediction.get("anomaly_reason") or "")
        record["recommendation"] = str(prediction.get("recommendation") or "")
        gen = prediction.get("generated_at")
        record["generated_at"] = gen.strftime("%Y-%m-%d %H:%M") if hasattr(gen, "strftime") else None

    batch_docs = _fetch_batch_docs(record["batch"], course_codes=[x["course_code"] for x in record["courses"] if x.get("course_code")])
    class_stats = _course_class_stats(record["batch"], docs=batch_docs)
    subject_rows = []
    chart_labels, chart_mine, chart_class = [], [], []
    for course in record["courses"]:
        code = course["course_code"] or "GENERAL"
        avg = class_stats.get(code) or {"attendance": 0.0, "marks": 0.0, "assignment": 0.0, "count": 0}
        diff = round(course["internal_marks"] - avg["marks"], 1)
        if course["internal_marks"] >= 80.0 and course["attendance_pct"] >= excellent_att:
            status = {"text": "Excellent", "status": "success"}
        elif course["internal_marks"] >= avg["marks"] - 2.0 and course["attendance_pct"] >= min_att:
            status = {"text": "Stable", "status": "info"}
        elif diff >= -8.0:
            status = {"text": "Needs Help", "status": "warning"}
        else:
            status = {"text": "At Risk", "status": "danger"}
        subject_rows.append({
            "course_code": code,
            "my_marks": course["internal_marks"],
            "class_marks": avg["marks"],
            "my_attendance": course["attendance_pct"],
            "class_attendance": avg["attendance"],
            "diff": diff,
            "status": status,
        })
        chart_labels.append(code)
        chart_mine.append(course["internal_marks"])
        chart_class.append(avg["marks"])

    rank = _batch_rank(student_id, record["batch"], record["avg_marks"], docs=batch_docs) if record["batch"] else None
    avg_marks_all = _safe_float(_batch_class_average(record["batch"], docs=batch_docs))
    avg_att_all = _safe_float(_batch_class_attendance(record["batch"], docs=batch_docs))
    tips = _build_tips(record, prediction, avg_marks_all, avg_att_all, min_att=min_att)
    insight = _build_insight(record, rank)

    unread_alerts = notifications_col().count_documents({"is_read": False, "$or": _alert_targets(student_id, user_id, role)})
    active_courses = courses_col().count_documents({"status": "ACTIVE"})
    credits = 0.0
    for c in courses_col().find({"course_code": {"$in": [x["course_code"] for x in record["courses"]]}}, {"_id": 0, "credits": 1}):
        credits += _safe_float(c.get("credits"), 3.0)
    if credits == 0.0 and record["courses"]:
        credits = round(3.0 * len(record["courses"]), 1)

    return {
        "record": record,
        "subject_rows": subject_rows,
        "chart": {"labels": chart_labels, "mine": chart_mine, "class_avg": chart_class},
        "rank": rank,
        "tips": tips,
        "insight": insight,
        "unread_alerts": unread_alerts,
        "active_courses": active_courses,
        "credits": round(credits, 1),
        "teacher_alerts": _load_recent_alerts(student_id, user_id, role, limit=5),
    }


def _batch_class_average(batch, docs=None):
    iterable = docs if docs is not None else student_records_col().find({"batch": batch} if batch else {}, {"_id": 0, "internal_marks": 1})
    values = [_safe_float(r.get("internal_marks")) for r in iterable]
    return round(sum(values) / len(values), 1) if values else 0.0


def _batch_class_attendance(batch, docs=None):
    iterable = docs if docs is not None else student_records_col().find({"batch": batch} if batch else {}, {"_id": 0, "attendance_pct": 1})
    values = [_safe_float(r.get("attendance_pct")) for r in iterable]
    return round(sum(values) / len(values), 1) if values else 0.0


def get_student_overview_context(student_id, user_id, role):
    key = f"student:overview:{student_id}:{user_id}:{role}"
    return get_cached(key, lambda: _load_student_overview(student_id, user_id, role), ttl=30.0)


def build_report_export_rows(record, subject_rows):
    rows = []
    for s in subject_rows:
        rows.append([
            record["full_name"] or record["student_id"],
            record["student_id"],
            record["batch"] or "-",
            s["course_code"],
            f"{s['my_marks']:.1f}",
            f"{s['class_marks']:.1f}",
            f"{s['my_attendance']:.1f}",
            f"{s['class_attendance']:.1f}",
            f"{record['predicted_gpa']:.2f}" if record["predicted_gpa"] is not None else "-",
            record["risk_level"],
            s["status"]["text"],
        ])
    return rows
