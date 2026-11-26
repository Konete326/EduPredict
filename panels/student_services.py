from pymongo import DESCENDING
from analytics.ml_engine import _resolve_runtime_settings
from core.db import courses_col, get_cached, notifications_col, predictions_col, student_records_col, support_tickets_col, users_col
from panels.student_alert_services import _alert_targets, _load_recent_alerts, get_student_alerts_context, mark_alert_read


def _safe_float(val, default=0.0):
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _empty_record(student_id):
    return {
        "student_id": student_id, "full_name": "", "batch": "", "department": "", "program_level": "",
        "records": [], "courses": [], "avg_attendance": 0.0, "avg_marks": 0.0,
        "avg_assignment": 0.0, "lms_hours_weekly": 0.0, "previous_gpa": 0.0,
        "predicted_gpa": None, "risk_level": "PENDING", "risk_score": None,
        "is_anomaly": False, "anomaly_reason": "", "recommendation": "", "generated_at": None,
    }


def _fetch_student_docs(student_id):
    records = list(student_records_col().find({"student_id": student_id}, {"_id": 0}).sort("updated_at", DESCENDING))
    preds = list(predictions_col().find({"student_id": student_id}, {"_id": 0}).sort("generated_at", DESCENDING).limit(1))
    return records, (preds[0] if preds else None)


def _resolve_program_level(user_doc, department, batch):
    explicit = str((user_doc or {}).get("program_level") or "").strip()
    if explicit:
        return explicit
    if department:
        return f"BS {department}"
    return f"Batch {batch}" if batch else "Undergraduate"


def _fetch_student_user_doc(student_id, user_id):
    proj = {"_id": 0, "full_name": 1, "batch": 1, "department": 1, "program_level": 1, "assigned_teacher_id": 1, "assigned_teacher_name": 1}
    try:
        ucol = users_col()
        doc = ucol.find_one({"student_id": student_id}, proj) if student_id else None
        if not doc and user_id:
            doc = ucol.find_one({"user_id": user_id}, proj)
        return doc
    except Exception:
        return None


def resolve_assigned_teacher(student_id, user_id, user_doc=None, records=None, enrolled_courses=None):
    udoc = user_doc if isinstance(user_doc, dict) else _fetch_student_user_doc(student_id, user_id)
    recs = records if records is not None else (list(student_records_col().find({"student_id": student_id}, {"_id": 0, "teacher_user_id": 1, "teacher_name": 1, "teacher_email": 1}).sort("updated_at", DESCENDING).limit(5)) if student_id else [])
    tid = str((udoc or {}).get("assigned_teacher_id") or "").strip()
    tname = str((udoc or {}).get("assigned_teacher_name") or "").strip()
    temail = ""
    for rec in recs:
        if not tid and rec.get("teacher_user_id"):
            tid = str(rec.get("teacher_user_id") or "").strip()
        if not tname and rec.get("teacher_name"):
            tname = str(rec.get("teacher_name") or "").strip()
        if not temail and rec.get("teacher_email"):
            temail = str(rec.get("teacher_email") or "").strip()
        if tid and tname and temail:
            break
    if not tname and enrolled_courses:
        for ec in enrolled_courses:
            cand = str(ec.get("teacher_name") or "").strip()
            if cand and cand.upper() != "TBA":
                tname = cand
                temail = temail or str(ec.get("teacher_email") or "").strip()
                break
    try:
        ucol = users_col()
        tdoc = ucol.find_one({"user_id": tid}, {"_id": 0, "user_id": 1, "full_name": 1, "email": 1}) if tid else None
        if not tdoc and tname:
            for cand in ucol.find({"role": "TEACHER"}, {"_id": 0, "user_id": 1, "full_name": 1, "email": 1}):
                if str(cand.get("full_name") or "").strip().lower() == tname.lower():
                    tdoc = cand
                    break
        if tdoc:
            tid = tid or str(tdoc.get("user_id") or "").strip()
            tname = tname or str(tdoc.get("full_name") or "").strip()
            temail = temail or str(tdoc.get("email") or "").strip()
    except Exception:
        pass
    return {"teacher_id": tid, "name": tname, "email": temail}


def _load_academic_context(course_codes, batch, records=None):
    clean_codes = [str(c).strip().upper() for c in (course_codes or []) if c]
    if clean_codes:
        course_docs = list(courses_col().find({"course_code": {"$in": clean_codes}}, {"_id": 0}))
    elif batch:
        course_docs = list(courses_col().find({"batch": batch, "status": "ACTIVE"}, {"_id": 0}))
    else:
        course_docs = []
    teachers_by_name = {}
    for t in users_col().find({"role": "TEACHER"}, {"_id": 0, "full_name": 1, "email": 1}):
        tname = str(t.get("full_name") or "").strip()
        if tname:
            teachers_by_name[tname.lower()] = {"name": tname, "email": str(t.get("email") or "").strip()}
    rec_teacher_by_code = {}
    for rec in (records or []):
        code = str(rec.get("course_code") or "").strip().upper()
        if code and code not in rec_teacher_by_code and rec.get("teacher_name"):
            rec_teacher_by_code[code] = {"name": str(rec.get("teacher_name") or "").strip(), "email": str(rec.get("teacher_email") or "").strip()}
    by_code = {str(c.get("course_code") or "").strip().upper(): c for c in course_docs}
    enrolled_courses = []
    for code in (clean_codes or list(by_code.keys())):
        cdoc = by_code.get(code) or {}
        rec_t = rec_teacher_by_code.get(code) or {}
        instructor = str(cdoc.get("instructor") or rec_t.get("name") or "TBA").strip() or "TBA"
        tinfo = teachers_by_name.get(instructor.lower()) or {}
        enrolled_courses.append({
            "course_code": code,
            "title": str(cdoc.get("title") or code),
            "credits": round(_safe_float(cdoc.get("credits"), 3.0), 1),
            "teacher_name": tinfo.get("name") or rec_t.get("name") or instructor,
            "teacher_email": tinfo.get("email") or rec_t.get("email") or "",
        })
    admin_doc = users_col().find_one({"role": "ADMIN", "is_active": True}, {"_id": 0, "full_name": 1, "email": 1}) or users_col().find_one({"role": "ADMIN"}, {"_id": 0, "full_name": 1, "email": 1})
    admin_contact = {"name": str((admin_doc or {}).get("full_name") or "Portal Administrator"), "email": str((admin_doc or {}).get("email") or "")}
    return enrolled_courses, admin_contact, course_docs


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
        b = stats.setdefault(code, {"att": 0.0, "marks": 0.0, "assign": 0.0, "count": 0})
        b["att"] += _safe_float(rec.get("attendance_pct"))
        b["marks"] += _safe_float(rec.get("internal_marks"))
        b["assign"] += _safe_float(rec.get("assignment_score"))
        b["count"] += 1
    return {code: {"attendance": round(b["att"] / b["count"], 1), "marks": round(b["marks"] / b["count"], 1), "assignment": round(b["assign"] / b["count"], 1), "count": b["count"]} for code, b in stats.items()}


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


def _build_tips(record, prediction, class_avg_marks, class_avg_att, min_att=75.0, has_records=True):
    if not has_records or ("courses" in record and not record.get("courses")):
        return []
    tips = []
    att, marks, risk, lms = record["avg_attendance"], record["avg_marks"], record["risk_level"], record["lms_hours_weekly"]
    class_att = class_avg_att or 0.0
    if att < float(min_att):
        target_att = min(100, int(round(float(min_att))) + 10)
        needed = max(0, int(round((float(target_att) - att) / 5.0 * 10)))
        tips.append({"icon": "fa-solid fa-calendar-check", "status": "danger" if att < 60.0 else "warning", "title": f"Raise your attendance above {target_att}%", "text": f"You are at {att:.1f}%. Attending the next {max(1, needed)} lectures will push you over {target_att}%."})
    elif att >= min(100.0, max(90.0, float(min_att) + 10.0)):
        tips.append({"icon": "fa-solid fa-medal", "status": "success", "title": "Attendance is excellent", "text": f"You are at {att:.1f}%, well above the class average of {class_att:.1f}%. Keep it up!"})
    if marks < class_avg_marks - 3:
        tips.append({"icon": "fa-solid fa-book-open", "status": "warning", "title": "Marks are below class average", "text": f"Your average is {marks:.1f} vs class {class_avg_marks:.1f}. Revise this week's topics and ask your teacher for practice work."})
    if lms < 5.0:
        tips.append({"icon": "fa-solid fa-clock", "status": "warning", "title": "Increase weekly study time", "text": f"You study about {lms:.1f} hours per week. Aim for 6-8 hours to see steady grade gains."})
    if risk == "HIGH":
        tips.append({"icon": "fa-solid fa-hands-holding-circle", "status": "danger", "title": "Extra support recommended", "text": "Your current risk is High. Message your teacher from the Alerts page and set a weekly catch-up plan."})
    if not tips:
        tips.append({"icon": "fa-solid fa-circle-check", "status": "success", "title": "You are on track", "text": "Attendance and marks look healthy. Keep your routine and stay ahead of deadlines."})
    return tips


def _build_insight(record, rank):
    if not record.get("courses"):
        return {"summary": "No course marks or attendance records have been uploaded for your Student ID yet. Your personal AI insights will appear once your teacher uploads class marks.", "status": "info", "points": []}
    risk, att, gpa = record["risk_level"], record["avg_attendance"], record["predicted_gpa"]
    summary_map = {
        "PENDING": ("Your prediction is not ready yet. Once your teacher uploads marks, your personal insight will appear here.", "info"),
        "HIGH": ("You are at high dropout risk right now. Focus on attendance first, then talk to your teacher about a catch-up plan.", "danger"),
        "MEDIUM": ("You are doing okay but slipping in some areas. Small weekly improvements will move you back on track.", "warning"),
    }
    summary, status = summary_map.get(risk, ("Great work! Your attendance and marks predict a strong final result. Keep your current routine.", "success"))
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
    user_doc = _fetch_student_user_doc(student_id, user_id)

    if records:
        primary = records[0]
        record["full_name"] = str(primary.get("full_name") or "")
        record["batch"] = str(primary.get("batch") or "")
        course_rows = [{"course_code": str(rec.get("course_code") or "").upper(), "attendance_pct": round(_safe_float(rec.get("attendance_pct")), 1), "internal_marks": round(_safe_float(rec.get("internal_marks")), 1), "assignment_score": round(_safe_float(rec.get("assignment_score")), 1), "lms_hours_weekly": round(_safe_float(rec.get("lms_hours_weekly")), 1)} for rec in records]
        record["courses"] = course_rows
        n = len(course_rows) or 1
        record["avg_attendance"] = round(sum(c["attendance_pct"] for c in course_rows) / n, 1)
        record["avg_marks"] = round(sum(c["internal_marks"] for c in course_rows) / n, 1)
        record["avg_assignment"] = round(sum(c["assignment_score"] for c in course_rows) / n, 1)
        record["lms_hours_weekly"] = course_rows[0]["lms_hours_weekly"]
        record["previous_gpa"] = round(_safe_float(primary.get("previous_gpa")), 2)

    if isinstance(user_doc, dict):
        record["full_name"] = record["full_name"] or str(user_doc.get("full_name") or "")
        record["batch"] = record["batch"] or str(user_doc.get("batch") or "")
        record["department"] = str(user_doc.get("department") or "")
    record["program_level"] = _resolve_program_level(user_doc, record["department"], record["batch"])

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

    if record["courses"] and record["predicted_gpa"] is None:
        record["predicted_gpa"] = round(min(4.0, max(0.0, (record["avg_marks"] / 100.0) * 4.0)), 2)
        if record["risk_level"] == "PENDING":
            record["risk_level"] = "HIGH" if (record["avg_attendance"] < min_att or record["avg_marks"] < 50.0) else ("MEDIUM" if record["avg_marks"] < 65.0 else "LOW")

    course_codes = [x["course_code"] for x in record["courses"] if x.get("course_code")]
    batch_docs = _fetch_batch_docs(record["batch"], course_codes=course_codes) if (record["courses"] and (record["batch"] or course_codes)) else []
    class_stats = _course_class_stats(record["batch"], docs=batch_docs)
    subject_rows, chart_labels, chart_mine, chart_class = [], [], [], []
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
        subject_rows.append({"course_code": code, "my_marks": course["internal_marks"], "class_marks": avg["marks"], "my_attendance": course["attendance_pct"], "class_attendance": avg["attendance"], "diff": diff, "status": status})
        chart_labels.append(code)
        chart_mine.append(course["internal_marks"])
        chart_class.append(avg["marks"])

    rank = _batch_rank(student_id, record["batch"], record["avg_marks"], docs=batch_docs) if (record["courses"] and record["batch"]) else None
    avg_marks_all = _safe_float(_batch_class_average(record["batch"], docs=batch_docs))
    avg_att_all = _safe_float(_batch_class_attendance(record["batch"], docs=batch_docs))
    tips = _build_tips(record, prediction, avg_marks_all, avg_att_all, min_att=min_att, has_records=bool(record["courses"]))
    insight = _build_insight(record, rank)
    unread_alerts = notifications_col().count_documents({"is_read": False, "$or": _alert_targets(student_id, user_id, role)})
    active_courses = courses_col().count_documents({"status": "ACTIVE"})
    enrolled_courses, admin_contact, course_docs = _load_academic_context(course_codes, record["batch"], records=records)
    assigned_teacher = resolve_assigned_teacher(student_id, user_id, user_doc=user_doc, records=records, enrolled_courses=enrolled_courses)
    credits = sum(_safe_float(c.get("credits"), 3.0) for c in course_docs if str(c.get("course_code") or "").upper() in course_codes)
    if credits == 0.0 and record["courses"]:
        credits = round(3.0 * len(record["courses"]), 1)

    return {
        "record": record, "subject_rows": subject_rows,
        "chart": {"labels": chart_labels, "mine": chart_mine, "class_avg": chart_class},
        "rank": rank, "tips": tips, "insight": insight,
        "unread_alerts": unread_alerts, "active_courses": active_courses, "credits": round(credits, 1),
        "teacher_alerts": _load_recent_alerts(student_id, user_id, role, limit=5),
        "enrolled_courses": enrolled_courses, "admin_contact": admin_contact, "assigned_teacher": assigned_teacher,
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
    return get_cached(f"student:overview:{student_id}:{user_id}:{role}", lambda: _load_student_overview(student_id, user_id, role), ttl=30.0)


def list_student_feedback_tickets(student_id, user_id):
    ids = [x for x in dict.fromkeys((str(user_id or "").strip(), str(student_id or "").strip())) if x]
    if not ids:
        return []
    query = {"$or": [{"user_id": {"$in": ids}}, {"student_id": {"$in": ids}}]}
    items = []
    for t in support_tickets_col().find(query, {"_id": 0}).sort("created_at", DESCENDING).limit(20):
        created = t.get("created_at")
        status = str(t.get("status") or "OPEN").upper()
        target_role = str(t.get("target_role") or "ADMIN").strip().upper()
        t_name = str(t.get("target_teacher_name") or "").strip()
        recipient_label = f"Teacher ({t_name})" if (target_role == "TEACHER" and t_name) else ("Teacher" if target_role == "TEACHER" else "Admin")
        items.append({
            "ticket_id": str(t.get("ticket_id") or ""),
            "subject": str(t.get("subject") or ""),
            "message": str(t.get("message") or ""),
            "target_role": target_role,
            "target_teacher_name": t_name,
            "recipient_label": recipient_label,
            "admin_reply": str(t.get("admin_reply") or ""),
            "replied_by": str(t.get("replied_by") or ""),
            "attachments": [str(a) for a in (t.get("attachments") or []) if a],
            "status": status,
            "created": created.strftime("%Y-%m-%d %H:%M") if hasattr(created, "strftime") else "-",
        })
    return items


def build_report_export_rows(record, subject_rows):
    gpa_str = f"{record['predicted_gpa']:.2f}" if record["predicted_gpa"] is not None else "-"
    return [
        [record["full_name"] or record["student_id"], record["student_id"], record["batch"] or "-", s["course_code"], f"{s['my_marks']:.1f}", f"{s['class_marks']:.1f}", f"{s['my_attendance']:.1f}", f"{s['class_attendance']:.1f}", gpa_str, record["risk_level"], s["status"]["text"]]
        for s in subject_rows
    ]
