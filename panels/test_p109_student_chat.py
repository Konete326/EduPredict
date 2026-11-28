import json
import re
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from core.db import invalidate_cache
from panels.teacher_academic_services import create_course_test


class _FakeCursor(list):
    def sort(self, key, direction=1):
        def _sort_key(d):
            val = d.get(key)
            if isinstance(val, datetime):
                return (1, val.timestamp())
            return (0, str(val or ""))
        return _FakeCursor(sorted(self, key=_sort_key, reverse=(direction == -1)))


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

    def insert_one(self, doc):
        d = dict(doc)
        d.setdefault("_id", f"id-{len(self.docs) + 1}")
        self.docs.append(d)
        return MagicMock(inserted_id=d["_id"])

    def update_one(self, query, update, upsert=False):
        for d in self.docs:
            if self._match(d, query):
                for key, val in (update.get("$set") or {}).items():
                    if "." in key:
                        parts = key.split(".")
                        target = d
                        for p in parts[:-1]:
                            if not isinstance(target.get(p), dict):
                                target[p] = {}
                            target = target[p]
                        target[parts[-1]] = val
                    else:
                        d[key] = val
                for key, val in (update.get("$addToSet") or {}).items():
                    arr = d.setdefault(key, [])
                    if val not in arr:
                        arr.append(val)
                return MagicMock(matched_count=1, modified_count=1)
        return MagicMock(matched_count=0, modified_count=0)

    def delete_one(self, query):
        for i, d in enumerate(self.docs):
            if self._match(d, query):
                self.docs.pop(i)
                return MagicMock(deleted_count=1)
        return MagicMock(deleted_count=0)


class StudentTestsAndClassroomChatTests(TestCase):
    def setUp(self):
        invalidate_cache()
        now = datetime.now(timezone.utc)
        yesterday = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
        tomorrow = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
        self.semesters = _FakeCol([
            {"semester_id": "SEM-1", "program_name": "BSCS", "semester_name": "Semester 1", "semester_number": 1},
            {"semester_id": "SEM-2", "program_name": "BSCS", "semester_name": "Semester 2", "semester_number": 2},
        ])
        self.users = _FakeCol([
            {"user_id": "USR-STU-1", "student_id": "STU-101", "full_name": "Sara Khan", "email": "sara@edupredict.edu", "role": "STUDENT", "semester_id": "SEM-1", "status": "ACTIVE"},
            {"user_id": "USR-TEA-1", "full_name": "Prof. Ali", "email": "ali@edupredict.edu", "role": "TEACHER", "status": "ACTIVE"},
            {"user_id": "USR-ADM-1", "full_name": "Root Admin", "email": "admin@edupredict.edu", "role": "ADMIN", "status": "ACTIVE"},
        ])
        self.courses = _FakeCol([
            {"course_code": "CS101", "title": "Intro to CS", "semester_id": "SEM-1", "instructor_id": "USR-TEA-1", "instructor_email": "ali@edupredict.edu", "instructor": "Prof. Ali", "status": "ACTIVE"},
            {"course_code": "CS201", "title": "Data Structures", "semester_id": "SEM-2", "instructor_id": "USR-TEA-1", "instructor_email": "ali@edupredict.edu", "instructor": "Prof. Ali", "status": "ACTIVE"},
            {"course_code": "CS301", "title": "Operating Systems", "semester_id": "SEM-2", "instructor_id": "USR-TEA-2", "instructor_email": "other@edupredict.edu", "instructor": "Prof. Zara", "status": "ACTIVE"},
        ])
        self.records = _FakeCol([
            {"student_id": "STU-101", "full_name": "Sara Khan", "course_code": "CS101", "semester_id": "SEM-1"},
        ])
        self.tests = _FakeCol([
            {"test_id": "TST-ONTIME", "title": "Quiz 1", "course_code": "CS101", "semester_id": "SEM-1", "test_type": "Quiz", "max_marks": 20, "test_date": yesterday, "due_date": tomorrow, "submissions": {}, "created_at": now},
            {"test_id": "TST-PAST", "title": "Lab 1", "course_code": "CS101", "semester_id": "SEM-1", "test_type": "Lab", "max_marks": 30, "test_date": yesterday, "due_date": yesterday, "submissions": {}, "created_at": now},
            {"test_id": "TST-OTHER", "title": "Other Sem Quiz", "course_code": "CS201", "semester_id": "SEM-2", "test_type": "Quiz", "max_marks": 20, "test_date": yesterday, "due_date": tomorrow, "submissions": {}, "created_at": now},
        ])
        self.chat_msgs = _FakeCol()

    def _client_as(self, user_doc):
        c = Client()
        s = c.session
        s["user"] = dict(user_doc)
        s.save()
        return c

    def test_student_tests_semester_filter_multifile_and_late_submission(self):
        stu = self.users.find_one({"user_id": "USR-STU-1"})
        client = self._client_as(stu)
        with patch("panels.student_test_services.users_col", return_value=self.users), \
             patch("panels.student_test_services.semesters_col", return_value=self.semesters), \
             patch("panels.student_test_services.courses_col", return_value=self.courses), \
             patch("panels.student_test_services.student_records_col", return_value=self.records), \
             patch("panels.student_test_services.course_tests_col", return_value=self.tests), \
             patch("panels.student_test_services.is_cloudinary_configured", return_value=True), \
             patch("panels.student_test_services.upload_academic_attachment", side_effect=lambda f, **kw: (f"https://cdn.example.com/{f.name}", f.name, f.name.endswith(".png"), None)):
            resp = client.get(reverse("panels:student_tests"))
            self.assertEqual(resp.status_code, 200)
            self.assertContains(resp, "Quiz 1")
            self.assertContains(resp, "Lab 1")
            self.assertNotContains(resp, "Other Sem Quiz")

            img = SimpleUploadedFile("ans.png", b"\x89PNG\r\n\x1a\n" + b"0" * 32, content_type="image/png")
            csv = SimpleUploadedFile("data.csv", b"col1,col2\n1,2\n", content_type="text/csv")
            post_ontime = client.post(reverse("panels:student_tests"), {"action": "submit_test", "test_id": "TST-ONTIME", "submission_note": "Attached both", "files": [img, csv]})
            self.assertEqual(post_ontime.status_code, 302)
            ontime_sub = self.tests.find_one({"test_id": "TST-ONTIME"})["submissions"]["STU-101"]
            self.assertEqual(ontime_sub["submission_status"], "SUBMITTED")
            self.assertEqual(len(ontime_sub["files"]), 2)

            late_csv = SimpleUploadedFile("late.csv", b"a,b\n3,4\n", content_type="text/csv")
            post_late = client.post(reverse("panels:student_tests"), {"action": "submit_test", "test_id": "TST-PAST", "submission_note": "Late work", "files": [late_csv]})
            self.assertEqual(post_late.status_code, 302)
            late_sub = self.tests.find_one({"test_id": "TST-PAST"})["submissions"]["STU-101"]
            self.assertEqual(late_sub["submission_status"], "LATE")

    def test_teacher_create_test_autoposts_assignment_card_to_chat(self):
        tea = self.users.find_one({"user_id": "USR-TEA-1"})
        with patch("panels.teacher_academic_services.courses_col", return_value=self.courses), \
             patch("panels.teacher_academic_services.course_tests_col", return_value=self.tests), \
             patch("panels.teacher_academic_services.classroom_messages_col", return_value=self.chat_msgs):
            doc, err = create_course_test({"title": "Midterm 1", "course_code": "CS101", "test_type": "Midterm", "max_marks": "50"}, teacher_user=tea)
            self.assertIsNone(err)
            self.assertIsNotNone(doc)
        posted = self.chat_msgs.find_one({"group_id": "CS101", "msg_type": "ASSIGNMENT"})
        self.assertIsNotNone(posted)
        self.assertEqual(posted["test_id"], doc["test_id"])
        self.assertIn("Midterm 1", posted["text"])

    def test_classroom_chat_rbac_badges_polls_media_edit_and_delete(self):
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
             patch("panels.chat_services.upload_academic_attachment", side_effect=lambda f, **kw: (f"https://cdn.example.com/{f.name}", f.name, f.name.endswith(".png"), None)):
            self.assertEqual([g["group_id"] for g in c_stu.get(api_url).json()["groups"]], ["CS101"])
            self.assertEqual([g["group_id"] for g in c_tea.get(api_url).json()["groups"]], ["CS101", "CS201"])
            self.assertEqual([g["group_id"] for g in c_adm.get(api_url).json()["groups"]], ["CS101", "CS201", "CS301"])
            self.assertEqual(c_stu.get(api_url, {"group_id": "CS301"}).status_code, 403)

            r_page = c_stu.get(reverse("panels:classroom_chat"))
            self.assertEqual(r_page.status_code, 200)

            poll_res = c_tea.post(api_url, data=json.dumps({"action": "poll", "group_id": "CS101", "poll_question": "Extra class?", "poll_options": ["Friday", "Saturday"]}), content_type="application/json").json()
            self.assertTrue(poll_res["ok"])
            poll_id = poll_res["msg_id"]
            self.assertTrue(c_stu.post(api_url, data=json.dumps({"action": "vote", "group_id": "CS101", "msg_id": poll_id, "option_idx": 0}), content_type="application/json").json()["ok"])

            img_res = c_stu.post(api_url, {"action": "send", "group_id": "CS101", "text": "Slide pic", "image": SimpleUploadedFile("pic.png", b"\x89PNG\r\n\x1a\n" + b"1" * 16, content_type="image/png")}).json()
            self.assertTrue(img_res["ok"])
            aud_res = c_adm.post(api_url, {"action": "send", "group_id": "CS101", "audio": SimpleUploadedFile("note.webm", b"WEBM" + b"2" * 16, content_type="audio/webm")}).json()
            self.assertTrue(aud_res["ok"])

            msgs = c_stu.get(api_url, {"group_id": "CS101"}).json()["messages"]
            roles = {m["sender_profile"]["role"] for m in msgs}
            self.assertEqual(roles, {"STUDENT", "TEACHER", "ADMIN"})
            poll_msg = next(m for m in msgs if m["msg_id"] == poll_id)
            self.assertEqual(poll_msg["poll"]["total_votes"], 1)
            self.assertEqual(poll_msg["poll"]["my_vote"], 0)

            img_id = img_res["msg_id"]
            self.assertTrue(c_stu.post(api_url, data=json.dumps({"action": "edit", "group_id": "CS101", "msg_id": img_id, "text": "Updated pic"}), content_type="application/json").json()["ok"])
            self.assertTrue(c_stu.post(api_url, data=json.dumps({"action": "delete", "group_id": "CS101", "msg_id": aud_res["msg_id"], "scope": "me"}), content_type="application/json").json()["ok"])
            stu_msgs_after_me = c_stu.get(api_url, {"group_id": "CS101"}).json()["messages"]
            self.assertFalse(any(m["msg_id"] == aud_res["msg_id"] for m in stu_msgs_after_me))
            self.assertTrue(any(m["msg_id"] == aud_res["msg_id"] for m in c_adm.get(api_url, {"group_id": "CS101"}).json()["messages"]))

            self.assertTrue(c_stu.post(api_url, data=json.dumps({"action": "delete", "group_id": "CS101", "msg_id": img_id, "scope": "everyone"}), content_type="application/json").json()["ok"])
            tea_msgs = c_tea.get(api_url, {"group_id": "CS101"}).json()["messages"]
            deleted_msg = next(m for m in tea_msgs if m["msg_id"] == img_id)
            self.assertTrue(deleted_msg["deleted_for_all"])
            self.assertEqual(deleted_msg["text"], "This message was deleted")

    def test_student_attendance_history_page(self):
        stu = self.users.find_one({"user_id": "USR-STU-1"})
        client = self._client_as(stu)
        att_col = _FakeCol([
            {"student_id": "STU-101", "course_code": "CS101", "date": "2026-11-25", "status": "PRESENT", "marked_by": "Prof. Ali"},
            {"student_id": "STU-101", "course_code": "CS101", "date": "2026-11-26", "status": "ABSENT", "marked_by": "Prof. Ali"},
            {"student_id": "STU-101", "course_code": "CS101", "date": "2026-11-27", "status": "LEAVE", "marked_by": "Prof. Ali"},
        ])
        with patch("panels.student_test_services.users_col", return_value=self.users), \
             patch("panels.student_test_services.semesters_col", return_value=self.semesters), \
             patch("panels.student_test_services.courses_col", return_value=self.courses), \
             patch("panels.student_test_services.student_records_col", return_value=self.records), \
             patch("panels.student_test_services.attendance_records_col", return_value=att_col):
            resp = client.get(reverse("panels:student_attendance"))
            self.assertEqual(resp.status_code, 200)
            self.assertContains(resp, "My Attendance")
            self.assertContains(resp, "CS101")
            self.assertContains(resp, "Present")
            self.assertContains(resp, "Absent")
            self.assertContains(resp, "Leave")
            self.assertContains(resp, "2026-11-27")

