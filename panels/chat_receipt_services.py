import os
import re
import uuid
from pathlib import Path
from django.conf import settings
from core.cloudinary_services import ALLOWED_IMAGE_EXTS
from core.db import classroom_messages_col, courses_col, student_records_col, users_col

MAX_CHAT_FILE_BYTES = 10 * 1024 * 1024
ALLOWED_CHAT_DOC_EXTS = {".pdf", ".csv", ".txt", ".docx", ".doc"}
ALLOWED_CHAT_AUDIO_EXTS = {".webm", ".ogg", ".mp3", ".wav", ".m4a"}


def _norm(val):
    return str(val or "").strip()


def file_size_bytes(file_obj):
    size = getattr(file_obj, "size", None)
    if size is not None:
        return int(size)
    if hasattr(file_obj, "seek") and hasattr(file_obj, "tell"):
        pos = file_obj.tell()
        file_obj.seek(0, os.SEEK_END)
        end = file_obj.tell()
        file_obj.seek(pos)
        return int(end)
    return 0


def validate_chat_media(file_obj, allowed_exts=None):
    if not file_obj or not getattr(file_obj, "name", ""):
        return "", 0, False, None
    orig_name = Path(str(file_obj.name)).name
    ext = os.path.splitext(orig_name)[1].lower()
    valid_exts = allowed_exts or (ALLOWED_IMAGE_EXTS | ALLOWED_CHAT_DOC_EXTS | ALLOWED_CHAT_AUDIO_EXTS)
    if ext not in valid_exts:
        return "", 0, False, f"Unsupported file type ({ext or 'unknown'}). Allowed: images, PDF, CSV, TXT, DOCX."
    fsize = file_size_bytes(file_obj)
    if fsize <= 0:
        return "", 0, False, "Selected file is empty."
    if fsize > MAX_CHAT_FILE_BYTES:
        return "", 0, False, "File size exceeds the 10 MB limit."
    return orig_name, fsize, ext in ALLOWED_IMAGE_EXTS, None


def save_chat_media(file_obj, allowed_exts=None, subfolder="chat", upload_fn=None):
    if not file_obj or not getattr(file_obj, "name", ""):
        return "", "", 0, False, None
    orig_name, fsize, is_image, val_err = validate_chat_media(file_obj, allowed_exts)
    if val_err:
        return "", "", 0, False, val_err
    if upload_fn is not None:
        url, _name, _img, err = upload_fn(file_obj, folder=f"edupredict/{subfolder}", max_bytes=MAX_CHAT_FILE_BYTES)
        if url:
            return url, orig_name, fsize, is_image, None
        if err and err != "not_configured" and any(k in err.lower() for k in ("unsupported", "empty", "exceeds", "choose a file")):
            return "", "", 0, False, err
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", orig_name).strip("_") or "media"
    upload_dir = Path(settings.BASE_DIR) / "static" / "uploads" / subfolder
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex[:8]}_{safe_name}"
    if hasattr(file_obj, "seek"):
        file_obj.seek(0)
    with (upload_dir / stored_name).open("wb") as fh:
        for chunk in file_obj.chunks():
            fh.write(chunk)
    return f"/static/uploads/{subfolder}/{stored_name}", orig_name, fsize, is_image, None


def normalize_media_list(raw_list, fallback_url="", fallback_name="", fallback_size=0, is_image=False):
    items = []
    if isinstance(raw_list, list):
        for entry in raw_list:
            if not isinstance(entry, dict):
                continue
            url = _norm(entry.get("url"))
            if not url:
                continue
            items.append({
                "url": url,
                "name": _norm(entry.get("name") or ("image" if is_image else "attachment")),
                "size": int(entry.get("size") or 0),
            })
    if not items and _norm(fallback_url):
        items.append({
            "url": _norm(fallback_url),
            "name": _norm(fallback_name or ("image" if is_image else "attachment")),
            "size": int(fallback_size or 0),
        })
    return items


def _member_entry(u):
    return {
        "user_id": _norm(u.get("user_id")),
        "full_name": _norm(u.get("full_name") or "Member"),
        "role": _norm(u.get("role") or "STUDENT").upper(),
        "student_id": _norm(u.get("student_id")),
        "email": _norm(u.get("email")),
    }


def get_group_members(gid):
    code = _norm(gid).upper()
    if not code:
        return []
    course = courses_col().find_one({"course_code": code}, {"_id": 0}) or {}
    c_sem = _norm(course.get("semester_id"))
    inst_id = _norm(course.get("instructor_id"))
    inst_email = _norm(course.get("instructor_email")).lower()
    inst_name = _norm(course.get("instructor")).lower()

    rec_sids = set()
    for r in student_records_col().find({"course_code": code, "is_training_dataset": {"$ne": True}}, {"_id": 0, "student_id": 1}):
        sid = _norm(r.get("student_id"))
        if sid:
            rec_sids.add(sid)

    members = {}
    proj = {"_id": 0, "user_id": 1, "student_id": 1, "full_name": 1, "role": 1, "email": 1, "semester_id": 1, "status": 1}
    for u in users_col().find({}, proj):
        uid = _norm(u.get("user_id"))
        if not uid or _norm(u.get("status") or "ACTIVE").upper() == "INACTIVE":
            continue
        urole = _norm(u.get("role") or "STUDENT").upper()
        if urole == "STUDENT":
            usid = _norm(u.get("student_id"))
            usem = _norm(u.get("semester_id"))
            if (c_sem and usem == c_sem) or (usid and usid in rec_sids):
                members[uid] = _member_entry(u)
        elif urole == "TEACHER":
            uemail = _norm(u.get("email")).lower()
            uname = _norm(u.get("full_name")).lower()
            if (inst_id and uid == inst_id) or (inst_email and uemail == inst_email) or (inst_name and uname == inst_name):
                members[uid] = _member_entry(u)

    return sorted(members.values(), key=lambda m: (0 if m["role"] == "TEACHER" else 1, m["full_name"].lower()))


def mark_messages_read(docs, uid):
    clean_uid = _norm(uid)
    if not clean_uid or not docs:
        return
    unread_ids = []
    for d in docs:
        mid = _norm(d.get("msg_id"))
        readers = [str(x).strip() for x in (d.get("read_by") or []) if str(x).strip()]
        if mid and clean_uid not in readers:
            unread_ids.append(mid)
            readers.append(clean_uid)
            d["read_by"] = readers
    if not unread_ids:
        return
    col = classroom_messages_col()
    if hasattr(col, "update_many"):
        col.update_many({"msg_id": {"$in": unread_ids}}, {"$addToSet": {"read_by": clean_uid}})
    else:
        for mid in unread_ids:
            col.update_one({"msg_id": mid}, {"$addToSet": {"read_by": clean_uid}})


def build_message_receipts(doc, group_members, extra_profiles, viewer_role):
    sender_uid = _norm(doc.get("sender_user_id"))
    readers = []
    seen_set = set()
    for x in (doc.get("read_by") or []):
        rx = _norm(x)
        if rx and rx not in seen_set:
            seen_set.add(rx)
            readers.append(rx)
    other_readers = [r for r in readers if r != sender_uid]
    tick_state = "double_blue" if len(other_readers) >= 1 else "single"

    if _norm(viewer_role).upper() not in ("TEACHER", "ADMIN"):
        return tick_state, None

    member_map = {m["user_id"]: m for m in (group_members or []) if m.get("user_id")}
    seen_by = []
    unseen_by = []
    for uid in other_readers:
        entry = member_map.get(uid) or extra_profiles.get(uid)
        if entry:
            seen_by.append({
                "user_id": uid,
                "full_name": _norm(entry.get("full_name") or "Member"),
                "role": _norm(entry.get("role") or "STUDENT").upper(),
                "student_id": _norm(entry.get("student_id")),
                "email": _norm(entry.get("email")),
            })
        else:
            seen_by.append({"user_id": uid, "full_name": uid, "role": "MEMBER", "student_id": "", "email": ""})

    for m in (group_members or []):
        muid = m.get("user_id")
        if not muid or muid == sender_uid or muid in seen_set:
            continue
        unseen_by.append(m)

    return tick_state, {"seen_by": seen_by, "unseen_by": unseen_by}
