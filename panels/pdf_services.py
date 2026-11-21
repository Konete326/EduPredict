import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import HRFlowable, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
import panels.admin_audit_services as _audit_services
from panels.admin_audit_services import get_portal_settings

_ORIG_GET_PORTAL_SETTINGS = get_portal_settings


def _resolve_pdf_branding(data):
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
    return inst or "EduPredict Academic Portal", term or "Fall 2026"


def _safe_float(val, default=0.0):
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _letter_grade(marks):
    score = _safe_float(marks, 0.0)
    if score >= 85:
        return "A"
    if score >= 80:
        return "A-"
    if score >= 75:
        return "B+"
    if score >= 70:
        return "B"
    if score >= 65:
        return "C+"
    if score >= 60:
        return "C"
    if score >= 50:
        return "D"
    return "F"


def _risk_colors(risk_level):
    norm = str(risk_level or "").strip().upper()
    if norm in ("HIGH", "HIGH RISK", "DANGER", "AT RISK"):
        return colors.HexColor("#DC2626"), colors.HexColor("#FEE2E2")
    if norm in ("MEDIUM", "MEDIUM RISK", "WARNING", "NEEDS HELP"):
        return colors.HexColor("#D97706"), colors.HexColor("#FEF3C7")
    if norm in ("LOW", "LOW RISK", "SUCCESS", "EXCELLENT", "STABLE"):
        return colors.HexColor("#16A34A"), colors.HexColor("#DCFCE7")
    return colors.HexColor("#2563EB"), colors.HexColor("#DBEAFE")


def _get_styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("T", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=15, leading=18, textColor=colors.HexColor("#0F172A")),
        "subtitle": ParagraphStyle("Sub", parent=base["Normal"], fontName="Helvetica", fontSize=8, leading=11, textColor=colors.HexColor("#64748B")),
        "portal_tag": ParagraphStyle("Tag", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=9, leading=11, textColor=colors.HexColor("#2563EB")),
        "sec_head": ParagraphStyle("SH", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=10, leading=13, textColor=colors.HexColor("#0F172A")),
        "meta_lbl": ParagraphStyle("ML", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=7, leading=9, textColor=colors.HexColor("#64748B")),
        "meta_val": ParagraphStyle("MV", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=colors.HexColor("#0F172A")),
        "card_val": ParagraphStyle("CV", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=13, leading=15, alignment=1, textColor=colors.HexColor("#0F172A")),
        "card_lbl": ParagraphStyle("CL", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=7, leading=9, alignment=1, textColor=colors.HexColor("#64748B")),
        "th": ParagraphStyle("TH", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=7, leading=9, textColor=colors.white, alignment=1),
        "td": ParagraphStyle("TD", parent=base["Normal"], fontName="Helvetica", fontSize=7, leading=9, textColor=colors.HexColor("#1E293B"), alignment=1),
        "td_left": ParagraphStyle("TDL", parent=base["Normal"], fontName="Helvetica", fontSize=7, leading=9, textColor=colors.HexColor("#1E293B"), alignment=0),
        "body": ParagraphStyle("B", parent=base["Normal"], fontName="Helvetica", fontSize=8, leading=11, textColor=colors.HexColor("#334155")),
        "footer": ParagraphStyle("F", parent=base["Normal"], fontName="Helvetica", fontSize=6, leading=8, textColor=colors.HexColor("#94A3B8"), alignment=1),
        "sig_line": ParagraphStyle("SL", parent=base["Normal"], fontName="Helvetica", fontSize=7, leading=9, textColor=colors.HexColor("#475569"), alignment=1),
        "sig_role": ParagraphStyle("SR", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=colors.HexColor("#0F172A"), alignment=1),
    }


def _extract_student_data(data):
    rec = data.get("record") if isinstance(data.get("record"), dict) else data
    full_name = str(rec.get("full_name") or data.get("full_name") or "Student Name")
    student_id = str(rec.get("student_id") or data.get("student_id") or "N/A")
    department = str(rec.get("department") or data.get("department") or "Computer Science & IT")
    batch = str(rec.get("batch") or data.get("batch") or "2026-A")
    att = _safe_float(rec.get("avg_attendance", rec.get("attendance_pct", data.get("attendance_pct", 0.0))))
    marks = _safe_float(rec.get("avg_marks", rec.get("internal_marks", data.get("internal_marks", 0.0))))
    raw_gpa = rec.get("predicted_gpa", data.get("predicted_gpa"))
    pred_gpa = f"{_safe_float(raw_gpa):.2f}" if raw_gpa is not None else "Pending"
    risk = str(rec.get("risk_level") or data.get("risk_level") or "PENDING").upper()
    insight_dict = data.get("insight") if isinstance(data.get("insight"), dict) else {}
    recommendation = str(rec.get("recommendation") or data.get("recommendation") or insight_dict.get("summary") or "Maintain consistent lecture attendance, engage in LMS coursework, and complete weekly milestones.")
    raw_subjects = data.get("subject_rows") or rec.get("courses") or data.get("courses") or []
    credits = _safe_float(data.get("credits"), 0.0)
    rank = data.get("rank")
    rank_text = f"#{rank['rank']} of {rank['total']}" if isinstance(rank, dict) and rank.get("rank") else "N/A"
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
            marks_val = _safe_float(s[1])
            subject_rows.append({"code": str(s[0]).upper(), "marks": str(s[1]), "class_marks": str(s[2]), "att": str(s[4] if "%" in str(s[4]) else s[3]), "class_att": str(s[3] if "%" in str(s[4]) else s[4]), "grade": _letter_grade(marks_val), "status": st_text})
    return {
        "full_name": full_name, "student_id": student_id, "department": department, "batch": batch,
        "attendance": att, "marks": marks, "predicted_gpa": pred_gpa, "risk_level": risk,
        "credits": credits, "rank_text": rank_text,
        "recommendation": recommendation, "subject_rows": subject_rows, "tips": data.get("tips") if isinstance(data.get("tips"), list) else [],
    }


def generate_student_report_card_pdf(data):
    info = _extract_student_data(data)
    institution_name, current_term = _resolve_pdf_branding(data)
    styles = _get_styles()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=32, bottomMargin=32, pageCompression=0)
    story = []
    now_str = datetime.now().strftime("%B %d, %Y - %H:%M")

    header_table = Table([[Paragraph(f"{institution_name} ({current_term})", styles["portal_tag"]), Paragraph(f"Report Date: {now_str}", styles["meta_lbl"])], [Paragraph("OFFICIAL ACADEMIC TRANSCRIPT & REPORT CARD", styles["title"]), Paragraph("Official Academic Record", styles["subtitle"])]], colWidths=[380, 160])
    header_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (1, 0), (1, -1), "RIGHT"), ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
    story.extend([header_table, HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2563EB"), spaceBefore=4, spaceAfter=8)])

    meta_table = Table([
        [Paragraph("STUDENT ID", styles["meta_lbl"]), Paragraph("STUDENT NAME", styles["meta_lbl"]), Paragraph("DEPARTMENT", styles["meta_lbl"]), Paragraph("BATCH / CLASS", styles["meta_lbl"])],
        [Paragraph(info["student_id"], styles["meta_val"]), Paragraph(info["full_name"], styles["meta_val"]), Paragraph(info["department"], styles["meta_val"]), Paragraph(info["batch"], styles["meta_val"])],
        [Paragraph("EARNED CREDITS", styles["meta_lbl"]), Paragraph("CLASS STANDING", styles["meta_lbl"]), Paragraph("ACADEMIC STATUS", styles["meta_lbl"]), Paragraph("ISSUED BY", styles["meta_lbl"])],
        [Paragraph(f"{info['credits']:.1f}", styles["meta_val"]), Paragraph(info["rank_text"], styles["meta_val"]), Paragraph(info["risk_level"], styles["meta_val"]), Paragraph(f"{institution_name} Registrar", styles["meta_val"])],
    ], colWidths=[110, 170, 170, 90])
    meta_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")), ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")), ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    story.extend([meta_table, Spacer(1, 6)])

    risk_text_color, risk_bg_color = _risk_colors(info["risk_level"])
    kpi_table = Table([[Paragraph(f"{info['attendance']:.1f}%", styles["card_val"]), Paragraph(f"{info['marks']:.1f}%", styles["card_val"]), Paragraph(info["predicted_gpa"], styles["card_val"]), Paragraph(info["risk_level"], ParagraphStyle("RiskCard", parent=styles["card_val"], textColor=risk_text_color))], [Paragraph("CURRENT ATTENDANCE", styles["card_lbl"]), Paragraph("CURRENT MARKS", styles["card_lbl"]), Paragraph("PREDICTED GPA", styles["card_lbl"]), Paragraph("RISK LEVEL", styles["card_lbl"])]], colWidths=[135, 135, 135, 135])
    kpi_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (2, -1), colors.HexColor("#F1F5F9")), ("BACKGROUND", (3, 0), (3, -1), risk_bg_color), ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")), ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    story.extend([kpi_table, Spacer(1, 8), Paragraph("Subject Breakdown & Class Comparison", styles["sec_head"]), Spacer(1, 3)])

    table_rows = [[Paragraph("COURSE CODE", styles["th"]), Paragraph("MY MARKS", styles["th"]), Paragraph("CLASS AVG", styles["th"]), Paragraph("MY ATT.", styles["th"]), Paragraph("CLASS ATT.", styles["th"]), Paragraph("GRADE", styles["th"]), Paragraph("STATUS", styles["th"])]]
    for s in info["subject_rows"]:
        table_rows.append([Paragraph(s["code"], styles["td"]), Paragraph(s["marks"], styles["td"]), Paragraph(s["class_marks"], styles["td"]), Paragraph(s["att"], styles["td"]), Paragraph(s["class_att"], styles["td"]), Paragraph(s["grade"], styles["td"]), Paragraph(s["status"], styles["td"])])
    if len(table_rows) == 1:
        table_rows.append([Paragraph("No course records found for this student.", styles["td_left"]), Paragraph("", styles["td"]), Paragraph("", styles["td"]), Paragraph("", styles["td"]), Paragraph("", styles["td"]), Paragraph("", styles["td"]), Paragraph("", styles["td"])])

    sub_styles = [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")), ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")), ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    for idx in range(1, len(table_rows)):
        sub_styles.append(("BACKGROUND", (0, idx), (-1, idx), colors.HexColor("#F8FAFC") if idx % 2 == 0 else colors.white))
    subject_table = Table(table_rows, colWidths=[76, 76, 76, 78, 78, 56, 100])
    subject_table.setStyle(TableStyle(sub_styles))
    story.extend([subject_table, Spacer(1, 8), Paragraph("AI Recommendation Notes & Academic Advisory", styles["sec_head"]), Spacer(1, 3)])

    advisory_content = [Paragraph(f"<b>Primary Guidance:</b> {info['recommendation']}", styles["body"])]
    for tip in info["tips"][:2]:
        tip_title = tip.get("title") if isinstance(tip, dict) else ""
        tip_text = tip.get("text") if isinstance(tip, dict) else str(tip)
        advisory_content.append(Spacer(1, 2))
        advisory_content.append(Paragraph(f"• <b>{tip_title}:</b> {tip_text}" if tip_title else f"• {tip_text}", styles["body"]))

    advisory_table = Table([[advisory_content]], colWidths=[540])
    advisory_bg = colors.HexColor("#F0FDF4") if info["risk_level"] == "LOW" else colors.HexColor("#FEF2F2") if info["risk_level"] == "HIGH" else colors.HexColor("#EFF6FF")
    advisory_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), advisory_bg), ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#93C5FD")), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5), ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8)]))
    story.extend([advisory_table, Spacer(1, 14)])

    sig_table = Table([[Paragraph("________________________________________", styles["sig_line"]), "", Paragraph("________________________________________", styles["sig_line"])], [Paragraph("Academic Advisor / Faculty Mentor", styles["sig_role"]), "", Paragraph("Controller of Examinations / Dean", styles["sig_role"])], [Paragraph(f"{institution_name} Academic Verification", styles["sig_line"]), "", Paragraph(f"{institution_name} Registrar", styles["sig_line"])]], colWidths=[240, 60, 240])
    sig_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
    footer_text = f"{institution_name} ({current_term}) | Document ID: EP-{info['student_id']}-{datetime.now().strftime('%Y%m%d%H%M')} | Certified System Copy"
    story.extend([KeepTogether(sig_table), Spacer(1, 6), Paragraph(footer_text, styles["footer"])])

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def _extract_teacher_data(data):
    if isinstance(data, list):
        students_raw = data
        kpis_raw = {}
        batch = "ALL"
        course = "ALL"
    else:
        students_raw = data.get("students") or data.get("export_rows") or data.get("student_rows") or []
        kpis_raw = data.get("kpis") or {}
        batch = str(data.get("batch") or "ALL")
        course = str(data.get("course_code") or data.get("course") or "ALL")

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
    at_risk = int(kpis_raw.get("at_risk_count", 0)) or sum(1 for x in students if x["status"] in ("High Risk", "Needs Help", "HIGH", "MEDIUM"))

    return {"batch": batch, "course": course, "total": total, "avg_attendance": avg_att, "avg_marks": avg_marks, "at_risk": at_risk, "students": students}


def generate_teacher_roster_pdf(data):
    info = _extract_teacher_data(data)
    institution_name, current_term = _resolve_pdf_branding(data)
    styles = _get_styles()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=32, bottomMargin=32, pageCompression=0)
    story = []
    now_str = datetime.now().strftime("%B %d, %Y - %H:%M")

    header_table = Table([[Paragraph(f"{institution_name} ({current_term})", styles["portal_tag"]), Paragraph(f"Generated: {now_str}", styles["meta_lbl"])], [Paragraph("CLASS PERFORMANCE ROSTER", styles["title"]), Paragraph(f"Batch: {info['batch']} | Course: {info['course']} | Issued By: {institution_name} Registrar", styles["subtitle"])]], colWidths=[370, 170])
    header_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (1, 0), (1, -1), "RIGHT"), ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
    story.extend([header_table, HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2563EB"), spaceBefore=4, spaceAfter=8)])

    risk_style = ParagraphStyle("RiskCount", parent=styles["card_val"], textColor=colors.HexColor("#DC2626") if info["at_risk"] > 0 else colors.HexColor("#16A34A"))
    kpi_table = Table([[Paragraph(str(info["total"]), styles["card_val"]), Paragraph(f"{info['avg_attendance']:.1f}%", styles["card_val"]), Paragraph(f"{info['avg_marks']:.1f}%", styles["card_val"]), Paragraph(str(info["at_risk"]), risk_style)], [Paragraph("TOTAL STUDENTS", styles["card_lbl"]), Paragraph("AVG ATTENDANCE", styles["card_lbl"]), Paragraph("AVG MARKS", styles["card_lbl"]), Paragraph("AT-RISK STUDENTS", styles["card_lbl"])]], colWidths=[135, 135, 135, 135])
    kpi_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (2, -1), colors.HexColor("#F1F5F9")), ("BACKGROUND", (3, 0), (3, -1), colors.HexColor("#FEE2E2") if info["at_risk"] > 0 else colors.HexColor("#DCFCE7")), ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")), ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    story.extend([kpi_table, Spacer(1, 8), Paragraph("Student Performance & Evaluation Roster", styles["sec_head"]), Spacer(1, 3)])

    table_rows = [[Paragraph("#", styles["th"]), Paragraph("STUDENT ID", styles["th"]), Paragraph("FULL NAME", styles["th"]), Paragraph("BATCH", styles["th"]), Paragraph("COURSE", styles["th"]), Paragraph("ATTENDANCE", styles["th"]), Paragraph("MARKS", styles["th"]), Paragraph("PRED GPA", styles["th"]), Paragraph("STATUS", styles["th"])]]
    for idx, s in enumerate(info["students"], start=1):
        table_rows.append([Paragraph(str(idx), styles["td"]), Paragraph(s["student_id"], styles["td"]), Paragraph(s["full_name"], styles["td_left"]), Paragraph(s["batch"], styles["td"]), Paragraph(s["course_code"], styles["td"]), Paragraph(f"{s['attendance_pct']:.1f}%", styles["td"]), Paragraph(f"{s['internal_marks']:.1f}", styles["td"]), Paragraph(s["predicted_gpa"], styles["td"]), Paragraph(s["status"], styles["td"])])
    if len(table_rows) == 1:
        table_rows.append([Paragraph("No student records found.", styles["td_left"]), Paragraph("", styles["td"]), Paragraph("", styles["td"]), Paragraph("", styles["td"]), Paragraph("", styles["td"]), Paragraph("", styles["td"]), Paragraph("", styles["td"]), Paragraph("", styles["td"]), Paragraph("", styles["td"])])

    roster_styles = [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")), ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")), ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")), ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]
    for idx in range(1, len(table_rows)):
        roster_styles.append(("BACKGROUND", (0, idx), (-1, idx), colors.HexColor("#F8FAFC") if idx % 2 == 0 else colors.white))
    roster_table = Table(table_rows, colWidths=[24, 66, 120, 55, 55, 60, 55, 50, 55], repeatRows=1)
    roster_table.setStyle(TableStyle(roster_styles))
    story.extend([roster_table, Spacer(1, 12)])

    sig_table = Table([[Paragraph("________________________________________", styles["sig_line"]), "", Paragraph("________________________________________", styles["sig_line"])], [Paragraph("Class Instructor / Teacher Signature", styles["sig_role"]), "", Paragraph("Academic Head / Department Chair", styles["sig_role"])], [Paragraph(f"Date: {now_str}", styles["sig_line"]), "", Paragraph(f"{institution_name} Registrar", styles["sig_line"])]], colWidths=[240, 60, 240])
    sig_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
    footer_text = f"{institution_name} ({current_term}) | Class Roster Export | Total Students: {info['total']} | Batch: {info['batch']} | Course: {info['course']}"
    story.extend([KeepTogether(sig_table), Spacer(1, 6), Paragraph(footer_text, styles["footer"])])

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
