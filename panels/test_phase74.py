import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch
from bson import ObjectId
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.test import Client, TestCase
from django.urls import reverse
import accounts.services as acc_svc
from core.db import invalidate_cache
import panels.admin_audit_services as audit_svc
import panels.admin_seed as admin_seed
from panels.admin_services import build_ticket_table_data
from panels.test_admin import _MemCol


class _Phase74MemCol(_MemCol):
    def _matches(self, doc, query):
        for k, v in (query or {}).items():
            if k == "$or":
                if not any(self._matches(doc, sub) for sub in v):
                    return False
            elif isinstance(v, dict):
                if (
                    ("$in" in v and doc.get(k) not in v["$in"])
                    or ("$nin" in v and doc.get(k) in v["$nin"])
                    or ("$exists" in v and (k in doc) != bool(v["$exists"]))
                    or ("$ne" in v and doc.get(k) == v["$ne"])
                ):
                    return False
            elif doc.get(k) != v:
                return False
        return True

    def update_one(self, query, update, upsert=False):
        for d in self.docs:
            if self._matches(d, query):
                d.update(dict(update.get("$set") or {}))
                for k in (update.get("$unset") or {}):
                    d.pop(k, None)
                return MagicMock(matched_count=1, modified_count=1)
        if upsert:
            self._seq += 1
            item = {**(query or {}), **dict(update.get("$set") or {})}
            item.setdefault("_id", f"mem-{self._seq}")
            self.docs.append(item)
        return MagicMock(matched_count=0, modified_count=0)

    def update_many(self, query, update):
        count = 0
        for d in self.docs:
            if self._matches(d, query):
                d.update(dict(update.get("$set") or {}))
                for k in (update.get("$unset") or {}):
                    d.pop(k, None)
                count += 1
        return MagicMock(matched_count=count, modified_count=count)


class Phase74VerificationTests(TestCase):
    def setUp(self):
        invalidate_cache()
        self.addCleanup(invalidate_cache)
        now = datetime(2026, 11, 22, 10, 0, tzinfo=timezone.utc)
        self.oid_gpa, self.oid_read, self.oid_reply = ObjectId(), ObjectId(), ObjectId()
        self.oid_admin, self.oid_teacher = ObjectId(), ObjectId()
        self.cols = {
            "users": _Phase74MemCol([
                {
                    "user_id": "USR-1000", "full_name": "System Administrator", "email": "admin@gmail.com",
                    "password_hash": make_password("admin123"), "role": "ADMIN", "department": "Administration",
                    "batch": "ALL", "is_active": True, "approval_status": "APPROVED", "created_at": now,
                },
                {
                    "user_id": "USR-1003", "student_id": "STD-2026-01", "full_name": "Zainab Raza",
                    "email": "zainab@edupredict.edu", "password_hash": make_password("student123"),
                    "role": "STUDENT", "department": "Computer Science", "batch": "2026-A",
                    "phone": "+92 300 1112233", "bio": "CS Undergraduate", "is_active": True,
                    "approval_status": "APPROVED", "created_at": now,
                },
                {
                    "user_id": "USR-1002", "full_name": "Prof. Tariq", "email": "tariq@edupredict.edu",
                    "password_hash": make_password("teacher123"), "role": "TEACHER",
                    "department": "Computer Science", "batch": "2026-A", "is_active": True,
                    "approval_status": "APPROVED", "created_at": now,
                },
            ]),
            "student_records": _Phase74MemCol([{
                "student_id": "STD-2026-01", "full_name": "Zainab Raza", "batch": "2026-A", "course_code": "CS-101",
                "attendance_pct": 88.0, "internal_marks": 82.0, "assignment_score": 84.0,
                "lms_hours_weekly": 6.5, "previous_gpa": 3.4, "updated_at": now,
            }]),
            "predictions": _Phase74MemCol([{
                "student_id": "STD-2026-01", "predicted_gpa": 3.48, "dropout_risk_score": 0.14, "risk_level": "LOW",
                "is_anomaly": False, "anomaly_reason": "", "recommendation": "Keep steady attendance.", "generated_at": now,
            }]),
            "support_tickets": _Phase74MemCol([
                {
                    "ticket_id": "TKT-7401", "user_id": "USR-1003", "user_name": "Zainab Raza", "role": "STUDENT",
                    "subject": "Lab attendance discrepancy", "message": "Please verify week 4 lab.",
                    "admin_reply": "Lab marks updated to 88.", "replied_by": "System Admin", "replied_at": now,
                    "status": "RESOLVED", "created_at": now,
                },
                {
                    "ticket_id": "TKT-7402", "user_id": "USR-1003", "user_name": "Zainab Raza", "role": "STUDENT",
                    "subject": "Portal password help", "message": "Reset link question.",
                    "admin_reply": "Use Change Password modal.", "replied_by": "System Admin", "replied_at": now,
                    "status": "RESOLVED", "attachments": ["https://res.cloudinary.com/demo/shot1.png"], "created_at": now,
                },
                {
                    "ticket_id": "TKT-7403", "user_id": "USR-1002", "user_name": "Prof. Tariq", "role": "TEACHER",
                    "subject": "Batch roster export", "message": "Need PDF header check.", "status": "OPEN", "created_at": now,
                },
            ]),
            "notifications": _Phase74MemCol([
                {
                    "_id": self.oid_gpa, "title": "Predicted GPA Alert", "message": "Your GPA forecast updated.",
                    "severity": "INFO", "category": "PREDICTION", "target_role": "STUDENT",
                    "target_user_id": "USR-1003", "is_read": False, "created_at": now,
                },
                {
                    "_id": self.oid_read, "title": "Campus Notice", "message": "Semester calendar published.",
                    "severity": "INFO", "category": "SYSTEM", "target_role": "STUDENT",
                    "target_user_id": "USR-1003", "is_read": True, "created_at": now,
                },
                {
                    "_id": self.oid_reply, "title": "Reply on TKT-7402: Portal password help",
                    "message": "Use Change Password modal.", "severity": "SUCCESS", "category": "FEEDBACK_REPLY",
                    "target_user_id": "USR-1003", "ticket_id": "TKT-7402",
                    "feedback_text": "Reset link question.", "reply_text": "Use Change Password modal.",
                    "is_read": False, "created_at": now,
                },
                {
                    "_id": self.oid_admin, "title": "New Ticket TKT-7403", "message": "Batch roster export",
                    "severity": "INFO", "category": "TICKET", "target_role": "ADMIN",
                    "target_user_id": "", "is_read": False, "created_at": now,
                },
                {
                    "_id": self.oid_teacher, "title": "Attendance Warning", "message": "Student below 75%.",
                    "severity": "WARNING", "category": "ALERT", "target_role": "TEACHER",
                    "target_user_id": "USR-1002", "is_read": False, "created_at": now,
                },
            ]),
            "datasets_log": _Phase74MemCol(), "activity_logs": _Phase74MemCol(),
            "courses": _Phase74MemCol(), "system_settings": _Phase74MemCol(),
        }
        for p in (
            patch("core.db.MongoDBClient.get_collection", side_effect=lambda name: self.cols.setdefault(name, _Phase74MemCol())),
            patch("core.db.MongoDBClient.check_health", return_value={"connected": True, "error": None}),
            patch.object(acc_svc, "_INDEXES_ENSURED", True),
            patch.object(acc_svc, "_DEFAULT_ADMIN_ENSURED", True),
            patch.object(admin_seed, "_ADMIN_SEED_DONE", True),
            patch.object(audit_svc, "_AUDIT_SEED_DONE", True),
        ):
            p.start()
            self.addCleanup(p.stop)

    def _login(self, role, user_id, email, full_name, student_id=""):
        client = Client()
        sess = client.session
        sess["user"] = {"user_id": user_id, "role": role, "email": email, "full_name": full_name, "student_id": student_id}
        sess.save()
        return client

    def test_notifications_history_tabs_mark_actions_feed_and_shell_links(self):
        self.assertEqual(Client().get(reverse("panels:notifications_history")).status_code, 302)
        student = self._login("STUDENT", "USR-1003", "zainab@edupredict.edu", "Zainab Raza", student_id="STD-2026-01")
        res_all = student.get(reverse("panels:notifications_history"))
        self.assertEqual(res_all.status_code, 200)
        html_all = res_all.content.decode("utf-8")
        self.assertEqual(res_all.context["tab_counts"], {"ALL": 4, "UNREAD": 2, "READ": 2, "REPLIES": 2})
        self.assertEqual([it["ticket_id"] for it in res_all.context["notifications_items"]].count("TKT-7402"), 1)
        self.assertIn("Lab marks updated to 88.", html_all)
        for marker in ("Alerts History", 'href="/notifications/"', 'id="view-all-notifications-link"', "data-notif-item", '<a href="/notifications/" data-notif-item'):
            self.assertIn(marker, html_all)

        for tab, exp_len in (("UNREAD", 2), ("READ", 2), ("REPLIES", 2)):
            res_tab = student.get(reverse("panels:notifications_history"), {"tab": tab})
            self.assertEqual(len(res_tab.context["notifications_items"]), exp_len)

        feed_student = student.get(reverse("panels:notifications_feed")).json()
        self.assertTrue(feed_student["ok"])
        targets_by_title = {n["title"]: n["target_url"] for n in feed_student["notifications"]}
        self.assertEqual(targets_by_title["Predicted GPA Alert"], "/student-panel/report/")
        self.assertEqual(targets_by_title["Reply on TKT-7402: Portal password help"], "/student-panel/notifications/")

        admin = self._login("ADMIN", "USR-1000", "admin@gmail.com", "System Administrator")
        self.assertEqual(admin.get(reverse("panels:notifications_feed")).json()["notifications"][0]["target_url"], "/admin-panel/tickets/")
        teacher = self._login("TEACHER", "USR-1002", "tariq@edupredict.edu", "Prof. Tariq")
        self.assertEqual(teacher.get(reverse("panels:notifications_feed")).json()["notifications"][0]["target_url"], "/teacher-panel/alerts/")

        self.assertEqual(student.post(reverse("panels:notifications_history"), {"action": "mark_one", "notification_id": str(self.oid_admin)}).status_code, 302)
        self.assertFalse(self.cols["notifications"].find_one({"_id": self.oid_admin})["is_read"])
        self.assertEqual(student.post(reverse("panels:notifications_history"), {"action": "mark_one", "notification_id": str(self.oid_gpa)}).status_code, 302)
        self.assertTrue(self.cols["notifications"].find_one({"_id": self.oid_gpa})["is_read"])
        self.assertFalse(self.cols["notifications"].find_one({"_id": self.oid_reply})["is_read"])
        self.assertEqual(student.post(reverse("panels:notifications_history"), {"action": "mark_all"}).status_code, 302)
        self.assertTrue(self.cols["notifications"].find_one({"_id": self.oid_reply})["is_read"])
        self.assertFalse(self.cols["notifications"].find_one({"_id": self.oid_admin})["is_read"])

    def test_profile_glassmorphism_portfolio_modals_and_update_post(self):
        student = self._login("STUDENT", "USR-1003", "zainab@edupredict.edu", "Zainab Raza", student_id="STD-2026-01")
        resp = student.get(reverse("panels:user_profile"))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode("utf-8")
        for marker in (
            "data-glass-profile", 'id="profile-edit-modal"', 'id="profile-avatar-modal"',
            'id="profile-faq-modal"', 'data-avatar-crop-input="profile-avatar-file"',
            "openChangePasswordModal()", "data-faq-pro", 'href="/notifications/"',
        ):
            self.assertIn(marker, html)

        post_res = student.post(reverse("panels:user_profile"), {
            "action": "update_profile", "full_name": "Zainab Raza Updated", "email": "zainab.updated@edupredict.edu",
            "department": "Data Science", "batch": "2026-B", "phone": "+92 321 9876543", "bio": "Honors ML Track",
        })
        self.assertEqual(post_res.status_code, 302)
        user_doc = self.cols["users"].find_one({"user_id": "USR-1003"})
        self.assertEqual((user_doc["full_name"], user_doc["email"], user_doc["department"], user_doc["batch"], user_doc["bio"]), ("Zainab Raza Updated", "zainab.updated@edupredict.edu", "Data Science", "2026-B", "Honors ML Track"))
        after_html = student.get(reverse("panels:user_profile")).content.decode("utf-8")
        self.assertIn("Zainab Raza Updated", after_html)
        self.assertIn("Honors ML Track", after_html)

    def test_admin_settings_three_tabs_studio_and_cross_tab_post_save(self):
        admin = self._login("ADMIN", "USR-1000", "admin@gmail.com", "System Administrator")
        html = admin.get(reverse("panels:admin_settings")).content.decode("utf-8")
        for marker in (
            'data-settings-tab="general"', 'data-settings-tab="alerts"', 'data-settings-tab="summary"',
            'id="admin-settings-form"', 'id="admin-settings-table"', "openThemeStudioModal()",
            "openResetDefaultsModal()", 'name="auto_student_alerts"', 'name="auto_teacher_alerts"',
        ):
            self.assertIn(marker, html)

        save_res = admin.post(reverse("panels:admin_settings"), {
            "action": "save_settings", "institution_name": "Metro Tech University", "current_term": "Spring 2027",
            "default_batch": "2027-B", "passing_gpa": "2.4", "min_attendance_pct": "80",
            "high_risk_threshold": "75", "medium_risk_threshold": "40", "anomaly_drop_pct": "20", "auto_student_alerts": "on",
        })
        self.assertEqual(save_res.status_code, 302)
        saved_doc = self.cols["system_settings"].find_one({"setting_key": "portal_config"})
        self.assertEqual((saved_doc["institution_name"], saved_doc["current_term"], saved_doc["min_attendance_pct"]), ("Metro Tech University", "Spring 2027", 80))
        self.assertTrue(saved_doc["auto_student_alerts"])
        self.assertFalse(saved_doc["auto_teacher_alerts"])
        after_html = admin.get(reverse("panels:admin_settings")).content.decode("utf-8")
        self.assertIn("Metro Tech University", after_html)
        self.assertIn("Spring 2027", after_html)

    def test_admin_tickets_compact_actions_drawer_blur_and_css_stacking(self):
        headers, rows = build_ticket_table_data(list(self.cols["support_tickets"].find({})), "ALL")
        self.assertEqual(headers, ["Ticket ID", "User", "Role", "Subject", "Status", "Date", "Actions"])
        replied_acts = rows[1][-1]["actions"]
        self.assertEqual([a["label"] for a in replied_acts], ["View", "Edit", "Clear", "Reopen", ""])
        self.assertEqual([a["onclick"] for a in replied_acts], ["openTicketDetailDrawer(this)", "openReplyTicketModal(this)", "openDeleteReplyModal(this)", "openToggleTicketModal(this)", "openDeleteTicketModal(this)"])
        self.assertEqual(replied_acts[-1]["attrs"].get("aria-label"), "Delete ticket TKT-7402")
        self.assertEqual([a["label"] for a in rows[2][-1]["actions"]], ["View", "Reply", "Resolve", ""])

        admin = self._login("ADMIN", "USR-1000", "admin@gmail.com", "System Administrator")
        ticket_html = admin.get(reverse("panels:admin_tickets")).content.decode("utf-8")
        for marker in (
            "flex-nowrap items-center justify-end gap-1 whitespace-nowrap",
            "openTicketDetailDrawer(this)", "openReplyTicketModal(this)",
            "openDeleteReplyModal(this)", "openToggleTicketModal(this)", "openDeleteTicketModal(this)",
            'id="drawer-edit-reply-btn"', 'id="drawer-delete-reply-btn"', 'id="drawer-toggle-status-btn"',
        ):
            self.assertIn(marker, ticket_html)

        base_dir = Path(settings.BASE_DIR)
        css = (base_dir / "static" / "css" / "global.css").read_text(encoding="utf-8")
        self.assertNotIn("will-change: opacity, transform", css)
        self.assertIn("to { opacity: 1; transform: none; }", css)
        self.assertIn("body.ep-overlay-blur #mobile-sidebar-drawer, body.ep-overlay-blur header.ep-topbar", css)
        self.assertIn("ep-overlay-blur", (base_dir / "static" / "js" / "app.js").read_text(encoding="utf-8"))
        self.assertIn("document.body.appendChild(drawer)", (base_dir / "static" / "js" / "image_cropper.js").read_text(encoding="utf-8"))
        self.assertIn("document.body.appendChild(drawer)", dir_js_src := (base_dir / "static" / "js" / "directory_ui.js").read_text(encoding="utf-8"))
        self.assertIn("ep-overlay-blur", dir_js_src)
        guides_src = (base_dir / "static" / "js" / "page_guides.js").read_text(encoding="utf-8")
        self.assertIn("openCommandSearchModal(initialQuery)", guides_src)
        self.assertIn("'/notifications/'", guides_src)
        self.assertIn("flex-nowrap items-center justify-end gap-1 whitespace-nowrap", (base_dir / "templates" / "components" / "data_table.html").read_text(encoding="utf-8"))

    def test_topbar_search_spinner_gap_academic_widgets_pages_and_node_vm(self):
        analyst = self._login("ANALYST", "USR-1004", "analyst@edupredict.edu", "Data Analyst")
        acc_html = analyst.get(reverse("panels:analyst_accuracy")).content.decode("utf-8")
        for marker in (
            'id="topbar-quick-search"', "openCommandSearchModal()", "academic_widgets.js?v=17",
            'id="academic-contour-card"', 'id="academic-contour-canvas"',
            'id="contour-strata-range"', "data-ep-marquee", 'id="accuracy-contour-data"',
        ):
            self.assertIn(marker, acc_html)

        student = self._login("STUDENT", "USR-1003", "zainab@edupredict.edu", "Zainab Raza", student_id="STD-2026-01")
        tips_html = student.get(reverse("panels:student_tips")).content.decode("utf-8")
        for marker in ('id="orbit-goals-card"', 'data-orbit-goal="attendance"', 'data-orbit-step="1"', 'data-orbit-step="-1"', "data-ep-marquee"):
            self.assertIn(marker, tips_html)

        base_dir = Path(settings.BASE_DIR)
        self.assertIn("inline-flex items-center justify-center gap-2", (base_dir / "static" / "js" / "ui_widgets.js").read_text(encoding="utf-8"))
        node_script = "\n".join([
            "const fs = require('fs'), vm = require('vm'), assert = require('assert');",
            "class CL { constructor(s = '') { this.s = new Set(String(s).split(/\\s+/).filter(Boolean)); } add(...x) { x.forEach((c) => c && this.s.add(c)); } remove(...x) { x.forEach((c) => this.s.delete(c)); } contains(c) { return this.s.has(c); } toggle(c, f) { const on = f === undefined ? !this.s.has(c) : Boolean(f); on ? this.s.add(c) : this.s.delete(c); return on; } }",
            "class El {",
            "  constructor(tag, attrs = {}, text = '') { this.tagName = tag.toUpperCase(); this.tag = tag.toLowerCase(); this.attrs = { ...attrs }; this.children = []; this._text = String(text); this._inner = ''; this.parentNode = null; this.parentElement = null; this.dataset = {}; this.style = {}; this.listeners = {}; this.value = attrs.value || ''; this.disabled = false; this.clientWidth = 540; this.clientHeight = 192; this.offsetWidth = 540; this.classList = new CL(attrs.class || ''); }",
            "  get innerHTML() { return this._inner; } set innerHTML(v) { this._inner = String(v); }",
            "  get textContent() { return this.children.length ? this.children.map((c) => c.textContent).join('') : this._text; } set textContent(v) { this.children = []; this._text = v == null ? '' : String(v); }",
            "  append(...ns) { ns.forEach((n) => { n.parentNode = this; n.parentElement = this; this.children.push(n); }); } appendChild(n) { this.append(n); return n; }",
            "  cloneNode(deep) { const c = new El(this.tag, { ...this.attrs }, this._text); c.dataset = { ...this.dataset }; c._inner = this._inner; if (deep) this.children.forEach((ch) => c.appendChild(ch.cloneNode(true))); return c; }",
            "  getAttribute(k) { return k in this.attrs ? String(this.attrs[k]) : null; } setAttribute(k, v) { this.attrs[k] = String(v); } removeAttribute(k) { delete this.attrs[k]; } hasAttribute(k) { return k in this.attrs; }",
            "  addEventListener(ev, fn) { (this.listeners[ev] = this.listeners[ev] || []).push(fn); } dispatchEvent(ev) { (this.listeners[ev.type] || []).forEach((fn) => fn(ev)); }",
            "  getBoundingClientRect() { return { left: 0, top: 0, width: 540, height: 192 }; } querySelector(s) { return this.querySelectorAll(s)[0] || null; }",
            "  querySelectorAll(s) { const ps = s.split(',').map((x) => x.trim()).filter(Boolean), out = [], seen = new Set(); const m = (el, tok) => { const tm = tok.match(/^[a-z0-9-]+/i); if (tm && el.tag !== tm[0].toLowerCase()) return false; for (const am of tok.matchAll(/\\[([a-z0-9_-]+)(?:=\"([^\"]*)\")?\\]/gi)) if (!(am[1] in el.attrs) || (am[2] !== undefined && String(el.attrs[am[1]]) !== am[2])) return false; return true; }; const w = (n) => n.children.forEach((c) => { if (ps.some((p) => m(c, p)) && !seen.has(c)) { seen.add(c); out.push(c); } w(c); }); w(this); return out; }",
            "}",
            "const shadowAssignments = []; let lineToCount = 0;",
            "const makeCtx = () => { let sb = 0; return { get shadowBlur() { return sb; }, set shadowBlur(v) { shadowAssignments.push(v); sb = v; }, setTransform() {}, clearRect() {}, save() {}, restore() {}, beginPath() {}, moveTo() {}, lineTo() { lineToCount += 1; }, stroke() {}, fill() {}, arc() {}, fillText() {}, setLineDash() {} }; };",
            "const root = new El('html'), body = new El('body'); root.append(body);",
            "const bar = new El('div', { id: 'ep-top-progress' }), form = new El('form', { action: '/profile/' }), submitBtn = new El('button', { type: 'submit' }, 'Save'); form.checkValidity = () => true; form.append(submitBtn);",
            "const bell = new El('button', { id: 'notification-bell-btn' }), badge = new El('span', { id: 'notification-unread-badge' }, '0'), nList = new El('div', { id: 'notification-list' });",
            "const cWrap = new El('div', { id: 'academic-contour-card' }), cStage = new El('div', { class: 'relative' }), canvas = new El('canvas', { id: 'academic-contour-canvas' }); canvas.getContext = () => makeCtx();",
            "const cRange = new El('input', { id: 'contour-strata-range', value: '7' }), cVal = new El('span', { id: 'contour-strata-val' }, '7'), cMean = new El('strong', { id: 'contour-stat-mean' }), cPeak = new El('strong', { id: 'contour-stat-peak' }), cCut = new El('strong', { id: 'contour-stat-cutoffs' }), cTip = new El('div', { id: 'contour-tooltip' }), cPin = new El('span', { id: 'contour-pin-status' });",
            "const cData = new El('script', { id: 'accuracy-contour-data' }, JSON.stringify({ portal_settings: { min_attendance_pct: 75, high_risk_threshold: 70 }, kpis: { stable_share: 84 }, contour_series: { labels: ['CS-101', 'CS-102', 'SE-201'], values: [81.5, 86.0, 79.0] } })); cStage.append(canvas, cTip); cWrap.append(cStage, cRange, cVal, cMean, cPeak, cCut, cPin);",
            "const orbit = new El('section', { id: 'orbit-goals-card', 'data-att': '85', 'data-hours': '4', 'data-marks': '80' });",
            "const oCenter = new El('span', { id: 'orbit-center-pct' }), oLabel = new El('span', { id: 'orbit-active-label' }), oTarget = new El('span', { id: 'orbit-active-target' }), oSpark = new El('div', { id: 'orbit-sparkline' }), oReset = new El('button', { id: 'orbit-reset-btn' });",
            "const gAtt = new El('button', { 'data-orbit-goal': 'attendance' }), gHrs = new El('button', { 'data-orbit-goal': 'study_hours' }), gCrs = new El('button', { 'data-orbit-goal': 'coursework' }), rAtt = new El('circle', { 'data-orbit-ring': 'attendance' }), rHrs = new El('circle', { 'data-orbit-ring': 'study_hours' }), rCrs = new El('circle', { 'data-orbit-ring': 'coursework' });",
            "const vAtt = new El('span', { 'data-orbit-val': 'attendance' }), pAtt = new El('span', { 'data-orbit-pct': 'attendance' }), vHrs = new El('span', { 'data-orbit-val': 'study_hours' }), pHrs = new El('span', { 'data-orbit-pct': 'study_hours' }), stepDown = new El('button', { 'data-orbit-step': '-1' }), stepUp = new El('button', { 'data-orbit-step': '1' });",
            "orbit.append(oCenter, oLabel, oTarget, oSpark, oReset, gAtt, gHrs, gCrs, rAtt, rHrs, rCrs, vAtt, pAtt, vHrs, pHrs, stepDown, stepUp);",
            "const mWrap = new El('section', { 'data-ep-marquee': '' }), mTrack = new El('div', { 'data-marquee-track': '' }); mTrack.append(new El('span', {}, 'Item1'), new El('span', {}, 'Item2'), new El('span', {}, 'Item3')); mWrap.append(mTrack);",
            "const mWrapRed = new El('section', { 'data-ep-marquee': '' }), mTrackRed = new El('div', { 'data-marquee-track': '' }); mTrackRed.append(new El('span', {}, 'R1'), new El('span', {}, 'R2')); mWrapRed.append(mTrackRed);",
            "body.append(bar, form, bell, badge, nList, cWrap, cData, orbit, mWrap);",
            "const findId = (n, id) => { if (n.attrs.id === id) return n; for (const c of n.children) { const f = findId(c, id); if (f) return f; } return null; };",
            "const store = {}, docListeners = {}; let reducedMotion = false;",
            "const doc = { readyState: 'complete', visibilityState: 'visible', documentElement: root, body, createElement: (t) => new El(t), createTextNode: (t) => new El('#text', {}, t), addEventListener: (ev, fn) => { (docListeners[ev] = docListeners[ev] || []).push(fn); }, getElementById: (id) => findId(root, id), querySelector: (s) => root.querySelector(s), querySelectorAll: (s) => root.querySelectorAll(s) };",
            "const feedPayload = { ok: true, unread_count: 1, notifications: [{ title: 'GPA Alert', message: 'Check report', severity: 'INFO', target_url: '/student-panel/report/' }] };",
            "const fetchMock = () => Promise.resolve({ ok: true, json: () => Promise.resolve(feedPayload) });",
            "const win = { innerWidth: 1280, devicePixelRatio: 1, document: doc, fetch: fetchMock, addEventListener: () => {}, dispatchEvent: () => {}, setTimeout: () => 0, clearTimeout: () => {}, setInterval: () => 0, clearInterval: () => {}, requestAnimationFrame: (f) => f(), matchMedia: () => ({ matches: reducedMotion }), getComputedStyle: () => ({ getPropertyValue: () => '' }), localStorage: { getItem: (k) => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); } }, Event: function (t) { this.type = t; } }; win.window = win;",
            "const ctx = vm.createContext({ ...win, window: win, document: doc, fetch: fetchMock, console, Math, Number, String, Boolean, Array, Object, JSON, Set, parseInt, parseFloat, isFinite });",
            "vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), ctx);",
            "vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), ctx);",
            "(docListeners.submit || []).forEach((fn) => fn({ target: form, submitter: submitBtn, defaultPrevented: false }));",
            "assert.ok(submitBtn.innerHTML.includes('inline-flex items-center justify-center gap-2') && submitBtn.innerHTML.includes('Processing...'));",
            "(docListeners.visibilitychange || []).forEach((fn) => fn());",
            "setImmediate(() => setImmediate(() => {",
            "  assert.strictEqual(badge.textContent, '1');",
            "  assert.ok(nList.children[0] && nList.children[0].tag === 'a' && nList.children[0].getAttribute('href') === '/student-panel/report/' && nList.children[0].hasAttribute('data-notif-item'));",
            "  assert.ok(shadowAssignments.length > 0 && shadowAssignments.every((v) => v === 0) && lineToCount > 40 && cMean.textContent !== '-');",
            "  const linesBefore = lineToCount; cRange.value = '9'; cRange.dispatchEvent({ type: 'input' });",
            "  assert.strictEqual(cVal.textContent, '9'); assert.ok(lineToCount > linesBefore);",
            "  canvas.dispatchEvent({ type: 'click', clientX: 40 }); assert.ok(cPin.textContent.includes('Pinned:'));",
            "  assert.strictEqual(oSpark.children.length, 7); const beforeCenter = oCenter.textContent;",
            "  gHrs.dispatchEvent({ type: 'click' }); assert.strictEqual(oLabel.textContent, 'Weekly Study Hours'); assert.strictEqual(oTarget.textContent, '8h');",
            "  stepUp.dispatchEvent({ type: 'click' }); assert.strictEqual(oTarget.textContent, '9h');",
            "  stepDown.dispatchEvent({ type: 'click' }); stepDown.dispatchEvent({ type: 'click' }); assert.strictEqual(oTarget.textContent, '7h');",
            "  assert.notStrictEqual(oCenter.textContent, beforeCenter); assert.strictEqual(JSON.parse(store.ep_student_orbit_goals).targets.study_hours, 7);",
            "  assert.strictEqual(mTrack.children.length, 6); assert.strictEqual(mTrack.children[3].getAttribute('aria-hidden'), 'true');",
            "  reducedMotion = true; body.append(mWrapRed); ctx.window.initAcademicWidgets(); assert.strictEqual(mTrackRed.children.length, 2);",
            "  console.log('PHASE74_NODE_VM_OK');",
            "}));",
        ])
        proc = subprocess.run(
            ["node", "-e", node_script, str(base_dir / "static" / "js" / "ui_widgets.js"), str(base_dir / "static" / "js" / "academic_widgets.js")],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
        self.assertIn("PHASE74_NODE_VM_OK", proc.stdout)
