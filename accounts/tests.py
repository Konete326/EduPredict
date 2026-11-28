from unittest.mock import MagicMock, patch
from django.test import SimpleTestCase
from django.urls import reverse
from accounts.public_data import get_public_landing_showcase
from accounts.services import get_public_admin_contact, get_public_portal_metrics
from core.db import invalidate_cache


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
