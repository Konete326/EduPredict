import json
import os
import re
import socket
import urllib.error
import urllib.request
from core.ai_dom_actions import (
    ROLE_PRD_CAPS,
    ROLE_ROUTES,
    build_dom_actions_and_poll,
    build_role_poll,
    describe_role_action_schema,
    evaluate_rbac_privacy_guard,
    sanitize_llm_dom_actions,
    sanitize_llm_poll,
)
from core.db import courses_col, predictions_col, student_records_col, support_tickets_col


def _svg_dp(bg_hex, body):
    c = bg_hex.replace("#", "%23")
    return f"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'><rect width='64' height='64' rx='32' fill='{c}'/>{body}</svg>"


AGENT_ORDER = ("coach", "analyst", "ops", "desk")
AGENT_ALIASES = {"amina": "coach", "zain": "analyst", "sara": "ops", "bilal": "desk"}

EDUPREDICT_AGENTS = {
    "coach": {
        "id": "coach", "name": "EduCoach AI", "role": "Academic & Study Advisor", "shortRole": "Academic Advisor",
        "icon": "fa-solid fa-graduation-cap", "accent": "#16a34a", "online": True,
        "avatar_url": _svg_dp("#16a34a", "<path d='M32 16L12 25l20 9 20-9-20-9z' fill='%23ffffff'/><path d='M20 31v10c0 4 5.4 7 12 7s12-3 12-7V31l-12 5-12-5z' fill='%23ffffff' fill-opacity='0.88'/><path d='M49 27v13' stroke='%23ffffff' stroke-width='3' stroke-linecap='round'/>"),
        "skills": "GPA improvement, attendance recovery, coursework and study tips",
    },
    "analyst": {
        "id": "analyst", "name": "PulseML AI", "role": "Predictive Risk & Data Agent", "shortRole": "ML & Risk Agent",
        "icon": "fa-solid fa-chart-line", "accent": "#2563eb", "online": True,
        "avatar_url": _svg_dp("#2563eb", "<path d='M15 47h34' stroke='%23ffffff' stroke-width='3' stroke-linecap='round'/><path d='M16 40l10-10 8 6 14-16' fill='none' stroke='%23ffffff' stroke-width='3.5' stroke-linecap='round' stroke-linejoin='round'/><circle cx='16' cy='40' r='3' fill='%23ffffff'/><circle cx='26' cy='30' r='3' fill='%23ffffff'/><circle cx='34' cy='36' r='3' fill='%23ffffff'/><circle cx='48' cy='20' r='3.5' fill='%23ffffff'/>"),
        "skills": "dropout risk scores, RandomForest/Ridge/IsolationForest metrics and anomalies",
    },
    "ops": {
        "id": "ops", "name": "CourseOps AI", "role": "Course, Roster & Marks Agent", "shortRole": "Course & Marks",
        "icon": "fa-solid fa-chalkboard-user", "accent": "#d97706", "online": True,
        "avatar_url": _svg_dp("#d97706", "<rect x='17' y='16' width='30' height='34' rx='5' fill='none' stroke='%23ffffff' stroke-width='3.2'/><path d='M25 14h14v5H25z' fill='%23ffffff'/><path d='M24 28h16M24 35h16M24 42h10' stroke='%23ffffff' stroke-width='3' stroke-linecap='round'/>"),
        "skills": "courses, seat capacity, CSV/Excel marks upload, quick entry and class rosters",
    },
    "desk": {
        "id": "desk", "name": "HelpDesk AI", "role": "Portal Guide, PDF & Support Agent", "shortRole": "Portal & Support",
        "icon": "fa-solid fa-headset", "accent": "#dc2626", "online": True,
        "avatar_url": _svg_dp("#dc2626", "<path d='M18 35v-4a14 14 0 0 1 28 0v4' fill='none' stroke='%23ffffff' stroke-width='3.5' stroke-linecap='round'/><rect x='14' y='32' width='7' height='12' rx='3.5' fill='%23ffffff'/><rect x='43' y='32' width='7' height='12' rx='3.5' fill='%23ffffff'/><path d='M36 47h7a4 4 0 0 0 4-4v-1' fill='none' stroke='%23ffffff' stroke-width='3' stroke-linecap='round'/>"),
        "skills": "A4 printable PDF transcripts, help tickets, profile, password and portal navigation",
    },
}

AGENT_KEYWORDS = {
    "analyst": (("random forest", 4), ("isolation forest", 4), ("risk score", 4), ("model health", 4), ("contour", 3), ("stratum", 3), ("anomaly", 3), ("anomalies", 3), ("prediction", 3), ("predictions", 3), ("accuracy", 3), ("ridge", 3), ("dataset", 3), ("datasets", 3), ("mae", 3), ("rmse", 3), ("ml", 3), ("model", 2), ("models", 2), ("dropout", 2), ("risk", 1)),
    "ops": (("marks upload", 4), ("upload marks", 4), ("quick entry", 4), ("add marks", 4), ("create course", 4), ("add course", 4), ("capacity", 3), ("roster", 3), ("rosters", 3), ("ingest", 3), ("ingestion", 3), ("instructor", 3), ("instructors", 3), ("csv", 3), ("excel", 3), ("xlsx", 3), ("course", 2), ("courses", 2), ("seat", 2), ("seats", 2), ("upload", 2), ("sheet", 2), ("sheets", 2), ("teacher", 2), ("teachers", 2), ("batch", 2), ("batches", 2)),
    "desk": (("transcript", 4), ("transcripts", 4), ("support ticket", 4), ("help ticket", 4), ("report card", 3), ("print report", 4), ("download pdf", 4), ("change password", 4), ("portal settings", 4), ("pdf", 3), ("ticket", 3), ("tickets", 3), ("password", 3), ("avatar", 3), ("approval", 3), ("printable", 3), ("print", 2), ("profile", 2), ("support", 2), ("theme", 2), ("setting", 2), ("settings", 2), ("account", 2), ("a4", 2), ("logs", 2), ("users", 2)),
    "coach": (("study tip", 4), ("study tips", 4), ("gpa", 3), ("attendance", 3), ("coursework", 3), ("assignment", 3), ("assignments", 3), ("exam", 3), ("exams", 3), ("orbit", 3), ("study", 2), ("studying", 2), ("tip", 2), ("tips", 2), ("marks", 2), ("hours", 2), ("focus", 2), ("goal", 2), ("goals", 2), ("improve", 2), ("improvement", 2), ("learn", 2), ("learning", 2)),
}


def resolve_agent_id(agent_id, default="coach"):
    raw = str(agent_id or "").strip().lower()
    mapped = AGENT_ALIASES.get(raw, raw)
    return mapped if mapped in EDUPREDICT_AGENTS else default


def list_edupredict_agents():
    return [dict(EDUPREDICT_AGENTS[key]) for key in AGENT_ORDER]


def _safe_float(val, default=0.0):
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _resolve_gemini_api_key():
    key = (os.getenv("GEMINI_BACKEND_KEY_3") or os.getenv("GEMINI_API_KEY") or "").strip()
    if key or os.name != "nt":
        return key
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as reg_key:
            for env_name in ("GEMINI_BACKEND_KEY_3", "GEMINI_API_KEY"):
                try:
                    val, _ = winreg.QueryValueEx(reg_key, env_name)
                    if str(val or "").strip():
                        return str(val).strip()
                except OSError:
                    continue
    except Exception:
        pass
    return ""


def detect_best_agent(message, current_agent_id=None):
    normalized_text = re.sub(r"[-_]+", " ", str(message or "").lower())
    scores = {key: sum(w for kw, w in AGENT_KEYWORDS[key] if re.search(r"\b" + re.escape(kw) + r"\b", normalized_text)) for key in AGENT_ORDER}
    best_id = max(AGENT_ORDER, key=lambda key: scores[key])
    raw_current = str(current_agent_id or "").strip().lower()
    mapped_current = AGENT_ALIASES.get(raw_current, raw_current)
    if mapped_current not in EDUPREDICT_AGENTS:
        return dict(EDUPREDICT_AGENTS[best_id if scores[best_id] > 0 else "coach"]), False
    if best_id != mapped_current and scores[best_id] > scores[mapped_current]:
        return dict(EDUPREDICT_AGENTS[best_id]), True
    return dict(EDUPREDICT_AGENTS[mapped_current]), False


def _build_live_mongo_context(user_doc):
    user = user_doc if isinstance(user_doc, dict) else {}
    role = str(user.get("role") or "").strip().upper() or "STUDENT"
    user_id = str(user.get("user_id") or "").strip()
    student_id = str(user.get("student_id") or (user_id if role == "STUDENT" else "")).strip()
    full_name = str(user.get("full_name") or "User").strip() or "User"
    ctx = {
        "role": role, "full_name": full_name, "student_id": student_id or None, "records_count": 0, "unique_students": 0,
        "avg_attendance_pct": None, "avg_internal_marks": None, "avg_previous_gpa": None, "low_attendance_count": 0,
        "student_courses": [], "predictions_count": 0, "high_risk_count": 0, "medium_risk_count": 0, "low_risk_count": 0,
        "anomaly_count": 0, "avg_predicted_gpa": None, "latest_risk_level": None, "latest_recommendation": "",
        "courses_count": 0, "active_courses_count": 0, "total_course_capacity": 0, "sample_courses": [],
        "tickets_total": 0, "open_tickets_count": 0, "resolved_tickets_count": 0,
    }
    try:
        rec_rows = [] if (role == "STUDENT" and not student_id) else list(student_records_col().find({"student_id": student_id} if role == "STUDENT" else {}, {"_id": 0, "student_id": 1, "course_code": 1, "attendance_pct": 1, "internal_marks": 1, "previous_gpa": 1}))
        ctx["records_count"] = len(rec_rows)
        if rec_rows:
            n = len(rec_rows)
            ctx["unique_students"] = len({str(r.get("student_id") or "").strip() for r in rec_rows if r.get("student_id")})
            ctx["avg_attendance_pct"] = round(sum(_safe_float(r.get("attendance_pct")) for r in rec_rows) / n, 1)
            ctx["avg_internal_marks"] = round(sum(_safe_float(r.get("internal_marks")) for r in rec_rows) / n, 1)
            ctx["avg_previous_gpa"] = round(sum(_safe_float(r.get("previous_gpa")) for r in rec_rows) / n, 2)
            ctx["low_attendance_count"] = sum(1 for r in rec_rows if _safe_float(r.get("attendance_pct"), 100.0) < 75.0)
            if role == "STUDENT":
                ctx["student_courses"] = [{"course_code": str(r.get("course_code") or "").upper(), "attendance_pct": round(_safe_float(r.get("attendance_pct")), 1), "internal_marks": round(_safe_float(r.get("internal_marks")), 1)} for r in rec_rows[:5]]
    except Exception:
        pass
    try:
        pred_rows = [] if (role == "STUDENT" and not student_id) else list(predictions_col().find({"student_id": student_id} if role == "STUDENT" else {}, {"_id": 0, "student_id": 1, "predicted_gpa": 1, "risk_level": 1, "is_anomaly": 1, "recommendation": 1}))
        ctx["predictions_count"] = len(pred_rows)
        if pred_rows:
            ctx["high_risk_count"] = sum(1 for p in pred_rows if str(p.get("risk_level") or "").upper() == "HIGH")
            ctx["medium_risk_count"] = sum(1 for p in pred_rows if str(p.get("risk_level") or "").upper() == "MEDIUM")
            ctx["low_risk_count"] = sum(1 for p in pred_rows if str(p.get("risk_level") or "").upper() == "LOW")
            ctx["anomaly_count"] = sum(1 for p in pred_rows if bool(p.get("is_anomaly")))
            gpa_vals = [_safe_float(p.get("predicted_gpa")) for p in pred_rows if p.get("predicted_gpa") is not None]
            ctx["avg_predicted_gpa"] = round(sum(gpa_vals) / len(gpa_vals), 2) if gpa_vals else None
            ctx["latest_risk_level"] = str(pred_rows[0].get("risk_level") or "").upper() or None
            ctx["latest_recommendation"] = str(pred_rows[0].get("recommendation") or "")[:160]
    except Exception:
        pass
    try:
        course_rows = list(courses_col().find({}, {"_id": 0, "course_code": 1, "capacity": 1, "status": 1}))
        active_courses = [c for c in course_rows if str(c.get("status") or "ACTIVE").upper() == "ACTIVE"]
        ctx["courses_count"] = len(course_rows)
        ctx["active_courses_count"] = len(active_courses)
        ctx["total_course_capacity"] = sum(int(_safe_float(c.get("capacity"), 0)) for c in active_courses)
        ctx["sample_courses"] = [str(c.get("course_code") or "").upper() for c in active_courses[:6] if c.get("course_code")]
    except Exception:
        pass
    try:
        ticket_query = {} if role == "ADMIN" else ({"user_id": user_id} if user_id else None)
        ticket_rows = [] if ticket_query is None else list(support_tickets_col().find(ticket_query, {"_id": 0, "status": 1}))
        ctx["tickets_total"] = len(ticket_rows)
        ctx["open_tickets_count"] = sum(1 for t in ticket_rows if str(t.get("status") or "OPEN").upper() == "OPEN")
        ctx["resolved_tickets_count"] = sum(1 for t in ticket_rows if str(t.get("status") or "").upper() == "RESOLVED")
    except Exception:
        pass
    return ctx


def _build_gemini_contents(user_message, history=None):
    contents = []
    if isinstance(history, list):
        for item in history[-10:]:
            if not isinstance(item, dict):
                continue
            txt = str(item.get("text") or item.get("content") or "").strip()[:600]
            if not txt:
                continue
            raw_role, side = str(item.get("role") or "").strip().lower(), str(item.get("side") or "").strip().lower()
            g_role = "user" if (raw_role == "user" or side == "right") else "model"
            if not contents and g_role == "model":
                continue
            contents.append({"role": g_role, "parts": [{"text": txt}]})
    clean_msg = str(user_message or "").strip()
    if clean_msg and (not contents or contents[-1]["role"] != "user" or contents[-1]["parts"][0]["text"] != clean_msg):
        contents.append({"role": "user", "parts": [{"text": clean_msg}]})
    return contents or [{"role": "user", "parts": [{"text": clean_msg}]}]


def call_gemini_flash(system_prompt, user_message, history=None, json_mode=False):
    api_key = _resolve_gemini_api_key()
    if not api_key:
        return None, "missing_api_key"
    gen_cfg = {"temperature": 0.35, "maxOutputTokens": 650}
    if json_mode:
        gen_cfg["responseMimeType"] = "application/json"
    payload = {"system_instruction": {"parts": [{"text": str(system_prompt or "")}]}, "contents": _build_gemini_contents(user_message, history), "generationConfig": gen_cfg}
    encoded = json.dumps(payload).encode("utf-8")
    timeout_s = max(2.0, min(25.0, _safe_float(os.getenv("GEMINI_TIMEOUT_SECS"), 10.0)))
    primary_model = (os.getenv("GEMINI_CHAT_MODEL") or "gemini-flash-lite-latest").strip()
    models = tuple(dict.fromkeys([primary_model, "gemini-flash-lite-latest", "gemini-3.5-flash-lite"]))
    last_error = "gemini_unavailable"
    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        req = urllib.request.Request(url, data=encoded, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                if getattr(resp, "status", 200) != 200:
                    last_error = f"{model}:http_{getattr(resp, 'status', 500)}"
                    continue
                parsed = json.loads(resp.read().decode("utf-8"))
                candidates = parsed.get("candidates") or []
                parts = ((candidates[0].get("content") or {}).get("parts") or []) if candidates else []
                text = "".join(str(p.get("text") or "") for p in parts).strip()
                if text:
                    return text, model
                last_error = f"{model}:empty_response"
        except urllib.error.HTTPError as exc:
            last_error = f"{model}:http_{exc.code}"
        except (socket.timeout, TimeoutError):
            last_error = f"{model}:timeout"
        except urllib.error.URLError as exc:
            last_error = f"{model}:timeout" if isinstance(getattr(exc, "reason", None), (socket.timeout, TimeoutError)) else f"{model}:network_error"
        except Exception as exc:
            last_error = f"{model}:{type(exc).__name__}"
    return None, last_error


def _parse_gemini_plan(raw_text):
    text = str(raw_text or "").strip()
    if not text:
        return None
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I | re.S).strip()
    if cleaned.startswith("{"):
        try:
            obj = json.loads(cleaned)
            if isinstance(obj, dict) and str(obj.get("reply") or "").strip():
                return {
                    "structured": True,
                    "reply": str(obj.get("reply")).strip(),
                    "dom_actions": obj.get("dom_actions"),
                    "poll": obj.get("poll"),
                    "handoff_to": obj.get("handoff_to"),
                }
        except json.JSONDecodeError:
            pass
    return {"structured": False, "reply": text, "dom_actions": None, "poll": None, "handoff_to": None}


def _build_fallback_reply(agent, ctx, dom_actions=None, poll=None):
    agent_id = agent["id"]
    if dom_actions:
        labels = ", ".join(a.get("label") or a.get("type") for a in dom_actions[:2])
        atype = dom_actions[0].get("type")
        if atype == "open_and_fill_form":
            return f"Main {labels} open aur pre-fill kar raha hoon. Details check karke submit karein."
        if atype == "redirect" and dom_actions[0].get("auto"):
            return f"Main aapko {dom_actions[0].get('label', 'target page')} par le ja raha hoon."
        if atype in ("filter_table", "click_element", "toggle_theme", "toggle_sidebar"):
            return f"Action ready hai: {labels}."
    if poll and not dom_actions:
        return f"{ctx['full_name']}, aapke {ctx['role']} portal ke quick options neeche poll mein maujood hain — kisi ek par click karein."
    if agent_id == "coach":
        if ctx["records_count"] == 0:
            return f"{ctx['full_name']}, abhi database mein 0 academic records (records_count: 0) maujood hain. Jab marks aur attendance upload hon ge to main aapka exact GPA aur attendance plan share kar sakunga."
        gpa_part = f", Predicted GPA {ctx['avg_predicted_gpa']}" if ctx["avg_predicted_gpa"] is not None else ""
        rec_tip = f" Tip: {ctx['latest_recommendation']}" if ctx["latest_recommendation"] else ""
        return f"Live DB ke mutabiq {ctx['records_count']} record(s) mein average attendance {ctx['avg_attendance_pct']}%, average marks {ctx['avg_internal_marks']}/100, aur previous GPA {ctx['avg_previous_gpa']}{gpa_part} hai.{rec_tip}"
    if agent_id == "analyst":
        if ctx["predictions_count"] == 0:
            return f"ML database mein abhi 0 predictions (predictions_count: 0) aur {ctx['records_count']} student record(s) hain. Data upload aur ML run hone ke baad RandomForest risk scores aur IsolationForest anomalies yahan show hon gi."
        gpa_txt = f"{ctx['avg_predicted_gpa']}" if ctx["avg_predicted_gpa"] is not None else "N/A"
        return f"Live ML summary ({ctx['predictions_count']} predictions): High Risk {ctx['high_risk_count']}, Medium Risk {ctx['medium_risk_count']}, Low Risk {ctx['low_risk_count']}, Anomalies {ctx['anomaly_count']}, aur avg Predicted GPA {gpa_txt}."
    if agent_id == "ops":
        if ctx["courses_count"] == 0 and ctx["records_count"] == 0:
            return "Abhi portal mein 0 courses (courses_count: 0) aur 0 student records maujood hain. Teacher/Admin panel se courses add karein ya 3-column CSV (student_id, marks, attendance) upload karein."
        codes = ", ".join(ctx["sample_courses"]) if ctx["sample_courses"] else "none"
        return f"Active courses {ctx['active_courses_count']} hain (total seat capacity {ctx['total_course_capacity']}; sample: {codes}) aur {ctx['records_count']} student record(s) maujood hain."
    return f"Portal support status ({ctx['role']}): aapke {ctx['tickets_total']} ticket(s) mein se {ctx['open_tickets_count']} open aur {ctx['resolved_tickets_count']} resolved hain. A4 PDF, profile, ya support actions ke liye quick buttons use karein."


def handle_agent_dock_message(user_doc, agent_id, message, history=None, current_path=None):
    clean_msg = str(message or "").strip()
    if not clean_msg:
        return {"ok": False, "error": "Please type a message first."}
    user = user_doc if isinstance(user_doc, dict) else {}
    role = str(user.get("role") or "STUDENT").strip().upper()
    req_id = resolve_agent_id(agent_id, default="coach")
    task_preview = clean_msg[:110] + ("..." if len(clean_msg) > 110 else "")
    refusal, blocked_reason = evaluate_rbac_privacy_guard(user, clean_msg)
    if refusal:
        base_agent = dict(EDUPREDICT_AGENTS[req_id])
        return {
            "ok": True, "handoff": False, "from_agent": base_agent, "active_agent": base_agent,
            "handoff_message": "", "task_preview": task_preview, "continue_prefix": "",
            "reply": refusal, "dom_actions": [], "poll": build_role_poll(role),
            "blocked": True, "blocked_reason": blocked_reason, "engine": "rbac_guard", "ephemeral": True,
        }
    active_agent, handoff = detect_best_agent(clean_msg, agent_id)
    det_actions, det_poll = build_dom_actions_and_poll(user, clean_msg, history=history)
    mongo_ctx = _build_live_mongo_context(user)
    path_note = str(current_path or "").strip()[:120] or "unknown"
    system_prompt = (
        f"You are {active_agent['name']}, {active_agent['role']} in EduPredict. Skills: {active_agent['skills']}. "
        f"Current User Role: {role}. Current Path: {path_note}. {ROLE_PRD_CAPS.get(role, '')} "
        f"{describe_role_action_schema(role)} "
        "Respond ONLY as a JSON object with keys: "
        '{"reply": string, "dom_actions": array, "poll": null | {"question": string, "options": [{"label": string, "prompt": string}]}, "handoff_to": null | "coach" | "analyst" | "ops" | "desk"}. '
        "Match user's language naturally (Latin-script Roman Urdu only, never Arabic/Urdu script, if they write Roman Urdu; clear English if English; 2-4 concise sentences). "
        "Use ONLY exact numbers from LIVE_DB_CONTEXT; never invent GPA, marks, attendance, or counts. Never reveal passwords, secrets, or cross-role data. "
        "Emit dom_actions ONLY when user requests navigation, filtering, theme/sidebar toggle, clicking a portal action, or opening/filling a form; otherwise []. "
        f"HINT_DOM_ACTIONS={json.dumps(det_actions, ensure_ascii=True)}. LIVE_DB_CONTEXT={json.dumps(mongo_ctx, ensure_ascii=True)}"
    )
    raw_reply, engine_info = call_gemini_flash(system_prompt, clean_msg, history=history, json_mode=True)
    plan = _parse_gemini_plan(raw_reply) if raw_reply else None
    if plan:
        reply_text, engine_used = plan["reply"], engine_info
        if plan["structured"]:
            llm_actions = sanitize_llm_dom_actions(user, plan["dom_actions"])
            llm_poll = sanitize_llm_poll(user, plan["poll"])
            dom_actions = llm_actions if llm_actions else det_actions
            poll = llm_poll if llm_poll is not None else (det_poll if not llm_actions else None)
            if not handoff and plan.get("handoff_to"):
                cand_id = resolve_agent_id(plan["handoff_to"], default="")
                if cand_id in EDUPREDICT_AGENTS and cand_id != active_agent["id"]:
                    active_agent, handoff = dict(EDUPREDICT_AGENTS[cand_id]), True
        else:
            dom_actions, poll = det_actions, det_poll
    else:
        dom_actions, poll = det_actions, det_poll
        reply_text, engine_used = _build_fallback_reply(active_agent, mongo_ctx, dom_actions, poll), f"fallback:{engine_info}"
    from_agent = dict(EDUPREDICT_AGENTS[req_id]) if handoff else dict(active_agent)
    handoff_message = f"Main aapka yeh kaam {active_agent['name']} ({active_agent['role']}) ko assign kar raha hoon — woh {active_agent['skills']} ke specialist hain." if handoff else ""
    continue_prefix = f"Mujhe aapka task mil gaya hai ({task_preview}) — main yahan se start aur continue kar raha hoon:" if handoff else ""
    return {
        "ok": True, "handoff": handoff, "from_agent": from_agent, "active_agent": active_agent,
        "handoff_message": handoff_message, "task_preview": task_preview,
        "continue_prefix": continue_prefix, "reply": reply_text,
        "dom_actions": dom_actions, "poll": poll, "blocked": False,
        "engine": engine_used, "ephemeral": True,
    }
