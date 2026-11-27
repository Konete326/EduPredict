import csv
import json
from pathlib import Path
from unittest.mock import patch
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from core.db import invalidate_cache
from panels.admin_academic_services import create_semester_record
from panels.admin_services import _load_training_uploads
from panels.test_admin import _MemCol


class AdminAcademicCrudTests(TestCase):
    def setUp(self):
        invalidate_cache()
        self.client = Client()
        self.users_mem = _MemCol([{
            "user_id": "USR-ADMIN", "full_name": "System Admin", "email": "admin@gmail.com",
            "role": "ADMIN", "is_active": True, "approval_status": "APPROVED",
        }])
        self.semesters_mem = _MemCol()
        self.courses_mem = _MemCol()
        self.sr_mem = _MemCol()
        self.audit_mem = _MemCol()
        self.patchers = [
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
        ]
        for p in self.patchers:
            p.start()
        s = self.client.session
        s["user"] = {"user_id": "USR-ADMIN", "full_name": "System Admin", "email": "admin@gmail.com", "role": "ADMIN"}
        s.save()

    def tearDown(self):
        for p in reversed(self.patchers):
            p.stop()
        invalidate_cache()

    def test_batch_and_school_levels_removed(self):
        res_users = self.client.get(reverse("panels:admin_users"))
        self.assertEqual(res_users.status_code, 200)
        self.assertNotContains(res_users, "Batch / Class")
        res_auth = Client().get(reverse("accounts:auth_view"))
        self.assertEqual(res_auth.status_code, 200)
        self.assertNotContains(res_auth, 'id="reg-batch"')
        self.assertNotContains(res_users, "Classes &amp; Semesters")

    def test_users_role_sync_to_teachers_and_students(self):
        self.client.post(reverse("panels:admin_users"), {
            "action": "create", "full_name": "Dr. Zara", "email": "zara@uni.edu",
            "password": "password123", "role": "TEACHER",
        })
        self.client.post(reverse("panels:admin_users"), {
            "action": "create", "full_name": "Ali Student", "email": "ali@uni.edu",
            "password": "password123", "role": "STUDENT",
        })
        self.assertContains(self.client.get(reverse("panels:admin_teachers")), "Dr. Zara")
        self.assertContains(self.client.get(reverse("panels:admin_students")), "Ali Student")

    def test_teachers_full_crud(self):
        url = reverse("panels:admin_teachers")
        self.client.post(url, {"action": "create_teacher", "full_name": "Prof. Bilal", "email": "bilal@uni.edu", "password": "password123", "phone": "03001112223"})
        t_doc = self.users_mem.find_one({"email": "bilal@uni.edu"})
        self.assertIsNotNone(t_doc)
        self.assertContains(self.client.get(url), "Prof. Bilal")
        self.client.post(url, {"action": "edit_teacher", "user_id": t_doc["user_id"], "full_name": "Prof. Bilal Khan", "email": "bilal@uni.edu", "phone": "03009998887", "is_active": "true"})
        self.assertEqual(self.users_mem.find_one({"user_id": t_doc["user_id"]})["full_name"], "Prof. Bilal Khan")
        self.client.post(url, {"action": "delete_teacher", "user_id": t_doc["user_id"]})
        self.assertIsNone(self.users_mem.find_one({"user_id": t_doc["user_id"]}))

    def test_semesters_and_students_crud(self):
        sem_url = reverse("panels:admin_semesters")
        self.client.post(sem_url, {"action": "create_semester", "program_name": "BSCS", "semester_number": "1", "total_semesters": "4", "status": "ACTIVE"})
        self.assertEqual(self.semesters_mem.count_documents({"program_name": "BSCS"}), 4)
        sem_1 = self.semesters_mem.find_one({"program_name": "BSCS", "semester_number": 1})
        self.client.post(sem_url, {"action": "edit_semester", "semester_id": sem_1["semester_id"], "program_name": "BSCS", "semester_number": "1", "semester_name": "Semester 1 (Fall)", "status": "ACTIVE"})
        self.assertEqual(self.semesters_mem.find_one({"semester_id": sem_1["semester_id"]})["semester_name"], "Semester 1 (Fall)")
        stu_url = reverse("panels:admin_students")
        self.client.post(stu_url, {"action": "create_student", "full_name": "Sana Tariq", "email": "sana@uni.edu", "password": "password123", "semester_id": sem_1["semester_id"]})
        s_doc = self.users_mem.find_one({"email": "sana@uni.edu"})
        self.assertEqual(s_doc["semester_id"], sem_1["semester_id"])
        self.assertContains(self.client.get(stu_url), "BSCS · Semester 1 (Fall)")
        self.client.post(stu_url, {"action": "delete_student", "user_id": s_doc["user_id"]})
        self.client.post(sem_url, {"action": "delete_semester", "semester_id": sem_1["semester_id"]})
        self.assertIsNone(self.semesters_mem.find_one({"semester_id": sem_1["semester_id"]}))

    def test_courses_auto_code_and_no_credits_crud(self):
        sem_doc, err = create_semester_record("BSSE", semester_number=2)
        self.assertIsNone(err)
        self.client.post(reverse("panels:admin_teachers"), {"action": "create_teacher", "full_name": "Dr. Omar", "email": "omar@uni.edu", "password": "password123"})
        t_doc = self.users_mem.find_one({"email": "omar@uni.edu"})
        url = reverse("panels:admin_courses")
        res_get = self.client.get(url)
        self.assertEqual(res_get.status_code, 200)
        self.assertNotContains(res_get, "Credits")
        self.client.post(url, {"action": "create_course", "course_code": "", "title": "Artificial Intelligence", "semester_id": sem_doc["semester_id"], "instructor_id": t_doc["user_id"], "status": "ACTIVE"})
        c_doc = self.courses_mem.find_one({"title": "Artificial Intelligence"})
        self.assertIsNotNone(c_doc)
        self.assertTrue(c_doc["course_code"].startswith("CRS-"))
        self.assertNotIn("credits", c_doc)
        self.client.post(url, {"action": "edit_course", "original_course_code": c_doc["course_code"], "course_code": c_doc["course_code"], "title": "Applied AI", "semester_id": sem_doc["semester_id"], "instructor_id": t_doc["user_id"], "status": "ACTIVE"})
        self.assertEqual(self.courses_mem.find_one({"course_code": c_doc["course_code"]})["title"], "Applied AI")
        self.client.post(url, {"action": "delete_course", "course_code": c_doc["course_code"]})
        self.assertIsNone(self.courses_mem.find_one({"course_code": c_doc["course_code"]}))

    def test_builtin_500_row_dataset_exists(self):
        csv_path = Path(__file__).resolve().parent.parent / "static" / "samples" / "university_training_dataset_500.csv"
        self.assertTrue(csv_path.exists())
        with csv_path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertGreaterEqual(len(rows), 500)
        self.assertIn("student_id", rows[0])
        self.assertIn("dropout_risk", rows[0])

    def test_training_dataset_persists_across_refresh_and_deletes(self):
        log_mem = _MemCol()
        pred_mem = _MemCol()
        url = reverse("panels:admin_training")
        fake_ingest = {
            "status": "COMPLETED",
            "filename": "custom_uni_batch.csv",
            "rows_processed": 12,
            "missing_values_fixed": 0,
            "column_mappings": {"student_id": "student_id", "marks": "internal_marks"},
            "preview_rows": [{"student_id": "STU-101", "marks": 84}],
            "ingested_rows": [{"student_id": "STU-101"}],
        }
        fake_pred = {"model_version": "v1.0", "predictions_generated": 12, "high_risk_count": 2}
        with patch("panels.admin_services.datasets_log_col", return_value=log_mem), \
             patch("panels.admin_services.predictions_col", return_value=pred_mem), \
             patch("panels.admin_services._audit", return_value=None), \
             patch("panels.admin_services.ingest_dataset", return_value=fake_ingest), \
             patch("panels.admin_services.run_prediction_pipeline", return_value=fake_pred):
            csv_file = SimpleUploadedFile("custom_uni_batch.csv", b"student_id,marks\nSTU-101,84\n", content_type="text/csv")
            res_post = self.client.post(url, {"action": "upload_master_csv", "dataset_file": csv_file})
            self.assertEqual(res_post.status_code, 302)
            uploads, _ = _load_training_uploads()
            self.assertEqual(len(uploads), 1)
            self.assertEqual(uploads[0]["filename"], "custom_uni_batch.csv")
            dataset_id = uploads[0]["dataset_id"]
            self.assertTrue(dataset_id.startswith("DS-"))
            res_get_1 = self.client.get(url)
            self.assertEqual(res_get_1.status_code, 200)
            self.assertContains(res_get_1, "custom_uni_batch.csv")
            invalidate_cache()
            res_get_2 = self.client.get(url)
            self.assertContains(res_get_2, "custom_uni_batch.csv")
            res_del = self.client.post(url, {"action": "delete_training_dataset", "dataset_id": dataset_id, "filename": "custom_uni_batch.csv"})
            self.assertEqual(res_del.status_code, 302)
            uploads_after, _ = _load_training_uploads()
            self.assertEqual(uploads_after, [])
            self.assertNotContains(self.client.get(url), "custom_uni_batch.csv")

    def test_admin_sidebar_theme_and_training_plain_english(self):
        with patch("panels.admin_services.datasets_log_col", return_value=_MemCol()), \
             patch("panels.admin_services.predictions_col", return_value=_MemCol()):
            res = self.client.get(reverse("panels:admin_training"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Training Data")
        self.assertContains(res, "Theme &amp; Colors")
        self.assertContains(res, "Train 500-Row Sample")
        html = res.content.decode("utf-8")
        sidebar_html = html.split("</aside>")[0]
        self.assertIn("openThemeStudioModal()", sidebar_html)
        self.assertNotIn("bg-emerald-500", sidebar_html)
        self.assertNotIn("text-emerald-500", sidebar_html)
