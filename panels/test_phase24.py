from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from django.test import Client, TestCase
from core.db import invalidate_cache
import panels.admin_seed as admin_seed
from panels.directory_card_services import build_admin_user_cards, build_teacher_student_cards
from panels.test_admin import _MemCol


class DirectoryCardServicesUnitTests(TestCase):
    def test_build_admin_user_cards_self_guard_and_fields(self):
        users = [
            {
                "user_id": "USR-ADM-1",
                "full_name": "Root Admin",
                "email": "admin@edupredict.edu",
                "role": "ADMIN",
                "department": "Administration",
                "batch": "ALL",
                "is_active": True,
                "avatar_url": "https://cdn.example.com/a.jpg",
                "created_at_str": "2026-11-18",
            },
            {
                "user_id": "USR-1002",
                "full_name": "Bilal Ahmed",
                "email": "bilal@edupredict.edu",
                "role": "TEACHER",
                "department": "CS",
                "batch": "2026-A",
                "is_active": False,
                "avatar_url": "",
                "created_at_str": "2026-11-19",
            },
        ]
        cards = build_admin_user_cards(users, "ALL", "USR-ADM-1", actor_email="admin@edupredict.edu")
        self.assertEqual(len(cards), 2)
        self_card, other_card = cards[0], cards[1]
        self.assertEqual(self_card["title"], "Root Admin (You)")
        self.assertEqual(self_card["avatar_url"], "https://cdn.example.com/a.jpg")
        self.assertEqual(self_card["role_badge"], {"text": "ADMIN", "status": "info"})
        self.assertEqual(len(self_card["actions"]), 1)
        self.assertEqual(self_card["actions"][0]["onclick"], "openEditUserModal(this)")
        self.assertEqual(self_card["actions"][0]["attrs"].get("data-is-self"), "true")

        self.assertEqual(other_card["title"], "Bilal Ahmed")
        self.assertEqual(other_card["initials"], "BA")
        self.assertEqual(other_card["badge"], {"text": "Inactive", "status": "danger"})
        self.assertEqual([a["onclick"] for a in other_card["actions"]], ["openEditUserModal(this)", "openToggleUserModal(this)", "openDeleteUserModal(this)"])
        self.assertEqual(other_card["actions"][2]["variant"], "danger")

    @patch("panels.directory_card_services.users_col")
    def test_build_teacher_student_cards_joined_and_fallback(self, mock_users_col):
        col = MagicMock()
        col.find.return_value = [{"student_id": "STD-2026-001", "avatar_url": "https://cdn.example.com/s1.jpg"}]
        mock_users_col.return_value = col

        joined = [{
            "student_id": "STD-2026-001",
            "full_name": "Zainab Raza",
            "batch": "2026-A",
            "course_code": "CS-101",
            "attendance_pct": 68.0,
            "internal_marks": 64.0,
            "assignment_score": 70.0,
            "lms_hours_weekly": 9.0,
            "previous_gpa": 2.8,
            "predicted_gpa": 2.6,
            "badge": {"text": "Needs Help", "status": "warning"},
        }]
        cards = build_teacher_student_cards(joined, include_alert=True, include_delete=True)
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0]["avatar_url"], "https://cdn.example.com/s1.jpg")
        self.assertEqual(cards[0]["badge"], {"text": "Needs Help", "status": "warning"})
        self.assertEqual([a["onclick"] for a in cards[0]["actions"]], ["openUpdateMarksModal(this)", "openSendAlertModal(this)", "openDeleteStudentModal(this)"])

        mock_users_col.side_effect = RuntimeError("db unavailable")
        rows_9 = [["STD-2026-002", "Hamza Ali", "2026-A", "CS-102", "90.0%", "88.0", "3.60", {"text": "Excellent", "status": "success"}, {"actions": []}]]
        fallback_cards = build_teacher_student_cards(None, fallback_rows=rows_9, include_alert=False, include_delete=True)
        self.assertEqual(len(fallback_cards), 1)
        self.assertEqual(fallback_cards[0]["id"], "STD-2026-002")
        self.assertEqual(fallback_cards[0]["meta"][3]["value"], "88.0 / 3.60")
        self.assertEqual([a["onclick"] for a in fallback_cards[0]["actions"]], ["openUpdateMarksModal(this)", "openDeleteStudentModal(this)"])


class Phase24IntegrationTests(TestCase):
    def setUp(self):
        invalidate_cache()
        now = datetime(2026, 11, 20, 9, 0, tzinfo=timezone.utc)
        self.cols = {
            "activity_logs": _MemCol(),
            "system_settings": _MemCol(),
            "notifications": _MemCol(),
            "datasets_log": _MemCol(),
            "users": _MemCol([
                {"user_id": "USR-ADM-1", "full_name": "Root Admin", "email": "admin@edupredict.edu", "role": "ADMIN", "department": "Admin", "batch": "ALL", "is_active": True, "created_at": now},
                {"user_id": "USR-1003", "student_id": "STD-2026-001", "full_name": "Zainab Raza", "email": "zainab@edupredict.edu", "role": "STUDENT", "department": "CS", "batch": "2026-A", "is_active": True, "created_at": now},
            ]),
            "courses": _MemCol([{"course_code": "CS-101", "title": "Intro to CS", "department": "CS", "batch": "2026-A", "instructor": "Dr. Ayesha", "status": "ACTIVE", "created_at": now}]),
            "student_records": _MemCol([{"student_id": "STD-2026-001", "full_name": "Zainab Raza", "batch": "2026-A", "course_code": "CS-101", "attendance_pct": 85.0, "internal_marks": 80.0, "assignment_score": 82.0, "lms_hours_weekly": 10.0, "previous_gpa": 3.4, "updated_at": now}]),
            "predictions": _MemCol([{"student_id": "STD-2026-001", "predicted_gpa": 3.5, "risk_level": "LOW", "risk_score": 0.15, "is_anomaly": False, "generated_at": now}]),
            "support_tickets": _MemCol(),
        }
        for p in (
            patch("core.db.MongoDBClient.get_collection", side_effect=lambda name: self.cols.setdefault(name, _MemCol())),
            patch("core.db.MongoDBClient.check_health", return_value={"connected": True, "error": None}),
            patch.object(admin_seed, "_ADMIN_SEED_DONE", True),
        ):
            p.start()
            self.addCleanup(p.stop)

    def _login(self, role, user_id="USR-1", student_id=None):
        client = Client()
        session = client.session
        user = {"user_id": user_id, "role": role, "email": f"{role.lower()}@edupredict.edu", "full_name": f"Test {role.title()}"}
        if student_id:
            user["student_id"] = student_id
        session["user"] = user
        session.save()
        return client

    def test_phase24_panel_markers(self):
        admin = self._login("ADMIN", user_id="USR-ADM-1")
        r_admin_users = admin.get("/admin-panel/users/")
        self.assertEqual(r_admin_users.status_code, 200)
        h_au = r_admin_users.content.decode("utf-8")
        for m in ('id="admin-users-table"', "data-directory-cards", "data-paginated-container"):
            self.assertIn(m, h_au)

        teacher = self._login("TEACHER", user_id="USR-T1")
        r_t_students = teacher.get("/teacher-panel/students/")
        self.assertEqual(r_t_students.status_code, 200)
        h_ts = r_t_students.content.decode("utf-8")
        for m in ('id="teacher-students-table"', "data-directory-cards", "openQuickEntryModal()"):
            self.assertIn(m, h_ts)

        r_t_ingest = teacher.get("/teacher-panel/ingest/")
        self.assertEqual(r_t_ingest.status_code, 200)
        h_ti = r_t_ingest.content.decode("utf-8")
        for m in ('id="teacher-roster-table"', 'id="teacher-upload-modal"', "openUploadSheetModal()", "openQuickEntryModal()"):
            self.assertIn(m, h_ti)

        analyst = self._login("ANALYST", user_id="USR-AN1")
        r_an = analyst.get("/analyst-panel/")
        self.assertEqual(r_an.status_code, 200)
        h_an = r_an.content.decode("utf-8")
        for m in ('id="analyst-upload-modal"', "openAnalystUploadModal()", "data-dot-kpi"):
            self.assertIn(m, h_an)

        student = self._login("STUDENT", user_id="USR-1003", student_id="STD-2026-001")
        for c, path in ((admin, "/admin-panel/"), (teacher, "/teacher-panel/"), (student, "/student-panel/")):
            resp = c.get(path)
            self.assertEqual(resp.status_code, 200)
            html = resp.content.decode("utf-8")
            self.assertIn("data-dot-kpi", html)
            self.assertIn("data-dot-matrix", html)
