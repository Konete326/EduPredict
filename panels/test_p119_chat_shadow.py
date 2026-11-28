import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from django.conf import settings
from django.test import Client, TestCase
from django.urls import reverse
from core.db import invalidate_cache
from panels.test_p109_student_chat import _FakeCol


class Phase119ChatAndShadowTests(TestCase):
    def setUp(self):
        invalidate_cache()
        now = datetime.now(timezone.utc)
        self.semesters = _FakeCol([
            {"semester_id": "SEM-1", "program_name": "BSCS", "semester_name": "Semester 1", "semester_number": 1},
        ])
        self.users = _FakeCol([
            {"user_id": "USR-STU-1", "student_id": "STU-101", "full_name": "Sara Khan", "email": "sara@edupredict.edu", "role": "STUDENT", "semester_id": "SEM-1", "status": "ACTIVE"},
            {"user_id": "USR-TEA-1", "full_name": "Prof. Ali", "email": "ali@edupredict.edu", "role": "TEACHER", "status": "ACTIVE"},
            {"user_id": "USR-ADM-1", "full_name": "Root Admin", "email": "admin@edupredict.edu", "role": "ADMIN", "status": "ACTIVE"},
        ])
        self.courses = _FakeCol([
            {"course_code": "CS101", "title": "Intro to CS", "semester_id": "SEM-1", "instructor_id": "USR-TEA-1", "instructor_email": "ali@edupredict.edu", "instructor": "Prof. Ali", "status": "ACTIVE", "chat_active": True},
        ])
        self.records = _FakeCol([
            {"student_id": "STU-101", "full_name": "Sara Khan", "course_code": "CS101", "semester_id": "SEM-1"},
        ])
        self.chat_msgs = _FakeCol([
            {"msg_id": "MSG-SEED", "group_id": "CS101", "sender_user_id": "USR-TEA-1", "sender_name": "Prof. Ali", "text": "Welcome", "msg_type": "TEXT", "read_by": ["USR-TEA-1"], "created_at": now},
        ])

    def _client_as(self, user_doc):
        c = Client()
        s = c.session
        s["user"] = dict(user_doc)
        s.save()
        return c

    def test_class_chat_realtime_send_edit_delete_vote_and_read_updated_at(self):
        stu = self.users.find_one({"user_id": "USR-STU-1"})
        tea = self.users.find_one({"user_id": "USR-TEA-1"})
        c_stu, c_tea = self._client_as(stu), self._client_as(tea)
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
            send_res = c_tea.post(api_url, data=json.dumps({"action": "send", "group_id": "CS101", "text": "Initial text"}), content_type="application/json").json()
            self.assertTrue(send_res["ok"])
            mid = send_res["msg_id"]
            self.assertEqual(next(m for m in send_res["messages"] if m["msg_id"] == mid)["tick_state"], "single")

            stu_get = c_stu.get(api_url, {"group_id": "CS101"}).json()
            self.assertEqual(next(m for m in stu_get["messages"] if m["msg_id"] == mid)["tick_state"], "double_blue")
            stored_doc = self.chat_msgs.find_one({"msg_id": mid})
            self.assertIn("updated_at", stored_doc)

            tea_after_read = c_tea.get(api_url, {"group_id": "CS101"}).json()
            self.assertEqual(next(m for m in tea_after_read["messages"] if m["msg_id"] == mid)["tick_state"], "double_blue")

            edit_res = c_tea.post(api_url, data=json.dumps({"action": "edit", "group_id": "CS101", "msg_id": mid, "text": "Edited text"}), content_type="application/json").json()
            self.assertTrue(edit_res["ok"])
            self.assertIn("messages", edit_res)
            self.assertIn("groups", edit_res)
            stu_sees_edit = next(m for m in c_stu.get(api_url, {"group_id": "CS101"}).json()["messages"] if m["msg_id"] == mid)
            self.assertEqual(stu_sees_edit["text"], "Edited text")
            self.assertTrue(stu_sees_edit["edited"])

            poll_res = c_tea.post(api_url, data=json.dumps({"action": "poll", "group_id": "CS101", "poll_question": "Lab?", "poll_options": ["Yes", "No"]}), content_type="application/json").json()
            poll_id = poll_res["msg_id"]
            vote_res = c_stu.post(api_url, data=json.dumps({"action": "vote", "group_id": "CS101", "msg_id": poll_id, "option_idx": 1}), content_type="application/json").json()
            self.assertTrue(vote_res["ok"])
            self.assertIn("messages", vote_res)
            self.assertIn("groups", vote_res)
            self.assertEqual(next(m for m in vote_res["messages"] if m["msg_id"] == poll_id)["poll"]["total_votes"], 1)

            del_res = c_tea.post(api_url, data=json.dumps({"action": "delete", "group_id": "CS101", "msg_id": mid, "scope": "everyone"}), content_type="application/json").json()
            self.assertTrue(del_res["ok"])
            self.assertIn("messages", del_res)
            self.assertIn("groups", del_res)
            self.assertTrue(next(m for m in del_res["messages"] if m["msg_id"] == mid)["deleted_for_all"])

    def test_staff_chat_realtime_send_edit_and_delete(self):
        adm = self.users.find_one({"user_id": "USR-ADM-1"})
        tea = self.users.find_one({"user_id": "USR-TEA-1"})
        c_adm, c_tea = self._client_as(adm), self._client_as(tea)
        staff_api = reverse("panels:staff_chat_api")

        with patch("panels.staff_chat_services.users_col", return_value=self.users), \
             patch("panels.staff_chat_services.classroom_messages_col", return_value=self.chat_msgs), \
             patch("panels.chat_receipt_services.users_col", return_value=self.users), \
             patch("panels.chat_receipt_services.classroom_messages_col", return_value=self.chat_msgs):
            sent = c_adm.post(staff_api, data=json.dumps({"action": "send", "group_id": "STAFF-ALL", "text": "Meeting at 3"}), content_type="application/json").json()
            self.assertTrue(sent["ok"])
            mid = sent["msg_id"]

            tea_read = c_tea.get(staff_api, {"group_id": "STAFF-ALL"}).json()
            self.assertEqual(next(m for m in tea_read["messages"] if m["msg_id"] == mid)["tick_state"], "double_blue")

            edited = c_adm.post(staff_api, data=json.dumps({"action": "edit", "group_id": "STAFF-ALL", "msg_id": mid, "text": "Meeting at 4"}), content_type="application/json").json()
            self.assertTrue(edited["ok"])
            self.assertIn("messages", edited)
            self.assertIn("groups", edited)
            tea_sees = next(m for m in c_tea.get(staff_api, {"group_id": "STAFF-ALL"}).json()["messages"] if m["msg_id"] == mid)
            self.assertEqual(tea_sees["text"], "Meeting at 4")
            self.assertTrue(tea_sees["edited"])

            deleted = c_adm.post(staff_api, data=json.dumps({"action": "delete", "group_id": "STAFF-ALL", "msg_id": mid, "scope": "everyone"}), content_type="application/json").json()
            self.assertTrue(deleted["ok"])
            self.assertTrue(next(m for m in deleted["messages"] if m["msg_id"] == mid)["deleted_for_all"])

    def test_phase119_frontend_contracts_nav_and_landing_shadows(self):
        base_dir = Path(settings.BASE_DIR)
        nav_js = (base_dir / "static" / "js" / "nav.js").read_text(encoding="utf-8")
        self.assertIn("'/chat'", nav_js)
        self.assertIn("'/staff-chat'", nav_js)
        self.assertIn("s.async = false", nav_js)
        self.assertIn("no-store", nav_js)

        css_src = (base_dir / "static" / "css" / "landing_provably.css").read_text(encoding="utf-8")
        self.assertIn(".targo-scrim", css_src)
        self.assertIn("mask-image:radial-gradient", css_src)

        public_base = (base_dir / "templates" / "public" / "_base.html").read_text(encoding="utf-8")
        self.assertIn("?v=18", public_base)
