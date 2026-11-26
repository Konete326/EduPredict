import ast
import io
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse
from sklearn.ensemble import RandomForestClassifier
import accounts.services as acc_svc
from analytics.data_pipeline import _normalize_column_name, ingest_dataset
from analytics.ml_engine import run_prediction_pipeline
from analytics.preprocessing import build_dropout_pipeline
from core.context_processors import global_context
from core.db import invalidate_cache
import panels.admin_audit_services as audit_svc
import panels.admin_seed as admin_seed
from panels.pdf_services import generate_student_report_card_pdf, generate_teacher_roster_pdf
from panels.test_admin import _MemCol
from panels.test_pdf import _sample_student_overview, _sample_teacher_students_context


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
            "student_records": _MemCol(), "predictions": _MemCol(), "datasets_log": _MemCol(),
            "notifications": _MemCol(), "activity_logs": _MemCol(), "courses": _MemCol(),
            "support_tickets": _MemCol(), "system_settings": _MemCol(),
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

    def test_student_self_signup_rejected_and_analyst_approval_flow(self):
        client = Client()
        std_resp = client.post(reverse("accounts:auth_view"), {"action": "register", "full_name": "Sara Ahmed", "email": "sara@edupredict.edu", "password": "password123", "confirm_password": "password123", "role": "STUDENT", "department": "Computer Science", "batch": "2026-A"})
        self.assertEqual(std_resp.status_code, 200)
        self.assertIn("class upload", std_resp.content.decode("utf-8"))
        self.assertIsNone(self.cols["users"].find_one({"email": "sara@edupredict.edu"}))

        reg_resp = client.post(reverse("accounts:auth_view"), {"action": "register", "full_name": "Nadia Khan", "email": "nadia@edupredict.edu", "password": "password123", "confirm_password": "password123", "role": "ANALYST", "department": "Analytics", "batch": "ALL"})
        self.assertEqual(reg_resp.status_code, 200)
        saved = self.cols["users"].find_one({"email": "nadia@edupredict.edu"})
        self.assertIsNotNone(saved)
        self.assertEqual((saved["role"], saved["approval_status"], saved["is_active"]), ("ANALYST", "PENDING", False))
        self.assertIsNotNone(self.cols["notifications"].find_one({"target_role": "ADMIN", "title": "Analyst Approval Needed"}))
        blocked = client.post(reverse("accounts:auth_view"), {"action": "login", "email": "nadia@edupredict.edu", "password": "password123"})
        self.assertEqual(blocked.status_code, 200)
        self.assertNotIn("user", client.session)
        self._login_admin_client().post(reverse("panels:admin_users"), {"action": "toggle", "user_id": saved["user_id"], "filter_role": "PENDING"})
        login_resp = client.post(reverse("accounts:auth_view"), {"action": "login", "email": "nadia@edupredict.edu", "password": "password123"})
        self.assertRedirects(login_resp, reverse("panels:analyst_dashboard"), fetch_redirect_response=False)
        self.assertEqual(client.session["user"]["role"], "ANALYST")

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
        for marker in ("data-auth-stepper", "auth_wizard.js?v=17", "teacher-approval-notice"):
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
        dash_resp = client.get(reverse("panels:student_dashboard"))
        self.assertEqual(dash_resp.status_code, 200)
        self.assertIn("My Report Card", dash_resp.content.decode("utf-8"))
        rep_resp = client.get(reverse("panels:student_report"))
        self.assertEqual(rep_resp.status_code, 200)
        self.assertIn("Download PDF Transcript", rep_resp.content.decode("utf-8"))
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

        markers = ("data-paginated-container", "data-view-payload", "window.openViewDetailsModal(", 'id="student-360-drawer"')
        for client, path in ((admin, reverse("panels:admin_users")), (teacher, reverse("panels:teacher_students"))):
            resp = client.get(path)
            self.assertEqual(resp.status_code, 200)
            html = resp.content.decode("utf-8")
            for marker in markers:
                self.assertIn(marker, html)
            if path.endswith("/students/"):
                self.assertIn("STD-2026-001", html)

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

    def test_phase63_hyper_automation_live_stream_and_aptech_pack(self):
        for raw, expected in (("Roll_No", "student_id"), ("Enrollment", "student_id"), ("Reg_No", "student_id"), ("Att_%", "attendance_pct"), ("Test_Score", "internal_marks"), ("Prev_GPA", "previous_gpa"), ("LMS_Hours", "lms_hours_weekly")):
            self.assertEqual(_normalize_column_name(raw), expected)

        csv_rows = [
            "Roll_No,Name,Course,Att_%,Test_Score,Prev_GPA,LMS_Hours",
            "STD-HIGH,High Risk Student,CS-101,35.0,28.0,1.40,1.5",
            "STD-ANOM,Anomaly Student,DS-204,86.0,38.0,3.60,10.0",
            "STD-LOWATT,Low Att Student,CS-101,71.0,88.0,3.40,14.0",
        ] + [f"STD-OK-{i},Steady Student {i},CS-101,91.0,86.0,3.50,13.5" for i in range(1, 9)]
        csv_file = io.BytesIO("\n".join(csv_rows).encode("utf-8"))
        csv_file.name = "aptech_aliases.csv"
        ingest_res = ingest_dataset(file_obj=csv_file, uploaded_by="teacher@edupredict.edu", mode="upload")
        self.assertEqual(ingest_res["status"], "COMPLETED")
        self.assertEqual(ingest_res["column_mappings"]["Roll_No"], "student_id")
        self.assertEqual(ingest_res["column_mappings"]["Att_%"], "attendance_pct")
        self.assertEqual(ingest_res["column_mappings"]["Test_Score"], "internal_marks")
        self.assertEqual(ingest_res["column_mappings"]["Prev_GPA"], "previous_gpa")
        self.assertEqual(ingest_res["column_mappings"]["LMS_Hours"], "lms_hours_weekly")
        self.assertEqual(len(ingest_res["preview_rows"]), 5)

        rf_model = build_dropout_pipeline().named_steps["model"]
        self.assertIsInstance(rf_model, RandomForestClassifier)
        self.assertEqual(rf_model.n_estimators, 50)
        self.assertEqual(rf_model.n_jobs, -1)

        ml_res = run_prediction_pipeline(persist=True)
        self.assertEqual(ml_res["status"], "COMPLETED")
        notif_titles = [d.get("title", "") for d in self.cols["notifications"].docs]
        self.assertTrue(any(t.startswith("High Dropout Risk:") for t in notif_titles))
        self.assertTrue(any(t.startswith("Academic Anomaly Flagged:") for t in notif_titles))
        self.assertTrue(any(t == "Low Attendance Alert: STD-LOWATT" for t in notif_titles))

        self.cols["notifications"].insert_one({
            "target_role": "STUDENT", "target_user_id": "STD-HIGH", "student_id": "STD-HIGH",
            "sender_user_id": "USR-T1", "sender_name": "Test Teacher",
            "title": "Teacher Alert (CS-101)", "message": "Previous read alert", "severity": "WARNING",
            "is_read": True, "created_at": datetime(2026, 11, 21, 11, 0, tzinfo=timezone.utc),
        })
        teacher = self._login_role("TEACHER", user_id="USR-T1")
        alerts_html = teacher.get(reverse("panels:teacher_alerts")).content.decode("utf-8")
        self.assertIn("Previous read alert", alerts_html)
        self.assertIn("Read", alerts_html)
        self.assertIn("Notify All High-Risk Students", alerts_html)
        self.assertIn("Auto-Alert &lt; 75%: On", alerts_html)

        self.assertEqual(teacher.post(reverse("panels:teacher_alerts"), {"action": "notify_all_high_risk"}).status_code, 302)
        self.assertGreaterEqual(len([d for d in self.cols["notifications"].docs if str(d.get("title", "")).startswith("Teacher Alert (") and not d.get("is_read")]), 1)
        self.assertEqual(teacher.post(reverse("panels:teacher_alerts"), {"action": "toggle_auto_alerts", "enabled": "0"}).status_code, 302)
        self.assertFalse(self.cols["system_settings"].find_one({"setting_key": "portal_config"})["auto_student_alerts"])
        self.assertIn("Auto-Alert &lt; 75%: Off", teacher.get(reverse("panels:teacher_alerts")).content.decode("utf-8"))

        analyst = self._login_role("ANALYST", user_id="USR-AN1")
        dash_html = analyst.get(reverse("panels:analyst_dashboard")).content.decode("utf-8")
        stream_url = reverse("analytics:stream_tick")
        self.assertIn('id="live-stream-toggle-btn"', dash_html)
        self.assertIn(stream_url, dash_html)
        self.assertEqual(analyst.get(stream_url).status_code, 405)
        tick_resp = analyst.post(stream_url)
        self.assertEqual(tick_resp.status_code, 200)
        tick_data = tick_resp.json()
        self.assertTrue(tick_data["ok"])
        self.assertGreaterEqual(tick_data["events_pushed"], 1)
        self.assertGreaterEqual(len(tick_data["events"]), 1)
        self.assertGreaterEqual(tick_data["predictions_generated"], 1)
        self.assertIsNotNone(self.cols["datasets_log"].find_one({"mode": "STREAM_TICK"}))

        with patch("panels.pdf_services.get_portal_settings", return_value={"settings_data": {"institution_name": "Aptech Metro Campus", "current_term": "Spring 2027"}}):
            s_pdf = generate_student_report_card_pdf(_sample_student_overview())
            t_pdf = generate_teacher_roster_pdf(_sample_teacher_students_context())
        for pdf_bytes in (s_pdf, t_pdf):
            self.assertTrue(pdf_bytes.startswith(b"%PDF-"))
            self.assertIn(b"Aptech Metro Campus", pdf_bytes)
            self.assertIn(b"Spring 2027", pdf_bytes)

        pack_dir = Path(settings.BASE_DIR) / "docs" / "aptech_submission"
        for fname in ("PROJECT_REPORT.md", "INSTALLATION_README.md", "DEMO_WALKTHROUGH.md", "sample_aptech_test_dataset.csv"):
            fpath = pack_dir / fname
            self.assertTrue(fpath.is_file(), fname)
            self.assertGreater(fpath.stat().st_size, 0, fname)

    def test_phase64_portal_branding_html_sync_and_pdf_imports(self):
        self.cols["system_settings"].insert_one({
            "setting_key": "portal_config", "institution_name": "Apex Tech Institute", "current_term": "Spring 2027",
        })
        invalidate_cache()
        student = self._login_role("STUDENT", user_id="USR-1003", student_id="STD-2026-001")
        resp = student.get(reverse("panels:student_report"))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode("utf-8")
        for expected in ("Portal / Term", "Apex Tech Institute", "Spring 2027"):
            self.assertIn(expected, html)
        pdf_resp = student.get(reverse("panels:student_report_pdf"))
        self.assertEqual(pdf_resp.status_code, 200)
        self.assertTrue(pdf_resp.content.startswith(b"%PDF-"))
        for expected_b in (b"Apex Tech Institute", b"Spring 2027"):
            self.assertIn(expected_b, pdf_resp.content)

        pdf_src = (Path(settings.BASE_DIR) / "panels" / "pdf_services.py").read_text(encoding="utf-8")
        tree = ast.parse(pdf_src)
        first_body_line = min(n.lineno for n in tree.body if not isinstance(n, (ast.Import, ast.ImportFrom)))
        import_lines = [n.lineno for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
        self.assertTrue(import_lines and all(ln < first_body_line for ln in import_lines))

    def test_phase65_global_branding_and_live_stream_charts(self):
        with patch("core.context_processors.check_db_health", return_value={"connected": False}):
            off_ctx = global_context(RequestFactory().get(reverse("panels:teacher_dashboard")))
        self.assertEqual((off_ctx["portal_institution_name"], off_ctx["portal_current_term"]), ("EduPredict Academic Portal", "Fall 2026"))

        self.cols["system_settings"].insert_one({"setting_key": "portal_config", "institution_name": "Global Tech College", "current_term": "Winter 2027"})
        invalidate_cache()
        rf_ctx = global_context(RequestFactory().get(reverse("panels:teacher_dashboard")))
        self.assertEqual((rf_ctx["portal_institution_name"], rf_ctx["portal_current_term"]), ("Global Tech College", "Winter 2027"))
        for role, uid, sid, url_name in (("TEACHER", "USR-T65", None, "panels:teacher_dashboard"), ("STUDENT", "USR-S65", "STD-6501", "panels:student_dashboard")):
            resp = self._login_role(role, user_id=uid, student_id=sid).get(reverse(url_name))
            self.assertEqual(resp.status_code, 200)
            self.assertEqual((resp.context["portal_institution_name"], resp.context["portal_current_term"]), ("Global Tech College", "Winter 2027"))

        analyst = self._login_role("ANALYST", user_id="USR-AN65")
        dash_html = analyst.get(reverse("panels:analyst_dashboard")).content.decode("utf-8")
        self.assertIn("Chart.getChart(document.getElementById('chart-dropout-doughnut'))", dash_html)
        self.assertIn("Chart.getChart(document.getElementById('chart-course-demand'))", dash_html)
        tick_data = analyst.post(reverse("analytics:stream_tick")).json()
        self.assertTrue(tick_data["ok"] and len(tick_data["events"]) >= 1 and tick_data["predictions_generated"] >= 1)
        self.assertEqual(tick_data["dropout_counts"], {"LOW": tick_data["low_risk_count"], "MEDIUM": tick_data["medium_risk_count"], "HIGH": tick_data["high_risk_count"]})
        self.assertTrue(tick_data["course_demand"] and "course_code" in tick_data["course_demand"][0])
