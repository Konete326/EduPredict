from unittest.mock import MagicMock, patch
from django.contrib.messages import get_messages
from django.test import SimpleTestCase
from django.urls import reverse
from accounts.public_data import get_public_landing_showcase
from accounts.services import get_public_admin_contact, get_public_portal_metrics
from core.db import invalidate_cache
from panels.admin_services import build_ticket_table_data, list_tickets


class _FakeCursor:
    def __init__(self, docs):
        self._docs = list(docs)

    def sort(self, *args, **kwargs):
        return self

    def limit(self, n):
        return _FakeCursor(self._docs[:n])

    def __iter__(self):
        return iter(self._docs)


class _FakeCol:
    def __init__(self, docs=None, counts=None):
        self._docs = list(docs or [])
        self._counts = dict(counts or {})
        self.inserted = []

    def count_documents(self, query=None):
        q = query or {}
        if not q:
            return self._counts.get("__all__", len(self._docs))
        key = tuple(sorted(q.items()))
        if key in self._counts:
            return self._counts[key]
        return sum(1 for d in self._docs if all(d.get(k) == v for k, v in q.items()))

    def find(self, query=None, proj=None):
        return _FakeCursor(self._docs)

    def find_one(self, query=None, proj=None):
        q = query or {}
        for d in self._docs:
            if all(d.get(k) == v for k, v in q.items()):
                return dict(d)
        return None

    def insert_one(self, doc):
        copy = dict(doc)
        self.inserted.append(copy)
        self._docs.append(copy)
        return MagicMock(inserted_id=len(self._docs))


class PublicRealDataTests(SimpleTestCase):
    def setUp(self):
        invalidate_cache("public:")

    def tearDown(self):
        invalidate_cache("public:")

    def test_public_portal_metrics_counts_real_student_users_not_records(self):
        fake_users = _FakeCol(
            counts={
                "__all__": 14,
                (("role", "STUDENT"),): 9,
                (("role", "TEACHER"),): 3,
            }
        )
        fake_records = _FakeCol(counts={"__all__": 703})
        fake_courses = _FakeCol(counts={"__all__": 6})
        fake_preds = _FakeCol(counts={"__all__": 42})

        with patch("accounts.services.resolve_portal_branding", return_value=("EduPredict Portal", "Spring 2026")), \
             patch("accounts.services.users_col", return_value=fake_users), \
             patch("accounts.services.student_records_col", return_value=fake_records), \
             patch("accounts.services.courses_col", return_value=fake_courses), \
             patch("accounts.services.predictions_col", return_value=fake_preds):
            metrics = get_public_portal_metrics()

        self.assertEqual(metrics["students_count"], 9)
        self.assertEqual(metrics["teachers_count"], 3)
        self.assertEqual(metrics["courses_count"], 6)
        self.assertEqual(metrics["predictions_count"], 42)
        self.assertEqual(metrics["records_count"], 703)
        self.assertEqual(metrics["users_count"], 14)

    def test_public_portal_metrics_returns_zero_on_empty_or_error(self):
        broken_col = MagicMock(side_effect=RuntimeError("db offline"))
        with patch("accounts.services.resolve_portal_branding", return_value=("EduPredict Portal", "Fall 2026")), \
             patch("accounts.services.users_col", broken_col), \
             patch("accounts.services.student_records_col", broken_col), \
             patch("accounts.services.courses_col", broken_col), \
             patch("accounts.services.predictions_col", broken_col):
            metrics = get_public_portal_metrics()

        self.assertEqual(metrics["students_count"], 0)
        self.assertEqual(metrics["teachers_count"], 0)
        self.assertEqual(metrics["courses_count"], 0)
        self.assertEqual(metrics["predictions_count"], 0)

    def test_public_admin_contact_uses_real_db_admin_and_empty_when_missing(self):
        real_users = _FakeCol(
            docs=[{"role": "ADMIN", "is_active": True, "full_name": "Dr. Tariq", "email": "tariq@campus.edu", "department": "Academics", "phone": "+92-300-1234567"}]
        )
        with patch("accounts.services.resolve_portal_branding", return_value=("Campus Portal", "Spring 2026")), \
             patch("accounts.services.users_col", return_value=real_users):
            contact = get_public_admin_contact()

        self.assertEqual(contact["full_name"], "Dr. Tariq")
        self.assertEqual(contact["name"], "Dr. Tariq")
        self.assertEqual(contact["email"], "tariq@campus.edu")
        self.assertEqual(contact["phone"], "+92-300-1234567")

        invalidate_cache("public:")
        with patch("accounts.services.resolve_portal_branding", return_value=("Campus Portal", "Spring 2026")), \
             patch("accounts.services.users_col", return_value=_FakeCol()):
            empty_contact = get_public_admin_contact()

        self.assertEqual(empty_contact["full_name"], "")
        self.assertEqual(empty_contact["email"], "")

    def test_public_landing_showcase_has_no_dummy_fallbacks_when_empty(self):
        empty_col = _FakeCol()
        with patch("accounts.public_data.resolve_portal_branding", return_value=("EduPredict Portal", "Spring 2026")), \
             patch("accounts.public_data.courses_col", return_value=empty_col), \
             patch("accounts.public_data.predictions_col", return_value=empty_col), \
             patch("accounts.public_data.student_records_col", return_value=empty_col), \
             patch("accounts.public_data.users_col", return_value=empty_col), \
             patch("accounts.public_data.support_tickets_col", return_value=empty_col):
            showcase = get_public_landing_showcase()

        self.assertEqual(showcase["credentials"], [])
        self.assertEqual(showcase["testimonials"], [])
        wt = showcase["walkthrough"]
        self.assertEqual(wt["student_id"], "")
        self.assertEqual(wt["course_label"], "")
        self.assertEqual(wt["marks"], 0)
        self.assertEqual(wt["attendance"], 0)
        self.assertEqual(wt["gpa"], "0.00")
        self.assertEqual(wt["risk"], "")

    def test_public_landing_showcase_does_not_inject_fake_defaults_for_sparse_record(self):
        sparse_records = _FakeCol(docs=[{"student_id": "STD-9001", "student_name": "Nadia"}])
        empty_col = _FakeCol()
        with patch("accounts.public_data.resolve_portal_branding", return_value=("EduPredict Portal", "Spring 2026")), \
             patch("accounts.public_data.courses_col", return_value=empty_col), \
             patch("accounts.public_data.predictions_col", return_value=empty_col), \
             patch("accounts.public_data.student_records_col", return_value=sparse_records), \
             patch("accounts.public_data.users_col", return_value=empty_col), \
             patch("accounts.public_data.support_tickets_col", return_value=empty_col):
            showcase = get_public_landing_showcase()

        self.assertEqual(len(showcase["credentials"]), 1)
        card = showcase["credentials"][0]
        self.assertEqual(card["gpa"], "0.00")
        self.assertEqual(card["marks"], 0)
        self.assertEqual(card["attendance"], 0)
        self.assertEqual(card["course_code"], "")

    def test_public_pages_render_real_metrics_and_admin_contact(self):
        sample_metrics = {
            "institution_name": "EduPredict",
            "current_term": "Spring 2026",
            "users_count": 20,
            "students_count": 12,
            "teachers_count": 4,
            "courses_count": 5,
            "records_count": 703,
            "predictions_count": 18,
        }
        sample_contact = {
            "institution_name": "EduPredict",
            "current_term": "Spring 2026",
            "name": "Hina Raza",
            "full_name": "Hina Raza",
            "email": "hina@edupredict.edu",
            "department": "Administration",
            "phone": "0300-0000000",
        }
        with patch("accounts.views.get_public_portal_metrics", return_value=sample_metrics), \
             patch("accounts.views.get_public_landing_showcase", return_value={"credentials": [], "testimonials": [], "walkthrough": {}}), \
             patch("accounts.views.get_public_admin_contact", return_value=sample_contact):
            home_resp = self.client.get(reverse("root"))
            about_resp = self.client.get(reverse("accounts:about_view"))
            contact_resp = self.client.get(reverse("accounts:contact_view"))

        self.assertEqual(home_resp.status_code, 200)
        self.assertEqual(about_resp.status_code, 200)
        self.assertEqual(contact_resp.status_code, 200)
        about_html = about_resp.content.decode("utf-8")
        self.assertIn(">12<", about_html)
        self.assertNotIn(">703<", about_html)
        contact_html = contact_resp.content.decode("utf-8")
        self.assertIn("Hina Raza", contact_html)
        self.assertIn("hina@edupredict.edu", contact_html)


class PublicContactAndLandingTests(SimpleTestCase):
    def setUp(self):
        invalidate_cache("public:")
        invalidate_cache("admin:")
        invalidate_cache("notifs:")

    def tearDown(self):
        invalidate_cache("public:")
        invalidate_cache("admin:")
        invalidate_cache("notifs:")

    def test_anonymous_contact_post_creates_ticket_and_admin_notification(self):
        fake_tickets = _FakeCol()
        fake_notifs = _FakeCol()
        sample_contact = {
            "institution_name": "EduPredict",
            "current_term": "Spring 2026",
            "name": "Hina Raza",
            "full_name": "Hina Raza",
            "email": "hina@edupredict.edu",
            "department": "Administration",
            "phone": "0300-0000000",
        }
        payload = {
            "name": "Ayesha Khan",
            "email": "ayesha@example.com",
            "subject": "Admission Query",
            "message": "How do teachers join the portal?",
        }
        with patch("accounts.services.support_tickets_col", return_value=fake_tickets), \
             patch("accounts.services.notifications_col", return_value=fake_notifs), \
             patch("accounts.views.get_public_admin_contact", return_value=sample_contact):
            resp = self.client.post(reverse("accounts:contact_view"), payload)

        self.assertRedirects(resp, reverse("accounts:contact_view"), fetch_redirect_response=False)
        self.assertEqual(len(fake_tickets.inserted), 1)
        ticket = fake_tickets.inserted[0]
        self.assertEqual(ticket["source"], "PUBLIC_CONTACT")
        self.assertEqual(ticket["role"], "GUEST")
        self.assertEqual(ticket["user_id"], "GUEST")
        self.assertEqual(ticket["user_name"], "Ayesha Khan")
        self.assertEqual(ticket["email"], "ayesha@example.com")
        self.assertEqual(ticket["subject"], "Admission Query")
        self.assertEqual(ticket["status"], "OPEN")
        self.assertIn("How do teachers join the portal?", ticket["message"])

        self.assertEqual(len(fake_notifs.inserted), 1)
        notif = fake_notifs.inserted[0]
        self.assertEqual(notif["target_role"], "ADMIN")
        self.assertEqual(notif["category"], "TICKET")
        self.assertEqual(notif["ticket_id"], ticket["ticket_id"])
        self.assertFalse(notif["is_read"])

        msgs = [str(m) for m in get_messages(resp.wsgi_request)]
        self.assertTrue(any(ticket["ticket_id"] in m for m in msgs))

    def test_anonymous_contact_post_validates_missing_or_invalid_fields(self):
        fake_tickets = _FakeCol()
        fake_notifs = _FakeCol()
        with patch("accounts.services.support_tickets_col", return_value=fake_tickets), \
             patch("accounts.services.notifications_col", return_value=fake_notifs), \
             patch("accounts.views.get_public_admin_contact", return_value={"institution_name": "EduPredict", "current_term": "Spring 2026", "name": "", "full_name": "", "email": "", "department": "", "phone": ""}):
            resp = self.client.post(
                reverse("accounts:contact_view"),
                {"name": "Ayesha", "email": "not-an-email", "subject": "Help", "message": "Test"},
            )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(fake_tickets.inserted), 0)
        self.assertEqual(len(fake_notifs.inserted), 0)
        self.assertIn("Please enter a valid email address.", resp.content.decode("utf-8"))

    def test_admin_tickets_list_includes_public_contact_guest_tickets(self):
        fake_tickets = _FakeCol(
            docs=[
                {
                    "ticket_id": "TCK-1001",
                    "user_id": "GUEST",
                    "user_name": "Ayesha Khan",
                    "email": "ayesha@example.com",
                    "role": "GUEST",
                    "subject": "Admission Query",
                    "message": "[Public Contact: ayesha@example.com] Need info.",
                    "attachments": [],
                    "status": "OPEN",
                    "source": "PUBLIC_CONTACT",
                }
            ]
        )
        with patch("panels.admin_services.ensure_admin_seed_data"), \
             patch("panels.admin_services.support_tickets_col", return_value=fake_tickets):
            tickets, counts = list_tickets("ALL")

        self.assertEqual(counts["ALL"], 1)
        self.assertEqual(counts["OPEN"], 1)
        self.assertEqual(len(tickets), 1)
        self.assertEqual(tickets[0]["ticket_id"], "TCK-1001")
        self.assertEqual(tickets[0]["role"], "GUEST")
        self.assertEqual(tickets[0]["user_id"], "GUEST")

        headers, rows = build_ticket_table_data(tickets, "ALL")
        self.assertEqual(len(headers), 4)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "Admission Query")
        self.assertEqual(rows[0][1], "Ayesha Khan")

    def test_landing_page_renders_real_metrics_footer_and_unified_cap_logo(self):
        sample_metrics = {
            "institution_name": "EduPredict",
            "current_term": "Spring 2026",
            "users_count": 20,
            "students_count": 12,
            "teachers_count": 4,
            "courses_count": 5,
            "records_count": 0,
            "predictions_count": 18,
        }
        with patch("accounts.views.get_public_portal_metrics", return_value=sample_metrics), \
             patch("accounts.views.get_public_landing_showcase", return_value={"credentials": [], "testimonials": [], "walkthrough": {}}):
            home_resp = self.client.get(reverse("root"))

        self.assertEqual(home_resp.status_code, 200)
        html = home_resp.content.decode("utf-8")
        self.assertIn("12", html)
        self.assertIn("4", html)
        self.assertIn("5", html)
        self.assertIn("18", html)
        self.assertIn("<footer", html)
        self.assertIn("M16 7L3 13l13 6 13-6-13-6z", html)
        self.assertNotIn('<span class="targo-logo-mark" aria-hidden="true"><span></span></span>', html)
        self.assertNotIn("rx='9'", html)
