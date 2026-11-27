import json
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from core.cloudinary_services import destroy_cloudinary_asset, extract_cloudinary_public_id
from core.db import invalidate_cache
from core.theme_services import remove_user_avatar, save_user_avatar
import panels.admin_audit_services as audit_svc
import panels.admin_seed as admin_seed


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
                for k in (update.get("$unset") or {}):
                    d.pop(k, None)
                return MagicMock(matched_count=1, modified_count=1)
        return MagicMock(matched_count=0, modified_count=0)

    def update_many(self, query, update):
        count = 0
        for d in self.docs:
            if self._matches(d, query):
                d.update(dict(update.get("$set") or {}))
                count += 1
        return MagicMock(modified_count=count)


class NotificationAndReplyTests(TestCase):
    def setUp(self):
        invalidate_cache()
        now = datetime(2026, 11, 20, 9, 0, tzinfo=timezone.utc)
        self.cols = {
            "users": _MemCol([{"user_id": "USR-1003", "full_name": "Zainab Raza", "email": "zainab@edupredict.edu", "role": "STUDENT", "student_id": "STD-2026-001", "is_active": True, "created_at": now}]),
            "support_tickets": _MemCol([{"ticket_id": "TKT-1001", "user_id": "USR-1003", "user_name": "Zainab Raza", "role": "STUDENT", "subject": "Lab marks mismatch", "message": "My lab attendance shows 60% instead of 85%.", "status": "OPEN", "created_at": now}]),
            "notifications": _MemCol([]),
            "activity_logs": _MemCol([]),
            "system_settings": _MemCol([]),
        }
        admin_seed._ADMIN_SEED_DONE = True
        audit_svc._AUDIT_SEED_DONE = True
        self.patchers = [
            patch("core.db.MongoDBClient.get_collection", side_effect=lambda name: self.cols.setdefault(name, _MemCol())),
            patch("core.db.MongoDBClient.check_health", return_value={"connected": True, "error": None}),
            patch("core.context_processors.check_db_health", return_value={"connected": True}),
            patch("core.context_processors.notifications_col", side_effect=lambda: self.cols["notifications"]),
            patch("panels.notification_services.notifications_col", side_effect=lambda: self.cols["notifications"]),
            patch("panels.notification_services.support_tickets_col", side_effect=lambda: self.cols["support_tickets"]),
            patch("panels.admin_services.support_tickets_col", side_effect=lambda: self.cols["support_tickets"]),
            patch("panels.admin_services.notifications_col", side_effect=lambda: self.cols["notifications"]),
            patch("panels.admin_audit_services.activity_logs_col", side_effect=lambda: self.cols["activity_logs"]),
        ]
        for p in self.patchers:
            p.start()
        self.addCleanup(self._stop_patchers)

    def _stop_patchers(self):
        for p in self.patchers:
            p.stop()
        invalidate_cache()

    def _set_session(self, client, role, user_id="USR-0001", full_name="System Admin", student_id=""):
        sess = client.session
        sess["user"] = {"user_id": user_id, "full_name": full_name, "email": f"{role.lower()}@edupredict.edu", "role": role, "student_id": student_id}
        sess.save()

    def test_notifications_feed_requires_auth_and_returns_json(self):
        anon = Client()
        res_anon = anon.get(reverse("panels:notifications_feed"))
        self.assertEqual(res_anon.status_code, 302)
        self.cols["notifications"].insert_one({
            "title": "Reply on TKT-1001",
            "message": "Updated your lab record.",
            "severity": "SUCCESS",
            "category": "FEEDBACK_REPLY",
            "target_user_id": "USR-1003",
            "ticket_id": "TKT-1001",
            "feedback_text": "My lab attendance shows 60% instead of 85%.",
            "reply_text": "Updated your lab record.",
            "is_read": False,
            "created_at": datetime.now(timezone.utc),
        })
        student = Client()
        self._set_session(student, "STUDENT", user_id="USR-1003", full_name="Zainab Raza", student_id="STD-2026-001")
        res = student.get(reverse("panels:notifications_feed"))
        self.assertEqual(res.status_code, 200)
        payload = json.loads(res.content)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["unread_count"], 1)
        self.assertEqual(payload["notifications"][0]["feedback_text"], "My lab attendance shows 60% instead of 85%.")
        self.assertEqual(payload["notifications"][0]["reply_text"], "Updated your lab record.")

    def test_admin_reply_ticket_and_delete_reply_crud(self):
        admin_client = Client()
        self._set_session(admin_client, "ADMIN")
        url = reverse("panels:admin_tickets")
        res_reply = admin_client.post(url, {"action": "reply_ticket", "ticket_id": "TKT-1001", "reply_text": "Lab attendance synced to 85%.", "resolve_ticket": "true"})
        self.assertEqual(res_reply.status_code, 302)
        ticket = self.cols["support_tickets"].find_one({"ticket_id": "TKT-1001"})
        self.assertEqual(ticket["admin_reply"], "Lab attendance synced to 85%.")
        self.assertEqual(ticket["status"], "RESOLVED")
        notif = self.cols["notifications"].find_one({"target_user_id": "USR-1003", "category": "FEEDBACK_REPLY"})
        self.assertIsNotNone(notif)
        self.assertEqual(notif["feedback_text"], "My lab attendance shows 60% instead of 85%.")
        self.assertEqual(notif["reply_text"], "Lab attendance synced to 85%.")
        res_del = admin_client.post(url, {"action": "delete_reply", "ticket_id": "TKT-1001"})
        self.assertEqual(res_del.status_code, 302)
        ticket_after = self.cols["support_tickets"].find_one({"ticket_id": "TKT-1001"})
        self.assertNotIn("admin_reply", ticket_after)

    def test_submit_support_ticket_creates_admin_notification(self):
        student = Client()
        self._set_session(student, "STUDENT", user_id="USR-1003", full_name="Zainab Raza", student_id="STD-2026-001")
        res = student.post(reverse("panels:submit_support_ticket"), {"subject": "Portal login issue", "message": "Password reset link expired."})
        self.assertEqual(res.status_code, 302)
        admin_notif = self.cols["notifications"].find_one({"target_role": "ADMIN", "category": "TICKET"})
        self.assertIsNotNone(admin_notif)
        self.assertEqual(admin_notif["feedback_text"], "Password reset link expired.")

    def test_avatar_save_and_remove_destroy_previous_cloudinary_asset(self):
        old_url = "https://res.cloudinary.com/demo/image/upload/v123/edupredict/avatars/user_USR-1003_old.jpg"
        new_url = "https://res.cloudinary.com/demo/image/upload/v456/edupredict/avatars/user_USR-1003_new.jpg"
        self.assertEqual(extract_cloudinary_public_id(old_url), "edupredict/avatars/user_USR-1003_old")
        with patch("core.cloudinary_services.is_cloudinary_configured", return_value=True), patch("core.cloudinary_services._configure_cloudinary"), patch("core.cloudinary_services.cloudinary.uploader.destroy", return_value={"result": "ok"}) as mock_cloud_destroy:
            self.assertTrue(destroy_cloudinary_asset(old_url))
            mock_cloud_destroy.assert_called_once_with("edupredict/avatars/user_USR-1003_old", invalidate=True)
        client = Client()
        sess = client.session
        sess["user"] = {"user_id": "USR-1003", "full_name": "Zainab Raza", "role": "STUDENT", "avatar_url": old_url}
        sess.save()
        req = SimpleNamespace(session=sess)
        with patch("core.theme_services.upload_user_avatar", return_value=(new_url, None)), patch("core.theme_services.destroy_cloudinary_asset", return_value=True) as mock_destroy:
            saved_url, err = save_user_avatar(req, SimpleUploadedFile("avatar.png", b"pngbytes", content_type="image/png"))
            self.assertIsNone(err)
            self.assertEqual(saved_url, new_url)
            mock_destroy.assert_called_once_with(old_url, default_public_id="edupredict/avatars/user_USR-1003")
            ok, rm_err = remove_user_avatar(req)
            self.assertTrue(ok)
            self.assertIsNone(rm_err)
            mock_destroy.assert_called_with(new_url, default_public_id="edupredict/avatars/user_USR-1003")
            self.assertEqual(req.session["user"]["avatar_url"], "")

    def test_support_ticket_attachments_capped_and_admin_drawer_lightbox_rendered(self):
        student = Client()
        self._set_session(student, "STUDENT", user_id="USR-1003", full_name="Zainab Raza", student_id="STD-2026-001")
        urls = [
            "data:image/png;base64,iVBORw0KGgo=",
            "https://res.cloudinary.com/demo/image/upload/v1/shot2.png",
            "https://res.cloudinary.com/demo/image/upload/v1/shot3.png",
            "https://res.cloudinary.com/demo/image/upload/v1/shot4.png",
        ]
        res = student.post(reverse("panels:submit_support_ticket"), {"subject": "Chart screenshot bug", "message": "Overlap on small screen.", "attachment_urls": urls})
        self.assertEqual(res.status_code, 302)
        saved = self.cols["support_tickets"].find_one({"subject": "Chart screenshot bug"})
        self.assertIsNotNone(saved)
        self.assertEqual(saved["attachments"], urls[:3])
        admin = Client()
        self._set_session(admin, "ADMIN")
        admin_res = admin.get(reverse("panels:admin_tickets"))
        self.assertEqual(admin_res.status_code, 200)
        html = admin_res.content.decode("utf-8")
        expected_attr = f'data-attachments="{"|".join(urls[:3])}"'
        for marker in (expected_attr, 'id="ticket-detail-drawer"', 'id="image-lightbox-modal"', 'id="image-cropper-modal"', 'id="support-ticket-modal"', "window.openViewDetailsModal("):
            self.assertIn(marker, html)

    def test_profile_and_student_notifications_render_cropper_and_hide_non_admin_theme_studio(self):
        student = Client()
        self._set_session(student, "STUDENT", user_id="USR-1003", full_name="Zainab Raza", student_id="STD-2026-001")
        prof_res = student.get(reverse("panels:user_profile"))
        self.assertEqual(prof_res.status_code, 200)
        prof_html = prof_res.content.decode("utf-8")
        for marker in ('id="image-cropper-modal"', 'id="support-ticket-modal"', "openSupportTicketModal()", "openThemeStudioModal()", 'id="theme-studio-modal"'):
            self.assertIn(marker, prof_html)
        self.assertNotIn("/admin-panel/settings/", prof_html)
        notif_res = student.get(reverse("panels:notifications_history"))
        self.assertEqual(notif_res.status_code, 200)
        notif_html = notif_res.content.decode("utf-8")
        for marker in ('id="image-cropper-modal"', 'id="support-ticket-modal"', "openSupportTicketModal()"):
            self.assertIn(marker, notif_html)
        admin = Client()
        self._set_session(admin, "ADMIN")
        admin_prof = admin.get(reverse("panels:user_profile"))
        self.assertEqual(admin_prof.status_code, 200)
        self.assertIn("openThemeStudioModal()", admin_prof.content.decode("utf-8"))
