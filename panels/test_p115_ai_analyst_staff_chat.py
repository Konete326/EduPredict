import json
import re
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from django.test import Client, TestCase
from django.urls import reverse
from core.ai_agent_services import _build_chat_and_training_context
from core.db import invalidate_cache


class _FakeCursor(list):
    def sort(self, key, direction=1):
        def _sort_key(d):
            val = d.get(key)
            if isinstance(val, datetime):
                return (1, val.timestamp())
            return (0, str(val or ""))
        return _FakeCursor(sorted(self, key=_sort_key, reverse=(direction == -1)))

    def limit(self, n):
        return _FakeCursor(self[:n])


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
            if k == "$and":
                if not all(self._match(doc, sub) for sub in v):
                    return False
                continue
            val = doc.get(k)
            if isinstance(v, dict):
                if "$in" in v and val not in v["$in"]:
                    return False
                if "$ne" in v and val == v["$ne"]:
                    return False
                if "$gt" in v and not (val is not None and val > v["$gt"]):
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

    def count_documents(self, query=None):
        return len([d for d in self.docs if self._match(d, query)])

    def insert_one(self, doc):
        d = dict(doc)
        d.setdefault("_id", f"id-{len(self.docs) + 1}")
        self.docs.append(d)
        return MagicMock(inserted_id=d["_id"])

    def update_one(self, query, update, upsert=False):
        for d in self.docs:
            if self._match(d, query):
                for key, val in (update.get("$set") or {}).items():
                    d[key] = val
                for key, val in (update.get("$addToSet") or {}).items():
                    arr = d.setdefault(key, [])
                    if val not in arr:
                        arr.append(val)
                return MagicMock(matched_count=1, modified_count=1)
        return MagicMock(matched_count=0, modified_count=0)


class Phase115AiAnalystStaffChatTests(TestCase):
    def setUp(self):
        invalidate_cache()
        now = datetime.now(timezone.utc)
        self.semesters = _FakeCol([
            {"semester_id": "SEM-1", "program_name": "BSCS", "semester_name": "Semester 1", "semester_number": 1},
        ])
        self.users = _FakeCol([
            {"user_id": "USR-STU-1", "student_id": "STU-101", "full_name": "Sara Khan", "email": "sara@edupredict.edu", "role": "STUDENT", "semester_id": "SEM-1", "status": "ACTIVE"},
            {"user_id": "USR-TEA-1", "full_name": "Prof. Ali", "email": "ali@edupredict.edu", "role": "TEACHER", "status": "ACTIVE"},
            {"user_id": "USR-ANA-1", "full_name": "Analyst Zara", "email": "zara@edupredict.edu", "role": "ANALYST", "status": "ACTIVE"},
            {"user_id": "USR-ADM-1", "full_name": "Root Admin", "email": "admin@edupredict.edu", "role": "ADMIN", "status": "ACTIVE"},
        ])
        self.courses = _FakeCol([
            {"course_code": "CS101", "title": "Intro to CS", "semester_id": "SEM-1", "instructor_id": "USR-TEA-1", "instructor_email": "ali@edupredict.edu", "instructor": "Prof. Ali", "status": "ACTIVE", "chat_active": True},
        ])
        self.records = _FakeCol([
            {"student_id": "STU-101", "full_name": "Sara Khan", "course_code": "CS101", "semester_id": "SEM-1", "attendance_pct": 62, "internal_marks": 54, "previous_gpa": 2.4, "batch": "2024"},
        ])
        self.predictions = _FakeCol([
            {"student_id": "STU-101", "predicted_gpa": 2.3, "risk_level": "HIGH", "is_anomaly": False, "recommendation": "Tutoring"},
        ])
        self.tests = _FakeCol([
            {"test_id": "TST-1", "title": "Quiz 1", "course_code": "CS101", "semester_id": "SEM-1", "teacher_user_id": "USR-TEA-1"},
        ])
        self.datasets = _FakeCol([
            {"filename": "fall_2026.csv", "rows_processed": 120, "missing_values_fixed": 4, "status": "COMPLETED", "uploaded_at": now},
        ])
        self.chat_msgs = _FakeCol([
            {"msg_id": "MSG-STU-1", "group_id": "CS101", "sender_user_id": "USR-TEA-1", "sender_name": "Prof. Ali", "text": "Class starts at 9", "msg_type": "TEXT", "read_by": ["USR-TEA-1"], "created_at": now},
            {"msg_id": "MSG-STAFF-1", "group_id": "STAFF", "sender_user_id": "USR-ADM-1", "sender_name": "Root Admin", "text": "Secret staff note", "msg_type": "TEXT", "read_by": ["USR-ADM-1"], "created_at": now},
        ])
        self.notifications = _FakeCol()

    def _client_as(self, user_doc):
        c = Client()
        s = c.session
        s["user"] = dict(user_doc)
        s.save()
        return c

    def test_ai_dock_role_scoped_context_and_ui_elements(self):
        stu = self.users.find_one({"user_id": "USR-STU-1"})
        adm = self.users.find_one({"user_id": "USR-ADM-1"})
        ana = self.users.find_one({"user_id": "USR-ANA-1"})
        with patch("core.ai_agent_services.classroom_messages_col", return_value=self.chat_msgs), \
             patch("core.ai_agent_services.course_tests_col", return_value=self.tests), \
             patch("core.ai_agent_services.datasets_log_col", return_value=self.datasets), \
             patch("panels.chat_services.users_col", return_value=self.users), \
             patch("panels.chat_services.semesters_col", return_value=self.semesters), \
             patch("panels.chat_services.courses_col", return_value=self.courses), \
             patch("panels.chat_services.student_records_col", return_value=self.records):
            stu_ctx = _build_chat_and_training_context(stu, "STUDENT", "USR-STU-1")
            self.assertEqual(stu_ctx["training_datasets_count"], 0)
            self.assertIsNone(stu_ctx["latest_training_dataset"])
            self.assertFalse(any(m["group"] in ("STAFF", "STAFF_CHAT", "STAFF_ROOM") for m in stu_ctx["recent_chat_messages"]))

            adm_ctx = _build_chat_and_training_context(adm, "ADMIN", "USR-ADM-1")
            self.assertEqual(adm_ctx["training_datasets_count"], 1)
            self.assertEqual(adm_ctx["latest_training_dataset"]["filename"], "fall_2026.csv")

            ana_ctx = _build_chat_and_training_context(ana, "ANALYST", "USR-ANA-1")
            self.assertEqual(ana_ctx["training_datasets_count"], 1)
            self.assertEqual(ana_ctx["latest_training_dataset"]["rows_processed"], 120)

        c_adm = self._client_as(adm)
        with patch("panels.analyst_alert_services.datasets_log_col", return_value=self.datasets), \
             patch("panels.analyst_alert_services.student_records_col", return_value=self.records), \
             patch("panels.analyst_alert_services.courses_col", return_value=self.courses):
            resp = c_adm.get(reverse("panels:analyst_health"))
            self.assertEqual(resp.status_code, 200)
            self.assertContains(resp, "id=\"ep-dock-mic\"")
            self.assertContains(resp, "<svg")

    def test_analyst_split_pages_and_teacher_risk_alert(self):
        ana = self.users.find_one({"user_id": "USR-ANA-1"})
        c_ana = self._client_as(ana)
        with patch("panels.views_analyst.student_records_col", return_value=self.records), \
             patch("panels.views_analyst.predictions_col", return_value=self.predictions), \
             patch("panels.analyst_alert_services.datasets_log_col", return_value=self.datasets), \
             patch("panels.analyst_alert_services.student_records_col", return_value=self.records), \
             patch("panels.analyst_alert_services.courses_col", return_value=self.courses), \
             patch("panels.analyst_alert_services.users_col", return_value=self.users), \
             patch("panels.analyst_alert_services.notifications_col", return_value=self.notifications):
            dash = c_ana.get(reverse("panels:analyst_dashboard"))
            self.assertEqual(dash.status_code, 200)
            self.assertNotContains(dash, "id=\"eval-metrics-body\"")

            acc = c_ana.get(reverse("panels:analyst_accuracy"))
            self.assertEqual(acc.status_code, 200)

            hlth = c_ana.get(reverse("panels:analyst_health"))
            self.assertEqual(hlth.status_code, 200)

            alert_resp = c_ana.post(reverse("panels:analyst_notify_teacher"), {
                "student_id": "STU-101",
                "course_code": "CS101",
                "severity": "HIGH",
                "message": "Attendance dropped below 65%",
            })
            self.assertEqual(alert_resp.status_code, 302)
            notif = self.notifications.find_one({"category": "RISK_ALERT"})
            self.assertIsNotNone(notif)
            self.assertEqual(notif["target_user_id"], "USR-TEA-1")
            self.assertEqual(notif["student_id"], "STU-101")
            self.assertEqual(notif["course_code"], "CS101")

    def test_staff_chat_rbac_for_all_roles(self):
        stu = self.users.find_one({"user_id": "USR-STU-1"})
        tea = self.users.find_one({"user_id": "USR-TEA-1"})
        ana = self.users.find_one({"user_id": "USR-ANA-1"})
        adm = self.users.find_one({"user_id": "USR-ADM-1"})

        with patch("panels.staff_chat_services.users_col", return_value=self.users), \
             patch("panels.staff_chat_services.classroom_messages_col", return_value=self.chat_msgs), \
             patch("panels.chat_receipt_services.users_col", return_value=self.users), \
             patch("panels.chat_receipt_services.classroom_messages_col", return_value=self.chat_msgs):
            c_stu = self._client_as(stu)
            self.assertIn(c_stu.get(reverse("panels:staff_chat")).status_code, (302, 403))
            self.assertIn(c_stu.get(reverse("panels:staff_chat_api")).status_code, (302, 403))

            for staff_doc in (adm, tea, ana):
                c_staff = self._client_as(staff_doc)
                page = c_staff.get(reverse("panels:staff_chat"))
                self.assertEqual(page.status_code, 200)
                api = c_staff.get(reverse("panels:staff_chat_api"))
                self.assertEqual(api.status_code, 200)
                gids = [g["group_id"] for g in api.json()["groups"]]
                self.assertEqual(gids, ["STAFF-ALL", "FACULTY-ML"])

    def test_admin_group_deactivation_blocks_writes_keeps_history(self):
        stu = self.users.find_one({"user_id": "USR-STU-1"})
        tea = self.users.find_one({"user_id": "USR-TEA-1"})
        adm = self.users.find_one({"user_id": "USR-ADM-1"})
        c_stu, c_tea, c_adm = self._client_as(stu), self._client_as(tea), self._client_as(adm)
        api_url = reverse("panels:classroom_chat_api")

        with patch("panels.chat_services.users_col", return_value=self.users), \
             patch("panels.chat_services.semesters_col", return_value=self.semesters), \
             patch("panels.chat_services.courses_col", return_value=self.courses), \
             patch("panels.chat_services.student_records_col", return_value=self.records), \
             patch("panels.chat_services.classroom_messages_col", return_value=self.chat_msgs), \
             patch("panels.chat_receipt_services.users_col", return_value=self.users), \
             patch("panels.chat_receipt_services.courses_col", return_value=self.courses), \
             patch("panels.chat_receipt_services.student_records_col", return_value=self.records), \
             patch("panels.chat_receipt_services.classroom_messages_col", return_value=self.chat_msgs):
            poll_res = c_tea.post(api_url, data=json.dumps({"action": "poll", "group_id": "CS101", "poll_question": "Q?", "poll_options": ["A", "B"]}), content_type="application/json").json()
            self.assertTrue(poll_res["ok"])
            poll_id = poll_res["msg_id"]

            deact = c_adm.post(api_url, data=json.dumps({"action": "toggle_group_active", "group_id": "CS101", "chat_active": False}), content_type="application/json")
            self.assertEqual(deact.status_code, 200)
            self.assertFalse(deact.json()["group"]["chat_active"])

            hist = c_stu.get(api_url, {"group_id": "CS101"})
            self.assertEqual(hist.status_code, 200)
            cs101_group = next(g for g in hist.json()["groups"] if g["group_id"] == "CS101")
            self.assertFalse(cs101_group["chat_active"])
            self.assertGreaterEqual(len(hist.json()["messages"]), 1)

            self.assertEqual(c_stu.post(api_url, data=json.dumps({"action": "send", "group_id": "CS101", "text": "Hi"}), content_type="application/json").status_code, 403)
            self.assertEqual(c_tea.post(api_url, data=json.dumps({"action": "poll", "group_id": "CS101", "poll_question": "X?", "poll_options": ["1", "2"]}), content_type="application/json").status_code, 403)
            self.assertEqual(c_stu.post(api_url, data=json.dumps({"action": "vote", "group_id": "CS101", "msg_id": poll_id, "option_idx": 0}), content_type="application/json").status_code, 403)
