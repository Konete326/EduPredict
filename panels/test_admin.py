import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from django.test import Client, TestCase
from django.urls import reverse
from core.db import _MEMORY_CACHE, invalidate_cache
import panels.admin_audit_services as audit_svc
import panels.admin_seed as admin_seed
from panels.admin_services import (
    build_user_table_data, create_course_record, create_ticket_record,
    delete_user_record, list_users, toggle_user_status, update_user_record,
)


class _MemCursor:
    def __init__(self, docs):
        self._docs = list(docs)

    def sort(self, field, direction):
        self._docs.sort(key=lambda d: str(d.get(field) or ""), reverse=(direction == -1))
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


class _AdminTestBase(TestCase):
    def setUp(self):
        invalidate_cache()
        now = datetime(2026, 11, 18, 9, 0, tzinfo=timezone.utc)
        self.cols = {
            "activity_logs": _MemCol(), "system_settings": _MemCol(), "notifications": _MemCol(),
            "users": _MemCol([{"user_id": "USR-1001", "full_name": "Dr. Ayesha Khan", "role": "TEACHER", "department": "Computer Science", "is_active": True, "created_at": now}]),
            "courses": _MemCol([{"course_code": "CS-101", "title": "Intro to CS", "department": "Computer Science", "instructor": "Dr. Ayesha Khan", "status": "ACTIVE", "created_at": now}]),
            "support_tickets": _MemCol([{"ticket_id": "TKT-1001", "user_name": "Zainab Raza", "role": "STUDENT", "subject": "Attendance check", "status": "OPEN", "created_at": now}]),
            "datasets_log": _MemCol([{"filename": "fall_2026.csv", "uploaded_by": "Saad Farooq", "rows_processed": 40, "missing_values_fixed": 2, "status": "COMPLETED", "uploaded_at": now}]),
        }
        for p in (
            patch("core.db.MongoDBClient.get_collection", side_effect=lambda name: self.cols.setdefault(name, _MemCol())),
            patch("core.db.MongoDBClient.check_health", return_value={"connected": True, "error": None}),
            patch.object(audit_svc, "_AUDIT_SEED_DONE", False),
            patch.object(admin_seed, "_ADMIN_SEED_DONE", True),
        ):
            p.start()
            self.addCleanup(p.stop)

    def _login_as(self, role, user_id="USR-ADM-1", student_id=None):
        client = Client()
        session = client.session
        user = {"user_id": user_id, "role": role, "email": f"{role.lower()}@edupredict.edu", "full_name": f"Test {role.title()}"}
        if student_id:
            user["student_id"] = student_id
        session["user"] = user
        session.save()
        return client


class AdminLogsAndSettingsTests(_AdminTestBase):
    def test_admin_logs_get_filters_csv_and_sidebar_links(self):
        client = self._login_as("ADMIN")
        resp = client.get(reverse("panels:admin_logs"))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode("utf-8")
        self.assertIn('id="admin-logs-table"', html)
        for text in ("Total Events", "Admin Actions", "Data & ML Events", "Security Events", "?category=USERS", "?category=COURSES", "?category=TICKETS", "?category=DATA", "?category=SYSTEM", reverse("panels:admin_logs"), reverse("panels:admin_settings")):
            self.assertIn(text, html)
        self.assertNotIn('data-coming-title="Activity Logs"', html)
        self.assertNotIn('data-coming-title="Settings"', html)
        self.assertIn('id="mobile-sidebar-close"', html)
        self.assertIn('id="mobile-sidebar-close" type="button" title="Hide menu" class="lg:hidden', html)
        data_resp = client.get(reverse("panels:admin_logs"), {"category": "DATA"})
        self.assertEqual(data_resp.status_code, 200)
        self.assertIn("fall_2026.csv", data_resp.content.decode("utf-8"))
        csv_resp = client.get(reverse("panels:admin_logs"), {"export": "csv"})
        self.assertEqual(csv_resp.status_code, 200)
        self.assertTrue(csv_resp["Content-Type"].startswith("text/csv"))
        self.assertIn("Log ID,Actor,Role,Category,Action,Activity Summary", csv_resp.content.decode("utf-8"))

    def test_admin_logs_post_note_records_and_invalidates_cache(self):
        client = self._login_as("ADMIN")
        client.get(reverse("panels:admin_logs"))
        self.assertIn("admin:logs:ALL", _MEMORY_CACHE)
        post_resp = client.post(reverse("panels:admin_logs"), {"action": "log_note", "filter_category": "ALL", "category": "SYSTEM", "severity": "WARNING", "summary": "Nightly audit note recorded"})
        self.assertRedirects(post_resp, reverse("panels:admin_logs"), fetch_redirect_response=False)
        self.assertNotIn("admin:logs:ALL", _MEMORY_CACHE)
        self.assertTrue(any(d.get("summary") == "Nightly audit note recorded" and d.get("source") == "MANUAL" for d in self.cols["activity_logs"].docs))
        self.assertIn("Nightly audit note recorded", client.get(reverse("panels:admin_logs")).content.decode("utf-8"))
        clear_resp = client.post(reverse("panels:admin_logs"), {"action": "clear_custom"})
        self.assertRedirects(clear_resp, reverse("panels:admin_logs"), fetch_redirect_response=False)
        self.assertNotIn("Nightly audit note recorded", client.get(reverse("panels:admin_logs")).content.decode("utf-8"))
        created_course, err = create_course_record("AI-900", "Deep Learning", "AI", "2026-A", "Dr. Bilal", 3, 50, actor_name="Dr. Admin Lead")
        self.assertIsNone(err)
        self.assertIsNotNone(created_course)
        self.assertTrue(any(d.get("action") == "CREATE_COURSE" and d.get("actor") == "Dr. Admin Lead" and "AI-900" in d.get("summary", "") for d in self.cols["activity_logs"].docs))
        created_ticket, t_err = create_ticket_record("USR-1003", "Zainab Raza", "STUDENT", "Lab issue", "Cannot open lab")
        self.assertIsNone(t_err)
        self.assertIsNotNone(created_ticket)
        self.assertTrue(any(d.get("action") == "CREATE_TICKET" and d.get("actor") == "Zainab Raza" for d in self.cols["activity_logs"].docs))

    def test_admin_settings_get_update_and_reset_defaults(self):
        client = self._login_as("ADMIN")
        get_resp = client.get(reverse("panels:admin_settings"))
        self.assertEqual(get_resp.status_code, 200)
        html = get_resp.content.decode("utf-8")
        for marker in ('id="admin-settings-table"', 'name="institution_name"', 'value="save_settings"'):
            self.assertIn(marker, html)
        save_resp = client.post(reverse("panels:admin_settings"), {"action": "save_settings", "institution_name": "EduPredict Flagship", "current_term": "Spring 2027", "default_batch": "2027-A", "passing_gpa": "2.5", "min_attendance_pct": "80", "high_risk_threshold": "75", "medium_risk_threshold": "40", "anomaly_drop_pct": "20", "auto_student_alerts": "on"})
        self.assertRedirects(save_resp, reverse("panels:admin_settings"), fetch_redirect_response=False)
        updated_html = client.get(reverse("panels:admin_settings")).content.decode("utf-8")
        for expected in ("EduPredict Flagship", "Spring 2027", "80%", "75%", "Custom"):
            self.assertIn(expected, updated_html)
        reset_resp = client.post(reverse("panels:admin_settings"), {"action": "reset_defaults"})
        self.assertRedirects(reset_resp, reverse("panels:admin_settings"), fetch_redirect_response=False)
        reset_html = client.get(reverse("panels:admin_settings")).content.decode("utf-8")
        for expected in ("EduPredict Academic Portal", "Fall 2026", "75%", "70%"):
            self.assertIn(expected, reset_html)

    def test_non_admin_roles_redirected_from_logs_and_settings(self):
        anon = Client()
        for route_name in ("panels:admin_logs", "panels:admin_settings"):
            self.assertEqual(anon.get(reverse(route_name)).status_code, 302)
        for role, expected_dash in (("STUDENT", "panels:student_dashboard"), ("TEACHER", "panels:teacher_dashboard"), ("ANALYST", "panels:analyst_dashboard")):
            client = self._login_as(role)
            for route_name in ("panels:admin_logs", "panels:admin_settings"):
                self.assertRedirects(client.get(reverse(route_name)), reverse(expected_dash), fetch_redirect_response=False)


class AdminCrudAndGuardsTests(_AdminTestBase):
    def test_admin_self_action_guards_and_ui_row_protection(self):
        self.cols["users"].insert_one({
            "user_id": "USR-ADM-1", "full_name": "Root Admin", "email": "admin@edupredict.edu",
            "role": "ADMIN", "department": "Admin", "batch": "ALL", "is_active": True,
        })
        del_by_id_ok, del_by_id_err = delete_user_record("USR-ADM-1", actor_user_id="USR-ADM-1")
        del_by_email_ok, del_by_email_err = delete_user_record("USR-ADM-1", actor_email="admin@edupredict.edu")
        toggle_state, toggle_err = toggle_user_status("USR-ADM-1", actor_user_id="USR-ADM-1")
        upd_ok, upd_err = update_user_record("USR-ADM-1", "Root Admin", "admin@edupredict.edu", "TEACHER", "Admin", "ALL", actor_user_id="USR-ADM-1")
        self.assertFalse(del_by_id_ok)
        self.assertIn("delete your own", del_by_id_err.lower())
        self.assertFalse(del_by_email_ok)
        self.assertIn("delete your own", del_by_email_err.lower())
        self.assertIsNone(toggle_state)
        self.assertIn("deactivate your own", toggle_err.lower())
        self.assertFalse(upd_ok)
        self.assertIn("change your own", upd_err.lower())
        users, _ = list_users("ALL")
        _, rows = build_user_table_data(users, "ALL", "USR-ADM-1", actor_email="admin@edupredict.edu")
        actions_by_uid = {row[0]: [a["label"] for a in row[6]["actions"]] for row in rows}
        self.assertEqual(actions_by_uid["USR-ADM-1"], ["Edit"])
        self.assertEqual(actions_by_uid["USR-1001"], ["Edit", "Deactivate", "Delete"])

    def test_admin_support_ticket_boundary_and_backup_exports(self):
        admin_client = self._login_as("ADMIN")
        initial_count = len(self.cols["support_tickets"].docs)
        admin_resp = admin_client.post(reverse("panels:submit_support_ticket"), {"subject": "Admin self", "message": "Ignored"})
        self.assertRedirects(admin_resp, reverse("panels:admin_tickets"), fetch_redirect_response=False)
        self.assertEqual(len(self.cols["support_tickets"].docs), initial_count)
        student_client = self._login_as("STUDENT", user_id="USR-1003")
        student_resp = student_client.post(reverse("panels:submit_support_ticket"), {"subject": "Portal help", "message": "Need GPA check"})
        self.assertRedirects(student_resp, reverse("panels:student_dashboard"), fetch_redirect_response=False)
        self.assertEqual(len(self.cols["support_tickets"].docs), initial_count + 1)
        self.assertTrue(any(d.get("user_id") == "USR-1003" and d.get("subject") == "Portal help" for d in self.cols["support_tickets"].docs))
        json_resp = admin_client.get(reverse("panels:admin_backup_export"), {"format": "json"})
        self.assertEqual(json_resp.status_code, 200)
        self.assertTrue(json_resp["Content-Type"].startswith("application/json"))
        self.assertIn("collections", json.loads(json_resp.content.decode("utf-8")))
        csv_resp = admin_client.get(reverse("panels:admin_backup_export"), {"format": "csv"})
        self.assertEqual(csv_resp.status_code, 200)
        self.assertTrue(csv_resp["Content-Type"].startswith("text/csv"))
        self.assertIn("Portal help", csv_resp.content.decode("utf-8"))

    def test_admin_dashboard_and_crud_views_against_memcol(self):
        admin_client = self._login_as("ADMIN")
        for route_name, marker in (
            ("panels:admin_dashboard", "System Overview"),
            ("panels:admin_users", "admin-users-table"),
            ("panels:admin_courses", "admin-courses-table"),
            ("panels:admin_tickets", "admin-tickets-table"),
        ):
            resp = admin_client.get(reverse(route_name))
            self.assertEqual(resp.status_code, 200)
            self.assertIn(marker, resp.content.decode("utf-8"))
        self.assertRedirects(admin_client.post(reverse("panels:admin_courses"), {"action": "create", "filter_dept": "ALL", "course_code": "CS-305", "title": "Cloud Systems", "department": "Computer Science", "batch": "2026-A", "instructor": "Dr. Ayesha Khan", "credits": "3", "capacity": "50"}), reverse("panels:admin_courses"), fetch_redirect_response=False)
        self.assertIsNotNone(self.cols["courses"].find_one({"course_code": "CS-305"}))
        self.assertRedirects(admin_client.post(reverse("panels:admin_courses"), {"action": "delete", "course_code": "CS-305"}), reverse("panels:admin_courses"), fetch_redirect_response=False)
        self.assertIsNone(self.cols["courses"].find_one({"course_code": "CS-305"}))
        self.assertRedirects(admin_client.post(reverse("panels:admin_tickets"), {"action": "toggle_status", "ticket_id": "TKT-1001"}), reverse("panels:admin_tickets"), fetch_redirect_response=False)
        self.assertEqual(self.cols["support_tickets"].find_one({"ticket_id": "TKT-1001"})["status"], "RESOLVED")
        self.assertRedirects(admin_client.post(reverse("panels:admin_tickets"), {"action": "delete", "ticket_id": "TKT-1001"}), reverse("panels:admin_tickets"), fetch_redirect_response=False)
        self.assertIsNone(self.cols["support_tickets"].find_one({"ticket_id": "TKT-1001"}))
        self.assertRedirects(admin_client.post(reverse("panels:admin_users"), {"action": "toggle", "user_id": "USR-1001"}), reverse("panels:admin_users"), fetch_redirect_response=False)
        self.assertFalse(self.cols["users"].find_one({"user_id": "USR-1001"})["is_active"])
        self.assertRedirects(admin_client.post(reverse("panels:admin_users"), {"action": "delete", "user_id": "USR-1001"}), reverse("panels:admin_users"), fetch_redirect_response=False)
        self.assertIsNone(self.cols["users"].find_one({"user_id": "USR-1001"}))
        self.assertEqual(self.cols["users"].delete_one({"user_id": "MISSING"}).deleted_count, 0)

    @patch("panels.views_admin.mark_notifications_read", return_value=3)
    def test_mark_notifications_read_view_unpacks_payload_and_handles_rbac(self, mock_mark):
        client = self._login_as("STUDENT", user_id="USR-STU-1", student_id="STD-999")
        get_resp = client.get(reverse("panels:mark_notifications_read"))
        self.assertRedirects(get_resp, reverse("panels:student_dashboard"), fetch_redirect_response=False)
        post_resp = client.post(reverse("panels:mark_notifications_read"))
        self.assertEqual(post_resp.status_code, 200)
        data = json.loads(post_resp.content.decode("utf-8"))
        self.assertTrue(data["ok"])
        self.assertEqual(data["updated"], 3)
        mock_mark.assert_called_once_with({"user_id": "USR-STU-1", "student_id": "STD-999", "role": "STUDENT"})
