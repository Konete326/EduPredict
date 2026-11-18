from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from django.test import Client, TestCase
from django.urls import reverse
from core.db import _MEMORY_CACHE, invalidate_cache
import panels.admin_audit_services as audit_svc
from panels.admin_services import create_course_record, create_ticket_record


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
        self.docs = [dict(d) for d in (docs or [])]

    def _matches(self, doc, query):
        for k, v in (query or {}).items():
            if k == "$or" and not any(self._matches(doc, sub) for sub in v):
                return False
            elif isinstance(v, dict):
                if ("$in" in v and doc.get(k) not in v["$in"]) or ("$exists" in v and (k in doc) != bool(v["$exists"])):
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

    def insert_one(self, doc):
        self.docs.append(dict(doc))
        return MagicMock(inserted_id=len(self.docs))

    def update_one(self, query, update, upsert=False):
        for d in self.docs:
            if self._matches(d, query):
                d.update(dict(update.get("$set") or {}))
                return MagicMock(matched_count=1, modified_count=1)
        if upsert:
            self.docs.append({**(query or {}), **dict(update.get("$set") or {})})
        return MagicMock(matched_count=0, modified_count=0)

    def delete_many(self, query):
        before = len(self.docs)
        self.docs = [d for d in self.docs if not self._matches(d, query)]
        return MagicMock(deleted_count=before - len(self.docs))


class AdminLogsAndSettingsTests(TestCase):
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
        ):
            p.start()
            self.addCleanup(p.stop)

    def _login_as(self, role, user_id="USR-ADM-1"):
        client = Client()
        session = client.session
        session["user"] = {"user_id": user_id, "role": role, "email": f"{role.lower()}@edupredict.edu", "full_name": f"Test {role.title()}"}
        session.save()
        return client

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
        self.assertNotIn('id="mobile-sidebar-close" type="button" title="Hide menu" class="lg:hidden', html)
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
