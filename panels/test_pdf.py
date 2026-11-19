from unittest.mock import MagicMock, patch
from django.test import Client, TestCase
from django.urls import reverse
from core.db import invalidate_cache
from panels.pdf_services import (
    generate_student_report_card_pdf,
    generate_teacher_roster_pdf,
)


def _login_client(user_data):
    client = Client()
    session = client.session
    session["user"] = dict(user_data)
    session.save()
    return client


def _mock_notifs_col():
    col = MagicMock()
    col.count_documents.return_value = 0
    col.find.return_value.sort.return_value.limit.return_value = []
    return col


def _sample_student_overview():
    return {
        "record": {
            "student_id": "STD-2026-001",
            "full_name": "Zainab Raza",
            "batch": "2026-A",
            "department": "Computer Science & IT",
            "courses": [
                {
                    "course_code": "CS-101",
                    "attendance_pct": 88.0,
                    "internal_marks": 82.0,
                    "assignment_score": 85.0,
                    "lms_hours_weekly": 8.0,
                }
            ],
            "avg_attendance": 88.0,
            "avg_marks": 82.0,
            "avg_assignment": 85.0,
            "lms_hours_weekly": 8.0,
            "previous_gpa": 3.4,
            "predicted_gpa": 3.55,
            "risk_level": "LOW",
            "risk_score": 0.12,
            "is_anomaly": False,
            "anomaly_reason": "",
            "recommendation": "Maintain consistent lecture attendance.",
            "generated_at": "2026-11-18 10:00",
        },
        "subject_rows": [
            {
                "course_code": "CS-101",
                "my_marks": 82.0,
                "class_marks": 76.0,
                "my_attendance": 88.0,
                "class_attendance": 81.0,
                "diff": 6.0,
                "status": {"text": "Excellent", "status": "success"},
            }
        ],
        "chart": {"labels": ["CS-101"], "mine": [82.0], "class_avg": [76.0]},
        "rank": {"rank": 3, "total": 25},
        "tips": [
            {
                "icon": "fa-solid fa-circle-check",
                "status": "success",
                "title": "You are on track",
                "text": "Keep your study routine steady.",
            }
        ],
        "insight": {
            "summary": "Great work!",
            "status": "success",
            "points": ["Attendance: 88.0%", "Predicted GPA: 3.55"],
        },
        "unread_alerts": 0,
        "active_courses": 1,
        "credits": 3.0,
        "teacher_alerts": [],
    }


def _sample_teacher_students_context():
    badge = {"text": "Needs Help", "status": "warning"}
    return {
        "filter_options": {
            "batches": ["2026-A"],
            "courses": ["CS-101"],
            "statuses": ["Excellent", "Stable", "Needs Help", "High Risk"],
        },
        "student_headers": [
            "Student ID", "Name", "Batch", "Course", "Attendance", "Marks", "Pred GPA", "Status", "Actions"
        ],
        "student_rows": [
            ["STD-2026-001", "Zainab Raza", "2026-A", "CS-101", "68.0%", "64.0", "2.60", badge, {}]
        ],
        "export_rows": [
            {
                "student_id": "STD-2026-001",
                "full_name": "Zainab Raza",
                "batch": "2026-A",
                "course_code": "CS-101",
                "attendance_pct": "68.0",
                "internal_marks": "64.0",
                "predicted_gpa": "2.60",
                "status": "Needs Help",
            }
        ],
        "kpis": {
            "total_students": 1,
            "avg_attendance": 68.0,
            "avg_marks": 64.0,
            "at_risk_count": 1,
        },
    }


class PdfServiceUnitTests(TestCase):
    def test_generate_student_report_card_pdf_output(self):
        data = _sample_student_overview()
        pdf_bytes = generate_student_report_card_pdf(data)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))
        self.assertGreater(len(pdf_bytes), 500)

    def test_generate_student_report_card_pdf_empty_and_high_risk(self):
        empty_data = {
            "record": {
                "student_id": "STD-9999-999",
                "full_name": "Ahmed Ali",
                "batch": "2026-B",
                "avg_attendance": 42.0,
                "avg_marks": 38.5,
                "predicted_gpa": 1.75,
                "risk_level": "HIGH",
                "recommendation": "Urgent academic counseling required.",
            },
            "subject_rows": [],
            "tips": [],
        }
        pdf_bytes = generate_student_report_card_pdf(empty_data)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))

    def test_generate_teacher_roster_pdf_output(self):
        data = _sample_teacher_students_context()
        pdf_bytes = generate_teacher_roster_pdf(data)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))
        self.assertGreater(len(pdf_bytes), 500)

    def test_generate_teacher_roster_pdf_empty(self):
        empty_data = {
            "batch": "ALL",
            "course_code": "ALL",
            "student_rows": [],
            "export_rows": [],
            "kpis": {"total_students": 0, "avg_attendance": 0.0, "avg_marks": 0.0, "at_risk_count": 0},
        }
        pdf_bytes = generate_teacher_roster_pdf(empty_data)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))


class PdfViewsIntegrationTests(TestCase):
    def setUp(self):
        invalidate_cache()

    @patch("panels.views_student.get_student_overview_context")
    def test_student_report_pdf_success_as_student(self, mock_overview):
        mock_overview.return_value = _sample_student_overview()
        client = _login_client({
            "user_id": "USR-1003",
            "student_id": "STD-2026-001",
            "role": "STUDENT",
            "email": "s@edupredict.edu",
            "full_name": "Zainab Raza",
        })
        resp = client.get(reverse("panels:student_report_pdf"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/pdf")
        self.assertTrue(resp.content.startswith(b"%PDF-"))
        self.assertIn("attachment", resp["Content-Disposition"])
        self.assertIn("edupredict_report_card.pdf", resp["Content-Disposition"])

    @patch("panels.views_student.get_student_overview_context")
    def test_student_report_pdf_success_as_admin(self, mock_overview):
        mock_overview.return_value = _sample_student_overview()
        client = _login_client({
            "user_id": "USR-ADMIN",
            "role": "ADMIN",
            "email": "admin@edupredict.edu",
            "full_name": "System Administrator",
        })
        resp = client.get(reverse("panels:student_report_pdf"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/pdf")
        self.assertTrue(resp.content.startswith(b"%PDF-"))

    def test_student_report_pdf_unauthenticated_blocked(self):
        client = Client()
        resp = client.get(reverse("panels:student_report_pdf"))
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, reverse("accounts:auth_view"), fetch_redirect_response=False)

    def test_student_report_pdf_wrong_role_blocked(self):
        for role, dash_route in (("TEACHER", "panels:teacher_dashboard"), ("ANALYST", "panels:analyst_dashboard")):
            client = _login_client({
                "user_id": f"USR-{role}",
                "role": role,
                "email": f"{role.lower()}@edupredict.edu",
                "full_name": f"Test {role.title()}",
            })
            resp = client.get(reverse("panels:student_report_pdf"))
            self.assertEqual(resp.status_code, 302)
            self.assertRedirects(resp, reverse(dash_route), fetch_redirect_response=False)

    @patch("panels.views_student.get_student_overview_context")
    def test_student_report_pdf_db_error_redirects(self, mock_overview):
        mock_overview.side_effect = RuntimeError("Database down")
        client = _login_client({
            "user_id": "USR-1003",
            "student_id": "STD-2026-001",
            "role": "STUDENT",
            "email": "s@edupredict.edu",
            "full_name": "Zainab Raza",
        })
        resp = client.get(reverse("panels:student_report_pdf"))
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, reverse("panels:student_report"), fetch_redirect_response=False)

    @patch("panels.views_teacher.get_teacher_students_context")
    def test_teacher_roster_pdf_success_as_teacher(self, mock_students):
        mock_students.return_value = _sample_teacher_students_context()
        client = _login_client({
            "user_id": "USR-T1",
            "role": "TEACHER",
            "email": "t@edupredict.edu",
            "full_name": "Dr. Ayesha Khan",
        })
        resp = client.get(reverse("panels:teacher_roster_pdf"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/pdf")
        self.assertTrue(resp.content.startswith(b"%PDF-"))
        self.assertIn("attachment", resp["Content-Disposition"])
        self.assertIn("edupredict_class_roster.pdf", resp["Content-Disposition"])

    @patch("panels.views_teacher.get_teacher_students_context")
    def test_teacher_roster_pdf_success_as_admin(self, mock_students):
        mock_students.return_value = _sample_teacher_students_context()
        client = _login_client({
            "user_id": "USR-ADMIN",
            "role": "ADMIN",
            "email": "admin@edupredict.edu",
            "full_name": "System Administrator",
        })
        resp = client.get(reverse("panels:teacher_roster_pdf"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/pdf")
        self.assertTrue(resp.content.startswith(b"%PDF-"))

    def test_teacher_roster_pdf_unauthenticated_blocked(self):
        client = Client()
        resp = client.get(reverse("panels:teacher_roster_pdf"))
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, reverse("accounts:auth_view"), fetch_redirect_response=False)

    def test_teacher_roster_pdf_wrong_role_blocked(self):
        for role, dash_route in (("STUDENT", "panels:student_dashboard"), ("ANALYST", "panels:analyst_dashboard")):
            client = _login_client({
                "user_id": f"USR-{role}",
                "role": role,
                "email": f"{role.lower()}@edupredict.edu",
                "full_name": f"Test {role.title()}",
            })
            resp = client.get(reverse("panels:teacher_roster_pdf"))
            self.assertEqual(resp.status_code, 302)
            self.assertRedirects(resp, reverse(dash_route), fetch_redirect_response=False)

    @patch("panels.views_teacher.get_teacher_students_context")
    def test_teacher_roster_pdf_error_redirects(self, mock_students):
        mock_students.side_effect = RuntimeError("Database down")
        client = _login_client({
            "user_id": "USR-T1",
            "role": "TEACHER",
            "email": "t@edupredict.edu",
            "full_name": "Dr. Ayesha Khan",
        })
        resp = client.get(reverse("panels:teacher_roster_pdf"))
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, reverse("panels:teacher_students"), fetch_redirect_response=False)
