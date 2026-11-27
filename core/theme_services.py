import uuid
from datetime import datetime, timezone
from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from pymongo.errors import DuplicateKeyError
from core.cloudinary_services import destroy_cloudinary_asset, upload_user_avatar
from core.db import invalidate_cache, notifications_col, password_requests_col, student_records_col, users_col
from panels.admin_audit_services import record_audit_log

APPEARANCE_MODES = (
    {"slug": "light", "label": "Light Mode"},
    {"slug": "dark", "label": "OLED Dark"},
)


def _shell(slug, label, dot_color, p_side, p_top, accent_sync, s_light, t_light, s_dark, t_dark, force_dark=False):
    return {
        "slug": slug, "label": label, "dot_color": dot_color, "preview_sidebar": p_side, "preview_topbar": p_top,
        "accent_sync": accent_sync, "sidebar_bg_light": s_light, "topbar_bg_light": t_light,
        "sidebar_bg_dark": s_dark, "topbar_bg_dark": t_dark, "force_dark_chrome": force_dark,
    }


SHELL_THEMES = (
    _shell("dark", "Dark", "#1e293b", "#0f172a", "#1e293b", "indigo", "#0f172a", "#1e293b", "#0d0e12", "#111217", True),
    _shell("red", "Red", "#dc2626", "#991b1b", "#dc2626", "crimson", "#fee2e2", "#fef0f0", "#1b0e12", "#221116"),
    _shell("dark-red", "Dark Red", "#991b1b", "#7f1d1d", "#991b1b", "crimson", "#7f1d1d", "#991b1b", "#1b0e12", "#221116", True),
    _shell("dark-green", "Dark Green", "#15803d", "#064e3b", "#065f46", "forest", "#064e3b", "#065f46", "#0b1a12", "#0f2218", True),
    _shell("green", "Green", "#10b981", "#047857", "#10b981", "emerald", "#d1fae5", "#e2f8ee", "#0b1d18", "#102620"),
    _shell("blue", "Blue", "#2563eb", "#1d4ed8", "#2563eb", "ocean", "#dbeafe", "#e8f0fe", "#0d0e12", "#111217"),
    _shell("white", "White", "#ffffff", "#f1f5f9", "#f8fafc", None, "#f1f5f9", "#f8fafc", "#111114", "#111217"),
)

BRAND_SWATCHES = (
    {"slug": "coral", "label": "Coral", "hex": "#e05a47", "hover": "#c94735", "soft_light": "#fdf2f0", "soft_dark": "rgba(224, 90, 71, 0.16)"},
    {"slug": "rose", "label": "Rose", "hex": "#db2777", "hover": "#be185d", "soft_light": "#fdf2f8", "soft_dark": "rgba(219, 39, 119, 0.16)"},
    {"slug": "teal", "label": "Teal", "hex": "#0d9488", "hover": "#0f766e", "soft_light": "#f0fdfa", "soft_dark": "rgba(13, 148, 136, 0.16)"},
    {"slug": "emerald", "label": "Emerald", "hex": "#10b981", "hover": "#059669", "soft_light": "#ecfdf5", "soft_dark": "rgba(16, 185, 129, 0.16)"},
    {"slug": "ocean", "label": "Ocean", "hex": "#2563eb", "hover": "#1d4ed8", "soft_light": "#eff6ff", "soft_dark": "rgba(37, 99, 235, 0.16)"},
    {"slug": "amber", "label": "Amber", "hex": "#d97706", "hover": "#b45309", "soft_light": "#fffbeb", "soft_dark": "rgba(217, 119, 6, 0.16)"},
    {"slug": "orange", "label": "Orange", "hex": "#ea580c", "hover": "#c2410c", "soft_light": "#fff7ed", "soft_dark": "rgba(234, 88, 12, 0.16)"},
    {"slug": "periwinkle", "label": "Periwinkle", "hex": "#6366f1", "hover": "#4f46e5", "soft_light": "#eef2ff", "soft_dark": "rgba(99, 102, 241, 0.16)"},
    {"slug": "indigo", "label": "Indigo", "hex": "#4f46e5", "hover": "#4338ca", "soft_light": "#eef2ff", "soft_dark": "rgba(79, 70, 229, 0.18)"},
    {"slug": "orchid", "label": "Orchid", "hex": "#a855f7", "hover": "#9333ea", "soft_light": "#faf5ff", "soft_dark": "rgba(168, 85, 247, 0.16)"},
    {"slug": "crimson", "label": "Crimson", "hex": "#dc2626", "hover": "#b91c1c", "soft_light": "#fef2f2", "soft_dark": "rgba(220, 38, 38, 0.16)"},
    {"slug": "forest", "label": "Forest", "hex": "#15803d", "hover": "#166534", "soft_light": "#f0fdf4", "soft_dark": "rgba(21, 128, 61, 0.16)"},
    {"slug": "violet", "label": "Violet", "hex": "#7e22ce", "hover": "#6b21a8", "soft_light": "#f5f3ff", "soft_dark": "rgba(126, 34, 206, 0.16)"},
)

def _preset(slug, label, cl, sl, el, tl, secl, ml, bl, cd, sd, ed, td, secd, md, bd, source="Studio", accent_slug="", shell_slug="", accent_hex="#2563eb"):
    return {
        "slug": slug, "label": label, "source": source, "accent_slug": accent_slug, "shell_slug": shell_slug, "accent_hex": accent_hex,
        "canvas_light": cl, "surface_light": sl, "elevated_light": el, "text_light": tl, "secondary_light": secl, "muted_light": ml, "border_light": bl,
        "canvas_dark": cd, "surface_dark": sd, "elevated_dark": ed, "text_dark": td, "secondary_dark": secd, "muted_dark": md, "border_dark": bd,
    }


SURFACE_PRESETS = (
    _preset("neutral", "Neutral", "#f8fafc", "#ffffff", "#f1f5f9", "#0f172a", "#475569", "#64748b", "#e2e8f0", "#09090b", "#111114", "#1b1b20", "#f4f4f5", "#d4d4d8", "#a1a1aa", "rgba(255, 255, 255, 0.08)"),
    _preset("butter", "Butter", "#fefce8", "#fffdf5", "#fef3c7", "#292524", "#57534e", "#78716c", "#fde68a", "#14120a", "#1e1a0f", "#2c2516", "#fef9c3", "#e7e5e4", "#a8a29e", "rgba(253, 230, 138, 0.14)"),
    _preset("matcha", "Matcha", "#f3faf4", "#fbfefb", "#e2f3e6", "#14261c", "#3f5a4a", "#647a6c", "#cbe5d2", "#09130d", "#101f16", "#192e21", "#ecfdf5", "#c8e0d2", "#8ba697", "rgba(167, 243, 208, 0.12)"),
    _preset("chocolate", "Chocolate", "#faf6f2", "#fffcf9", "#f1e8df", "#291d17", "#5c493e", "#7c685d", "#e4d5c7", "#140f0c", "#1f1713", "#2e221c", "#f5ebe4", "#d6c5b9", "#a38f82", "rgba(228, 213, 199, 0.12)"),
    _preset("stone", "Stone", "#f5f5f4", "#fafaf9", "#e7e5e4", "#1c1917", "#44403c", "#78716c", "#d6d3d1", "#0c0a09", "#1c1917", "#292524", "#fafaf9", "#d6d3d1", "#a8a29e", "rgba(255, 255, 255, 0.09)"),
    _preset("gothic", "Gothic", "#f4f4f6", "#fafafc", "#e4e4ec", "#18181b", "#3f3f46", "#71717a", "#d4d4dc", "#050508", "#0d0e14", "#181924", "#f4f4f5", "#d4d4d8", "#9496a6", "rgba(255, 255, 255, 0.09)"),
    _preset("meridian", "Meridian Blue", "#eef0f3", "#ffffff", "#e8eaee", "#181b21", "#3e4454", "#5a6072", "#c9cfd8", "#14171c", "#1c2027", "#232831", "#e6e9ef", "#cbd5e1", "#9097a6", "#353c48", "21st.dev", "ocean", "blue", "#3b608f"),
    _preset("harbor", "Harbor Blue", "#ffffff", "#f8fafc", "#f1f5f9", "#0f172a", "#334155", "#64748b", "#e2e8f0", "#0f172a", "#1e293b", "#334155", "#f8fafc", "#dce6f9", "#94a3b8", "#334155", "21st.dev", "indigo", "blue", "#194391"),
    _preset("claude-linen", "Claude Linen", "#faf9f5", "#ffffff", "#ede9de", "#3d3929", "#535146", "#83827d", "#dad9d4", "#262624", "#30302e", "#1b1b19", "#e5e5e2", "#c3c0b6", "#b7b5a9", "#3e3e38", "21st.dev", "coral", "white", "#c96442"),
    _preset("catppuccin", "Catppuccin", "#e4e8ef", "#ffffff", "#dee1e8", "#4e5069", "#5a5d78", "#6d7083", "#bcc1ce", "#11111b", "#181825", "#313244", "#cdd6f4", "#bac2de", "#a6adc8", "#45475a", "21st.dev", "violet", "dark", "#8839ef"),
    _preset("respec", "Respec Mint", "#fcfcfc", "#ffffff", "#ededed", "#171717", "#202020", "#525252", "#dfdfdf", "#121212", "#171717", "#242424", "#e2e8f0", "#cbd5e1", "#a2a2a2", "#292929", "21st.dev", "emerald", "green", "#10b981"),
    _preset("sage", "Sage Studio", "#fdfdfd", "#f5f8fb", "#e4eae1", "#080808", "#3b4636", "#687066", "#e7e7ee", "#070503", "#100d08", "#1e1a14", "#f9f8f7", "#e7e4df", "#928f8a", "#2f281b", "21st.dev", "forest", "dark-green", "#7f956a"),
)

_MODE_SLUGS = {item["slug"] for item in APPEARANCE_MODES}
_SHELL_MAP = {item["slug"]: item for item in SHELL_THEMES}
_SWATCH_MAP = {item["slug"]: item for item in BRAND_SWATCHES}
_PRESET_MAP = {item["slug"]: item for item in SURFACE_PRESETS}
_DENSITY_VALUES = {"comfortable", "compact"}
_VALID_ROLES = {"ADMIN", "TEACHER", "STUDENT", "ANALYST", "PORTAL"}
_PATH_ROLE_MAP = (("/admin-panel", "ADMIN"), ("/teacher-panel", "TEACHER"), ("/student-panel", "STUDENT"), ("/analyst-panel", "ANALYST"))
_PREF_KEYS = ("mode", "shell_theme", "accent", "preset", "density", "sync_shell")


def _parse_bool(value, default=True):
    if value is None:
        return default
    if isinstance(value, (bool, int, float)):
        return bool(value)
    cleaned = str(value).strip().lower()
    return True if cleaned in ("true", "1", "yes", "on") else (False if cleaned in ("false", "0", "no", "off") else default)


def _pick(source, key, allowed, default):
    val = str(source.get(key) or default).strip().lower()
    return val if val in allowed else default


def _resolve_theme_scope(request):
    _, user, uid = _session_user_ctx(request)
    uid = uid or "guest"
    raw_role = str(user.get("role") or "").strip().upper()
    if raw_role in _VALID_ROLES:
        return raw_role, uid
    path = str(getattr(request, "path", "") or "").strip()
    for prefix, mapped_role in _PATH_ROLE_MAP:
        if path.startswith(prefix):
            return mapped_role, uid
    return "PORTAL", uid


def get_theme_studio_catalog():
    return {"modes": [dict(i) for i in APPEARANCE_MODES], "shell_themes": [dict(i) for i in SHELL_THEMES], "swatches": [dict(i) for i in BRAND_SWATCHES], "presets": [dict(i) for i in SURFACE_PRESETS], "save_url": "/theme/preferences/"}


def normalize_theme_prefs(raw, role="PORTAL", user_id="guest"):
    source = raw if isinstance(raw, dict) else {}
    clean_role = str(role or "PORTAL").strip().upper() or "PORTAL"
    clean_uid = str(user_id or "guest").strip() or "guest"
    mode = _pick(source, "mode", _MODE_SLUGS, "light")
    shell_theme = _pick(source, "shell_theme", _SHELL_MAP, "green")
    accent = _pick(source, "accent", _SWATCH_MAP, "emerald")
    preset = _pick(source, "preset", _PRESET_MAP, "neutral")
    density = _pick(source, "density", _DENSITY_VALUES, "comfortable")
    sync_shell = _parse_bool(source.get("sync_shell"), default=True)
    shell_cfg, swatch_cfg, preset_cfg = _SHELL_MAP[shell_theme], _SWATCH_MAP[accent], _PRESET_MAP[preset]
    is_dark = mode == "dark"
    tokens = {
        "bg_canvas": preset_cfg["canvas_dark"] if is_dark else preset_cfg["canvas_light"],
        "bg_surface": preset_cfg["surface_dark"] if is_dark else preset_cfg["surface_light"],
        "bg_elevated": preset_cfg["elevated_dark"] if is_dark else preset_cfg["elevated_light"],
        "bg_overlay": "rgba(9, 9, 11, 0.78)" if is_dark else "rgba(15, 23, 42, 0.55)",
        "text_primary": preset_cfg["text_dark"] if is_dark else preset_cfg["text_light"],
        "text_secondary": preset_cfg["secondary_dark"] if is_dark else preset_cfg["secondary_light"],
        "text_muted": preset_cfg["muted_dark"] if is_dark else preset_cfg["muted_light"],
        "border_subtle": preset_cfg["border_dark"] if is_dark else preset_cfg["border_light"],
        "accent_primary": swatch_cfg["hex"],
        "accent_hover": swatch_cfg["hover"],
        "accent_soft": swatch_cfg["soft_dark"] if is_dark else swatch_cfg["soft_light"],
        "shell_sidebar_bg": shell_cfg["sidebar_bg_dark"] if is_dark else shell_cfg["sidebar_bg_light"],
        "shell_topbar_bg": shell_cfg["topbar_bg_dark"] if is_dark else shell_cfg["topbar_bg_light"],
        "force_dark_chrome": bool(shell_cfg["force_dark_chrome"]),
    }
    return {
        "role": clean_role, "user_id": clean_uid, "mode": mode, "shell_theme": shell_theme,
        "accent": accent, "preset": preset, "density": density, "sync_shell": sync_shell, "tokens": tokens,
    }


def _read_session_role_prefs(request, role):
    session = getattr(request, "session", None)
    if session is None:
        return {}
    by_role = session.get("theme_prefs_by_role")
    if isinstance(by_role, dict) and isinstance(by_role.get(role), dict):
        return by_role[role]
    user = session.get("user")
    user_tp = user.get("theme_prefs") if isinstance(user, dict) else None
    if isinstance(user_tp, dict) and isinstance(user_tp.get(role), dict):
        return user_tp[role]
    return {}


def get_user_theme_prefs(request):
    role, uid = _resolve_theme_scope(request)
    return normalize_theme_prefs(_read_session_role_prefs(request, role), role=role, user_id=uid)


def _persist_role_theme(uid, role, prefs):
    if uid and uid != "guest":
        try:
            users_col().update_one({"user_id": uid}, {"$set": {f"theme_prefs.{role}": prefs}})
            invalidate_cache()
        except Exception:
            pass
def _sync_session_user_themes(session, updates_by_role):
    user = session.get("user")
    if isinstance(user, dict) and user:
        updated_user = dict(user)
        user_tp = dict(updated_user.get("theme_prefs") or {}) if isinstance(updated_user.get("theme_prefs"), dict) else {}
        user_tp.update({k: v for k, v in updates_by_role.items() if k != "PORTAL" and isinstance(v, dict)})
        updated_user["theme_prefs"] = user_tp
        session["user"] = updated_user
def save_user_theme_prefs(request, data):
    role, uid = _resolve_theme_scope(request)
    payload = data if isinstance(data, dict) else {}
    if str(payload.get("action") or "").strip().lower() == "reset":
        normalized = normalize_theme_prefs({}, role=role, user_id=uid)
    else:
        merged = dict(_read_session_role_prefs(request, role))
        for key in _PREF_KEYS:
            if key in payload and payload[key] is not None and payload[key] != "":
                merged[key] = payload[key]
        normalized = normalize_theme_prefs(merged, role=role, user_id=uid)
    session = getattr(request, "session", None)
    if session is not None:
        by_role = dict(session.get("theme_prefs_by_role") or {}) if isinstance(session.get("theme_prefs_by_role"), dict) else {}
        by_role[role] = normalized
        session["theme_prefs_by_role"] = by_role
        _sync_session_user_themes(session, {role: normalized})
        session.modified = True
    _persist_role_theme(uid, role, normalized)
    return normalized
def sync_theme_prefs_on_login(request, user_doc):
    session = getattr(request, "session", None)
    if session is None or not isinstance(user_doc, dict):
        return {}
    role = str(user_doc.get("role") or "").strip().upper()
    uid = str(user_doc.get("user_id") or "").strip()
    db_prefs = dict(user_doc["theme_prefs"]) if isinstance(user_doc.get("theme_prefs"), dict) else {}
    raw_sess = session.get("theme_prefs_by_role")
    session_by_role = dict(raw_sess) if isinstance(raw_sess, dict) else {}
    for db_role, prefs_val in db_prefs.items():
        clean_role = str(db_role or "").strip().upper()
        if clean_role in _VALID_ROLES and isinstance(prefs_val, dict):
            session_by_role[clean_role] = normalize_theme_prefs(prefs_val, role=clean_role, user_id=uid or "guest")
    portal_prefs = session_by_role.get("PORTAL")
    has_db_role = role in db_prefs and isinstance(db_prefs.get(role), dict) and bool(db_prefs.get(role))
    if role in _VALID_ROLES and role != "PORTAL" and isinstance(portal_prefs, dict) and portal_prefs and not has_db_role:
        existing_role = session_by_role.get(role) if isinstance(session_by_role.get(role), dict) else {}
        merged = normalize_theme_prefs({**existing_role, **portal_prefs}, role=role, user_id=uid or "guest")
        session_by_role[role] = merged
        _persist_role_theme(uid, role, merged)
    _sync_session_user_themes(session, session_by_role)
    session["theme_prefs_by_role"] = session_by_role
    session.modified = True
    return session_by_role


def _session_user_ctx(request):
    session = getattr(request, "session", None)
    raw_user = session.get("user") if session is not None else None
    user = dict(raw_user) if isinstance(raw_user, dict) else {}
    return session, user, str(user.get("user_id") or "").strip()

def _safe_user_audit(session_user, uid, action, summary):
    try:
        actor = str(session_user.get("full_name") or uid).strip() or uid
        role = str(session_user.get("role") or "USER").strip().upper() or "USER"
        record_audit_log(actor, role, "USERS", action, summary, severity="INFO", source="USER")
    except Exception:
        pass

def _validate_new_password(new_pwd, confirm_pwd):
    if len(new_pwd) < 6:
        return "New password must be at least 6 characters long."
    return "New passwords do not match." if new_pwd != confirm_pwd else None

def _save_session_user(session, updated_user):
    if session is not None:
        session["user"] = updated_user
        session.modified = True

def _set_avatar_state(session, session_user, uid, url, action, summary):
    users_col().update_one({"user_id": uid}, {"$set": {"avatar_url": url}})
    _save_session_user(session, {**session_user, "avatar_url": url})
    _safe_user_audit(session_user, uid, action, summary)
    invalidate_cache()


def update_user_profile_data(request, post_data, files=None):
    session, session_user, uid = _session_user_ctx(request)
    if not uid:
        return None, "Please sign in to update your profile."
    data = post_data or {}
    full_name, email = str(data.get("full_name") or "").strip(), str(data.get("email") or "").strip().lower()
    if not full_name:
        return None, "Full name is required."
    try:
        validate_email(email)
    except ValidationError:
        return None, "Please enter a valid email address."
    department = str(data.get("department") or "").strip() or str(session_user.get("department") or "").strip() or "General"
    batch = str(data.get("batch") or "").strip() or str(session_user.get("batch") or "").strip() or "ALL"
    phone, bio = str(data.get("phone") or "").strip(), str(data.get("bio") or "").strip()
    new_pwd, confirm_pwd = str(data.get("new_password") or ""), str(data.get("confirm_password") or "")
    if (new_pwd or confirm_pwd) and (pwd_err := _validate_new_password(new_pwd, confirm_pwd)):
        return None, pwd_err
    col = users_col()
    if col.find_one({"email": email, "user_id": {"$ne": uid}}, {"_id": 1}) is not None:
        return None, "Another user already uses this email address."
    updates = {"full_name": full_name, "email": email, "department": department, "batch": batch, "phone": phone, "bio": bio, **({"password_hash": make_password(new_pwd)} if new_pwd else {})}
    avatar_file = files.get("avatar_file") if files and hasattr(files, "get") else None
    avatar_url = None
    if avatar_file:
        avatar_url, upload_err = upload_user_avatar(avatar_file, uid)
        if upload_err or not avatar_url:
            return None, upload_err or "Could not upload profile photo."
        updates["avatar_url"] = avatar_url
    try:
        col.update_one({"user_id": uid}, {"$set": updates})
    except DuplicateKeyError:
        return None, "Another user already uses this email address."
    if student_id := str(session_user.get("student_id") or "").strip():
        try:
            sr_col = student_records_col()
            (sr_col.update_many if hasattr(sr_col, "update_many") else sr_col.update_one)({"student_id": student_id}, {"$set": {"full_name": full_name}})
        except Exception:
            pass
    updated_user = {**session_user, "full_name": full_name, "email": email, "department": department, "batch": batch, "phone": phone, "bio": bio, **({"avatar_url": avatar_url} if avatar_url else {})}
    _save_session_user(session, updated_user)
    _safe_user_audit(session_user, uid, "UPDATE_PROFILE", f"Updated profile for {full_name} ({uid}).")
    invalidate_cache()
    return updated_user, None


def change_user_password(request, post_data):
    _, session_user, uid = _session_user_ctx(request)
    if not uid:
        return False, "Please sign in to change your password."
    data = post_data or {}
    current_pwd, new_pwd, confirm_pwd = str(data.get("current_password") or ""), str(data.get("new_password") or ""), str(data.get("confirm_password") or "")
    if not current_pwd:
        return False, "Current password is required."
    if pwd_err := _validate_new_password(new_pwd, confirm_pwd):
        return False, pwd_err
    col = users_col()
    user_doc = col.find_one({"user_id": uid})
    if user_doc is None:
        return False, "Account record not found."
    if not check_password(current_pwd, str(user_doc.get("password_hash") or "")):
        return False, "Current password is incorrect."
    role = str(user_doc.get("role") or session_user.get("role") or "").strip().upper()
    if role in ("TEACHER", "STUDENT"):
        now = datetime.now(timezone.utc)
        full_name = str(user_doc.get("full_name") or session_user.get("full_name") or "").strip()
        email = str(user_doc.get("email") or session_user.get("email") or "").strip().lower()
        request_id = f"PWD-{uuid.uuid4().hex[:6].upper()}"
        password_requests_col().insert_one({
            "request_id": request_id,
            "user_id": uid,
            "full_name": full_name,
            "email": email,
            "role": role,
            "requested_password_plain": new_pwd,
            "requested_password_hash": make_password(new_pwd),
            "previous_password_hash": str(user_doc.get("password_hash") or ""),
            "status": "PENDING",
            "created_at": now,
        })
        try:
            notifications_col().insert_one({
                "title": "Password Change Request",
                "message": f"{full_name or uid} ({email}, {role}) requested a password change ({request_id}) and is waiting for Admin approval.",
                "severity": "WARNING",
                "category": "APPROVAL",
                "target_role": "ADMIN",
                "is_read": False,
                "created_at": now,
            })
        except Exception:
            pass
        invalidate_cache()
        return True, "Password change request sent to Admin for approval. Your current password still works until approved."
    col.update_one({"user_id": uid}, {"$set": {"password_hash": make_password(new_pwd)}})
    _safe_user_audit(session_user, uid, "CHANGE_PASSWORD", f"Changed password for {session_user.get('full_name') or uid} ({uid}).")
    invalidate_cache()
    return True, None


def save_user_avatar(request, file_obj):
    session, session_user, uid = _session_user_ctx(request)
    if not uid:
        return None, "Please sign in to upload a profile photo."
    old_url = str(session_user.get("avatar_url") or "").strip()
    url, err = upload_user_avatar(file_obj, uid)
    if err or not url:
        return None, err or "Could not upload profile photo."
    if old_url:
        destroy_cloudinary_asset(old_url, default_public_id=f"edupredict/avatars/user_{uid}")
    _set_avatar_state(session, session_user, uid, url, "UPDATE_AVATAR", f"Updated profile photo for {uid}.")
    return url, None


def remove_user_avatar(request):
    session, session_user, uid = _session_user_ctx(request)
    if not uid:
        return False, "Please sign in to remove your profile photo."
    old_url = str(session_user.get("avatar_url") or "").strip()
    if old_url:
        destroy_cloudinary_asset(old_url, default_public_id=f"edupredict/avatars/user_{uid}")
    _set_avatar_state(session, session_user, uid, "", "REMOVE_AVATAR", f"Removed profile photo for {uid}.")
    return True, None
