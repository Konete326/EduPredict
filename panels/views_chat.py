import json
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import NoReverseMatch, reverse
from core.decorators import role_required
from panels.chat_services import (
    delete_group_message,
    edit_group_message,
    get_user_chat_groups,
    list_group_messages,
    send_group_message,
    toggle_group_active,
    update_group_settings,
    vote_group_poll,
)
from panels.staff_chat_services import (
    delete_staff_message,
    edit_staff_message,
    get_staff_chat_groups,
    list_staff_messages,
    send_staff_message,
    vote_staff_poll,
)


def _no_cache(response):
    response["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response["Pragma"] = "no-cache"
    return response


def _parse_payload(request):
    content_type = str(request.content_type or "").lower()
    if "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type:
        try:
            return request.POST, None
        except Exception:
            return None, "Uploaded payload exceeds the maximum allowed size."
    if "application/json" in content_type or (not request.POST and not request.FILES):
        try:
            raw = request.body.decode("utf-8") if request.body else "{}"
            parsed = json.loads(raw or "{}")
            return parsed if isinstance(parsed, dict) else {}, None
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None, "Invalid JSON payload."
        except Exception:
            return None, "Uploaded payload exceeds the maximum allowed size."
    return request.POST, None


def _extract_poll_options(payload, request):
    raw_opts = payload.get("poll_options")
    if isinstance(raw_opts, list):
        return raw_opts
    if hasattr(request.POST, "getlist"):
        listed = request.POST.getlist("poll_options")
        if len(listed) > 1:
            return listed
    if isinstance(raw_opts, str) and raw_opts.strip():
        try:
            parsed = json.loads(raw_opts)
            if isinstance(parsed, list):
                return parsed
        except ValueError:
            return [x.strip() for x in raw_opts.splitlines() if x.strip()]
    return []


def _resolve_api_url(is_staff_chat):
    if not is_staff_chat:
        return reverse("panels:classroom_chat_api")
    try:
        return reverse("panels:staff_chat_api")
    except NoReverseMatch:
        return "/panels/staff-chat/api/"


def _render_chat_page(request, is_staff_chat=False):
    user = request.session.get("user") or {}
    role = str(user.get("role") or "STUDENT").strip().upper()
    uid = str(user.get("user_id") or "").strip()
    groups_fn = get_staff_chat_groups if is_staff_chat else get_user_chat_groups
    list_fn = list_staff_messages if is_staff_chat else list_group_messages
    groups, db_error = [], None
    try:
        groups = groups_fn(user)
    except Exception as exc:
        db_error = str(exc)

    req_gid = str(request.GET.get("group_id") or "").strip().upper()
    selected_group = next((g for g in groups if g["group_id"] == req_gid), None) or (groups[0] if groups else None)
    selected_gid = selected_group["group_id"] if selected_group else ""

    messages_list = []
    if selected_gid and not db_error:
        try:
            messages_list, msg_err = list_fn(selected_gid, user)
            if msg_err:
                db_error = msg_err
        except Exception as exc:
            db_error = str(exc)

    return _no_cache(render(
        request,
        "panels/classroom_chat.html",
        {
            "page_title": "Staff Chat" if is_staff_chat else "Class Chat",
            "is_staff_chat": is_staff_chat,
            "chat_api_url": _resolve_api_url(is_staff_chat),
            "active_role": role,
            "groups": groups,
            "selected_group": selected_group,
            "selected_group_id": selected_gid,
            "messages_list": messages_list,
            "messages_json": json.dumps(messages_list),
            "groups_json": json.dumps(groups),
            "current_user_id": uid,
            "current_user_role": role,
            "db_error": db_error,
        },
    ))


def _handle_chat_api(request, is_staff_chat=False):
    user = request.session.get("user") or {}
    groups_fn = get_staff_chat_groups if is_staff_chat else get_user_chat_groups
    list_fn = list_staff_messages if is_staff_chat else list_group_messages
    send_fn = send_staff_message if is_staff_chat else send_group_message
    edit_fn = edit_staff_message if is_staff_chat else edit_group_message
    del_fn = delete_staff_message if is_staff_chat else delete_group_message
    vote_fn = vote_staff_poll if is_staff_chat else vote_group_poll

    if request.method == "GET":
        gid = str(request.GET.get("group_id") or "").strip().upper()
        since_iso = str(request.GET.get("since") or "").strip()
        try:
            groups = groups_fn(user)
            if not gid and groups:
                gid = groups[0]["group_id"]
            if not gid:
                return _no_cache(JsonResponse({"ok": True, "group_id": "", "groups": groups, "messages": []}))
            msgs, err = list_fn(gid, user, since_iso=since_iso)
            if err:
                return _no_cache(JsonResponse({"ok": False, "error": err}, status=403))
            return _no_cache(JsonResponse({"ok": True, "group_id": gid, "groups": groups, "messages": msgs}))
        except Exception as exc:
            return _no_cache(JsonResponse({"ok": False, "error": str(exc)}, status=500))

    if request.method != "POST":
        return _no_cache(JsonResponse({"ok": False, "error": "Method not allowed."}, status=405))

    payload, parse_err = _parse_payload(request)
    if parse_err:
        return _no_cache(JsonResponse({"ok": False, "error": parse_err}, status=400))

    action = str(payload.get("action") or "send").strip().lower()
    gid = str(payload.get("group_id") or "").strip().upper()
    try:
        if action in ("send", "poll"):
            poll_q = str(payload.get("poll_question") or "").strip()
            poll_opts = _extract_poll_options(payload, request) if poll_q else []
            image_files = list(request.FILES.getlist("images"))
            single_image = request.FILES.get("image")
            if single_image and single_image not in image_files:
                image_files.append(single_image)
            doc_files = list(request.FILES.getlist("files"))
            for key in ("file", "document"):
                single_doc = request.FILES.get(key)
                if single_doc and single_doc not in doc_files:
                    doc_files.append(single_doc)
            msg_id, err = send_fn(
                gid, user, text=payload.get("text") or "", audio_file=request.FILES.get("audio"),
                poll_question=poll_q, poll_options=poll_opts, reply_to_id=payload.get("reply_to_id") or "",
                image_files=image_files, doc_files=doc_files,
            )
            if err:
                status = 403 if any(k in err.lower() for k in ("deactivated", "access", "required")) else 400
                return _no_cache(JsonResponse({"ok": False, "error": err}, status=status))
            msgs, _ = list_fn(gid, user)
            return _no_cache(JsonResponse({"ok": True, "msg_id": msg_id, "group_id": gid, "messages": msgs}))

        if action == "update_group" and not is_staff_chat:
            updated_group, err = update_group_settings(gid, user, group_name=payload.get("group_name") or "", dp_file=request.FILES.get("group_dp"))
            if err:
                status = 403 if any(k in err.lower() for k in ("only teachers or admins", "access")) else 400
                return _no_cache(JsonResponse({"ok": False, "error": err}, status=status))
            return _no_cache(JsonResponse({"ok": True, "group_id": gid, "group": updated_group, "groups": get_user_chat_groups(user)}))

        if action == "toggle_group_active" and not is_staff_chat:
            raw_active = payload.get("chat_active")
            active_val = None if raw_active is None else (str(raw_active).lower() not in ("0", "false", "no"))
            updated_group, err = toggle_group_active(gid, user, active=active_val)
            if err:
                status = 403 if any(k in err.lower() for k in ("only admins", "access")) else 400
                return _no_cache(JsonResponse({"ok": False, "error": err}, status=status))
            return _no_cache(JsonResponse({"ok": True, "group_id": gid, "group": updated_group, "groups": get_user_chat_groups(user)}))

        if action == "edit":
            ok, err = edit_fn(payload.get("msg_id"), payload.get("text") or "", user)
            return _no_cache(JsonResponse({"ok": True, "msg_id": payload.get("msg_id")}) if ok else JsonResponse({"ok": False, "error": err}, status=400))

        if action == "delete":
            ok, err = del_fn(payload.get("msg_id"), payload.get("scope") or "me", user)
            return _no_cache(JsonResponse({"ok": True, "msg_id": payload.get("msg_id")}) if ok else JsonResponse({"ok": False, "error": err}, status=400))

        if action == "vote":
            ok, err = vote_fn(payload.get("msg_id"), payload.get("option_idx"), user)
            if not ok:
                status = 403 if any(k in str(err or "").lower() for k in ("deactivated", "access")) else 400
                return _no_cache(JsonResponse({"ok": False, "error": err}, status=status))
            return _no_cache(JsonResponse({"ok": True, "msg_id": payload.get("msg_id")}))

        return _no_cache(JsonResponse({"ok": False, "error": "Unsupported chat action."}, status=400))
    except Exception as exc:
        return _no_cache(JsonResponse({"ok": False, "error": str(exc)}, status=500))


@role_required(["STUDENT", "TEACHER", "ADMIN"])
def classroom_chat_view(request):
    return _render_chat_page(request, is_staff_chat=False)


@role_required(["STUDENT", "TEACHER", "ADMIN"])
def classroom_chat_api(request):
    return _handle_chat_api(request, is_staff_chat=False)


@role_required(["ADMIN", "TEACHER", "ANALYST"])
def staff_chat_view(request):
    return _render_chat_page(request, is_staff_chat=True)


@role_required(["ADMIN", "TEACHER", "ANALYST"])
def staff_chat_api(request):
    return _handle_chat_api(request, is_staff_chat=True)
