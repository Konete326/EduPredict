import re

ROLE_ROUTES = {
    "STUDENT": (
        ("/student-panel/", "My Dashboard", ("dashboard", "home", "student panel", "overview", "my dashboard")),
        ("/student-panel/report/", "My Report Card", ("report card", "report", "transcript", "grade sheet", "result")),
        ("/student-panel/tips/", "Study Tips", ("study tips", "tips", "study plan", "advice", "goals", "orbit")),
        ("/student-panel/notifications/", "Alerts & Support", ("student alerts", "support", "help ticket", "alerts")),
        ("/notifications/", "Alerts History", ("notifications", "alert history", "history")),
        ("/profile/", "My Profile", ("profile", "my profile", "avatar", "bio", "account")),
    ),
    "TEACHER": (
        ("/teacher-panel/", "Class Home", ("dashboard", "home", "class home", "teacher panel", "overview")),
        ("/teacher-panel/students/", "Student List", ("students", "student list", "roster", "class list", "performance")),
        ("/teacher-panel/ingest/", "Upload Marks", ("upload marks", "ingest", "marks upload", "upload", "csv", "excel", "quick entry")),
        ("/teacher-panel/alerts/", "Risk Alerts", ("risk alerts", "alerts", "at risk")),
        ("/notifications/", "Alerts History", ("notifications", "alert history", "history")),
        ("/profile/", "My Profile", ("profile", "my profile", "avatar", "bio", "account")),
    ),
    "ANALYST": (
        ("/analyst-panel/", "Data & ML Hub", ("dashboard", "home", "data hub", "ml hub", "analyst", "predictions", "evaluation")),
        ("/analyst-panel/#ml-evaluation-section", "AI Accuracy", ("accuracy", "ai accuracy", "confusion matrix", "mae", "rmse")),
        ("/analyst-panel/accuracy/", "Model Health", ("model health", "health", "thresholds", "drift", "contour")),
        ("/notifications/", "Alerts History", ("notifications", "alert history", "history")),
        ("/profile/", "My Profile", ("profile", "my profile", "avatar", "bio", "account")),
    ),
    "ADMIN": (
        ("/admin-panel/", "Admin Dashboard", ("dashboard", "home", "admin panel", "overview")),
        ("/admin-panel/users/", "Users", ("users", "user management", "manage users", "accounts")),
        ("/admin-panel/courses/", "Courses", ("courses", "course management", "batches", "subjects")),
        ("/admin-panel/tickets/", "Help Tickets", ("tickets", "help tickets", "support tickets", "feedback")),
        ("/admin-panel/logs/", "Activity Logs", ("logs", "activity logs", "audit logs", "audit")),
        ("/admin-panel/settings/", "Portal Settings", ("settings", "portal settings", "thresholds", "backup")),
        ("/notifications/", "Alerts History", ("notifications", "alert history", "history", "alerts")),
        ("/profile/", "My Profile", ("profile", "my profile", "avatar", "bio", "account")),
    ),
}

ROLE_PRD_CAPS = {
    "STUDENT": "Student scope: personal attendance %, marks, predicted GPA, risk level, AI study tips, A4 printable PDF/CSV report card, alerts & support tickets, and own profile/password.",
    "TEACHER": "Teacher scope: class overview, student performance list, CSV/Excel or quick student marks entry, high-risk alerts, A4 class roster PDF, support tickets, and own profile/password.",
    "ANALYST": "Analyst scope: Data & ML Hub, dataset upload, RandomForest/Ridge/IsolationForest predictions, model evaluation metrics, live LMS stream simulation, model health & thresholds, and own profile/password.",
    "ADMIN": "Admin scope: portal overview, user CRUD & teacher approval/rejection, course/batch CRUD, support ticket replies & lightbox review, activity logs, MongoDB backups, portal settings, Theme Studio, and own profile/password.",
}

ROLE_POLLS = {
    "STUDENT": {"question": "Aap kis Student feature mein madad chahte hain?", "options": [
        {"label": "My Report Card", "prompt": "Open my report card page"},
        {"label": "Study Tips & GPA", "prompt": "Give me study tips based on my attendance and GPA"},
        {"label": "Submit Help Ticket", "prompt": "Open support ticket form"},
        {"label": "Print A4 Report", "prompt": "Print A4 report"},
    ]},
    "TEACHER": {"question": "Teacher Portal mein aap kya karna chahte hain?", "options": [
        {"label": "Quick Marks Entry", "prompt": "Open quick marks entry form"},
        {"label": "Filter High Risk", "prompt": "Filter high risk students"},
        {"label": "Open Student List", "prompt": "Go to student list page"},
        {"label": "Print Class Roster", "prompt": "Print A4 report"},
    ]},
    "ANALYST": {"question": "Data & ML Hub mein kaunsa action chalayein?", "options": [
        {"label": "Model Accuracy", "prompt": "Check ML model accuracy and risk distribution"},
        {"label": "Open Model Health", "prompt": "Go to model health page"},
        {"label": "Filter High Risk", "prompt": "Filter high risk predictions"},
        {"label": "Open Data Hub", "prompt": "Go to data hub"},
    ]},
    "ADMIN": {"question": "Admin Portal mein kaunsa task start karein?", "options": [
        {"label": "Add New Course", "prompt": "Open create course form"},
        {"label": "Add New User", "prompt": "Open create user form"},
        {"label": "Review Open Tickets", "prompt": "Go to help tickets and filter open"},
        {"label": "Open Portal Settings", "prompt": "Go to portal settings"},
    ]},
}

_FORM_POLLS = {
    "support_ticket": {"question": "Support Ticket kis topic par bhejna hai?", "options": [
        {"label": "Marks Mismatch", "prompt": "Open support ticket subject: Marks Mismatch message: Please review my uploaded internal marks."},
        {"label": "Attendance Issue", "prompt": "Open support ticket subject: Attendance Update message: My recent class attendance needs correction."},
        {"label": "Login / Account Help", "prompt": "Open support ticket subject: Account Help message: Need assistance with my portal account."},
    ]},
    "profile_update": {"question": "Profile ka kaunsa field update karna hai?", "options": [
        {"label": "Update Department", "prompt": "Update profile department: Computer Science batch: 2026-A"},
        {"label": "Update Bio", "prompt": "Update profile bio: Focused on academic excellence and analytics."},
        {"label": "Change Password", "prompt": "Open change password"},
    ]},
    "quick_marks": {"question": "Quick Marks Entry ke liye preset sample try karein:", "options": [
        {"label": "CS-101 Sample Entry", "prompt": "Add marks student_id: STD-2026-001 course_code: CS-101 marks: 82 attendance: 88"},
        {"label": "Low Attendance Alert", "prompt": "Add marks student_id: STD-2026-002 course_code: SE-201 marks: 55 attendance: 60"},
        {"label": "Open Upload Marks", "prompt": "Go to upload marks page"},
    ]},
    "create_course": {"question": "Naya course add karne ke liye template chunein:", "options": [
        {"label": "CS-401 AI Systems", "prompt": "Create course course_code: CS-401 title: Applied AI Systems department: Computer Science batch: 2026-A credits: 3 capacity: 60"},
        {"label": "DS-305 Big Data", "prompt": "Create course course_code: DS-305 title: Big Data Engineering department: Data Science batch: 2026-A credits: 3 capacity: 50"},
        {"label": "View Courses Page", "prompt": "Go to courses page"},
    ]},
    "create_user": {"question": "Naya user kis role ke sath add karna hai?", "options": [
        {"label": "Add Student", "prompt": "Add user full_name: Ayesha Khan email: ayesha.khan@edupredict.edu role: STUDENT department: Computer Science batch: 2026-A"},
        {"label": "Add Teacher", "prompt": "Add user full_name: Dr. Tariq Mahmood email: tariq@edupredict.edu role: TEACHER department: Computer Science batch: ALL"},
        {"label": "Open Users Page", "prompt": "Go to users page"},
    ]},
}

_SECRET_RE = re.compile(r"(password_hash|secret_key|secret\s+key|api_key|api\s+key|\.env\b|dotenv|env\s+file|mongodb_uri|cloudinary_api|gemini_backend_key|access_token|auth_token|csrf_token|session_key|bearer\s+token|\bjwt\b|\bcredentials\b|\bcreds\b|\btokens?\b)", re.I)
_SELF_PWD_RE = re.compile(r"\b(change|update|reset|open)\b.*\bpassword\b|\bpassword\b.*\b(change|update|reset|modal|dialog)\b", re.I)
_PWD_LEAK_RE = re.compile(r"\b(show|give|tell|reveal|dump|print|fetch|read|get|what|find|other|admin|teacher|student|analyst|someone|all|list|hash|secret|api|env)\b", re.I)
_FIELD_STOP = r"(?=\s+(?:subject|message|full_name|name|email|role|department|dept|batch|phone|bio|student_id|course_code|course|marks|internal_marks|attendance|attendance_pct|title|instructor|credits|capacity)\s*[:=]|$)"

_FORM_SPECS = (
    ("support_ticket", ("STUDENT", "TEACHER", "ANALYST"), r"\b(support ticket|help ticket|new ticket|open ticket|create ticket|submit ticket|send feedback|report issue|file ticket|contact support)\b", "Open Support Ticket Form", 2, (("subject", ("subject", "title")), ("message", ("message", "details", "issue")))),
    ("profile_update", ("STUDENT", "TEACHER", "ANALYST", "ADMIN"), r"\b(update profile|edit profile|fill profile|update bio|change bio|update phone|update department|update batch)\b", "Open Edit Profile Form", 1, (("full_name", ("full_name", "name")), ("department", ("department", "dept")), ("batch", ("batch",)), ("phone", ("phone", "contact")), ("bio", ("bio",)), ("email", ("email",)))),
    ("quick_marks", ("TEACHER",), r"\b(add marks|enter marks|quick entry|update marks|fill marks|record marks|log marks|student marks)\b", "Open Quick Marks Form", 3, (("student_id", ("student_id", "student")), ("full_name", ("full_name", "name")), ("course_code", ("course_code", "course")), ("internal_marks", ("internal_marks", "marks")), ("attendance_pct", ("attendance_pct", "attendance")))),
    ("create_course", ("ADMIN",), r"\b(create course|add course|new course|open course form)\b", "Open Create Course Form", 2, (("course_code", ("course_code", "code")), ("title", ("title", "name")), ("department", ("department", "dept")), ("batch", ("batch",)), ("instructor", ("instructor", "teacher")), ("credits", ("credits",)), ("capacity", ("capacity", "seats")))),
    ("create_user", ("ADMIN",), r"\b(create user|add user|new user|create teacher|add student|new analyst|add admin)\b", "Open Create User Form", 2, (("full_name", ("full_name", "name")), ("email", ("email",)), ("role", ("role",)), ("department", ("department", "dept")), ("batch", ("batch",)))),
)


def _extract_field(text, keys):
    for k in keys:
        m = re.search(rf"\b{k}\s*[:=]\s*([^\n]+?){_FIELD_STOP}", str(text or ""), re.I)
        if m and m.group(1).strip():
            return m.group(1).strip().strip("\"'")
    return ""


def _history_text(history):
    if not isinstance(history, list):
        return ""
    return " ".join(str(item.get("text") or "").strip() for item in history[-4:] if isinstance(item, dict) and item.get("text"))


def evaluate_rbac_privacy_guard(user_doc, message):
    user = user_doc if isinstance(user_doc, dict) else {}
    role = str(user.get("role") or "STUDENT").strip().upper()
    own_sid = str(user.get("student_id") or "").strip().upper()
    low = re.sub(r"\s+", " ", str(message or "").strip().lower())
    if not low:
        return None, None
    if _SECRET_RE.search(low) or (re.search(r"\b(passwords?|passcode|pwd)\b", low) and (not _SELF_PWD_RE.search(low) or _PWD_LEAK_RE.search(low))):
        return "Security Policy: I cannot view, reveal, or share passwords, password hashes, secret keys, API keys, .env variables, tokens, or credentials. You can only update your own password safely via Change Password.", "security_policy"
    if role == "STUDENT":
        foreign_sid = bool(own_sid and any(s.upper() != own_sid for s in re.findall(r"\bstd-[a-z0-9-]+\b", low)))
        if foreign_sid or re.search(r"\b(admin|administrator)\b.*\b(email|detail|details|info|account|panel|user|users|log|logs|setting|settings|backup|ticket|tickets)\b|\b(teacher|teachers|instructor|instructors)\b.*\b(email|emails|phone|contact|private|detail|details|info|panel|account)\b|\b(other students?|another student|all students|classmates?|friend'?s|student list|class roster|export roster|user list|all users|list users|manage users|user management|create user|delete user|edit user|approve teacher|reject teacher|activity logs?|audit logs?|system logs?|admin logs?|backups?|export backup|portal settings|admin settings|system settings|theme studio|upload marks|teacher panel|analyst panel|run ml|upload dataset|model health)\b", low):
            return "RBAC Privacy Guard: As a Student, you cannot access Admin details, Teacher private info, other students' records, user lists, activity logs, backups, or portal settings. Your Student scope covers: my attendance, marks, predicted GPA, study tips, A4 report card, and help tickets.", "role_isolation"
    elif role == "TEACHER" and re.search(r"\b(admin\b.*\b(email|detail|details|info|account|panel|log|logs|credentials)|create user|add user|delete user|remove user|user list|all users|manage users|user management|approve teacher|reject teacher|activity logs?|audit logs?|system settings|portal settings|admin settings|theme studio|backups?|export backup)\b", low):
        return "RBAC Privacy Guard: As a Teacher, you cannot access Admin details, user creation/deletion, activity logs, system settings, or backups. Your Teacher scope covers: class overview, student performance list, marks/attendance upload, risk alerts, and A4 class roster PDF.", "role_isolation"
    elif role == "ANALYST" and re.search(r"\b(create user|add user|delete user|remove user|edit user|user list|all users|manage users|user management|approve teacher|reject teacher|admin panel|admin settings|portal settings|system settings|theme studio|activity logs?|audit logs?|backups?|export backup)\b", low):
        return "RBAC Privacy Guard: As a Data Analyst, you cannot access user creation/deletion, user management, admin settings, activity logs, or backups. Your Analyst scope covers: dataset upload, ML predictions, model evaluation metrics, live LMS stream, and model health.", "role_isolation"
    return None, None


def check_rbac_privacy_guard(user_doc, message):
    return evaluate_rbac_privacy_guard(user_doc, message)[0]


def _detect_filter_query(low):
    has_filter_verb = bool(re.search(r"\b(filter|search|find|show only|sort by|narrow|list)\b", low))
    for phrase, query in (("high risk", "High"), ("medium risk", "Medium"), ("low risk", "Low"), ("unread", "Unread"), ("resolved", "Resolved"), ("pending", "Pending"), ("open tickets", "Open"), ("needs help", "Needs Help"), ("anomaly", "Anomaly"), ("anomalies", "Anomaly")):
        if phrase in low and (has_filter_verb or len(low.split()) <= 5):
            return query
    if has_filter_verb and re.search(r"\bopen\b", low):
        return "Open"
    m = re.search(r"\b(?:filter|search)\s+(?:by|for|table)?\s*([a-z0-9_.-]{2,32})", low)
    if m and m.group(1) not in ("the", "table", "rows", "students", "users", "tickets", "alerts", "records", "me"):
        return m.group(1).upper() if "-" in m.group(1) else m.group(1)
    return ""


def _detect_form_action(role, raw_msg, low, history):
    combined = f"{_history_text(history)} {raw_msg}".strip()
    route_map = {"support_ticket": "/student-panel/notifications/" if role == "STUDENT" else "/notifications/", "profile_update": "/profile/", "quick_marks": "/teacher-panel/ingest/", "create_course": "/admin-panel/courses/", "create_user": "/admin-panel/users/"}
    for kind, allowed_roles, pat, label, min_fields, fdefs in _FORM_SPECS:
        if role not in allowed_roles or not re.search(pat, low):
            continue
        fields = {}
        for fname, keys in fdefs:
            val = _extract_field(raw_msg, keys)
            if val:
                fields[fname] = val.upper() if kind == "create_user" and fname == "role" else val
        if kind == "quick_marks":
            for fname, regex, upper in (("student_id", r"\b(STD-[A-Z0-9-]+)\b", True), ("course_code", r"\b([A-Z]{2,5}-\d{2,4})\b", True), ("internal_marks", r"\bmarks?\s+(\d+(?:\.\d+)?)\b", False), ("attendance_pct", r"\battendance\s+(\d+(?:\.\d+)?)\b", False)):
                m = re.search(regex, combined if fname in ("student_id", "course_code") else raw_msg, re.I)
                if fname not in fields and m:
                    fields[fname] = m.group(1).upper() if upper else m.group(1)
        elif kind == "create_course" and "course_code" not in fields:
            m = re.search(r"\b([A-Z]{2,5}-\d{2,4})\b", raw_msg)
            if m:
                fields["course_code"] = m.group(1).upper()
        elif kind == "create_user" and "email" not in fields:
            m = re.search(r"\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})\b", raw_msg)
            if m:
                fields["email"] = m.group(1).lower()
        return {"type": "open_and_fill_form", "form_kind": kind, "route": route_map[kind], "fields": fields, "label": label, "auto": True}, len(fields) < min_fields
    return None, False


def build_role_poll(role):
    return dict(ROLE_POLLS.get(str(role or "STUDENT").strip().upper(), ROLE_POLLS["STUDENT"]))


def build_dom_actions_and_poll(user_doc, message, history=None):
    user = user_doc if isinstance(user_doc, dict) else {}
    role = str(user.get("role") or "STUDENT").strip().upper()
    role = role if role in ROLE_ROUTES else "STUDENT"
    raw_msg = str(message or "").strip()
    low = re.sub(r"\s+", " ", raw_msg.lower())
    dom_actions, poll = [], None
    is_nav_cmd = bool(re.search(r"\b(go to|open|navigate|redirect|take me|visit|switch to|view|kholo|jao|le chalo)\b", low))
    is_cmd = bool(re.search(r"\b(open|click|trigger|start|print|download|export|change|update|reset|karo|kholo)\b", low))

    if role in ("STUDENT", "TEACHER") and re.search(r"\b(print report|print a4|print transcript|print roster)\b", low):
        dom_actions.append({"type": "click_element", "action": "print_a4_report", "label": "Print A4 Report", "auto": is_cmd})
    if role in ("STUDENT", "TEACHER") and re.search(r"\b(download pdf|export pdf|pdf transcript|pdf roster)\b", low):
        dom_actions.append({"type": "click_element", "action": "download_pdf", "label": "Download A4 PDF", "auto": is_cmd})
    if _SELF_PWD_RE.search(low):
        dom_actions.append({"type": "click_element", "action": "open_change_password", "label": "Open Change Password", "auto": is_cmd})
    if role == "ADMIN" and re.search(r"\b(theme studio|change theme|theme colors)\b", low):
        dom_actions.append({"type": "click_element", "action": "open_theme_studio", "label": "Open Theme Studio", "auto": is_cmd})

    form_act, form_incomplete = _detect_form_action(role, raw_msg, low, history)
    if form_act:
        dom_actions.append(form_act)
        if form_incomplete:
            poll = dict(_FORM_POLLS.get(form_act["form_kind"], build_role_poll(role)))

    filter_q = _detect_filter_query(low)
    if filter_q:
        dom_actions.append({"type": "filter_table", "query": filter_q, "label": "Filter: " + filter_q, "auto": True})

    if not form_act and not any(a["type"] == "click_element" for a in dom_actions):
        best_route, best_score = None, 0
        for url, title, kws in ROLE_ROUTES[role]:
            score = sum(len(kw.split()) * 2 for kw in kws if re.search(r"\b" + re.escape(kw) + r"\b", low))
            if score > best_score:
                best_route, best_score = (url, title), score
        if best_route and (is_nav_cmd or best_score >= 2):
            dom_actions.append({"type": "redirect", "url": best_route[0], "label": "Go to " + best_route[1], "auto": is_nav_cmd})

    broad = bool(re.search(r"\b(what can you do|help|kya kar sakta|kya kar sakte|capabilities|options|menu|guide me|hi|hello|salam|assalam)\b", low))
    if poll is None and (broad or (not dom_actions and len(low.split()) <= 3)):
        poll = build_role_poll(role)
    return dom_actions, poll
