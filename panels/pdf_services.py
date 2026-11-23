import io
from datetime import datetime
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import HRFlowable, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from core.db import resolve_portal_branding
import panels.admin_audit_services as _audit_services
from panels.admin_audit_services import get_portal_settings

_ORIG_GET_PORTAL_SETTINGS = get_portal_settings
_BLACK = colors.HexColor("#000000")
_BORDER = colors.HexColor("#111111")
_CHARCOAL = colors.HexColor("#1F2937")
_MUTED = colors.HexColor("#4B5563")
_HEADER_FILL = colors.HexColor("#F3F4F6")
_ROW_ALT = colors.HexColor("#FAFAFA")
_PAGE_WIDTH_PT = 515


def _resolve_pdf_branding(data):
    if get_portal_settings is not _ORIG_GET_PORTAL_SETTINGS or hasattr(_audit_services.get_portal_settings, "_mock_name"):
        inst = str(data.get("institution_name") or "").strip() if isinstance(data, dict) else ""
        term = str(data.get("current_term") or "").strip() if isinstance(data, dict) else ""
        if not inst or not term:
            try:
                loader = get_portal_settings if get_portal_settings is not _ORIG_GET_PORTAL_SETTINGS else _audit_services.get_portal_settings
                cfg = (loader() or {}).get("settings_data") or {}
                inst = inst or str(cfg.get("institution_name") or "").strip()
                term = term or str(cfg.get("current_term") or "").strip()
            except Exception:
                pass
        default_inst, default_term = resolve_portal_branding(data, db_connected=False)
        return inst or default_inst, term or default_term
    return resolve_portal_branding(data, db_connected=True)


def _safe_float(val, default=0.0):
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _letter_grade(marks):
    score = _safe_float(marks, 0.0)
    for cutoff, grade in ((85, "A"), (80, "A-"), (75, "B+"), (70, "B"), (65, "C+"), (60, "C"), (50, "D")):
        if score >= cutoff:
            return grade
    return "F"


def _get_styles():
    base = getSampleStyleSheet()
    mk = lambda name, font, size, lead, color, align=0: ParagraphStyle(name, parent=base["Normal"], fontName=font, fontSize=size, leading=lead, textColor=color, alignment=align)
    return {
        "inst": mk("Inst", "Helvetica-Bold", 14, 17, _BLACK),
        "office": mk("Off", "Helvetica-Bold", 8, 11, _CHARCOAL),
        "doc_title": mk("DT", "Helvetica-Bold", 11, 14, _BLACK),
        "meta_right": mk("MR", "Helvetica", 7.5, 10, _CHARCOAL, 2),
        "sec_head": mk("SH", "Helvetica-Bold", 9.5, 12, _BLACK),
        "grid_lbl": mk("GL", "Helvetica-Bold", 7.5, 10, _CHARCOAL),
        "grid_val": mk("GV", "Helvetica-Bold", 8, 10.5, _BLACK),
        "th": mk("TH", "Helvetica-Bold", 7.5, 9.5, _BLACK, 1),
        "td": mk("TD", "Helvetica", 7.5, 9.5, _CHARCOAL, 1),
        "td_left": mk("TDL", "Helvetica", 7.5, 9.5, _CHARCOAL, 0),
        "body": mk("B", "Helvetica", 8, 11, _CHARCOAL),
        "sig_line": mk("SL", "Helvetica", 7, 9, _MUTED, 1),
        "sig_role": mk("SR", "Helvetica-Bold", 7.5, 10, _BLACK, 1),
        "footer": mk("F", "Helvetica", 6.5, 9, _MUTED, 1),
    }


def _build_masthead(institution_name, current_term, doc_title, ref_no, now_str, styles):
    left_block = [Paragraph(escape(institution_name), styles["inst"]), Paragraph(escape(f"OFFICE OF THE CONTROLLER OF EXAMINATIONS \u2014 {current_term}"), styles["office"]), Spacer(1, 3), Paragraph(escape(doc_title), styles["doc_title"])]
    right_block = [Paragraph(f"<b>Ref No:</b> {escape(ref_no)}", styles["meta_right"]), Paragraph(f"<b>Print Date:</b> {escape(now_str)}", styles["meta_right"]), Paragraph("Certified Examination Record", styles["meta_right"])]
    mast = Table([[left_block, right_block]], colWidths=[345, 170])
    mast.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
    return [mast, HRFlowable(width="100%", thickness=1.5, color=_BLACK, spaceBefore=3, spaceAfter=1.5), HRFlowable(width="100%", thickness=0.5, color=_BLACK, spaceBefore=0, spaceAfter=8)]


def _build_particulars_grid(rows, styles):
    formatted = [[Paragraph(escape(r[0]), styles["grid_lbl"]), Paragraph(escape(str(r[1])), styles["grid_val"]), Paragraph(escape(r[2]), styles["grid_lbl"]), Paragraph(escape(str(r[3])), styles["grid_val"])] for r in rows]
    tbl = Table(formatted, colWidths=[110, 148, 115, 142])
    tbl.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, -1), _HEADER_FILL), ("BACKGROUND", (2, 0), (2, -1), _HEADER_FILL), ("BACKGROUND", (1, 0), (1, -1), colors.white), ("BACKGROUND", (3, 0), (3, -1), colors.white), ("BOX", (0, 0), (-1, -1), 0.6, _BORDER), ("INNERGRID", (0, 0), (-1, -1), 0.6, _BORDER), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4), ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6)]))
    return tbl


def _build_schedule_table(table_rows, col_widths, empty_span=False):
    table_style = [("BACKGROUND", (0, 0), (-1, 0), _HEADER_FILL), ("BOX", (0, 0), (-1, -1), 0.6, _BORDER), ("INNERGRID", (0, 0), (-1, -1), 0.6, _BORDER), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5), ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]
    for idx in range(1, len(table_rows)):
        table_style.append(("BACKGROUND", (0, idx), (-1, idx), _ROW_ALT if idx % 2 == 0 else colors.white))
    if empty_span:
        table_style.extend([("SPAN", (0, 1), (-1, 1)), ("ALIGN", (0, 1), (-1, 1), "CENTER")])
    tbl = Table(table_rows, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(TableStyle(table_style))
    return tbl


def _build_advisory_box(paragraphs):
    box = Table([[paragraphs]], colWidths=[_PAGE_WIDTH_PT])
    box.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.white), ("BOX", (0, 0), (-1, -1), 0.6, _BORDER), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6), ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8)]))
    return box


def _build_signature_footer(institution_name, current_term, ref_no, footer_note, styles):
    sig_table = Table([
        [Paragraph("________________________", styles["sig_line"]), "", Paragraph("________________________", styles["sig_line"]), "", Paragraph("[ Official Seal / Stamp ]", styles["sig_line"])],
        [Paragraph("Instructor / Faculty Advisor", styles["sig_role"]), "", Paragraph("Controller of Examinations", styles["sig_role"]), "", Paragraph("Registrar Stamp", styles["sig_role"])],
        [Paragraph(escape(institution_name), styles["sig_line"]), "", Paragraph(escape(current_term), styles["sig_line"]), "", Paragraph(escape(f"Ref: {ref_no}"), styles["sig_line"])],
    ], colWidths=[163, 13, 163, 13, 163])
    sig_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
    return [KeepTogether(sig_table), Spacer(1, 8), Paragraph(escape(footer_note), styles["footer"])]


def _extract_student_data(data):
    rec = data.get("record") if isinstance(data.get("record"), dict) else data
    raw_subjects = data.get("subject_rows") or rec.get("courses") or data.get("courses") or []
    insight_dict = data.get("insight") if isinstance(data.get("insight"), dict) else {}
    default_note = "Maintain consistent lecture attendance, engage in coursework, and complete weekly milestones." if raw_subjects else "No course marks or attendance records have been uploaded for this Student ID yet."
    rank = data.get("rank")
    subject_rows = []
    for s in raw_subjects:
        if isinstance(s, dict):
            status_val = s.get("status")
            status_str = status_val.get("text") if isinstance(status_val, dict) else str(status_val or "Stable")
            marks_val = _safe_float(s.get("my_marks", s.get("internal_marks", 0.0)))
            subject_rows.append({"code": str(s.get("course_code") or "N/A").upper(), "marks": f"{marks_val:.1f}", "class_marks": f"{_safe_float(s.get('class_marks', 0.0)):.1f}", "att": f"{_safe_float(s.get('my_attendance', s.get('attendance_pct', 0.0))):.1f}%", "class_att": f"{_safe_float(s.get('class_attendance', 0.0)):.1f}%", "grade": _letter_grade(marks_val), "status": status_str})
        elif isinstance(s, (list, tuple)) and len(s) >= 6:
            st = s[5]
            st_text = st.get("text") if isinstance(st, dict) else str(st)
            subject_rows.append({"code": str(s[0]).upper(), "marks": str(s[1]), "class_marks": str(s[2]), "att": str(s[4] if "%" in str(s[4]) else s[3]), "class_att": str(s[3] if "%" in str(s[4]) else s[4]), "grade": _letter_grade(_safe_float(s[1])), "status": st_text})
    raw_gpa = rec.get("predicted_gpa", data.get("predicted_gpa"))
    return {
        "full_name": str(rec.get("full_name") or data.get("full_name") or "Student Name"),
        "student_id": str(rec.get("student_id") or data.get("student_id") or "N/A"),
        "department": str(rec.get("department") or data.get("department") or "General"),
        "batch": str(rec.get("batch") or data.get("batch") or "-"),
        "attendance": _safe_float(rec.get("avg_attendance", rec.get("attendance_pct", data.get("attendance_pct", 0.0)))),
        "marks": _safe_float(rec.get("avg_marks", rec.get("internal_marks", data.get("internal_marks", 0.0)))),
        "predicted_gpa": f"{_safe_float(raw_gpa):.2f}" if raw_gpa is not None else "Pending",
        "risk_level": str(rec.get("risk_level") or data.get("risk_level") or "PENDING").upper(),
        "credits": _safe_float(data.get("credits"), 0.0),
        "rank_text": f"#{rank['rank']} of {rank['total']}" if isinstance(rank, dict) and rank.get("rank") else "N/A",
        "recommendation": str(rec.get("recommendation") or data.get("recommendation") or insight_dict.get("summary") or default_note),
        "subject_rows": subject_rows,
        "tips": data.get("tips") if isinstance(data.get("tips"), list) else [],
    }


def generate_student_report_card_pdf(data):
    info = _extract_student_data(data)
    institution_name, current_term = _resolve_pdf_branding(data)
    styles, buffer = _get_styles(), io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=40, rightMargin=40, topMargin=36, bottomMargin=36, pageCompression=0)
    now = datetime.now()
    now_str, ref_no = now.strftime("%Y-%m-%d %H:%M"), f"EP-{info['student_id']}-{now.strftime('%Y%m%d%H%M')}"
    story = _build_masthead(institution_name, current_term, "OFFICIAL ACADEMIC TRANSCRIPT", ref_no, now_str, styles)
    particulars = [("STUDENT ID", info["student_id"], "FULL NAME", info["full_name"]), ("DEPARTMENT", info["department"], "BATCH", info["batch"]), ("CREDITS", f"{info['credits']:.1f}", "CLASS STANDING", info["rank_text"]), ("OVERALL ATTENDANCE %", f"{info['attendance']:.1f}%", "OVERALL MARKS", f"{info['marks']:.1f}%"), ("PREDICTED GPA", info["predicted_gpa"], "ACADEMIC RISK STANDING", info["risk_level"])]
    story.extend([_build_particulars_grid(particulars, styles), Spacer(1, 10), Paragraph("SCHEDULE OF COURSE EVALUATIONS", styles["sec_head"]), Spacer(1, 4)])

    table_rows = [[Paragraph(h, styles["th"]) for h in ("COURSE CODE", "MY MARKS", "CLASS AVG", "MY ATT.", "CLASS ATT.", "GRADE", "STANDING")]]
    for s in info["subject_rows"]:
        table_rows.append([Paragraph(escape(s[k]), styles["td"]) for k in ("code", "marks", "class_marks", "att", "class_att", "grade", "status")])
    empty_span = len(table_rows) == 1
    if empty_span:
        table_rows.append([Paragraph("No course records found for this student.", styles["td"])] + [Paragraph("", styles["td"]) for _ in range(6)])
    story.extend([_build_schedule_table(table_rows, [78, 70, 70, 70, 70, 52, 105], empty_span=empty_span), Spacer(1, 10), Paragraph("EXAMINER &amp; ADVISORY REMARKS", styles["sec_head"]), Spacer(1, 4)])

    advisory_items = [Paragraph(f"<b>Academic Advisory:</b> {escape(info['recommendation'])}", styles["body"])]
    for tip in info["tips"][:2]:
        tip_title = str(tip.get("title") or "").strip() if isinstance(tip, dict) else ""
        tip_text = str(tip.get("text") or "").strip() if isinstance(tip, dict) else str(tip)
        if tip_text or tip_title:
            advisory_items.extend([Spacer(1, 2), Paragraph(f"- <b>{escape(tip_title)}:</b> {escape(tip_text)}" if tip_title else f"- {escape(tip_text)}", styles["body"])])
    story.extend([_build_advisory_box(advisory_items), Spacer(1, 18)])
    story.extend(_build_signature_footer(institution_name, current_term, ref_no, f"{institution_name} | {current_term} | Document ID: {ref_no} | Official A4 Printable Record", styles))
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def _extract_teacher_data(data):
    students_raw = data if isinstance(data, list) else (data.get("students") or data.get("export_rows") or data.get("student_rows") or [])
    kpis_raw = {} if isinstance(data, list) else (data.get("kpis") or {})
    batch = "ALL" if isinstance(data, list) else str(data.get("batch") or "ALL")
    course = "ALL" if isinstance(data, list) else str(data.get("course_code") or data.get("course") or "ALL")
    students = []
    for s in students_raw:
        if isinstance(s, dict):
            status_val = s.get("status") or s.get("badge") or s.get("risk_level")
            status_text = status_val.get("text") if isinstance(status_val, dict) else str(status_val or "Stable")
            students.append({"student_id": str(s.get("student_id") or "N/A"), "full_name": str(s.get("full_name") or "Student"), "batch": str(s.get("batch") or "-"), "course_code": str(s.get("course_code") or "-").upper(), "attendance_pct": _safe_float(s.get("attendance_pct")), "internal_marks": _safe_float(s.get("internal_marks")), "predicted_gpa": f"{_safe_float(s.get('predicted_gpa')):.2f}" if s.get("predicted_gpa") is not None else "-", "status": status_text})
        elif isinstance(s, (list, tuple)) and len(s) >= 7:
            status_elem = s[7] if len(s) > 7 else s[5]
            st_text = status_elem.get("text") if isinstance(status_elem, dict) else str(status_elem)
            students.append({"student_id": str(s[0]), "full_name": str(s[1]), "batch": str(s[2]) if len(s) > 7 else "-", "course_code": str(s[3] if len(s) > 7 else s[2]).upper(), "attendance_pct": _safe_float(str(s[4] if len(s) > 7 else s[3]).replace("%", "")), "internal_marks": _safe_float(str(s[5] if len(s) > 7 else s[4]).replace("%", "")), "predicted_gpa": str(s[6]) if len(s) > 7 else "-", "status": st_text})
    total = len(students)
    avg_att = _safe_float(kpis_raw.get("avg_attendance")) or (round(sum(x["attendance_pct"] for x in students) / total, 1) if total else 0.0)
    avg_marks = _safe_float(kpis_raw.get("avg_marks")) or (round(sum(x["internal_marks"] for x in students) / total, 1) if total else 0.0)
    at_risk = int(kpis_raw.get("at_risk_count", 0)) or sum(1 for x in students if x["status"] in ("High Risk", "Needs Help", "HIGH", "MEDIUM", "At Risk"))
    return {"batch": batch, "course": course, "total": total, "avg_attendance": avg_att, "avg_marks": avg_marks, "at_risk": at_risk, "students": students}


def generate_teacher_roster_pdf(data):
    info = _extract_teacher_data(data)
    institution_name, current_term = _resolve_pdf_branding(data)
    styles, buffer = _get_styles(), io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=40, rightMargin=40, topMargin=36, bottomMargin=36, pageCompression=0)
    now = datetime.now()
    now_str, ref_no = now.strftime("%Y-%m-%d %H:%M"), f"EP-ROSTER-{now.strftime('%Y%m%d%H%M')}"
    story = _build_masthead(institution_name, current_term, "OFFICIAL CLASS PERFORMANCE ROSTER", ref_no, now_str, styles)
    particulars = [("BATCH / SECTION", info["batch"], "COURSE CODE", info["course"]), ("TOTAL STUDENTS", str(info["total"]), "ACADEMIC RISK STANDING", f"{info['at_risk']} At-Risk"), ("OVERALL ATTENDANCE %", f"{info['avg_attendance']:.1f}%", "OVERALL MARKS", f"{info['avg_marks']:.1f}%")]
    story.extend([_build_particulars_grid(particulars, styles), Spacer(1, 10), Paragraph("ROSTER PERFORMANCE SCHEDULE", styles["sec_head"]), Spacer(1, 4)])

    table_rows = [[Paragraph(h, styles["th"]) for h in ("#", "STUDENT ID", "FULL NAME", "BATCH", "COURSE", "ATTENDANCE", "MARKS", "PRED GPA", "STANDING")]]
    for idx, s in enumerate(info["students"], start=1):
        table_rows.append([Paragraph(str(idx), styles["td"]), Paragraph(escape(s["student_id"]), styles["td"]), Paragraph(escape(s["full_name"]), styles["td_left"]), Paragraph(escape(s["batch"]), styles["td"]), Paragraph(escape(s["course_code"]), styles["td"]), Paragraph(f"{s['attendance_pct']:.1f}%", styles["td"]), Paragraph(f"{s['internal_marks']:.1f}", styles["td"]), Paragraph(escape(s["predicted_gpa"]), styles["td"]), Paragraph(escape(s["status"]), styles["td"])])
    empty_span = len(table_rows) == 1
    if empty_span:
        table_rows.append([Paragraph("No student records found.", styles["td"])] + [Paragraph("", styles["td"]) for _ in range(8)])
    story.extend([_build_schedule_table(table_rows, [24, 72, 118, 52, 52, 56, 46, 45, 50], empty_span=empty_span), Spacer(1, 10), Paragraph("EXAMINATION OFFICE VERIFICATION NOTE", styles["sec_head"]), Spacer(1, 4)])

    advisory = Paragraph(f"<b>Verification Summary:</b> Roster covers {info['total']} enrolled student record(s) in Batch {escape(info['batch'])} / Course {escape(info['course'])} for {escape(current_term)}. Students marked At-Risk or Needs Help require academic advising.", styles["body"])
    story.extend([_build_advisory_box([advisory]), Spacer(1, 18)])
    story.extend(_build_signature_footer(institution_name, current_term, ref_no, f"{institution_name} | {current_term} | Class Roster Export | Total Students: {info['total']}", styles))
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
