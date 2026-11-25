from core.db import (
    courses_col,
    get_cached,
    predictions_col,
    resolve_portal_branding,
    student_records_col,
    support_tickets_col,
    users_col,
)

CAMPUS_COORDS = [
    ("Karachi", "PK", 24.8607, 67.0011, "#2563eb"),
    ("Lahore", "PK", 31.5204, 74.3587, "#059669"),
    ("Islamabad", "PK", 33.6844, 73.0479, "#d97706"),
    ("Dubai", "AE", 25.2048, 55.2708, "#0284c7"),
    ("London", "UK", 51.5072, -0.1276, "#7c3aed"),
    ("Toronto", "CA", 43.6532, -79.3832, "#dc2626"),
]


def _initials(name):
    parts = [p for p in str(name or "").strip().split() if p]
    if not parts:
        return "EP"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def _is_meaningful_feedback(subject, message):
    subj = str(subject or "").strip()
    msg = str(message or "").strip()
    if len(subj) < 6 or len(msg) < 18:
        return False
    words = [w for w in msg.split() if len(w) >= 2]
    if len(words) < 4:
        return False
    vowels = sum(1 for ch in msg.lower() if ch in "aeiou")
    return vowels >= max(3, int(len(msg) * 0.2))


def _build_live_credentials(current_term):
    courses = list(courses_col().find({}, {"_id": 0}).limit(25))
    course_map = {}
    for c in courses:
        code = str(c.get("course_code") or c.get("code") or "").strip().upper()
        if code:
            course_map[code] = c

    preds = list(predictions_col().find({}, {"_id": 0}).sort("updated_at", -1).limit(20))
    pred_map = {str(p.get("student_id") or "").strip(): p for p in preds if p.get("student_id")}
    records = list(student_records_col().find({}, {"_id": 0}).limit(30))

    cards = []
    seen_students = set()
    for rec in records:
        sid = str(rec.get("student_id") or "").strip()
        if not sid or sid in seen_students:
            continue
        pred = pred_map.get(sid)
        if not pred and len(cards) >= 3:
            continue
        seen_students.add(sid)
        raw_course = str(rec.get("course_code") or rec.get("course") or "").strip().upper()
        c_doc = course_map.get(raw_course) or (courses[len(cards) % len(courses)] if courses else {})
        c_code = str(c_doc.get("course_code") or c_doc.get("code") or raw_course or "CS-101").strip().upper()
        c_title = str(c_doc.get("title") or "Academic Course").strip()
        instructor = str(c_doc.get("instructor") or "Assigned Faculty").strip()
        student_name = str(rec.get("student_name") or rec.get("full_name") or rec.get("name") or sid).strip()
        program = str(rec.get("program_level") or c_doc.get("program_level") or rec.get("department") or "BS / Undergraduate").strip()
        gpa_val = pred.get("predicted_gpa") if pred else rec.get("gpa")
        try:
            gpa_str = f"{float(gpa_val):.2f}" if gpa_val is not None else "3.20"
        except (TypeError, ValueError):
            gpa_str = "3.20"
        risk_raw = str((pred or {}).get("risk_level") or "LOW").strip().upper()
        suffix = sid.split("-")[-1] if "-" in sid else sid[-4:]
        clean_code = "".join(ch for ch in c_code if ch.isalnum()) or "REC"
        cards.append(
            {
                "id": f"CERT-{clean_code}-{suffix}",
                "program": program,
                "course": f"{c_code} · {c_title}",
                "short_course": f"{c_code} · {c_title[:22]}",
                "student": f"{sid} · {student_name}",
                "student_name": student_name,
                "student_id": sid,
                "gpa": gpa_str,
                "risk": f"{risk_raw} RISK",
                "risk_short": risk_raw,
                "term": current_term,
                "issuer": f"Registrar & {instructor}",
                "marks": int(round(float(rec.get("marks") or rec.get("final_score") or 80))),
                "attendance": int(round(float(rec.get("attendance") or rec.get("attendance_pct") or 85))),
                "instructor": instructor,
                "course_code": c_code,
            }
        )
        if len(cards) >= 3:
            break
    return cards


def _build_live_testimonials(current_term):
    users = list(users_col().find({"is_active": True}, {"_id": 0, "full_name": 1, "role": 1, "department": 1, "program_level": 1}).limit(25))
    user_dept = {str(u.get("full_name") or "").strip().lower(): str(u.get("department") or "Campus").strip() for u in users}
    tickets = list(support_tickets_col().find({}, {"_id": 0}).sort("created_at", -1).limit(20))

    items = []
    seen_names = set()
    for t in tickets:
        name = str(t.get("user_name") or "").strip()
        subj = str(t.get("subject") or "").strip()
        msg = str(t.get("message") or "").strip()
        if not name or name.lower() in seen_names or not _is_meaningful_feedback(subj, msg):
            continue
        seen_names.add(name.lower())
        idx = len(items) % len(CAMPUS_COORDS)
        city, country, lat, lng, tone = CAMPUS_COORDS[idx]
        role_raw = str(t.get("role") or "MEMBER").strip().upper()
        role_label = {"STUDENT": "Student", "TEACHER": "Faculty", "ANALYST": "Data Analyst", "ADMIN": "Administrator", "GUEST": "Campus Visitor"}.get(role_raw, role_raw.title())
        dept = user_dept.get(name.lower()) or "EduPredict Portal"
        status_label = str(t.get("status") or "OPEN").strip().upper()
        clean_msg = msg.split("]", 1)[-1].strip() if msg.startswith("[Public Contact:") else msg
        quote = f"{subj}: {clean_msg}"
        if len(quote) > 175:
            quote = quote[:172].rstrip() + "..."
        items.append(
            {
                "name": name,
                "role": role_label,
                "org": f"{dept} · {status_label}",
                "city": city,
                "country": country,
                "lat": lat,
                "lng": lng,
                "rating": 5 if status_label == "RESOLVED" else 4,
                "initials": _initials(name),
                "tone": tone,
                "quote": quote,
            }
        )
        if len(items) >= 6:
            break

    if len(items) < 6:
        for u in users:
            name = str(u.get("full_name") or "").strip()
            if not name or name.lower() in seen_names:
                continue
            seen_names.add(name.lower())
            idx = len(items) % len(CAMPUS_COORDS)
            city, country, lat, lng, tone = CAMPUS_COORDS[idx]
            role_raw = str(u.get("role") or "MEMBER").strip().upper()
            dept = str(u.get("department") or "Academic Portal").strip()
            prog = str(u.get("program_level") or current_term).strip()
            role_quotes = {
                "TEACHER": f"Managing {dept} attendance and 3-column marks uploads in {current_term} gives early clarity on students needing support.",
                "ANALYST": f"Tracking {dept} RandomForest, Ridge, and IsolationForest runs keeps campus risk thresholds calibrated in real time.",
                "STUDENT": f"Checking {dept} ({prog}) marks, predicted GPA, and A4 transcripts keeps semester progress clear.",
                "ADMIN": f"Connecting {dept} faculty, courses, and student cohorts in one place keeps approvals and reporting organized.",
            }
            items.append(
                {
                    "name": name,
                    "role": role_raw.title(),
                    "org": f"{dept} · {current_term}",
                    "city": city,
                    "country": country,
                    "lat": lat,
                    "lng": lng,
                    "rating": 5,
                    "initials": _initials(name),
                    "tone": tone,
                    "quote": role_quotes.get(role_raw, f"Active {dept} member on EduPredict for {current_term}."),
                }
            )
            if len(items) >= 6:
                break
    return items


def get_public_landing_showcase():
    def _fetch():
        _, current_term = resolve_portal_branding(db_connected=True)
        try:
            credentials = _build_live_credentials(current_term)
        except Exception:
            credentials = []
        try:
            testimonials = _build_live_testimonials(current_term)
        except Exception:
            testimonials = []
        first = credentials[0] if credentials else {}
        walkthrough = {
            "course_label": first.get("course") or "No active courses yet",
            "course_program": first.get("program") or "BS / Undergraduate",
            "course_teacher": first.get("instructor") or "Assigned Faculty",
            "student_id": first.get("student_id") or "STD-2026-001",
            "marks": first.get("marks") if first else 0,
            "attendance": first.get("attendance") if first else 0,
            "gpa": first.get("gpa") or "0.00",
            "risk": first.get("risk_short") or "LOW",
        }
        return {"credentials": credentials, "testimonials": testimonials, "walkthrough": walkthrough}

    return get_cached("public:landing_showcase", _fetch, ttl=60.0)
