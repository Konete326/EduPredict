from datetime import datetime, timezone
from unittest.mock import patch
from django.contrib.auth.hashers import make_password
from django.test import Client, TestCase
from django.urls import reverse
import accounts.services as acc_svc
from core.db import invalidate_cache
import panels.admin_audit_services as audit_svc
import panels.admin_seed as admin_seed
from panels.pdf_services import generate_student_report_card_pdf
from panels.test_admin import _MemCol
from panels.test_pdf import _sample_student_overview


class Phase25IntegrationTests(TestCase):
    def setUp(self):
        invalidate_cache()
        now = datetime(2026, 11, 20, 9, 0, tzinfo=timezone.utc)
        self.cols = {
            "users": _MemCol([{
                "user_id": "USR-1000", "full_name": "System Administrator", "email": "admin@gmail.com",
                "password_hash": make_password("admin123"), "role": "ADMIN", "department": "Administration",
                "batch": "ALL", "is_active": True, "approval_status": "APPROVED", "created_at": now,
            }]),
            "student_records": _MemCol(), "predictions": _MemCol(), "notifications": _MemCol(),
            "activity_logs": _MemCol(), "courses": _MemCol(), "support_tickets": _MemCol(), "system_settings": _MemCol(),
        }
        for p in (
            patch("core.db.MongoDBClient.get_collection", side_effect=lambda name: self.cols.setdefault(name, _MemCol())),
            patch("core.db.MongoDBClient.check_health", return_value={"connected": True, "error": None}),
            patch.object(acc_svc, "_INDEXES_ENSURED", True),
            patch.object(acc_svc, "_DEFAULT_ADMIN_ENSURED", True),
            patch.object(admin_seed, "_ADMIN_SEED_DONE", True),
            patch.object(audit_svc, "_AUDIT_SEED_DONE", True),
        ):
            p.start()
            self.addCleanup(p.stop)

    def _login_admin_client(self):
        client = Client()
        session = client.session
        session["user"] = {"user_id": "USR-1000", "role": "ADMIN", "email": "admin@gmail.com", "full_name": "System Administrator"}
        session.save()
        return client

    def _login_role(self, role, user_id="USR-2000", student_id=None):
        client = Client()
        session = client.session
        user = {"user_id": user_id, "role": role, "email": f"{role.lower()}@edupredict.edu", "full_name": f"Test {role.title()}"}
        if student_id:
            user["student_id"] = student_id
        session["user"] = user
        session.save()
        return client

    def test_student_self_signup_approves_and_redirects(self):
        client = Client()
        resp = client.post(reverse("accounts:auth_view"), {
            "action": "register", "full_name": "Sara Ahmed", "email": "sara@edupredict.edu",
            "password": "password123", "confirm_password": "password123", "role": "STUDENT",
            "department": "Computer Science", "batch": "2026-A", "phone": "0300-1234567", "bio": "BSCS Student",
        })
        self.assertRedirects(resp, reverse("panels:student_dashboard"), fetch_redirect_response=False)
        saved = self.cols["users"].find_one({"email": "sara@edupredict.edu"})
        self.assertIsNotNone(saved)
        self.assertEqual(saved["phone"], "0300-1234567")
        self.assertEqual(saved["bio"], "BSCS Student")
        self.assertEqual(saved["approval_status"], "APPROVED")
        self.assertTrue(saved["is_active"])
        self.assertEqual(client.session["user"]["role"], "STUDENT")

    def test_teacher_self_signup_is_pending_and_blocks_login_until_approved(self):
        anon = Client()
        reg_resp = anon.post(reverse("accounts:auth_view"), {
            "action": "register", "full_name": "Dr. Tariq Mahmood", "email": "tariq@edupredict.edu",
            "password": "password123", "confirm_password": "password123", "role": "TEACHER",
            "department": "Data Science", "batch": "ALL", "phone": "0321-7654321", "bio": "ML Lecturer",
        })
        self.assertEqual(reg_resp.status_code, 200)
        self.assertNotIn("user", anon.session)
        teacher = self.cols["users"].find_one({"email": "tariq@edupredict.edu"})
        self.assertIsNotNone(teacher)
        self.assertFalse(teacher["is_active"])
        self.assertEqual(teacher["approval_status"], "PENDING")
        self.assertEqual(teacher["phone"], "0321-7654321")
        self.assertEqual(teacher["bio"], "ML Lecturer")
        notif = self.cols["notifications"].find_one({"target_role": "ADMIN", "title": "Teacher Approval Needed"})
        self.assertIsNotNone(notif)
        self.assertFalse(notif["is_read"])

        blocked = anon.post(reverse("accounts:auth_view"), {"action": "login", "email": "tariq@edupredict.edu", "password": "password123"})
        self.assertEqual(blocked.status_code, 200)
        self.assertNotIn("user", anon.session)
        self.assertIn("pending Admin approval", blocked.content.decode("utf-8"))

        admin_client = self._login_admin_client()
        pending_page = admin_client.get(reverse("panels:admin_users"), {"role": "PENDING"})
        self.assertEqual(pending_page.status_code, 200)
        pending_html = pending_page.content.decode("utf-8")
        self.assertIn("Pending Approval", pending_html)
        self.assertIn("Approve", pending_html)

        approve_resp = admin_client.post(reverse("panels:admin_users"), {"action": "toggle", "user_id": teacher["user_id"], "filter_role": "PENDING"})
        self.assertEqual(approve_resp.status_code, 302)
        updated = self.cols["users"].find_one({"user_id": teacher["user_id"]})
        self.assertTrue(updated["is_active"])
        self.assertEqual(updated["approval_status"], "APPROVED")
        self.assertIsNotNone(self.cols["notifications"].find_one({"target_user_id": teacher["user_id"], "title": "Account Approved"}))

        login_ok = anon.post(reverse("accounts:auth_view"), {"action": "login", "email": "tariq@edupredict.edu", "password": "password123"})
        self.assertRedirects(login_ok, reverse("panels:teacher_dashboard"), fetch_redirect_response=False)

    def test_public_admin_self_signup_is_rejected(self):
        client = Client()
        resp = client.post(reverse("accounts:auth_view"), {
            "action": "register", "full_name": "Fake Admin", "email": "fakeadmin@edupredict.edu",
            "password": "password123", "confirm_password": "password123", "role": "ADMIN", "department": "IT", "batch": "ALL",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(self.cols["users"].find_one({"email": "fakeadmin@edupredict.edu"}))
        self.assertNotIn("user", client.session)

    def test_auth_page_renders_stepper_wizard_and_excludes_admin_role(self):
        resp = Client().get(reverse("accounts:auth_view"))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode("utf-8")
        for marker in ("data-auth-stepper", "auth_wizard.js?v=15", "teacher-approval-notice"):
            self.assertIn(marker, html)
        reg_start = html.find('id="reg-role"')
        reg_end = html.find("</select>", reg_start)
        self.assertGreater(reg_start, -1)
        self.assertNotIn('value="ADMIN"', html[reg_start:reg_end])

    @patch("panels.views_student.get_student_overview_context")
    def test_student_transcript_links_and_pdf_generation(self, mock_overview):
        overview = _sample_student_overview()
        overview["credits"] = 12.0
        overview["rank"] = {"rank": 2, "total": 30}
        overview["subject_rows"][0]["my_marks"] = 88.0
        mock_overview.return_value = overview
        client = self._login_role("STUDENT", user_id="USR-1003", student_id="STD-2026-001")
        for route_name in ("panels:student_dashboard", "panels:student_report"):
            resp = client.get(reverse(route_name))
            self.assertEqual(resp.status_code, 200)
            self.assertIn("Download PDF Transcript", resp.content.decode("utf-8"))
        pdf_bytes = generate_student_report_card_pdf(overview)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))
        self.assertGreater(len(pdf_bytes), 500)

    def test_admin_reject_pending_teacher_with_reason_and_login_block(self):
        anon = Client()
        anon.post(reverse("accounts:auth_view"), {
            "action": "register", "full_name": "Dr. Farhan Ali", "email": "farhan@edupredict.edu",
            "password": "password123", "confirm_password": "password123", "role": "TEACHER",
            "department": "Computer Science", "batch": "ALL",
        })
        teacher = self.cols["users"].find_one({"email": "farhan@edupredict.edu"})
        self.assertIsNotNone(teacher)

        admin_client = self._login_admin_client()
        pending_resp = admin_client.get(reverse("panels:admin_users"), {"role": "PENDING"})
        self.assertEqual(pending_resp.status_code, 200)
        pending_html = pending_resp.content.decode("utf-8")
        self.assertIn("openRejectUserModal(this)", pending_html)
        self.assertIn("Rejected", pending_html)

        reason = "Faculty verification document did not match."
        rej_resp = admin_client.post(reverse("panels:admin_users"), {
            "action": "reject", "user_id": teacher["user_id"], "rejection_reason": reason, "filter_role": "PENDING",
        })
        self.assertEqual(rej_resp.status_code, 302)

        rejected_user = self.cols["users"].find_one({"user_id": teacher["user_id"]})
        self.assertEqual(rejected_user["approval_status"], "REJECTED")
        self.assertFalse(rejected_user["is_active"])
        self.assertEqual(rejected_user["rejection_reason"], reason)

        audit = self.cols["activity_logs"].find_one({"action": "REJECT_USER"})
        self.assertIsNotNone(audit)
        self.assertIn(reason, audit["summary"])
        notif = self.cols["notifications"].find_one({"target_user_id": teacher["user_id"], "category": "APPROVAL"})
        self.assertIsNotNone(notif)
        self.assertEqual(notif["severity"], "DANGER")
        self.assertIn(reason, notif["message"])

        admin_client.post(reverse("panels:admin_users"), {"action": "reject", "user_id": "USR-1000", "rejection_reason": "Self guard check"})
        self_admin = self.cols["users"].find_one({"user_id": "USR-1000"})
        self.assertTrue(self_admin["is_active"])
        self.assertEqual(self_admin["approval_status"], "APPROVED")

        blocked = anon.post(reverse("accounts:auth_view"), {"action": "login", "email": "farhan@edupredict.edu", "password": "password123"})
        self.assertEqual(blocked.status_code, 200)
        self.assertNotIn("user", anon.session)
        self.assertIn(reason, blocked.content.decode("utf-8"))

        rej_page = admin_client.get(reverse("panels:admin_users"), {"role": "REJECTED"})
        self.assertEqual(rej_page.status_code, 200)
        rej_html = rej_page.content.decode("utf-8")
        self.assertIn("openRejectUserModal", rej_html)
        self.assertIn("Rejected", rej_html)
        self.assertIn(reason, rej_html)

    def test_phase62_table_first_toggle_copy_and_student_360(self):
        now = datetime(2026, 11, 21, 10, 0, tzinfo=timezone.utc)
        self.cols["student_records"].insert_one({
            "student_id": "STD-2026-001", "full_name": "Zainab Raza", "batch": "2026-A", "course_code": "CS-101",
            "attendance_pct": 62.5, "internal_marks": 58.0, "assignment_score": 64.0, "lms_hours_weekly": 6.5, "previous_gpa": 2.9, "updated_at": now,
        })
        self.cols["predictions"].insert_one({
            "student_id": "STD-2026-001", "predicted_gpa": 2.45, "dropout_risk_score": 0.68,
            "risk_level": "MEDIUM", "is_anomaly": False, "recommendation": "Increase attendance above 75%.", "generated_at": now,
        })
        self.cols["notifications"].insert_one({
            "target_user_id": "STD-2026-001", "title": "Attendance Warning",
            "message": "Attendance fell to 62.5%.", "severity": "WARNING", "is_read": False, "created_at": now,
        })

        admin = self._login_admin_client()
        teacher = self._login_role("TEACHER", user_id="USR-T1")
        analyst = self._login_role("ANALYST", user_id="USR-AN1")
        student = self._login_role("STUDENT", user_id="USR-1003", student_id="STD-2026-001")

        markers = (
            'data-directory-mode="table"', "data-directory-view-toggle", "data-directory-table-view",
            "data-directory-cards-view", "data-copy-text", 'id="student-360-drawer"',
        )
        for client, path in ((admin, reverse("panels:admin_users")), (teacher, reverse("panels:teacher_students"))):
            resp = client.get(path)
            self.assertEqual(resp.status_code, 200)
            html = resp.content.decode("utf-8")
            for marker in markers:
                self.assertIn(marker, html)
            if path.endswith("/students/"):
                self.assertIn("openStudent360Drawer(", html)
                self.assertIn('data-copy-text="STD-2026-001"', html)

        summary_url = reverse("panels:student_360_summary", args=["STD-2026-001"])
        for client in (teacher, analyst, admin):
            res = client.get(summary_url)
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertTrue(data["ok"])
            summary = data["summary"]
            for key in ("avg_attendance", "predicted_gpa", "risk_level", "risk_reasons", "courses", "recent_alerts"):
                self.assertIn(key, summary)
            self.assertAlmostEqual(summary["avg_attendance"], 62.5)
            self.assertAlmostEqual(summary["predicted_gpa"], 2.45)
            self.assertEqual(summary["risk_level"], "MEDIUM")
            self.assertGreaterEqual(len(summary["risk_reasons"]), 2)
            self.assertEqual(len(summary["courses"]), 1)
            self.assertEqual(len(summary["recent_alerts"]), 1)

        denied = student.get(summary_url)
        self.assertEqual(denied.status_code, 302)

        missing = teacher.get(reverse("panels:student_360_summary", args=["STD-9999-MISSING"]))
        self.assertEqual(missing.status_code, 404)
        self.assertFalse(missing.json()["ok"])
