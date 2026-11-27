from unittest.mock import patch
from django.test import Client, TestCase
from django.urls import reverse
from pymongo import UpdateOne
from core.db import invalidate_cache
from panels.test_admin import _MemCol


class _BulkMemCol(_MemCol):
    def bulk_write(self, ops, ordered=False):
        for op in ops or []:
            if isinstance(op, UpdateOne):
                self.update_one(op._filter, op._doc, upsert=op._upsert)
        return None


class TeacherAcademicFlowTests(TestCase):
    def setUp(self):
        invalidate_cache()
        self.users_mem = _BulkMemCol([{
            "user_id": "USR-ADMIN", "full_name": "System Admin", "email": "admin@edupredict.edu",
            "role": "ADMIN", "is_active": True, "approval_status": "APPROVED",
        }])
        self.semesters_mem = _BulkMemCol()
        self.courses_mem = _BulkMemCol()
        self.sr_mem = _BulkMemCol()
        self.pred_mem = _BulkMemCol()
        self.notif_mem = _BulkMemCol()
        self.tickets_mem = _BulkMemCol()
        self.log_mem = _BulkMemCol()
        self.settings_mem = _BulkMemCol()
        self.patchers = [
            patch("core.context_processors.notifications_col", return_value=self.notif_mem),
            patch("analytics.ml_engine.student_records_col", return_value=self.sr_mem),
            patch("analytics.ml_engine.predictions_col", return_value=self.pred_mem),
            patch("analytics.ml_engine.notifications_col", return_value=self.notif_mem),
            patch("analytics.ml_engine._resolve_runtime_settings", return_value={
                "high_risk_threshold": 70, "medium_risk_threshold": 35, "anomaly_drop_pct": 25,
                "min_attendance_pct": 75, "passing_gpa": 2.0, "auto_student_alerts": True, "auto_teacher_alerts": True,
            }),
            patch("panels.admin_services.users_col", return_value=self.users_mem),
            patch("panels.admin_services.student_records_col", return_value=self.sr_mem),
            patch("panels.admin_services.ensure_admin_seed_data", return_value=None),
            patch("panels.admin_services.ensure_accounts_indexes_once", return_value=None),
            patch("panels.admin_academic_services.users_col", return_value=self.users_mem),
            patch("panels.admin_academic_services.semesters_col", return_value=self.semesters_mem),
            patch("panels.admin_academic_services.courses_col", return_value=self.courses_mem),
            patch("panels.admin_academic_services.student_records_col", return_value=self.sr_mem),
            patch("panels.admin_academic_services.ensure_accounts_indexes_once", return_value=None),
            patch("panels.admin_academic_services.record_audit_log", return_value=None),
            patch("panels.teacher_services.users_col", return_value=self.users_mem),
            patch("panels.teacher_services.semesters_col", return_value=self.semesters_mem),
            patch("panels.teacher_services.courses_col", return_value=self.courses_mem),
            patch("panels.teacher_services.student_records_col", return_value=self.sr_mem),
            patch("panels.teacher_services.predictions_col", return_value=self.pred_mem),
            patch("panels.teacher_services.notifications_col", return_value=self.notif_mem),
            patch("panels.teacher_services.support_tickets_col", return_value=self.tickets_mem),
            patch("panels.teacher_services.datasets_log_col", return_value=self.log_mem),
            patch("panels.teacher_academic_services.users_col", return_value=self.users_mem),
            patch("panels.teacher_academic_services.semesters_col", return_value=self.semesters_mem),
            patch("panels.teacher_academic_services.courses_col", return_value=self.courses_mem),
            patch("panels.teacher_academic_services.student_records_col", return_value=self.sr_mem),
            patch("panels.teacher_alert_services.courses_col", return_value=self.courses_mem),
            patch("panels.teacher_alert_services.notifications_col", return_value=self.notif_mem),
            patch("panels.teacher_alert_services.users_col", return_value=self.users_mem),
            patch("panels.teacher_alert_services.system_settings_col", return_value=self.settings_mem),
            patch("panels.teacher_alert_services._resolve_runtime_settings", return_value={"auto_teacher_alerts": True}),
            patch("panels.views_teacher.notifications_col", return_value=self.notif_mem),
            patch("panels.student_services.users_col", return_value=self.users_mem),
            patch("panels.student_services.courses_col", return_value=self.courses_mem),
            patch("panels.student_services.student_records_col", return_value=self.sr_mem),
            patch("panels.student_services.predictions_col", return_value=self.pred_mem),
            patch("panels.student_services.notifications_col", return_value=self.notif_mem),
            patch("panels.student_services.support_tickets_col", return_value=self.tickets_mem),
            patch("panels.student_services._resolve_runtime_settings", return_value={"min_attendance_pct": 75.0}),
            patch("panels.student_alert_services.notifications_col", return_value=self.notif_mem),
            patch("panels.student_alert_services.support_tickets_col", return_value=self.tickets_mem),
            patch("panels.notification_services.notifications_col", return_value=self.notif_mem),
            patch("panels.notification_services.support_tickets_col", return_value=self.tickets_mem),
        ]
        for p in self.patchers:
            p.start()

    def tearDown(self):
        for p in reversed(self.patchers):
            p.stop()
        invalidate_cache()

    def _client_for(self, user_doc):
        client = Client()
        s = client.session
        s["user"] = {
            "user_id": user_doc["user_id"],
            "full_name": user_doc["full_name"],
            "email": user_doc["email"],
            "role": user_doc["role"],
            "student_id": user_doc.get("student_id", ""),
        }
        s.save()
        return client

    def _seed_admin_assignments(self):
        admin = self._client_for(self.users_mem.find_one({"role": "ADMIN"}))
        admin.post(reverse("panels:admin_semesters"), {
            "action": "create_semester", "program_name": "BSCS", "semester_number": "1", "total_semesters": "1", "status": "ACTIVE",
        })
        sem = self.semesters_mem.find_one({"program_name": "BSCS", "semester_number": 1})
        admin.post(reverse("panels:admin_teachers"), {
            "action": "create_teacher", "full_name": "Dr. Hina", "email": "hina@edupredict.edu", "password": "password123",
        })
        teacher = self.users_mem.find_one({"email": "hina@edupredict.edu"})
        admin.post(reverse("panels:admin_students"), {
            "action": "create_student", "full_name": "Amina Noor", "email": "amina@edupredict.edu",
            "password": "password123", "semester_id": sem["semester_id"],
        })
        student = self.users_mem.find_one({"email": "amina@edupredict.edu"})
        admin.post(reverse("panels:admin_courses"), {
            "action": "create_course", "course_code": "CS-101", "title": "Programming Fundamentals",
            "semester_id": sem["semester_id"], "instructor_id": teacher["user_id"], "status": "ACTIVE",
        })
        return sem, teacher, student

    def test_admin_semester_and_course_sync_to_teacher_pages(self):
        _, teacher, student = self._seed_admin_assignments()
        t_client = self._client_for(teacher)
        sid = student["student_id"]
        res_dash = t_client.get(reverse("panels:teacher_dashboard"))
        self.assertEqual(res_dash.status_code, 200)
        self.assertEqual(res_dash.context["kpis"]["total_students"], 1)
        res_courses = t_client.get(reverse("panels:teacher_courses"))
        self.assertEqual(res_courses.status_code, 200)
        self.assertContains(res_courses, "CS-101")
        self.assertContains(res_courses, "Programming Fundamentals")
        res_students = t_client.get(reverse("panels:teacher_students"))
        self.assertEqual(res_students.status_code, 200)
        self.assertContains(res_students, sid)
        self.assertContains(res_students, "Amina Noor")
        res_marks = t_client.get(reverse("panels:teacher_marks"))
        self.assertEqual(res_marks.status_code, 200)
        self.assertContains(res_marks, sid)
        self.assertContains(res_marks, "Amina Noor")

    def test_teacher_marks_entry_updates_ml_and_student_panel(self):
        sem, teacher, student = self._seed_admin_assignments()
        t_client = self._client_for(teacher)
        sid = student["student_id"]
        res_post = t_client.post(reverse("panels:teacher_marks"), {
            "action": "save_bulk_marks",
            "student_ids": sid,
            "course_code": "CS-101",
            "semester_id": sem["semester_id"],
            f"attendance_pct_{sid}": "48.0",
            f"internal_marks_{sid}": "35.0",
            f"assignment_score_{sid}": "40.0",
            f"lms_hours_weekly_{sid}": "2.0",
            f"previous_gpa_{sid}": "2.10",
        })
        self.assertEqual(res_post.status_code, 302)
        rec = self.sr_mem.find_one({"student_id": sid})
        self.assertIsNotNone(rec)
        self.assertEqual(rec["attendance_pct"], 48.0)
        self.assertEqual(rec["internal_marks"], 35.0)
        pred = self.pred_mem.find_one({"student_id": sid})
        self.assertIsNotNone(pred)
        self.assertEqual(pred["risk_level"], "HIGH")
        self.assertIsNotNone(pred["predicted_gpa"])
        s_client = self._client_for(student)
        res_stu = s_client.get(reverse("panels:student_dashboard"))
        self.assertEqual(res_stu.status_code, 200)
        self.assertContains(res_stu, "48.0%")
        self.assertContains(res_stu, "35.0")
        self.assertContains(res_stu, "HIGH")

    def test_teacher_alert_reaches_student_notifications_and_dashboard(self):
        _, teacher, student = self._seed_admin_assignments()
        t_client = self._client_for(teacher)
        sid = student["student_id"]
        res_alert = t_client.post(reverse("panels:teacher_students"), {
            "action": "send_alert",
            "student_id": sid,
            "full_name": "Amina Noor",
            "course_code": "CS-101",
            "severity": "DANGER",
            "message": "Please attend extra lab tomorrow",
        })
        self.assertEqual(res_alert.status_code, 302)
        notif = self.notif_mem.find_one({"target_user_id": sid, "target_role": "STUDENT"})
        self.assertIsNotNone(notif)
        self.assertIn("Please attend extra lab tomorrow", notif["message"])
        s_client = self._client_for(student)
        res_notifs = s_client.get(reverse("panels:notifications_history"))
        self.assertEqual(res_notifs.status_code, 200)
        self.assertContains(res_notifs, "Please attend extra lab tomorrow")
        res_stu = s_client.get(reverse("panels:student_dashboard"))
        self.assertEqual(res_stu.status_code, 200)
        self.assertContains(res_stu, "Please attend extra lab tomorrow")
