from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from pymongo.errors import DuplicateKeyError
from core.db import invalidate_cache, student_records_col, users_col
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
    _shell("dark", "Dark", "#1e293b", "#0f172a", "#1e293b", "indigo", "#0f172a", "#111827", "#090d16", "#111827", True),
    _shell("red", "Red", "#dc2626", "#991b1b", "#dc2626", "crimson", "#fef2f2", "#fff5f5", "#1b0e12", "#221116"),
    _shell("dark-green", "Dark Green", "#15803d", "#14532d", "#166534", "forest", "#f0fdf4", "#f4fbf6", "#0b1a12", "#0f2218"),
    _shell("green", "Green", "#10b981", "#047857", "#10b981", "emerald", "#ecfdf5", "#f2fbf7", "#0b1d18", "#102620"),
    _shell("blue", "Blue", "#2563eb", "#1d4ed8", "#2563eb", "ocean", "#eff6ff", "#f5f9ff", "#0d182b", "#112038"),
    _shell("white", "White", "#ffffff", "#f8fafc", "#ffffff", None, "#ffffff", "#ffffff", "#111827", "#111827"),
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

SURFACE_PRESETS = (
    {"slug": "neutral", "label": "Neutral", "canvas_light": "#f8fafc", "surface_light": "#ffffff", "elevated_light": "#f1f5f9", "canvas_dark": "#090d16", "surface_dark": "#111827", "elevated_dark": "#1e293b"},
    {"slug": "butter", "label": "Butter", "canvas_light": "#fefce8", "surface_light": "#fffdf5", "elevated_light": "#fef3c7", "canvas_dark": "#14120a", "surface_dark": "#1e1a0f", "elevated_dark": "#2c2516"},
    {"slug": "matcha", "label": "Matcha", "canvas_light": "#f3faf4", "surface_light": "#fbfefb", "elevated_light": "#e2f3e6", "canvas_dark": "#09130d", "surface_dark": "#101f16", "elevated_dark": "#192e21"},
    {"slug": "chocolate", "label": "Chocolate", "canvas_light": "#faf6f2", "surface_light": "#fffcf9", "elevated_light": "#f1e8df", "canvas_dark": "#140f0c", "surface_dark": "#1f1713", "elevated_dark": "#2e221c"},
    {"slug": "stone", "label": "Stone", "canvas_light": "#f5f5f4", "surface_light": "#fafaf9", "elevated_light": "#e7e5e4", "canvas_dark": "#0c0a09", "surface_dark": "#1c1917", "elevated_dark": "#292524"},
    {"slug": "gothic", "label": "Gothic", "canvas_light": "#f4f4f6", "surface_light": "#fafafc", "elevated_light": "#e4e4ec", "canvas_dark": "#050508", "surface_dark": "#0d0e14", "elevated_dark": "#181924"},
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
    session = getattr(request, "session", None)
    raw_user = session.get("user") if session is not None else None
    user = raw_user if isinstance(raw_user, dict) and raw_user else None
    uid = str((user or {}).get("user_id") or "").strip() or "guest"
    raw_role = str((user or {}).get("role") or "").strip().upper()
    if raw_role in _VALID_ROLES:
        return raw_role, uid
    path = str(getattr(request, "path", "") or "").strip()
    for prefix, mapped_role in _PATH_ROLE_MAP:
        if path.startswith(prefix):
            return mapped_role, uid
    return "PORTAL", uid


def get_theme_studio_catalog():
    return {
        "modes": [dict(item) for item in APPEARANCE_MODES],
        "shell_themes": [dict(item) for item in SHELL_THEMES],
        "swatches": [dict(item) for item in BRAND_SWATCHES],
        "presets": [dict(item) for item in SURFACE_PRESETS],
        "save_url": "/theme/preferences/",
    }


def normalize_theme_prefs(raw, role="PORTAL", user_id="guest"):
    source = raw if isinstance(raw, dict) else {}
    clean_role = str(role or "PORTAL").strip().upper() or "PORTAL"
    clean_uid = str(user_id or "guest").strip() or "guest"
    mode = _pick(source, "mode", _MODE_SLUGS, "light")
    shell_theme = _pick(source, "shell_theme", _SHELL_MAP, "white")
    accent = _pick(source, "accent", _SWATCH_MAP, "indigo")
    preset = _pick(source, "preset", _PRESET_MAP, "neutral")
    density = _pick(source, "density", _DENSITY_VALUES, "comfortable")
    sync_shell = _parse_bool(source.get("sync_shell"), default=True)
    shell_cfg, swatch_cfg, preset_cfg = _SHELL_MAP[shell_theme], _SWATCH_MAP[accent], _PRESET_MAP[preset]
    is_dark = mode == "dark"
    tokens = {
        "bg_canvas": preset_cfg["canvas_dark"] if is_dark else preset_cfg["canvas_light"],
        "bg_surface": preset_cfg["surface_dark"] if is_dark else preset_cfg["surface_light"],
        "bg_elevated": preset_cfg["elevated_dark"] if is_dark else preset_cfg["elevated_light"],
        "bg_overlay": "rgba(2, 6, 23, 0.78)" if is_dark else "rgba(15, 23, 42, 0.55)",
        "text_primary": "#f8fafc" if is_dark else "#0f172a",
        "text_secondary": "#cbd5e1" if is_dark else "#475569",
        "text_muted": "#94a3b8" if is_dark else "#64748b",
        "border_subtle": "#1e293b" if is_dark else "#e2e8f0",
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


def update_user_profile_data(request, post_data):
    session = getattr(request, "session", None)
    raw_user = session.get("user") if session is not None else None
    session_user = dict(raw_user) if isinstance(raw_user, dict) else {}
    uid = str(session_user.get("user_id") or "").strip()
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
    if new_pwd or confirm_pwd:
        if len(new_pwd) < 6:
            return None, "New password must be at least 6 characters long."
        if new_pwd != confirm_pwd:
            return None, "New passwords do not match."
    col = users_col()
    if col.find_one({"email": email, "user_id": {"$ne": uid}}, {"_id": 1}) is not None:
        return None, "Another user already uses this email address."
    updates = {"full_name": full_name, "email": email, "department": department, "batch": batch, "phone": phone, "bio": bio}
    if new_pwd:
        updates["password_hash"] = make_password(new_pwd)
    try:
        col.update_one({"user_id": uid}, {"$set": updates})
    except DuplicateKeyError:
        return None, "Another user already uses this email address."
    student_id = str(session_user.get("student_id") or "").strip()
    if student_id:
        try:
            sr_col = student_records_col()
            (sr_col.update_many if hasattr(sr_col, "update_many") else sr_col.update_one)({"student_id": student_id}, {"$set": {"full_name": full_name}})
        except Exception:
            pass
    updated_user = {**session_user, "full_name": full_name, "email": email, "department": department, "batch": batch, "phone": phone, "bio": bio}
    if session is not None:
        session["user"] = updated_user
        session.modified = True
    try:
        record_audit_log(full_name, str(session_user.get("role") or "USER").strip().upper() or "USER", "USERS", "UPDATE_PROFILE", f"Updated profile for {full_name} ({uid}).", severity="INFO", source="USER")
    except Exception:
        pass
    invalidate_cache()
    return updated_user, None
