import json
from django.contrib import messages
from django.contrib.messages.api import MessageFailure
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from core.db import check_db_health, users_col
from core.decorators import login_required_custom
from core.theme_services import get_user_theme_prefs, save_user_theme_prefs, update_user_profile_data


def _parse_payload(request):
    content_type = str(request.content_type or request.META.get("CONTENT_TYPE") or "").strip().lower()
    is_json = content_type.startswith("application/json")
    if is_json:
        try:
            body = request.body.decode("utf-8") if request.body else "{}"
            parsed = json.loads(body or "{}")
            return (parsed if isinstance(parsed, dict) else {}), True
        except Exception:
            return {}, True
    return {key: request.POST.get(key) for key in request.POST}, False


def _flash(level_fn, request, text):
    try:
        level_fn(request, text)
    except MessageFailure:
        pass


def theme_preferences_view(request):
    if request.method == "GET":
        return JsonResponse({"ok": True, "theme_prefs": get_user_theme_prefs(request)})
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Method not allowed."}, status=405)

    payload, is_json = _parse_payload(request)
    prefs = save_user_theme_prefs(request, payload)
    x_req = str(request.headers.get("X-Requested-With") or request.META.get("HTTP_X_REQUESTED_WITH") or "").strip()
    if is_json or x_req == "EduPredict-Theme":
        return JsonResponse({"ok": True, "theme_prefs": prefs})

    action = str(payload.get("action") or "").strip().lower()
    _flash(messages.success, request, "Theme settings reset to default." if action == "reset" else "Theme settings updated.")
    referer = request.META.get("HTTP_REFERER", "")
    next_url = referer if referer and url_has_allowed_host_and_scheme(referer, allowed_hosts={request.get_host()}) else "/"
    return redirect(next_url)


@login_required_custom
def user_profile_view(request):
    if request.method == "POST":
        try:
            updated, err = update_user_profile_data(request, request.POST)
            if err or updated is None:
                _flash(messages.error, request, err or "Could not update profile.")
            else:
                _flash(messages.success, request, "Your profile has been updated.")
        except Exception as exc:
            _flash(messages.error, request, f"Profile update failed: {exc}")
        return redirect("panels:user_profile")

    session_user = dict(request.session.get("user") or {})
    uid = str(session_user.get("user_id") or "").strip()
    role = str(session_user.get("role") or "").strip().upper()
    merged = dict(session_user)
    if uid:
        try:
            if check_db_health().get("connected"):
                db_doc = users_col().find_one({"user_id": uid}, {"_id": 0, "password_hash": 0})
                if isinstance(db_doc, dict):
                    merged.update(db_doc)
        except Exception:
            pass
    resolved_role = str(merged.get("role") or role).strip().upper()
    profile_user = {
        "user_id": str(merged.get("user_id") or uid),
        "student_id": str(merged.get("student_id") or ""),
        "full_name": str(merged.get("full_name") or ""),
        "email": str(merged.get("email") or ""),
        "role": resolved_role,
        "department": str(merged.get("department") or "General"),
        "batch": str(merged.get("batch") or "ALL"),
        "phone": str(merged.get("phone") or ""),
        "bio": str(merged.get("bio") or ""),
        "is_active": bool(merged.get("is_active", True)),
    }
    return render(
        request,
        "panels/user_profile.html",
        {
            "page_title": "My Profile",
            "active_role": resolved_role or role,
            "profile_user": profile_user,
        },
    )
