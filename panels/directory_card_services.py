from core.db import users_col
from panels.teacher_services import classify_performance_badge


def _action(label, icon, onclick, title, attrs, variant="default"):
    return {"label": label, "icon": icon, "variant": variant, "title": title, "onclick": onclick, "attrs": attrs}


def _initials(name, fallback="U"):
    parts = [p[0] for p in str(name or "").split() if p]
    return "".join(parts[:2]).upper() or fallback


def _safe_num_str(val, default="0.0"):
    text = str(val or "").replace("%", "").strip()
    try:
        return f"{float(text):.1f}"
    except (TypeError, ValueError):
        return default


def _lookup_avatars(student_ids):
    avatar_map = {}
    sids = [sid for sid in student_ids if sid]
    if not sids:
        return avatar_map
    try:
        for doc in users_col().find({"student_id": {"$in": sids}}, {"_id": 0, "student_id": 1, "avatar_url": 1}):
            sid = str(doc.get("student_id") or "").strip()
            url = str(doc.get("avatar_url") or "").strip()
            if sid and url:
                avatar_map[sid] = url
    except Exception:
        pass
    return avatar_map


def build_admin_user_cards(users, filter_role, actor_user_id, actor_email=""):
    role_status_map = {"ADMIN": "info", "ANALYST": "info", "TEACHER": "warning", "STUDENT": "success"}
    clean_actor_id = str(actor_user_id or "").strip()
    clean_actor_email = str(actor_email or "").strip().lower()
    cards = []
    for u in users or []:
        uid = str(u.get("user_id") or "").strip()
        full_name = str(u.get("full_name") or uid or "User")
        email = str(u.get("email") or "")
        role = str(u.get("role") or "USER").upper()
        dept = str(u.get("department") or "General")
        batch = str(u.get("batch") or "ALL")
        program_level = str(u.get("program_level") or ("BS / Undergraduate" if role == "STUDENT" else ""))
        is_active = bool(u.get("is_active", True))
        approval_status = str(u.get("approval_status") or ("APPROVED" if is_active else "INACTIVE")).upper()
        is_pending = approval_status == "PENDING"
        is_rejected = approval_status == "REJECTED"
        is_self = (clean_actor_id and uid == clean_actor_id) or (clean_actor_email and email.strip().lower() == clean_actor_email)
        edit_attrs = {"data-user-id": uid, "data-full-name": full_name, "data-email": email, "data-role": role, "data-department": dept, "data-batch": batch, "data-program-level": program_level, "data-filter-role": filter_role}
        if is_self:
            edit_attrs["data-is-self"] = "true"
        actions = [_action("Edit", "fa-solid fa-pen-to-square", "openEditUserModal(this)", f"Edit {full_name}", edit_attrs)]
        if not is_self:
            if is_pending:
                lbl, ico, toggle_variant = "Approve", "fa-solid fa-user-check", "primary"
            else:
                lbl, ico = ("Deactivate", "fa-solid fa-user-slash") if is_active else ("Activate", "fa-solid fa-user-check")
                toggle_variant = "default"
            toggle_attrs = {"data-user-id": uid, "data-full-name": full_name, "data-is-active": "true" if is_active else "false", "data-filter-role": filter_role}
            if is_pending:
                toggle_attrs["data-approval-status"] = approval_status
            actions.append(_action(lbl, ico, "openToggleUserModal(this)", f"{lbl} {full_name}", toggle_attrs, variant=toggle_variant))
            if is_pending:
                actions.append(_action("Reject", "fa-solid fa-user-xmark", "openRejectUserModal(this)", f"Reject {full_name}", {"data-user-id": uid, "data-full-name": full_name, "data-filter-role": filter_role}, variant="danger"))
            actions.append(_action("Delete", "fa-solid fa-trash", "openDeleteUserModal(this)", f"Delete {full_name}", {"data-user-id": uid, "data-full-name": full_name, "data-filter-role": filter_role}, variant="danger"))
        if is_pending:
            badge = {"text": "Pending Approval", "status": "warning"}
        elif is_rejected:
            badge = {"text": "Rejected", "status": "danger"}
        else:
            badge = {"text": "Active" if is_active else "Inactive", "status": "success" if is_active else "danger"}
        cards.append({
            "id": uid,
            "kind": "user",
            "title": f"{full_name} (You)" if is_self else full_name,
            "subtitle": email,
            "code": uid,
            "avatar_url": str(u.get("avatar_url") or ""),
            "initials": _initials(full_name, "U"),
            "badge": badge,
            "role_badge": {"text": role, "status": role_status_map.get(role, "info")},
            "rejection_reason": str(u.get("rejection_reason") or ""),
            "meta": [
                {"label": "Role", "value": role},
                {"label": "Dept", "value": dept},
                {"label": "Batch", "value": f"{batch} · {program_level}" if program_level else batch},
                {"label": "Joined", "value": u.get("created_at_str") or "-"},
                {"label": "Level", "value": program_level or "-"},
            ],
            "actions": actions,
        })
    return cards


def _parse_fallback_rows(fallback_rows):
    parsed = []
    for row in fallback_rows or []:
        if not isinstance(row, (list, tuple)) or len(row) < 7:
            continue
        sid = str(row[0] or "").strip()
        full_name = str(row[1] or sid)
        batch = str(row[2] or "2026-A")
        course_code = str(row[3] or "CS-101").upper()
        att_str = _safe_num_str(row[4], "0.0")
        marks_str = _safe_num_str(row[5], "0.0")
        gpa_str = str(row[6] or "0.00").strip()
        badge = row[7] if len(row) >= 9 and isinstance(row[7], dict) and "text" in row[7] else classify_performance_badge(att_str, marks_str, "")
        parsed.append({
            "student_id": sid,
            "full_name": full_name,
            "batch": batch,
            "course_code": course_code,
            "attendance_pct": float(att_str),
            "internal_marks": float(marks_str),
            "assignment_score": float(marks_str),
            "lms_hours_weekly": 8.0,
            "previous_gpa": float(gpa_str) if gpa_str.replace(".", "", 1).isdigit() else 0.0,
            "predicted_gpa": float(gpa_str) if gpa_str.replace(".", "", 1).isdigit() else None,
            "badge": badge,
        })
    return parsed


def build_teacher_student_cards(students=None, fallback_rows=None, include_alert=True, include_delete=True):
    items = list(students) if students else _parse_fallback_rows(fallback_rows)
    if not items:
        return []
    avatar_map = _lookup_avatars([str(s.get("student_id") or "").strip() for s in items])
    cards = []
    for s in items:
        sid = str(s.get("student_id") or "").strip()
        full_name = str(s.get("full_name") or sid)
        batch = str(s.get("batch") or "2026-A")
        course_code = str(s.get("course_code") or "CS-101").upper()
        att = float(s.get("attendance_pct") or 0.0)
        marks = float(s.get("internal_marks") or 0.0)
        assign = float(s.get("assignment_score") or marks)
        lms = float(s.get("lms_hours_weekly") or 8.0)
        prev_gpa = float(s.get("previous_gpa") or 0.0)
        pred_gpa = s.get("predicted_gpa")
        gpa_display = f"{float(pred_gpa):.2f}" if pred_gpa is not None else f"{prev_gpa:.2f}"
        badge = s.get("badge") if isinstance(s.get("badge"), dict) else classify_performance_badge(att, marks, s.get("risk_level", ""))
        edit_attrs = {
            "data-student-id": sid,
            "data-full-name": full_name,
            "data-batch": batch,
            "data-course-code": course_code,
            "data-attendance-pct": f"{att:.1f}",
            "data-internal-marks": f"{marks:.1f}",
            "data-assignment-score": f"{assign:.1f}",
            "data-lms-hours-weekly": f"{lms:.1f}",
            "data-previous-gpa": f"{prev_gpa:.2f}",
        }
        actions = [_action("Update Marks", "fa-solid fa-pen-to-square", "openUpdateMarksModal(this)", f"Edit marks for {full_name}", edit_attrs)]
        if include_alert:
            actions.append(_action("Send Alert", "fa-solid fa-bell", "openSendAlertModal(this)", f"Send alert to {full_name}", {"data-student-id": sid, "data-full-name": full_name, "data-course-code": course_code}, variant="primary"))
        if include_delete:
            actions.append(_action("Delete", "fa-solid fa-trash", "openDeleteStudentModal(this)", f"Delete {full_name}", {"data-student-id": sid, "data-full-name": full_name}, variant="danger"))
        cards.append({
            "id": sid,
            "kind": "student",
            "student_360_id": sid,
            "title": full_name,
            "subtitle": f"{course_code} · Batch {batch}",
            "code": sid,
            "avatar_url": str(s.get("avatar_url") or avatar_map.get(sid) or ""),
            "initials": _initials(full_name, "S"),
            "badge": badge,
            "attendance_pct": round(att, 1),
            "marks_display": f"{marks:.1f}",
            "gpa_display": gpa_display,
            "course_code": course_code,
            "batch": batch,
            "meta": [
                {"label": "Course", "value": course_code},
                {"label": "Batch", "value": batch},
                {"label": "Attendance", "value": f"{att:.1f}%"},
                {"label": "Marks / GPA", "value": f"{marks:.1f} / {gpa_display}"},
            ],
            "actions": actions,
        })
    return cards
