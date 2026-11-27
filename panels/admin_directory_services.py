import json


def _action(label, icon, onclick, title, attrs, variant="default"):
    return {"label": label, "icon": icon, "variant": variant, "title": title, "onclick": onclick, "attrs": attrs}


def _view_action(title, payload):
    return {"type": "view_modal", "label": "View", "icon": "fa-solid fa-eye", "variant": "default", "title": title, "payload_json": json.dumps(payload)}


def _initials(name, fallback="U"):
    parts = [p[0] for p in str(name or "").split() if p]
    return "".join(parts[:2]).upper() or fallback


def build_user_table_data(users, filter_role, actor_user_id, actor_email=""):
    headers = ["Name", "Role", "Status", "Actions"]
    role_status_map = {"ADMIN": "info", "ANALYST": "info", "TEACHER": "warning", "STUDENT": "success"}
    clean_actor_id = str(actor_user_id or "").strip()
    clean_actor_email = str(actor_email or "").strip().lower()
    rows = []
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
        status_badge = (
            {"text": "Pending Approval", "status": "warning"} if is_pending
            else ({"text": "Rejected", "status": "danger"} if is_rejected
                  else {"text": "Active" if is_active else "Inactive", "status": "success" if is_active else "danger"})
        )
        display_name = f"{full_name} (You)" if is_self else full_name
        view_payload = {
            "title": display_name,
            "subtitle": f"{role} · {uid}",
            "badge": status_badge["text"],
            "items": [
                {"label": "User ID", "value": uid or "-"},
                *([{"label": "Student ID", "value": str(u.get("student_id") or "-")}] if (role == "STUDENT" or u.get("student_id")) else []),
                {"label": "Email", "value": email or "-"},
                {"label": "Department", "value": dept or "-"},
                {"label": "Program / Level", "value": program_level or "-"},
                {"label": "Batch", "value": batch or "-"},
                {"label": "Assigned Teacher", "value": str(u.get("assigned_teacher_name") or "-")},
                {"label": "Joined Date", "value": str(u.get("created_at_str") or "-"), "fullWidth": True},
                {"label": "Last Login", "value": str(u.get("last_login_str") or "Not logged in yet"), "fullWidth": True},
                *([{"label": "Rejection Reason", "value": str(u["rejection_reason"]), "fullWidth": True}] if u.get("rejection_reason") else []),
            ],
        }
        edit_attrs = {"data-user-id": uid, "data-full-name": full_name, "data-email": email, "data-role": role, "data-department": dept, "data-batch": batch, "data-program-level": program_level, "data-filter-role": filter_role, **({"data-is-self": "true"} if is_self else {})}
        actions = [_view_action(f"View {full_name}", view_payload), _action("Edit", "fa-solid fa-pen-to-square", "openEditUserModal(this)", f"Edit {full_name}", edit_attrs)]
        if not is_self:
            if is_pending:
                lbl, ico, toggle_variant = "Approve", "fa-solid fa-user-check", "primary"
            else:
                lbl, ico = ("Deactivate", "fa-solid fa-user-slash") if is_active else ("Activate", "fa-solid fa-user-check")
                toggle_variant = "default"
            toggle_attrs = {"data-user-id": uid, "data-full-name": full_name, "data-is-active": "true" if is_active else "false", "data-filter-role": filter_role, **({"data-approval-status": approval_status} if is_pending else {})}
            actions.append(_action(lbl, ico, "openToggleUserModal(this)", f"{lbl} {full_name}", toggle_attrs, variant=toggle_variant))
            if is_pending:
                actions.append(_action("Reject", "fa-solid fa-user-xmark", "openRejectUserModal(this)", f"Reject {full_name}", {"data-user-id": uid, "data-full-name": full_name, "data-filter-role": filter_role}, variant="danger"))
            actions.append(_action("Delete", "fa-solid fa-trash", "openDeleteUserModal(this)", f"Delete {full_name}", {"data-user-id": uid, "data-full-name": full_name, "data-filter-role": filter_role}, variant="danger"))
        name_cell = {"text": display_name, "initials": _initials(full_name, "U"), "avatar_url": str(u.get("avatar_url") or "")}
        rows.append([name_cell, {"text": role, "status": role_status_map.get(role, "info")}, status_badge, {"actions": actions}])
    return headers, rows


def build_ticket_table_data(tickets, filter_status):
    headers = ["Subject", "User", "Status", "Actions"]
    rows = []
    for t in tickets or []:
        tid, status = t["ticket_id"], t["status"]
        is_open, has_reply = status == "OPEN", bool(t.get("admin_reply"))
        lbl, ico = ("Resolve", "fa-solid fa-circle-check") if is_open else ("Reopen", "fa-solid fa-rotate-left")
        raw_dt = t.get("created_at_str") or t.get("created_at") or ""
        created_at = raw_dt.strftime("%Y-%m-%d %H:%M") if hasattr(raw_dt, "strftime") else str(raw_dt)
        attachments = [str(a) for a in (t.get("attachments") or []) if a]
        view_payload = {
            "title": t["subject"],
            "subtitle": f"{tid} · {t.get('user_name') or 'User'}",
            "badge": status,
            "items": [
                {"label": "Ticket ID", "value": tid or "-"},
                {"label": "User", "value": t.get("user_name") or "User"},
                {"label": "Role", "value": t.get("role") or "USER"},
                {"label": "Date", "value": created_at or "-"},
                {"label": "Full Message", "value": t.get("message") or "-", "fullWidth": True},
                {"label": "Reply", "value": t.get("admin_reply") or "No reply yet.", "fullWidth": True},
            ],
        }
        base_attrs = {"data-ticket-id": tid, "data-subject": t["subject"], "data-filter-status": filter_status}
        reply_attrs = {**base_attrs, "data-message": t.get("message", ""), "data-admin-reply": t.get("admin_reply", ""), "data-status": status, "data-attachments": "|".join(attachments)}
        actions = [
            _view_action(f"View {tid}", view_payload),
            _action("Edit" if has_reply else "Reply", "fa-solid fa-reply", "openReplyTicketModal(this)", f"Reply to {tid}", reply_attrs, variant="primary"),
            _action(lbl, ico, "openToggleTicketModal(this)", f"{lbl} {tid}", {**base_attrs, "data-status": status}),
            _action("Delete", "fa-solid fa-trash", "openDeleteTicketModal(this)", f"Delete ticket {tid}", {**base_attrs, "aria-label": f"Delete ticket {tid}"}, variant="danger"),
        ]
        rows.append([t["subject"], t.get("user_name") or "User", {"text": status, "status": "success" if status == "RESOLVED" else "warning"}, {"actions": actions}])
    return headers, rows


def build_training_upload_rows(uploads):
    rows = []
    for u in uploads or []:
        did = str(u.get("dataset_id") or "").strip()
        fn = str(u.get("filename") or "master.csv")
        by = str(u.get("uploaded_by") or "System Admin")
        rc = int(u.get("rows_processed") or 0)
        preds = int(u.get("predictions_generated") or 0)
        st = str(u.get("status") or "COMPLETED").upper()
        dt = str(u.get("uploaded_at_str") or "-")
        cols = [str(c) for c in (u.get("columns") or []) if c]
        preview_lines = []
        for r in (u.get("preview_rows") or [])[:5]:
            if not isinstance(r, dict):
                continue
            sid = str(r.get("student_id") or "-")
            name = str(r.get("full_name") or "").strip()
            parts = [f"{sid} ({name})" if name else sid]
            if r.get("attendance_pct") is not None:
                parts.append(f"Att {r.get('attendance_pct')}%")
            if r.get("internal_marks") is not None:
                parts.append(f"Marks {r.get('internal_marks')}")
            if r.get("previous_gpa") is not None:
                parts.append(f"GPA {r.get('previous_gpa')}")
            preview_lines.append(" · ".join(parts))
        view_payload = {
            "title": fn,
            "subtitle": f"{did + ' · ' if did else ''}{by} · {dt}",
            "badge": st,
            "items": [
                {"label": "Dataset ID", "value": did or "-"},
                {"label": "Filename", "value": fn},
                {"label": "Uploaded By", "value": by},
                {"label": "Rows", "value": str(rc)},
                {"label": "Predictions", "value": str(preds)},
                {"label": "Missing Fixed", "value": str(int(u.get("missing_values_fixed") or 0))},
                {"label": "Model Version", "value": str(u.get("model_version") or "-")},
                {"label": "Uploaded At", "value": dt},
                {"label": "Columns", "value": ", ".join(cols) if cols else "-"},
                {"label": "Sample Preview", "value": "\n".join(preview_lines) if preview_lines else "No preview rows available.", "fullWidth": True},
            ],
        }
        actions = [
            _view_action(f"View {fn}", view_payload),
            _action("Delete", "fa-solid fa-trash", "openDeleteDatasetModal(this)", f"Delete {fn}", {"data-dataset-id": did, "data-filename": fn}, variant="danger"),
        ]
        rows.append([fn, by, rc, preds, {"text": st, "status": "success" if st == "COMPLETED" else "warning"}, dt, {"actions": actions}])
    return rows
