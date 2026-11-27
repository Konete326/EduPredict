import json
import re
from pathlib import Path
from unittest.mock import MagicMock, patch
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from accounts.services import authenticate_user
from core.db import invalidate_cache
from core.theme_services import get_theme_studio_catalog, normalize_theme_prefs


class _FakeCursor(list):
    def sort(self, key, direction=1):
        return _FakeCursor(sorted(self, key=lambda d: str(d.get(key) or ""), reverse=(direction == -1)))


class _FakeCol:
    def __init__(self, docs=None):
        self.docs = []
        for i, d in enumerate(docs or []):
            item = dict(d)
            item.setdefault("_id", f"init-{i + 1}")
            self.docs.append(item)

    def _match(self, doc, query):
        for k, v in (query or {}).items():
            if k == "$or":
                if not any(self._match(doc, sub) for sub in v):
                    return False
                continue
            val = doc.get(k)
            if isinstance(v, dict):
                if "$in" in v and val not in v["$in"]:
                    return False
                if "$ne" in v and val == v["$ne"]:
                    return False
                if "$regex" in v:
                    flags = re.IGNORECASE if "i" in str(v.get("$options") or "") else 0
                    if not re.search(v["$regex"], str(val or ""), flags):
                        return False
            elif val != v:
                return False
        return True

    def find(self, query=None, projection=None):
        return _FakeCursor([dict(d) for d in self.docs if self._match(d, query)])

    def find_one(self, query=None, projection=None):
        for d in self.docs:
            if self._match(d, query):
                return dict(d)
        return None

    def insert_one(self, doc):
        d = dict(doc)
        d.setdefault("_id", f"id-{len(self.docs) + 1}")
        self.docs.append(d)
        return MagicMock(inserted_id=d["_id"])

    def update_one(self, query, update, upsert=False):
        for d in self.docs:
            if self._match(d, query):
                if "$set" in update:
                    d.update(update["$set"])
                return MagicMock(matched_count=1, modified_count=1)
        if upsert:
            new_doc = dict(query)
            new_doc.update(update.get("$setOnInsert", {}))
            new_doc.update(update.get("$set", {}))
            self.insert_one(new_doc)
            return MagicMock(matched_count=1, modified_count=1)
        return MagicMock(matched_count=0, modified_count=0)

    def delete_one(self, query):
        for i, d in enumerate(self.docs):
            if self._match(d, query):
                self.docs.pop(i)
                return MagicMock(deleted_count=1)
        return MagicMock(deleted_count=0)


class PasswordApprovalWorkflowTests(TestCase):
    def setUp(self):
        invalidate_cache()
        self.users = _FakeCol([
            {
                "user_id": "USR-STU-1",
                "full_name": "Sara Khan",
                "email": "sara@edupredict.edu",
                "role": "STUDENT",
                "password_hash": make_password("oldpass123"),
                "is_active": True,
                "approval_status": "APPROVED",
            },
            {
                "user_id": "USR-ADM-1",
                "full_name": "Root Admin",
                "email": "admin@edupredict.edu",
                "role": "ADMIN",
                "password_hash": make_password("adminpass1"),
                "is_active": True,
                "approval_status": "APPROVED",
            },
        ])
        self.pwd_reqs = _FakeCol()
        self.notifs = _FakeCol()
        self.audits = _FakeCol()

    def _login_session(self, role, user_id, email, full_name):
        client = Client()
        session = client.session
        session["user"] = {"user_id": user_id, "role": role, "email": email, "full_name": full_name}
        session.save()
        return client

    def test_student_password_request_admin_approval_and_login_messages(self):
        with (
            patch("core.theme_services.users_col", return_value=self.users),
            patch("core.theme_services.password_requests_col", return_value=self.pwd_reqs),
            patch("core.theme_services.notifications_col", return_value=self.notifs),
            patch("panels.admin_password_services.users_col", return_value=self.users),
            patch("panels.admin_password_services.password_requests_col", return_value=self.pwd_reqs),
            patch("panels.notification_services.notifications_col", return_value=self.notifs),
            patch("panels.admin_password_services.record_audit_log"),
            patch("accounts.services.users_col", return_value=self.users),
            patch("accounts.services.ensure_accounts_indexes_once"),
            patch("core.context_processors.notifications_col", return_value=self.notifs),
            patch("core.db.MongoDBClient.check_health", return_value=True),
        ):
            stu_client = self._login_session("STUDENT", "USR-STU-1", "sara@edupredict.edu", "Sara Khan")
            resp = stu_client.post(
                reverse("panels:user_profile"),
                {
                    "action": "change_password",
                    "current_password": "oldpass123",
                    "new_password": "NewSecure99",
                    "confirm_password": "NewSecure99",
                },
            )
            self.assertRedirects(resp, reverse("panels:user_profile"), fetch_redirect_response=False)
            self.assertEqual(len(self.pwd_reqs.docs), 1)
            req_doc = self.pwd_reqs.docs[0]
            self.assertEqual(req_doc["status"], "PENDING")
            self.assertEqual(req_doc["requested_password_plain"], "NewSecure99")
            self.assertTrue(any(n.get("target_role") == "ADMIN" and n.get("title") == "Password Change Request" for n in self.notifs.docs))

            still_old, old_err = authenticate_user("sara@edupredict.edu", "oldpass123")
            self.assertIsNotNone(still_old)
            self.assertIsNone(old_err)

            adm_client = self._login_session("ADMIN", "USR-ADM-1", "admin@edupredict.edu", "Root Admin")
            page = adm_client.get(reverse("panels:admin_password_requests"))
            self.assertEqual(page.status_code, 200)
            self.assertContains(page, "NewSecure99")
            self.assertContains(page, "Sara Khan")

            app_resp = adm_client.post(
                reverse("panels:admin_password_requests"),
                {"action": "approve_password", "request_id": req_doc["request_id"]},
            )
            self.assertRedirects(app_resp, reverse("panels:admin_password_requests"), fetch_redirect_response=False)
            self.assertEqual(self.pwd_reqs.docs[0]["status"], "APPROVED")
            updated_user = self.users.find_one({"user_id": "USR-STU-1"})
            self.assertTrue(check_password("NewSecure99", updated_user["password_hash"]))
            self.assertTrue(check_password("oldpass123", updated_user["previous_password_hash"]))
            self.assertTrue(
                any(
                    n.get("target_user_id") == "USR-STU-1" and "NewSecure99" in str(n.get("message") or "")
                    for n in self.notifs.docs
                )
            )

            fail_old, msg_old = authenticate_user("sara@edupredict.edu", "oldpass123")
            self.assertIsNone(fail_old)
            self.assertIn("changed after Admin approval", msg_old)

            ok_new, err_new = authenticate_user("sara@edupredict.edu", "NewSecure99")
            self.assertIsNotNone(ok_new)
            self.assertIsNone(err_new)


class TeacherAttendanceAndTestsWorkflowTests(TestCase):
    def setUp(self):
        invalidate_cache()
        self.courses = _FakeCol([
            {"course_code": "CS-101", "title": "Intro to AI", "semester_id": "SEM-1", "instructor_id": "USR-TCH-1", "status": "ACTIVE"},
            {"course_code": "CS-102", "title": "Data Mining", "semester_id": "SEM-1", "instructor_id": "USR-TCH-1", "status": "ACTIVE"},
        ])
        self.semesters = _FakeCol([{"semester_id": "SEM-1", "name": "Fall 2026"}])
        self.students = _FakeCol([
            {
                "student_id": "STD-101",
                "full_name": "Ali Raza",
                "course_code": "CS-101",
                "semester_id": "SEM-1",
                "semester_label": "Fall 2026",
                "attendance_pct": 100.0,
                "internal_marks": 60.0,
                "teacher_user_id": "USR-TCH-1",
            },
            {
                "student_id": "STD-102",
                "full_name": "Zara Tariq",
                "course_code": "CS-102",
                "semester_id": "SEM-1",
                "semester_label": "Fall 2026",
                "attendance_pct": 95.0,
                "internal_marks": 75.0,
                "teacher_user_id": "USR-TCH-1",
            },
        ])
        self.attendance = _FakeCol()
        self.tests = _FakeCol()
        self.users = _FakeCol([])
        self.preds = _FakeCol([])
        self.notifs = _FakeCol([])

    def _teacher_client(self):
        client = Client()
        session = client.session
        session["user"] = {"user_id": "USR-TCH-1", "role": "TEACHER", "email": "t@edupredict.edu", "full_name": "Prof. Zain"}
        session.save()
        return client

    def test_nine_shell_themes_catalog_and_legacy_fallback(self):
        catalog = get_theme_studio_catalog()
        slugs = [item["slug"] for item in catalog["shell_themes"]]
        self.assertEqual(len(slugs), 9)
        self.assertNotIn("dark-red", slugs)
        self.assertEqual(set(slugs), {"dark", "dark-green", "blue", "green", "red", "teal", "purple", "amber", "white"})
        self.assertEqual(normalize_theme_prefs({"shell_theme": "dark-red"})["shell_theme"], "red")

    def test_teacher_students_no_update_and_attendance_single_course_default(self):
        with (
            patch("panels.teacher_services.courses_col", return_value=self.courses),
            patch("panels.teacher_services.semesters_col", return_value=self.semesters),
            patch("panels.teacher_services.student_records_col", return_value=self.students),
            patch("panels.teacher_services.users_col", return_value=self.users),
            patch("panels.teacher_services.predictions_col", return_value=self.preds),
            patch("panels.teacher_academic_services.courses_col", return_value=self.courses),
            patch("panels.teacher_academic_services.semesters_col", return_value=self.semesters),
            patch("panels.teacher_academic_services.student_records_col", return_value=self.students),
            patch("panels.teacher_academic_services.attendance_records_col", return_value=self.attendance),
            patch("core.context_processors.notifications_col", return_value=self.notifs),
            patch("core.db.MongoDBClient.check_health", return_value=True),
        ):
            client = self._teacher_client()
            stu_page = client.get(reverse("panels:teacher_students"))
            self.assertEqual(stu_page.status_code, 200)
            self.assertContains(stu_page, "Ali Raza")
            self.assertNotContains(stu_page, "openUpdateMarksModal")

            att_page = client.get(reverse("panels:teacher_attendance"))
            self.assertEqual(att_page.status_code, 200)
            self.assertEqual(att_page.context["course_filter"], "CS-101")
            self.assertContains(att_page, "Ali Raza")
            self.assertNotContains(att_page, "Zara Tariq")

    def test_teacher_attendance_and_tests_crud_update_records_and_ml(self):
        uploaded_file = None
        try:
            with (
                patch("panels.teacher_services.courses_col", return_value=self.courses),
                patch("panels.teacher_services.semesters_col", return_value=self.semesters),
                patch("panels.teacher_services.student_records_col", return_value=self.students),
                patch("panels.teacher_services.users_col", return_value=self.users),
                patch("panels.teacher_services.predictions_col", return_value=self.preds),
                patch("panels.teacher_academic_services.courses_col", return_value=self.courses),
                patch("panels.teacher_academic_services.semesters_col", return_value=self.semesters),
                patch("panels.teacher_academic_services.student_records_col", return_value=self.students),
                patch("panels.teacher_academic_services.attendance_records_col", return_value=self.attendance),
                patch("panels.teacher_academic_services.course_tests_col", return_value=self.tests),
                patch("panels.teacher_academic_services.users_col", return_value=self.users),
                patch("panels.teacher_academic_services.run_prediction_pipeline") as mock_ml,
                patch("core.context_processors.notifications_col", return_value=self.notifs),
                patch("core.db.MongoDBClient.check_health", return_value=True),
            ):
                client = self._teacher_client()
                att1 = client.post(
                    reverse("panels:teacher_attendance"),
                    {"action": "save_attendance", "course": "CS-101", "course_code": "CS-101", "date": "2026-11-26", "attendance_json": json.dumps([{"student_id": "STD-101", "status": "PRESENT"}])},
                )
                self.assertRedirects(att1, f"{reverse('panels:teacher_attendance')}?course=CS-101&date=2026-11-26", fetch_redirect_response=False)
                att2 = client.post(
                    reverse("panels:teacher_attendance"),
                    {"action": "save_attendance", "course": "CS-101", "course_code": "CS-101", "date": "2026-11-27", "attendance_json": json.dumps([{"student_id": "STD-101", "status": "ABSENT"}])},
                )
                self.assertRedirects(att2, f"{reverse('panels:teacher_attendance')}?course=CS-101&date=2026-11-27", fetch_redirect_response=False)
                att3 = client.post(
                    reverse("panels:teacher_attendance"),
                    {"action": "save_attendance", "course": "CS-101", "course_code": "CS-101", "date": "2026-11-28", "attendance_json": json.dumps([{"student_id": "STD-101", "status": "LEAVE"}])},
                )
                self.assertRedirects(att3, f"{reverse('panels:teacher_attendance')}?course=CS-101&date=2026-11-28", fetch_redirect_response=False)
                self.assertEqual(len(self.attendance.docs), 3)
                self.assertAlmostEqual(self.students.find_one({"student_id": "STD-101"})["attendance_pct"], 33.33, places=2)
                self.assertEqual(mock_ml.call_count, 3)

                att_upload = SimpleUploadedFile("quiz_guide.txt", b"Quiz instructions", content_type="text/plain")
                c_resp = client.post(
                    reverse("panels:teacher_tests"),
                    {"action": "create_test", "title": "Quiz 1", "course_code": "CS-101", "test_type": "Quiz", "max_marks": "50", "due_date": "2026-12-05", "notes": "Bring calculator", "attachment": att_upload},
                )
                self.assertRedirects(c_resp, reverse("panels:teacher_tests"), fetch_redirect_response=False)
                self.assertEqual(len(self.tests.docs), 1)
                created = self.tests.docs[0]
                tid = created["test_id"]
                self.assertEqual(created["due_date"], "2026-12-05")
                self.assertEqual(created["attachment_name"], "quiz_guide.txt")
                self.assertTrue(created["attachment_url"].startswith("/static/uploads/tests/"))
                uploaded_file = Path(settings.BASE_DIR) / created["attachment_url"].lstrip("/")
                self.assertTrue(uploaded_file.exists())

                u_resp = client.post(
                    reverse("panels:teacher_tests"),
                    {"action": "update_test", "test_id": tid, "title": "Quiz 1 Updated", "course_code": "CS-101", "test_type": "Midterm", "max_marks": "50", "due_date": "2026-12-06"},
                )
                self.assertRedirects(u_resp, reverse("panels:teacher_tests"), fetch_redirect_response=False)
                self.assertEqual(self.tests.docs[0]["title"], "Quiz 1 Updated")

                grade_url = reverse("panels:teacher_test_grade", kwargs={"test_id": tid})
                grade_page = client.get(grade_url)
                self.assertEqual(grade_page.status_code, 200)
                self.assertContains(grade_page, "Ali Raza")
                self.assertNotContains(grade_page, "Zara Tariq")

                g_resp = client.post(grade_url, {"student_id": "STD-101", "marks_STD-101": "42", "remarks_STD-101": "Good work"})
                self.assertRedirects(g_resp, grade_url, fetch_redirect_response=False)
                sub = self.tests.docs[0]["submissions"]["STD-101"]
                self.assertEqual(sub["obtained_marks"], 42.0)
                self.assertEqual(sub["percentage"], 84.0)
                self.assertEqual(sub["remarks"], "Good work")
                self.assertEqual(self.students.find_one({"student_id": "STD-101"})["internal_marks"], 84.0)
                self.assertEqual(mock_ml.call_count, 4)

                d_resp = client.post(reverse("panels:teacher_tests"), {"action": "delete_test", "test_id": tid})
                self.assertRedirects(d_resp, reverse("panels:teacher_tests"), fetch_redirect_response=False)
                self.assertEqual(len(self.tests.docs), 0)
        finally:
            if uploaded_file and uploaded_file.exists():
                uploaded_file.unlink()
