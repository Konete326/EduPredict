import uuid
from datetime import datetime, timezone
from core.cloudinary_services import ALLOWED_IMAGE_EXTS, upload_academic_attachment
from core.db import classroom_messages_col, get_cached, invalidate_cache, users_col
from panels.chat_receipt_services import (
    ALLOWED_CHAT_AUDIO_EXTS,
    ALLOWED_CHAT_DOC_EXTS,
    build_message_receipts,
    mark_messages_read,
    normalize_media_list,
    save_chat_media,
    validate_chat_media,
)
from panels.chat_services import (
    _build_reply_snapshot,
    _format_created_at,
    _format_poll,
    _load_sender_profiles,
    _norm,
    _parse_iso_dt,
    _sem_map,
)

STAFF_ROLES = ("ADMIN", "TEACHER", "ANALYST")

STAFF_CHANNELS = [
    {"group_id": "STAFF-ALL", "title": "All Staff Coordination", "subtitle": "Admin · Teachers · Analysts"},
    {"group_id": "FACULTY-ML", "title": "Faculty & ML Sync", "subtitle": "Teachers · Analysts · Admin"},
]

STAFF_CHANNEL_IDS = {c["group_id"] for c in STAFF_CHANNELS}


def is_staff_user(session_user):
    return _norm((session_user or {}).get("role")).upper() in STAFF_ROLES


def get_staff_channel_members():
    members = []
    proj = {"_id": 0, "user_id": 1, "student_id": 1, "full_name": 1, "role": 1, "email": 1, "status": 1}
    for u in users_col().find({"role": {"$in": list(STAFF_ROLES)}}, proj):
        uid = _norm(u.get("user_id"))
        if not uid or _norm(u.get("status") or "ACTIVE").upper() == "INACTIVE":
            continue
        members.append({
            "user_id": uid,
            "full_name": _norm(u.get("full_name") or "Staff"),
            "role": _norm(u.get("role") or "TEACHER").upper(),
            "student_id": _norm(u.get("student_id")),
            "email": _norm(u.get("email")),
        })
    order = {"ADMIN": 0, "TEACHER": 1, "ANALYST": 2}
    return sorted(members, key=lambda m: (order.get(m["role"], 3), m["full_name"].lower()))


def get_staff_chat_groups(session_user):
    if not is_staff_user(session_user):
        return []
    def _build():
        cnt = len(get_staff_channel_members())
        return [
            {
                "group_id": ch["group_id"],
                "title": ch["title"],
                "dp_url": "",
                "semester_id": "",
                "semester_label": ch["subtitle"],
                "teacher_name": "Staff Channel",
                "member_count": cnt,
                "chat_active": True,
            }
            for ch in STAFF_CHANNELS
        ]
    return get_cached("staff_chat:groups", _build, ttl=20.0)


def _has_staff_access(channel_id, session_user):
    cid = _norm(channel_id).upper()
    return is_staff_user(session_user) and cid in STAFF_CHANNEL_IDS


def list_staff_messages(channel_id, session_user, since_iso=""):
    cid = _norm(channel_id).upper()
    if not _has_staff_access(cid, session_user):
        return [], "Staff access is required for this channel."
    uid = _norm((session_user or {}).get("user_id"))
    query = {"group_id": cid}
    since_dt = _parse_iso_dt(since_iso)
    if since_dt is not None:
        query["$and"] = [{"$or": [{"created_at": {"$gt": since_dt}}, {"updated_at": {"$gt": since_dt}}]}]
    docs = list(classroom_messages_col().find(query, {"_id": 0}).sort("created_at", 1))
    if uid and any(_norm(d.get("msg_id")) and uid not in [str(x).strip() for x in (d.get("read_by") or [])] for d in docs):
        mark_messages_read(docs, uid)
    profile_ids = [_norm(d.get("sender_user_id")) for d in docs]
    for d in docs:
        profile_ids.extend([_norm(x) for x in (d.get("read_by") or [])])
    profiles = _load_sender_profiles(profile_ids, _sem_map())
    members = get_staff_channel_members()
    out = []
    for d in docs:
        if uid and uid in [str(x) for x in (d.get("deleted_for") or [])]:
            continue
        sender_uid = _norm(d.get("sender_user_id"))
        is_mine, deleted_all = bool(uid and sender_uid == uid), bool(d.get("deleted_for_all"))
        profile = profiles.get(sender_uid) or {"user_id": sender_uid, "student_id": "", "full_name": _norm(d.get("sender_name") or "Staff"), "role": _norm(d.get("sender_role") or "TEACHER").upper(), "email": _norm(d.get("sender_email")), "semester_label": "-"}
        created_iso, created_str = _format_created_at(d.get("created_at"))
        updated_iso, _ = _format_created_at(d.get("updated_at") or d.get("created_at"))
        images_list = [] if deleted_all else normalize_media_list(d.get("images"), d.get("image_url"), is_image=True)
        files_list = [] if deleted_all else normalize_media_list(d.get("files"), d.get("file_url"), d.get("file_name"), d.get("file_size"), is_image=False)
        tick_state, read_receipts = build_message_receipts(d, members, profiles, "ADMIN")
        out.append({
            "msg_id": _norm(d.get("msg_id")), "group_id": cid,
            "msg_type": "DELETED" if deleted_all else _norm(d.get("msg_type") or "TEXT").upper(),
            "text": ("You deleted this message" if is_mine else "This message was deleted") if deleted_all else _norm(d.get("text")),
            "image_url": images_list[0]["url"] if images_list else "",
            "file_url": files_list[0]["url"] if files_list else "",
            "file_name": files_list[0]["name"] if files_list else "",
            "file_size": files_list[0]["size"] if files_list else 0,
            "images": images_list, "files": files_list,
            "audio_url": "" if deleted_all else _norm(d.get("audio_url")),
            "poll": None if deleted_all else _format_poll(d.get("poll"), uid),
            "assignment": None, "reply_to": None if deleted_all else d.get("reply_to"),
            "tick_state": tick_state, "read_receipts": read_receipts,
            "edited": bool(d.get("edited")) and not deleted_all, "deleted_for_all": deleted_all,
            "is_mine": is_mine, "sender_profile": profile,
            "created_at_iso": created_iso, "updated_at_iso": updated_iso, "created_at_str": created_str,
        })
    return out, None


def send_staff_message(channel_id, session_user, text="", image_file=None, doc_file=None, audio_file=None, poll_question="", poll_options=None, reply_to_id="", image_files=None, doc_files=None):
    cid = _norm(channel_id).upper()
    if not _has_staff_access(cid, session_user):
        return None, "Staff access is required for this channel."
    clean_text, clean_q = _norm(text), _norm(poll_question)
    clean_opts = [_norm(o) for o in (poll_options or []) if _norm(o)]
    if clean_q and len(clean_opts) < 2:
        return None, "Polls require a question and at least 2 options."
    all_images = [f for f in (list(image_files or []) + ([image_file] if image_file else [])) if f]
    all_docs = [f for f in (list(doc_files or []) + ([doc_file] if doc_file else [])) if f]
    if len(all_images) > 5 or len(all_docs) > 5:
        return None, "You can upload a maximum of 5 items per message."
    for img_f in all_images:
        _, _, _, val_err = validate_chat_media(img_f, ALLOWED_IMAGE_EXTS)
        if val_err:
            return None, val_err
    for doc_f in all_docs:
        _, _, _, val_err = validate_chat_media(doc_f, ALLOWED_IMAGE_EXTS | ALLOWED_CHAT_DOC_EXTS)
        if val_err:
            return None, val_err
    if audio_file:
        _, _, _, aud_val_err = validate_chat_media(audio_file, ALLOWED_CHAT_AUDIO_EXTS)
        if aud_val_err:
            return None, aud_val_err
    images, files = [], []
    for img_f in all_images:
        url, orig_name, fsize, _is_img, err = save_chat_media(img_f, ALLOWED_IMAGE_EXTS, "staff_chat", upload_fn=upload_academic_attachment)
        if err:
            return None, err
        images.append({"url": url, "name": orig_name, "size": fsize})
    for doc_f in all_docs:
        url, orig_name, fsize, is_img, err = save_chat_media(doc_f, ALLOWED_IMAGE_EXTS | ALLOWED_CHAT_DOC_EXTS, "staff_chat", upload_fn=upload_academic_attachment)
        if err:
            return None, err
        if is_img and not all_images and len(images) < 5 and len(all_docs) == 1 and doc_file is not None and not doc_files:
            images.append({"url": url, "name": orig_name, "size": fsize})
        else:
            files.append({"url": url, "name": orig_name, "size": fsize})
    audio_url, _an, _as, _ai, aud_err = save_chat_media(audio_file, ALLOWED_CHAT_AUDIO_EXTS, "staff_chat", upload_fn=upload_academic_attachment)
    if aud_err:
        return None, aud_err
    if not clean_text and not images and not files and not audio_url and not clean_q:
        return None, "Message cannot be empty."
    msg_type = "POLL" if clean_q else ("IMAGE" if images else ("FILE" if files else ("AUDIO" if audio_url else "TEXT")))
    now, user = datetime.now(timezone.utc), (session_user if isinstance(session_user, dict) else {})
    sender_uid = _norm(user.get("user_id"))
    doc = {
        "msg_id": f"SMSG-{uuid.uuid4().hex[:10].upper()}", "group_id": cid, "course_code": "", "channel_scope": "STAFF",
        "sender_user_id": sender_uid, "sender_student_id": "",
        "sender_name": _norm(user.get("full_name") or "Staff"), "sender_role": _norm(user.get("role") or "TEACHER").upper(),
        "sender_email": _norm(user.get("email")), "msg_type": msg_type, "text": clean_text,
        "image_url": images[0]["url"] if images else "", "file_url": files[0]["url"] if files else "",
        "file_name": files[0]["name"] if files else "", "file_size": files[0]["size"] if files else 0,
        "images": images, "files": files, "audio_url": audio_url,
        "read_by": [sender_uid] if sender_uid else [],
        "reply_to": _build_reply_snapshot(cid, reply_to_id),
        "poll": {"question": clean_q, "options": clean_opts, "votes": {}} if clean_q else None,
        "assignment": None, "deleted_for": [], "deleted_for_all": False, "edited": False, "created_at": now, "updated_at": now,
    }
    classroom_messages_col().insert_one(doc)
    invalidate_cache("staff_chat:")
    return doc["msg_id"], None


def edit_staff_message(msg_id, new_text, session_user):
    mid, clean_text = _norm(msg_id), _norm(new_text)
    if not mid or not clean_text or not is_staff_user(session_user):
        return False, "Message ID and updated text are required."
    col = classroom_messages_col()
    doc = col.find_one({"msg_id": mid, "group_id": {"$in": list(STAFF_CHANNEL_IDS)}}, {"_id": 0})
    if not doc or doc.get("deleted_for_all"):
        return False, "Message not found or deleted."
    uid = _norm((session_user or {}).get("user_id"))
    if not uid or _norm(doc.get("sender_user_id")) != uid:
        return False, "You can only edit your own messages."
    col.update_one({"msg_id": mid}, {"$set": {"text": clean_text, "edited": True, "updated_at": datetime.now(timezone.utc)}})
    invalidate_cache("staff_chat:")
    return True, None


def delete_staff_message(msg_id, scope, session_user):
    mid, clean_scope = _norm(msg_id), _norm(scope or "me").lower()
    if not mid or not is_staff_user(session_user):
        return False, "Message ID is required."
    col = classroom_messages_col()
    doc = col.find_one({"msg_id": mid, "group_id": {"$in": list(STAFF_CHANNEL_IDS)}}, {"_id": 0})
    if not doc:
        return False, "Message not found."
    uid, role = _norm((session_user or {}).get("user_id")), _norm((session_user or {}).get("role")).upper()
    now = datetime.now(timezone.utc)
    if clean_scope == "everyone":
        if _norm(doc.get("sender_user_id")) != uid and role != "ADMIN":
            return False, "Only the sender or an admin can delete for everyone."
        col.update_one({"msg_id": mid}, {"$set": {"deleted_for_all": True, "text": "", "image_url": "", "file_url": "", "file_name": "", "file_size": 0, "images": [], "files": [], "audio_url": "", "reply_to": None, "poll": None, "updated_at": now}})
    else:
        if not uid:
            return False, "User session required."
        col.update_one({"msg_id": mid}, {"$addToSet": {"deleted_for": uid}, "$set": {"updated_at": now}})
    invalidate_cache("staff_chat:")
    return True, None


def vote_staff_poll(msg_id, option_idx, session_user):
    mid, uid = _norm(msg_id), _norm((session_user or {}).get("user_id"))
    if not mid or not uid or not is_staff_user(session_user):
        return False, "Invalid poll vote request."
    col = classroom_messages_col()
    doc = col.find_one({"msg_id": mid, "group_id": {"$in": list(STAFF_CHANNEL_IDS)}}, {"_id": 0})
    if not doc or doc.get("deleted_for_all") or not isinstance(doc.get("poll"), dict):
        return False, "Poll not found."
    try:
        idx = int(option_idx)
    except (TypeError, ValueError):
        return False, "Invalid poll option."
    if idx < 0 or idx >= len(doc["poll"].get("options") or []):
        return False, "Selected poll option does not exist."
    col.update_one({"msg_id": mid}, {"$set": {f"poll.votes.{uid}": idx, "updated_at": datetime.now(timezone.utc)}})
    invalidate_cache("staff_chat:")
    return True, None
