import json, re, uuid
from datetime import datetime, timezone
from pathlib import Path
from django.conf import settings
from django.urls import reverse
from core.cloudinary_services import upload_academic_attachment
from core.db import classroom_messages_col, courses_col, get_cached, invalidate_cache, semesters_col, student_records_col, users_col


def _norm(val):
    return str(val or "").strip()


def _semester_label(sem_doc):
    if not isinstance(sem_doc, dict) or not sem_doc:
        return "-"
    prog = _norm(sem_doc.get("program_name") or "BSCS")
    sname = _norm(sem_doc.get("semester_name") or f"Semester {sem_doc.get('semester_number') or 1}")
    return f"{prog} · {sname}"


def _sem_map():
    return {_norm(s.get("semester_id")): s for s in semesters_col().find({}, {"_id": 0}) if _norm(s.get("semester_id"))}


def _resolve_student_semester_id(session_user):
    sem_id = _norm((session_user or {}).get("semester_id"))
    if sem_id:
        return sem_id
    uid, sid = _norm((session_user or {}).get("user_id")), _norm((session_user or {}).get("student_id"))
    ucol = users_col()
    doc = (ucol.find_one({"user_id": uid}, {"_id": 0, "semester_id": 1}) if uid else None) or (ucol.find_one({"student_id": sid}, {"_id": 0, "semester_id": 1}) if sid else None)
    if doc and doc.get("semester_id"):
        return _norm(doc.get("semester_id"))
    if sid:
        rec = student_records_col().find_one({"student_id": sid}, {"_id": 0, "semester_id": 1})
        if rec and rec.get("semester_id"):
            return _norm(rec.get("semester_id"))
    return ""


def _build_user_chat_groups(session_user):
    user = session_user if isinstance(session_user, dict) else {}
    role = _norm(user.get("role") or "STUDENT").upper()
    uid, email, full_name = _norm(user.get("user_id")), _norm(user.get("email")).lower(), _norm(user.get("full_name")).lower()
    smap, student_sem_id = _sem_map(), (_resolve_student_semester_id(user) if role == "STUDENT" else "")
    filtered = []
    for c in courses_col().find({}, {"_id": 0}).sort("course_code", 1):
        code, status, c_sem = _norm(c.get("course_code")).upper(), _norm(c.get("status") or "ACTIVE").upper(), _norm(c.get("semester_id"))
        if not code or status == "INACTIVE":
            continue
        if role == "ADMIN" or (role == "TEACHER" and ((uid and _norm(c.get("instructor_id")) == uid) or (email and _norm(c.get("instructor_email")).lower() == email) or (full_name and _norm(c.get("instructor")).lower() == full_name))) or (role == "STUDENT" and student_sem_id and c_sem == student_sem_id):
            filtered.append(c)
    sem_counts, rec_counts = {}, {}
    for u in users_col().find({"role": "STUDENT"}, {"_id": 0, "semester_id": 1, "status": 1}):
        if _norm(u.get("status") or "ACTIVE").upper() != "INACTIVE" and _norm(u.get("semester_id")):
            s_id = _norm(u.get("semester_id"))
            sem_counts[s_id] = sem_counts.get(s_id, 0) + 1
    for r in student_records_col().find({"is_training_dataset": {"$ne": True}}, {"_id": 0, "course_code": 1, "student_id": 1}):
        cc = _norm(r.get("course_code")).upper()
        if cc:
            rec_counts.setdefault(cc, set()).add(_norm(r.get("student_id")))
    groups = []
    for c in filtered:
        code, c_sem = _norm(c.get("course_code")).upper(), _norm(c.get("semester_id"))
        teacher_name = _norm(c.get("instructor") or "TBA") or "TBA"
        s_count = max(sem_counts.get(c_sem, 0), len(rec_counts.get(code, set())))
        groups.append({"group_id": code, "title": _norm(c.get("title") or code) or code, "semester_id": c_sem, "semester_label": _semester_label(smap.get(c_sem)), "teacher_name": teacher_name, "member_count": s_count + (1 if teacher_name != "TBA" else 0)})
    return groups


def get_user_chat_groups(session_user):
    user = session_user if isinstance(session_user, dict) else {}
    role = _norm(user.get("role") or "STUDENT").upper()
    uid = _norm(user.get("user_id") or user.get("email") or "anon")
    return get_cached(f"chat:groups:{role}:{uid}", lambda: _build_user_chat_groups(user), ttl=20.0)


def _has_group_access(group_id, session_user):
    gid = _norm(group_id).upper()
    return bool(gid and any(g["group_id"] == gid for g in get_user_chat_groups(session_user)))


def _save_chat_media(file_obj):
    if not file_obj or not getattr(file_obj, "name", ""):
        return "", None
    url, _name, _img, err = upload_academic_attachment(file_obj, folder="edupredict/chat")
    if url:
        return url, None
    if err and err != "not_configured" and any(k in err.lower() for k in ("unsupported", "empty", "exceeds", "choose a file")):
        return "", err
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(file_obj.name).name).strip("_") or "media"
    upload_dir = Path(settings.BASE_DIR) / "static" / "uploads" / "chat"
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex[:8]}_{safe_name}"
    if hasattr(file_obj, "seek"):
        file_obj.seek(0)
    with (upload_dir / stored_name).open("wb") as fh:
        for chunk in file_obj.chunks():
            fh.write(chunk)
    return f"/static/uploads/chat/{stored_name}", None


def _parse_iso_dt(raw):
    text = _norm(raw)
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text[:-1] + "+00:00" if text.endswith("Z") else text)
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
    except ValueError:
        return None


def _format_created_at(dt):
    if not isinstance(dt, datetime):
        return "", ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat(), dt.strftime("%b %d, %H:%M")


def _load_sender_profiles(user_ids, smap):
    clean_ids = [uid for uid in set(user_ids) if uid]
    profiles = {}
    if not clean_ids:
        return profiles
    proj = {"_id": 0, "user_id": 1, "student_id": 1, "full_name": 1, "role": 1, "email": 1, "semester_id": 1}
    for u in users_col().find({"user_id": {"$in": clean_ids}}, proj):
        uid = _norm(u.get("user_id"))
        if uid:
            profiles[uid] = {
                "user_id": uid,
                "student_id": _norm(u.get("student_id")),
                "full_name": _norm(u.get("full_name") or "User"),
                "role": _norm(u.get("role") or "STUDENT").upper(),
                "email": _norm(u.get("email")),
                "semester_label": _semester_label(smap.get(_norm(u.get("semester_id")))),
            }
    return profiles


def _format_poll(raw_poll, current_uid):
    if not isinstance(raw_poll, dict) or not _norm(raw_poll.get("question")):
        return None
    raw_opts = raw_poll.get("options") or []
    votes_map = raw_poll.get("votes") if isinstance(raw_poll.get("votes"), dict) else {}
    counts = [0] * len(raw_opts)
    for opt_idx in votes_map.values():
        if isinstance(opt_idx, int) and 0 <= opt_idx < len(raw_opts):
            counts[opt_idx] += 1
    total_votes = sum(counts)
    my_vote = votes_map.get(current_uid)
    if not isinstance(my_vote, int) or not (0 <= my_vote < len(raw_opts)):
        my_vote = None
    options = [{"idx": idx, "text": _norm(t), "votes": counts[idx], "pct": round((counts[idx] / total_votes) * 100.0, 1) if total_votes else 0.0} for idx, t in enumerate(raw_opts)]
    return {"question": _norm(raw_poll.get("question")), "options": options, "total_votes": total_votes, "my_vote": my_vote}


def _assignment_link(raw_assign, viewer_role):
    if not isinstance(raw_assign, dict) or not _norm(raw_assign.get("test_id")):
        return None
    tid = _norm(raw_assign.get("test_id"))
    url = reverse("panels:student_tests") if viewer_role == "STUDENT" else reverse("panels:teacher_test_grade", args=[tid])
    return {"test_id": tid, "title": _norm(raw_assign.get("title") or "Course Test"), "test_type": _norm(raw_assign.get("test_type") or "Quiz"), "due_date": _norm(raw_assign.get("due_date")), "max_marks": raw_assign.get("max_marks", 100), "url": url}


def list_group_messages(group_id, session_user, since_iso=""):
    gid = _norm(group_id).upper()
    if not _has_group_access(gid, session_user):
        return [], "You do not have access to this classroom chat."
    uid, viewer_role = _norm((session_user or {}).get("user_id")), _norm((session_user or {}).get("role") or "STUDENT").upper()
    query = {"$or": [{"group_id": gid}, {"course_code": gid}]}
    since_dt = _parse_iso_dt(since_iso)
    if since_dt is not None:
        query["$and"] = [{"$or": [{"created_at": {"$gt": since_dt}}, {"updated_at": {"$gt": since_dt}}]}]
    docs = list(classroom_messages_col().find(query, {"_id": 0}).sort("created_at", 1))
    profiles = _load_sender_profiles([_norm(d.get("sender_user_id")) for d in docs], _sem_map())
    out = []
    for d in docs:
        if uid and uid in [str(x) for x in (d.get("deleted_for") or [])]:
            continue
        sender_uid = _norm(d.get("sender_user_id"))
        is_mine, deleted_all = bool(uid and sender_uid == uid), bool(d.get("deleted_for_all"))
        profile = profiles.get(sender_uid) or {"user_id": sender_uid, "student_id": _norm(d.get("sender_student_id")), "full_name": _norm(d.get("sender_name") or "User"), "role": _norm(d.get("sender_role") or "STUDENT").upper(), "email": _norm(d.get("sender_email")), "semester_label": "-"}
        created_iso, created_str = _format_created_at(d.get("created_at"))
        out.append({
            "msg_id": _norm(d.get("msg_id")),
            "group_id": gid,
            "msg_type": "DELETED" if deleted_all else _norm(d.get("msg_type") or "TEXT").upper(),
            "text": ("You deleted this message" if is_mine else "This message was deleted") if deleted_all else _norm(d.get("text")),
            "image_url": "" if deleted_all else _norm(d.get("image_url")),
            "audio_url": "" if deleted_all else _norm(d.get("audio_url")),
            "poll": None if deleted_all else _format_poll(d.get("poll"), uid),
            "assignment": None if deleted_all else _assignment_link(d.get("assignment"), viewer_role),
            "edited": bool(d.get("edited")) and not deleted_all,
            "deleted_for_all": deleted_all,
            "is_mine": is_mine,
            "sender_profile": profile,
            "created_at_iso": created_iso,
            "created_at_str": created_str,
        })
    return out, None


def send_group_message(group_id, session_user, text="", image_file=None, audio_file=None, poll_question="", poll_options=None):
    gid = _norm(group_id).upper()
    if not _has_group_access(gid, session_user):
        return None, "You do not have access to this classroom chat."
    clean_text, clean_q = _norm(text), _norm(poll_question)
    clean_opts = [_norm(o) for o in (poll_options or []) if _norm(o)]
    if clean_q and len(clean_opts) < 2:
        return None, "Polls require a question and at least 2 options."
    image_url, img_err = _save_chat_media(image_file)
    if img_err:
        return None, img_err
    audio_url, aud_err = _save_chat_media(audio_file)
    if aud_err:
        return None, aud_err
    if not clean_text and not image_url and not audio_url and not clean_q:
        return None, "Message cannot be empty."
    msg_type = "POLL" if clean_q else ("IMAGE" if image_url else ("AUDIO" if audio_url else "TEXT"))
    now, user = datetime.now(timezone.utc), (session_user if isinstance(session_user, dict) else {})
    doc = {
        "msg_id": f"MSG-{uuid.uuid4().hex[:10].upper()}", "group_id": gid, "course_code": gid,
        "sender_user_id": _norm(user.get("user_id")), "sender_student_id": _norm(user.get("student_id")),
        "sender_name": _norm(user.get("full_name") or "User"), "sender_role": _norm(user.get("role") or "STUDENT").upper(),
        "sender_email": _norm(user.get("email")), "msg_type": msg_type, "text": clean_text,
        "image_url": image_url, "audio_url": audio_url,
        "poll": {"question": clean_q, "options": clean_opts, "votes": {}} if clean_q else None,
        "assignment": None, "deleted_for": [], "deleted_for_all": False, "edited": False, "created_at": now, "updated_at": now,
    }
    classroom_messages_col().insert_one(doc)
    invalidate_cache("chat:")
    return doc["msg_id"], None


def edit_group_message(msg_id, new_text, session_user):
    mid, clean_text = _norm(msg_id), _norm(new_text)
    if not mid or not clean_text:
        return False, "Message ID and updated text are required."
    col = classroom_messages_col()
    doc = col.find_one({"msg_id": mid}, {"_id": 0})
    if not doc:
        return False, "Message not found."
    if doc.get("deleted_for_all"):
        return False, "Deleted messages cannot be edited."
    uid = _norm((session_user or {}).get("user_id"))
    if not uid or _norm(doc.get("sender_user_id")) != uid:
        return False, "You can only edit your own messages."
    col.update_one({"msg_id": mid}, {"$set": {"text": clean_text, "edited": True, "updated_at": datetime.now(timezone.utc)}})
    invalidate_cache("chat:")
    return True, None


def delete_group_message(msg_id, scope, session_user):
    mid, clean_scope = _norm(msg_id), _norm(scope or "me").lower()
    if not mid:
        return False, "Message ID is required."
    col = classroom_messages_col()
    doc = col.find_one({"msg_id": mid}, {"_id": 0})
    if not doc:
        return False, "Message not found."
    uid, role = _norm((session_user or {}).get("user_id")), _norm((session_user or {}).get("role")).upper()
    gid = _norm(doc.get("group_id") or doc.get("course_code")).upper()
    if not _has_group_access(gid, session_user):
        return False, "You do not have access to this message."
    now = datetime.now(timezone.utc)
    if clean_scope == "everyone":
        if _norm(doc.get("sender_user_id")) != uid and role != "ADMIN":
            return False, "Only the sender or an admin can delete for everyone."
        col.update_one({"msg_id": mid}, {"$set": {"deleted_for_all": True, "text": "", "image_url": "", "audio_url": "", "poll": None, "updated_at": now}})
    else:
        if not uid:
            return False, "User session required."
        col.update_one({"msg_id": mid}, {"$addToSet": {"deleted_for": uid}, "$set": {"updated_at": now}})
    invalidate_cache("chat:")
    return True, None


def vote_group_poll(msg_id, option_idx, session_user):
    mid, uid = _norm(msg_id), _norm((session_user or {}).get("user_id"))
    if not mid or not uid:
        return False, "Invalid poll vote request."
    col = classroom_messages_col()
    doc = col.find_one({"msg_id": mid}, {"_id": 0})
    if not doc or doc.get("deleted_for_all") or not isinstance(doc.get("poll"), dict):
        return False, "Poll not found."
    gid = _norm(doc.get("group_id") or doc.get("course_code")).upper()
    if not _has_group_access(gid, session_user):
        return False, "You do not have access to this poll."
    try:
        idx = int(option_idx)
    except (TypeError, ValueError):
        return False, "Invalid poll option."
    if idx < 0 or idx >= len(doc["poll"].get("options") or []):
        return False, "Selected poll option does not exist."
    col.update_one({"msg_id": mid}, {"$set": {f"poll.votes.{uid}": idx, "updated_at": datetime.now(timezone.utc)}})
    invalidate_cache("chat:")
    return True, None
