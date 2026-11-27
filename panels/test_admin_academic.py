from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from django.test import Client, TestCase
from django.urls import reverse
from core.db import invalidate_cache
import panels.admin_audit_services as audit_svc
import panels.admin_seed as admin_seed


class _MemCursor:
    def __init__(self, docs):
        self._docs = list(docs)

    def sort(self, field, direction=1):
        if isinstance(field, list):
            for f, d in reversed(field):
                self._docs.sort(key=lambda doc: (doc.get(f) is None, str(doc.get(f) or "")), reverse=(d == -1))
            return self
        self._docs.sort(key=lambda doc: str(doc.get(field) or ""), reverse=(direction == -1))
        return self

    def limit(self, count):
        self._docs = self._docs[:count]
        return self

    def __iter__(self):
        return iter(self._docs)


class _MemCol:
    def __init__(self, docs=None):
        self._seq = 0
        self.docs = []
        for d in (docs or []):
            self.insert_one(d)

    def _matches(self, doc, query):
        for k, v in (query or {}).items():
            if k == "$or" and not any(self._matches(doc, sub) for sub in v):
                return False
            elif isinstance(v, dict):
                if ("$in" in v and doc.get(k) not in v["$in"]) or ("$exists" in v and (k in doc) != bool(v["$exists"])) or ("$ne" in v and doc.get(k) == v["$ne"]):
                    return False
            elif k != "$or" and doc.get(k) != v:
                return False
        return True

    def create_index(self, *args, **kwargs):
        return "idx"

    def count_documents(self, query=None):
        return sum(1 for d in self.docs if self._matches(d, query))

    def find_one(self, query=None, projection=None):
        return next((dict(d) for d in self.docs if self._matches(d, query)), None)

    def find(self, query=None, projection=None):
        return _MemCursor([dict(d) for d in self.docs if self._matches(d, query)])

    def aggregate(self, pipeline):
        return []

    def insert_one(self, doc):
        self._seq += 1
        item = dict(doc)
        item.setdefault("_id", f"mem-{self._seq}")
        self.docs.append(item)
        return MagicMock(inserted_id=item["_id"])

    def insert_many(self, docs):
        ids = [self.insert_one(d).inserted_id for d in docs]
        return MagicMock(inserted_ids=ids)

    def update_one(self, query, update, upsert=False):
        for d in self.docs:
            if self._matches(d, query):
                d.update(dict(update.get("$set") or {}))
                return MagicMock(matched_count=1, modified_count=1)
        if upsert:
            self._seq += 1
            item = {**(query or {}), **dict(update.get("$set") or {})}
            item.setdefault("_id", f"mem-{self._seq}")
            self.docs.append(item)
            return MagicMock(matched_count=0, modified_count=0, upserted_id=item["_id"])
        return MagicMock(matched_count=0, modified_count=0)

    def delete_one(self, query):
        for idx, d in enumerate(self.docs):
            if self._matches(d, query):
                self.docs.pop(idx)
                return MagicMock(deleted_count=1)
        return MagicMock(deleted_count=0)

    def delete_many(self, query):
        before = len(self.docs)
        self.docs = [d for d in self.docs if not self._matches(d, query)]
        return MagicMock(deleted_count=before - len(self.docs))


class AdminAcademicPanelTests(TestCase):
    def setUp(self):
        invalidate_cache()
        now = datetime(2026, 11, 20, 9, 0, tzinfo=timezone.utc)
        self.cols = {
            "activity_logs": _MemCol(),
            "system_settings": _MemCol(),
            "notifications": _MemCol(),
            "student_records": _MemCol(),
            "classes": _MemCol(),
            "semesters": _MemCol(),
            "courses": _MemCol(),
            "users": _MemCol([
                {"user_id": "USR-ADM-1", "full_name": "System Admin", "email": "admin@edupredict.edu", "role": "ADMIN", "is_active": True, "created_at": now},
                {"user_id": "USR-1002", "full_name": "Pending User", "email": "pending@edupredict.edu", "role": "ANALYST", "is_active": True, "created_at": now},
            ]),
        }
        for p in (
            patch("core.db.MongoDBClient.get_collection", side_effect=lambda name: self.cols.setdefault(name, _MemCol())),
            patch("core.db.MongoDBClient.check_health", return_value={"connected": True, "error": None}),
            patch("accounts.services.ensure_accounts_indexes_once", return_value=None),
            patch.object(audit_svc, "_AUDIT_SEED_DONE", True),
            patch.object(admin_seed, "_ADMIN_SEED_DONE", True),
        ):
            p.start()
            self.addCleanup(p.stop)

    def _login_admin(self):
        client = Client()
        session = client.session
        session["user"] = {"user_id": "USR-ADM-1", "role": "ADMIN", "email": "admin@edupredict.edu", "full_name": "System Admin"}
        session.save()
        return client

    def test_batch_removed_from_admin_users_and_auth_registration(self):
        client = self._login_admin()
        users_html = client.get(reverse("panels:admin_users")).content.decode("utf-8")
        self.assertNotIn("Batch / Class", users_html)
        self.assertNotIn("defaultBatch", users_html)
        auth_html = Client().get(f"{reverse('accounts:auth_view')}?tab=register").content.decode("utf-8")
        self.assertNotIn('id="reg-batch"', auth_html)
        self.assertNotIn("BATCH / TERM", auth_html)

    def test_users_role_sync_to_teachers_and_students_pages(self):
        client = self._login_admin()
        client.post(reverse("panels:admin_users"), {"action": "create", "full_name": "Prof. Tariq", "email": "tariq@edupredict.edu", "password": "secret123", "role": "TEACHER", "department": "CS"})
        client.post(reverse("panels:admin_users"), {"action": "create", "full_name": "Hina Ali", "email": "hina@edupredict.edu", "password": "secret123", "role": "STUDENT", "department": "CS"})
        teachers_html = client.get(reverse("panels:admin_teachers")).content.decode("utf-8")
        students_html = client.get(reverse("panels:admin_students")).content.decode("utf-8")
        self.assertIn("Prof. Tariq", teachers_html)
        self.assertIn("tariq@edupredict.edu", teachers_html)
        self.assertIn("Hina Ali", students_html)

        client.post(reverse("panels:admin_users"), {"action": "update", "user_id": "USR-1002", "full_name": "Pending User", "email": "pending@edupredict.edu", "role": "TEACHER", "department": "AI"})
        self.assertIn("Pending User", client.get(reverse("panels:admin_teachers")).content.decode("utf-8"))
        client.post(reverse("panels:admin_users"), {"action": "update", "user_id": "USR-1002", "full_name": "Pending User", "email": "pending@edupredict.edu", "role": "STUDENT", "department": "AI"})
        self.assertIn("Pending User", client.get(reverse("panels:admin_students")).content.decode("utf-8"))

    def test_teachers_full_crud(self):
        client = self._login_admin()
        url = reverse("panels:admin_teachers")
        self.assertRedirects(client.post(url, {"action": "create_teacher", "full_name": "Dr. Sana", "email": "sana@edupredict.edu", "password": "pass123", "phone": "03001112233", "department": "Math", "is_active": "true"}), url, fetch_redirect_response=False)
        doc = self.cols["users"].find_one({"email": "sana@edupredict.edu"})
        self.assertIsNotNone(doc)
        self.assertIn("Dr. Sana", client.get(url).content.decode("utf-8"))

        self.assertRedirects(client.post(url, {"action": "edit_teacher", "user_id": doc["user_id"], "full_name": "Dr. Sana Malik", "email": "sana@edupredict.edu", "phone": "03009998877", "department": "Physics", "is_active": "false"}), url, fetch_redirect_response=False)
        updated = self.cols["users"].find_one({"user_id": doc["user_id"]})
        self.assertEqual(updated["full_name"], "Dr. Sana Malik")
        self.assertFalse(updated["is_active"])

        self.assertRedirects(client.post(url, {"action": "delete_teacher", "user_id": doc["user_id"]}), url, fetch_redirect_response=False)
        self.assertIsNone(self.cols["users"].find_one({"user_id": doc["user_id"]}))

    def test_classes_auto_semesters_and_semester_full_crud(self):
        client = self._login_admin()
        url = reverse("panels:admin_classes")
        self.assertRedirects(client.post(url, {"action": "create_class", "class_code": "BSCS-2026", "class_name": "BS Computer Science", "total_semesters": "4", "status": "ACTIVE"}), url, fetch_redirect_response=False)
        cls = self.cols["classes"].find_one({"class_code": "BSCS-2026"})
        self.assertIsNotNone(cls)
        self.assertEqual(self.cols["semesters"].count_documents({"class_id": cls["class_id"]}), 4)
        self.assertIn("BS Computer Science", client.get(url).content.decode("utf-8"))

        self.assertRedirects(client.post(url, {"action": "edit_class", "class_id": cls["class_id"], "class_code": "BSCS-26", "class_name": "BS CS Updated", "total_semesters": "4", "status": "INACTIVE"}), url, fetch_redirect_response=False)
        self.assertEqual(self.cols["classes"].find_one({"class_id": cls["class_id"]})["class_name"], "BS CS Updated")

        self.assertRedirects(client.post(url, {"action": "create_semester", "class_id": cls["class_id"], "semester_number": "5", "semester_name": "Summer Bridge", "status": "ACTIVE"}), url, fetch_redirect_response=False)
        sem5 = self.cols["semesters"].find_one({"class_id": cls["class_id"], "semester_number": 5})
        self.assertIsNotNone(sem5)
        self.assertIn("Summer Bridge", client.get(url).content.decode("utf-8"))

        self.assertRedirects(client.post(url, {"action": "edit_semester", "semester_id": sem5["semester_id"], "class_id": cls["class_id"], "semester_number": "5", "semester_name": "Fall Bridge", "status": "INACTIVE"}), url, fetch_redirect_response=False)
        self.assertEqual(self.cols["semesters"].find_one({"semester_id": sem5["semester_id"]})["semester_name"], "Fall Bridge")

        self.assertRedirects(client.post(url, {"action": "delete_semester", "semester_id": sem5["semester_id"]}), url, fetch_redirect_response=False)
        self.assertIsNone(self.cols["semesters"].find_one({"semester_id": sem5["semester_id"]}))

        self.assertRedirects(client.post(url, {"action": "delete_class", "class_id": cls["class_id"]}), url, fetch_redirect_response=False)
        self.assertIsNone(self.cols["classes"].find_one({"class_id": cls["class_id"]}))
        self.assertEqual(self.cols["semesters"].count_documents({"class_id": cls["class_id"]}), 0)

    def test_students_and_courses_full_crud(self):
        client = self._login_admin()
        client.post(reverse("panels:admin_classes"), {"action": "create_class", "class_code": "BSSE", "class_name": "BS Software Eng", "total_semesters": "2", "status": "ACTIVE"})
        cls = self.cols["classes"].find_one({"class_code": "BSSE"})
        sem = self.cols["semesters"].find_one({"class_id": cls["class_id"], "semester_number": 1})
        client.post(reverse("panels:admin_teachers"), {"action": "create_teacher", "full_name": "Mr. Kamran", "email": "kamran@edupredict.edu", "password": "pass123", "is_active": "true"})
        teacher = self.cols["users"].find_one({"email": "kamran@edupredict.edu"})

        s_url = reverse("panels:admin_students")
        self.assertRedirects(client.post(s_url, {"action": "create_student", "full_name": "Bilal Raza", "email": "bilal@edupredict.edu", "password": "pass123", "class_id": cls["class_id"], "semester_id": sem["semester_id"], "phone": "03110001122"}), s_url, fetch_redirect_response=False)
        stu = self.cols["users"].find_one({"email": "bilal@edupredict.edu"})
        self.assertIsNotNone(stu)
        self.assertIn("Bilal Raza", client.get(s_url).content.decode("utf-8"))

        self.assertRedirects(client.post(s_url, {"action": "edit_student", "user_id": stu["user_id"], "full_name": "Bilal Raza Jr", "email": "bilal@edupredict.edu", "class_id": cls["class_id"], "semester_id": sem["semester_id"], "phone": "03119990000"}), s_url, fetch_redirect_response=False)
        self.assertEqual(self.cols["users"].find_one({"user_id": stu["user_id"]})["full_name"], "Bilal Raza Jr")
        self.assertRedirects(client.post(s_url, {"action": "delete_student", "user_id": stu["user_id"]}), s_url, fetch_redirect_response=False)
        self.assertIsNone(self.cols["users"].find_one({"user_id": stu["user_id"]}))

        c_url = reverse("panels:admin_courses")
        self.assertRedirects(client.post(c_url, {"action": "create_course", "course_code": "SE-101", "title": "Software Engineering", "class_id": cls["class_id"], "semester_id": sem["semester_id"], "instructor_id": teacher["user_id"], "credits": "3", "status": "ACTIVE"}), c_url, fetch_redirect_response=False)
        courses_html = client.get(c_url).content.decode("utf-8")
        self.assertIn("SE-101", courses_html)
        self.assertIn("BS Software Eng", courses_html)
        self.assertIn("Mr. Kamran", courses_html)

        self.assertRedirects(client.post(c_url, {"action": "edit_course", "original_course_code": "SE-101", "course_code": "SE-102", "title": "Advanced SE", "class_id": cls["class_id"], "semester_id": sem["semester_id"], "instructor_id": teacher["user_id"], "credits": "4", "status": "INACTIVE"}), c_url, fetch_redirect_response=False)
        self.assertEqual(self.cols["courses"].find_one({"course_code": "SE-102"})["title"], "Advanced SE")
        self.assertRedirects(client.post(c_url, {"action": "delete_course", "course_code": "SE-102"}), c_url, fetch_redirect_response=False)
        self.assertIsNone(self.cols["courses"].find_one({"course_code": "SE-102"}))
