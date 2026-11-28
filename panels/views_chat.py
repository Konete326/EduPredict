import json
from django.http import JsonResponse
from django.shortcuts import render
from core.decorators import role_required
from panels.chat_services import (
    delete_group_message,
    edit_group_message,
    get_user_chat_groups,
    list_group_messages,
    send_group_message,
    update_group_settings,
    vote_group_poll,
)


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


@role_required(["STUDENT", "TEACHER", "ADMIN"])
def classroom_chat_view(request):
    user = request.session.get("user") or {}
    role = str(user.get("role") or "STUDENT").strip().upper()
    uid = str(user.get("user_id") or "").strip()
    groups, db_error = [], None
    try:
        groups = get_user_chat_groups(user)
    except Exception as exc:
        db_error = str(exc)

    req_gid = str(request.GET.get("group_id") or "").strip().upper()
    selected_group = next((g for g in groups if g["group_id"] == req_gid), None)
    if selected_group is None and groups:
        selected_group = groups[0]
    selected_gid = selected_group["group_id"] if selected_group else ""

    messages_list = []
    if selected_gid and not db_error:
        try:
            messages_list, msg_err = list_group_messages(selected_gid, user)
            if msg_err:
                db_error = msg_err
        except Exception as exc:
            db_error = str(exc)

    return render(
        request,
        "panels/classroom_chat.html",
        {
            "page_title": "Class Chat",
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
    )


@role_required(["STUDENT", "TEACHER", "ADMIN"])
def classroom_chat_api(request):
    user = request.session.get("user") or {}
    if request.method == "GET":
        gid = str(request.GET.get("group_id") or "").strip().upper()
        since_iso = str(request.GET.get("since") or "").strip()
        try:
            groups = get_user_chat_groups(user)
            if not gid and groups:
                gid = groups[0]["group_id"]
            if not gid:
                return JsonResponse({"ok": True, "group_id": "", "groups": groups, "messages": []})
            msgs, err = list_group_messages(gid, user, since_iso=since_iso)
            if err:
                return JsonResponse({"ok": False, "error": err}, status=403)
            return JsonResponse({"ok": True, "group_id": gid, "groups": groups, "messages": msgs})
        except Exception as exc:
            return JsonResponse({"ok": False, "error": str(exc)}, status=500)

    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Method not allowed."}, status=405)

    payload, parse_err = _parse_payload(request)
    if parse_err:
        return JsonResponse({"ok": False, "error": parse_err}, status=400)

    action = str(payload.get("action") or "send").strip().lower()
    gid = str(payload.get("group_id") or "").strip().upper()
    try:
        if action in ("send", "poll"):
            poll_q = str(payload.get("poll_question") or "").strip()
            poll_opts = _extract_poll_options(payload, request) if poll_q else []
            msg_id, err = send_group_message(
                gid,
                user,
                text=payload.get("text") or "",
                image_file=request.FILES.get("image"),
                doc_file=request.FILES.get("file") or request.FILES.get("document"),
                audio_file=request.FILES.get("audio"),
                poll_question=poll_q,
                poll_options=poll_opts,
                reply_to_id=payload.get("reply_to_id") or "",
            )
            if err:
                return JsonResponse({"ok": False, "error": err}, status=400)
            msgs, _ = list_group_messages(gid, user)
            return JsonResponse({"ok": True, "msg_id": msg_id, "group_id": gid, "messages": msgs})

        if action == "update_group":
            updated_group, err = update_group_settings(
                gid,
                user,
                group_name=payload.get("group_name") or "",
                dp_file=request.FILES.get("group_dp"),
            )
            if err:
                status = 403 if "only teachers or admins" in err.lower() or "access" in err.lower() else 400
                return JsonResponse({"ok": False, "error": err}, status=status)
            groups = get_user_chat_groups(user)
            return JsonResponse({"ok": True, "group_id": gid, "group": updated_group, "groups": groups})

        if action == "edit":
            ok, err = edit_group_message(payload.get("msg_id"), payload.get("text") or "", user)
            if not ok:
                return JsonResponse({"ok": False, "error": err}, status=400)
            return JsonResponse({"ok": True, "msg_id": payload.get("msg_id")})

        if action == "delete":
            ok, err = delete_group_message(payload.get("msg_id"), payload.get("scope") or "me", user)
            if not ok:
                return JsonResponse({"ok": False, "error": err}, status=400)
            return JsonResponse({"ok": True, "msg_id": payload.get("msg_id")})

        if action == "vote":
            ok, err = vote_group_poll(payload.get("msg_id"), payload.get("option_idx"), user)
            if not ok:
                return JsonResponse({"ok": False, "error": err}, status=400)
            return JsonResponse({"ok": True, "msg_id": payload.get("msg_id")})

        return JsonResponse({"ok": False, "error": "Unsupported chat action."}, status=400)
    except Exception as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=500)
