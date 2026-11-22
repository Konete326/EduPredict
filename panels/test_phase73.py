import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.test import Client, TestCase
from django.urls import reverse
import accounts.services as acc_svc
from core.db import invalidate_cache
import panels.admin_audit_services as audit_svc
import panels.admin_seed as admin_seed
from panels.test_admin import _MemCol


class Phase73AuthShowcaseTests(TestCase):
    def setUp(self):
        invalidate_cache()
        now = datetime(2026, 11, 22, 10, 0, tzinfo=timezone.utc)
        self.cols = {
            "users": _MemCol([{
                "user_id": "USR-1000", "full_name": "System Administrator", "email": "admin@gmail.com",
                "password_hash": make_password("admin123"), "role": "ADMIN", "department": "Administration",
                "batch": "ALL", "is_active": True, "approval_status": "APPROVED", "created_at": now,
            }]),
            "student_records": _MemCol(), "predictions": _MemCol(), "datasets_log": _MemCol(),
            "notifications": _MemCol(), "activity_logs": _MemCol(), "courses": _MemCol(),
            "support_tickets": _MemCol(), "system_settings": _MemCol(),
        }
        for p in (
            patch("core.db.MongoDBClient.get_collection", side_effect=lambda name: self.cols.setdefault(name, _MemCol())),
            patch("core.db.MongoDBClient.check_health", return_value={"connected": True, "error": None}),
            patch.object(acc_svc, "_INDEXES_ENSURED", True),
            patch.object(acc_svc, "_DEFAULT_ADMIN_ENSURED", True),
            patch.object(admin_seed, "_ADMIN_SEED_DONE", True),
            patch.object(audit_svc, "_AUDIT_SEED_DONE", True),
        ):
            p.start()
            self.addCleanup(p.stop)

    def test_login03_showcase_slots_floating_paths_and_strength_meter_html(self):
        resp = Client().get(reverse("accounts:auth_view"))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode("utf-8")
        markers = (
            'data-slot="login"', 'data-slot="login-aside"', 'data-slot="login-main"',
            'data-slot="login-panel"', 'data-slot="login-header"', "Sign in or join.",
            'id="ep-floating-paths"', "data-floating-paths", 'id="reg-password-strength"',
            'data-strength-bar="1"', "data-pending-approval-card", "auth_wizard.js?v=17",
        )
        for marker in markers:
            self.assertIn(marker, html)

    def test_teacher_registration_renders_pending_approval_status_card(self):
        client = Client()
        resp = client.post(reverse("accounts:auth_view"), {
            "action": "register", "full_name": "Prof. Nadia Khan", "email": "nadia@edupredict.edu",
            "password": "StrongPass!99", "confirm_password": "StrongPass!99", "role": "TEACHER",
            "department": "Computer Science", "batch": "ALL",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context.get("pending_teacher_approval"))
        html = resp.content.decode("utf-8")
        self.assertIn("Account Created — Awaiting Admin Approval", html)
        idx = html.find("data-pending-approval-card")
        self.assertGreater(idx, -1)
        tag_start = html.rfind("<", 0, idx)
        tag_end = html.find(">", idx)
        self.assertNotIn("hidden", html[tag_start:tag_end].split())

    def test_auth_wizard_js_floating_paths_and_password_strength_in_node_vm(self):
        js_path = (Path(settings.BASE_DIR) / "static" / "js" / "auth_wizard.js").as_posix()
        script = "\n".join([
            "const fs = require('fs');",
            "const vm = require('vm');",
            "const makeClassList = () => {",
            "  const set = new Set();",
            "  return {",
            "    add: (...c) => c.forEach((x) => set.add(x)),",
            "    remove: (...c) => c.forEach((x) => set.delete(x)),",
            "    toggle: (c, force) => (force === undefined ? (set.has(c) ? set.delete(c) : set.add(c)) : (force ? set.add(c) : set.delete(c))),",
            "    contains: (c) => set.has(c),",
            "    toArray: () => Array.from(set),",
            "  };",
            "};",
            "const makeEl = (tag, ns = null) => ({",
            "  tagName: tag, namespaceURI: ns, attributes: {}, children: [], dataset: {}, textContent: '', innerHTML: '', value: '', listeners: {},",
            "  style: { setProperty(k, v) { this[k] = v; } },",
            "  classList: makeClassList(),",
            "  setAttribute(k, v) { this.attributes[k] = String(v); },",
            "  getAttribute(k) { return this.attributes[k] ?? null; },",
            "  appendChild(c) { this.children.push(c); return c; },",
            "  querySelectorAll() { return []; }, querySelector() { return null; },",
            "  addEventListener(ev, fn) { (this.listeners[ev] = this.listeners[ev] || []).push(fn); },",
            "});",
            "const fp = makeEl('div'); fp.attributes.id = 'ep-floating-paths';",
            "const passInput = makeEl('input'); passInput.attributes.id = 'reg-password';",
            "const bars = [1, 2, 3, 4].map((i) => { const b = makeEl('div'); b.setAttribute('data-strength-bar', String(i)); return b; });",
            "const label = makeEl('span'); label.attributes.id = 'reg-password-strength-label';",
            "const meter = makeEl('div'); meter.attributes.id = 'reg-password-strength';",
            "meter.querySelectorAll = (s) => (String(s).includes('data-strength-bar') ? bars : []);",
            "const doc = {",
            "  readyState: 'complete',",
            "  createElementNS: (ns, tag) => makeEl(tag, ns),",
            "  createElement: (tag) => makeEl(tag),",
            "  getElementById: (id) => ({ 'ep-floating-paths': fp, 'reg-password': passInput, 'reg-password-strength': meter, 'reg-password-strength-label': label }[id] || null),",
            "  querySelector: () => null,",
            "  querySelectorAll: (s) => (String(s).includes('data-strength-bar') ? bars : []),",
            "  addEventListener: () => {},",
            "};",
            "const ctx = { window: null, document: doc, console, Number, String, Boolean, Array, Math, Set };",
            "ctx.window = ctx;",
            f"vm.runInNewContext(fs.readFileSync({json.dumps(js_path)}, 'utf8'), ctx);",
            "const countPaths = (node) => node.children.reduce((acc, c) => acc + (c.tagName === 'path' ? 1 : 0) + countPaths(c), 0);",
            "const samples = ['', 'abc', 'abcdef', 'abcdef12', 'Abcdef12', 'Xy9!Kp2$Lm8@Qz4'].map((pw) => {",
            "  const res = ctx.window.evaluatePasswordStrength(pw);",
            "  passInput.value = pw;",
            "  (passInput.listeners.input || []).forEach((fn) => fn());",
            "  const activeBars = bars.filter((b) => b.style.backgroundColor && b.style.backgroundColor !== 'var(--border-subtle)').length;",
            "  return { pw, score: res.score, resLabel: res.label, domLabel: label.textContent, activeBars };",
            "});",
            "console.log(JSON.stringify({ pathCount: countPaths(fp), samples }));",
        ])
        proc = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
        payload = json.loads(proc.stdout.strip())
        self.assertEqual(payload["pathCount"], 72)
        self.assertEqual([(s["score"], s["resLabel"], s["activeBars"]) for s in payload["samples"]], [
            (0, "Enter at least 6 characters", 0),
            (0, "Enter at least 6 characters", 0),
            (1, "Weak", 1),
            (2, "Fair", 2),
            (3, "Good", 3),
            (4, "Strong", 4),
        ])
        self.assertTrue(all(s["domLabel"] == s["resLabel"] for s in payload["samples"]))
