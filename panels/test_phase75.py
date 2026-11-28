import io
import json
import re
import subprocess
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.test import Client, TestCase
from django.urls import reverse
import accounts.services as acc_svc
from analytics.model_health import _load_model_health
import core.ai_agent_services as ai_svc
from core.db import invalidate_cache
import panels.admin_audit_services as audit_svc
import panels.admin_seed as admin_seed
from panels.admin_services import create_user_record
from panels.pdf_services import generate_student_report_card_pdf, generate_teacher_roster_pdf
from panels.teacher_services import provision_student_accounts
from panels.test_phase74 import _Phase74MemCol


class _Phase75MemCol(_Phase74MemCol):
    def estimated_document_count(self):
        return len(self.docs)

    def _matches(self, doc, query):
        for k, v in (query or {}).items():
            if isinstance(v, dict) and "$regex" in v:
                flags = re.IGNORECASE if "i" in str(v.get("$options") or "") else 0
                if not re.search(v["$regex"], str(doc.get(k) or ""), flags):
                    return False
            elif not super()._matches(doc, {k: v}):
                return False
        return True


class Phase75VerificationTests(TestCase):
    def setUp(self):
        invalidate_cache()
        self.addCleanup(invalidate_cache)
        now = datetime(2026, 11, 22, 12, 0, tzinfo=timezone.utc)
        self.cols = {
            "users": _Phase75MemCol([
                {
                    "user_id": "USR-1000", "full_name": "System Administrator", "email": "admin@gmail.com",
                    "password_hash": make_password("admin123"), "role": "ADMIN", "department": "Administration",
                    "batch": "ALL", "is_active": True, "approval_status": "APPROVED", "created_at": now,
                },
                {
                    "user_id": "USR-1004", "full_name": "Data Analyst", "email": "analyst@edupredict.edu",
                    "password_hash": make_password("analyst123"), "role": "ANALYST", "department": "Analytics",
                    "batch": "ALL", "is_active": True, "approval_status": "APPROVED", "created_at": now,
                },
            ]),
            "student_records": _Phase75MemCol(),
            "predictions": _Phase75MemCol(),
            "courses": _Phase75MemCol(),
            "support_tickets": _Phase75MemCol(),
            "notifications": _Phase75MemCol(),
            "datasets_log": _Phase75MemCol(),
            "activity_logs": _Phase75MemCol(),
            "system_settings": _Phase75MemCol(),
            "ai_chats": _Phase75MemCol(),
        }
        for p in (
            patch("core.db.MongoDBClient.get_collection", side_effect=lambda name: self.cols.setdefault(name, _Phase75MemCol())),
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

    def _run_node_vm(self, js_code, *script_paths):
        proc = subprocess.run(["node", "-e", js_code, *[str(p) for p in script_paths]], capture_output=True, text=True, check=False)
        self.assertEqual(proc.returncode, 0, f"STDOUT: {proc.stdout}\nSTDERR: {proc.stderr}")
        return proc.stdout

    def test_env_agents_sparkle_ban_handoff_gemini_fallback_and_ephemeral(self):
        base_dir = Path(settings.BASE_DIR)
        env_text = (base_dir / ".env").read_text(encoding="utf-8")
        example_text = (base_dir / ".env.example").read_text(encoding="utf-8")
        self.assertRegex(env_text, r"(?m)^GEMINI_BACKEND_KEY_3=")
        self.assertIn("GEMINI_BACKEND_KEY_3=", example_text)
        for rel in ("templates/components/ai_message_dock.html", "static/js/ai_agent_dock.js", "core/ai_agent_services.py", "templates/panels/student_dashboard.html"):
            src = (base_dir / rel).read_text(encoding="utf-8")
            self.assertNotIn("fa-wand-magic-sparkles", src, rel)
            self.assertNotIn("\u2728", src, rel)

        self.assertEqual(Client().get(reverse("panels:ai_agent_chat")).status_code, 302)
        student = self._login("STUDENT", "USR-2001", "ayesha@edupredict.edu", "Ayesha Siddiqui", student_id="STD-2026-2001")
        get_resp = student.get(reverse("panels:ai_agent_chat"))
        self.assertEqual(get_resp.status_code, 200)
        get_data = get_resp.json()
        self.assertTrue(get_data["ok"])
        self.assertTrue(get_data["ephemeral"])
        self.assertEqual([(a["id"], a["name"]) for a in get_data["agents"]], [("coach", "EduCoach AI"), ("analyst", "PulseML AI"), ("ops", "CourseOps AI"), ("desk", "HelpDesk AI")])
        for old_id, new_id in (("amina", "coach"), ("zain", "analyst"), ("sara", "ops"), ("bilal", "desk")):
            self.assertEqual(ai_svc.resolve_agent_id(old_id), new_id)

        target, handoff = ai_svc.detect_best_agent("Check ML model accuracy, MAE and dropout risk score anomalies", "coach")
        self.assertTrue(handoff)
        self.assertEqual(target["id"], "analyst")

        url = reverse("panels:ai_agent_chat")
        self.assertEqual(student.post(url, data=json.dumps({"agent_id": "coach", "message": "   "}), content_type="application/json").status_code, 400)
        self.assertEqual(student.post(url, data="{bad-json", content_type="application/json").status_code, 400)
        self.assertEqual(student.put(url).status_code, 405)

        captured_req = {}
        gemini_body = json.dumps({"candidates": [{"content": {"parts": [{"text": "Live DB mein abhi 0 records aur 0 predictions hain; upload ke baad accuracy dikhegi."}]}}]}).encode("utf-8")

        class _FakeResp:
            status = 200
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self):
                return gemini_body

        def _fake_urlopen(req, timeout=5):
            captured_req["url"] = req.full_url
            captured_req["payload"] = json.loads(req.data.decode("utf-8"))
            return _FakeResp()

        with patch.dict("os.environ", {"GEMINI_BACKEND_KEY_3": "test-gemini-key"}), patch.object(ai_svc.urllib.request, "urlopen", side_effect=_fake_urlopen):
            res = student.post(url, data=json.dumps({"agent_id": "coach", "message": "Check ML model accuracy and dropout risk score anomalies"}), content_type="application/json").json()

        self.assertTrue(res["ok"])
        self.assertTrue(res["handoff"])
        self.assertTrue(res["ephemeral"])
        self.assertEqual(res["from_agent"]["id"], "coach")
        self.assertEqual(res["active_agent"]["id"], "analyst")
        self.assertIn("PulseML AI", res["handoff_message"])
        self.assertIn("Check ML model accuracy", res["task_preview"])
        self.assertIn("Mujhe aapka task mil gaya hai", res["continue_prefix"])
        self.assertEqual(res["engine"], "gemini-flash-lite-latest")
        self.assertIn("0 records", res["reply"])
        self.assertIn("gemini-flash-lite-latest:generateContent", captured_req["url"])
        self.assertIn('"records_count": 0', captured_req["payload"]["system_instruction"]["parts"][0]["text"])

        with patch.dict("os.environ", {"GEMINI_BACKEND_KEY_3": "test-gemini-key"}), patch.object(ai_svc.urllib.request, "urlopen", side_effect=urllib.error.URLError("offline")):
            fb = student.post(url, data=json.dumps({"agent_id": "coach", "message": "Show prediction model accuracy and anomalies"}), content_type="application/json").json()

        self.assertTrue(fb["ok"])
        self.assertTrue(fb["handoff"])
        self.assertTrue(fb["ephemeral"])
        self.assertEqual(fb["active_agent"]["id"], "analyst")
        self.assertTrue(fb["engine"].startswith("fallback:"))
        self.assertIn("0 predictions", fb["reply"])
        self.assertEqual(self.cols["ai_chats"].count_documents({}), 0)
        self.assertEqual(self.cols["notifications"].count_documents({}), 0)

    def test_ai_agent_dock_node_vm_zig_zag_handoff_and_ephemeral_clear(self):
        base_dir = Path(settings.BASE_DIR)
        node_script = "\n".join([
            "const fs = require('fs'), vm = require('vm'), assert = require('assert');",
            "class CL { constructor(s = '') { this.s = new Set(String(s).split(/\\s+/).filter(Boolean)); } add(...x) { x.forEach((c) => c && this.s.add(c)); } remove(...x) { x.forEach((c) => this.s.delete(c)); } contains(c) { return this.s.has(c); } toggle(c, f) { const on = f === undefined ? !this.s.has(c) : Boolean(f); on ? this.s.add(c) : this.s.delete(c); return on; } }",
            "class El {",
            "  constructor(tag, attrs = {}, text = '') { this.tag = tag.toLowerCase(); this.attrs = { ...attrs }; this.children = []; this._text = String(text); this.parentNode = null; this.dataset = {}; this.style = {}; this.listeners = {}; this.value = attrs.value || ''; this.src = attrs.src || ''; this.alt = attrs.alt || ''; this.placeholder = attrs.placeholder || ''; this.disabled = false; this.scrollTop = 0; this.scrollHeight = 120; this.classList = new CL(attrs.class || ''); }",
            "  get className() { return Array.from(this.classList.s).join(' '); } set className(v) { this.classList = new CL(v); }",
            "  get textContent() { return this.children.length ? this.children.map((c) => c.textContent).join(' ') : this._text; } set textContent(v) { this.children = []; this._text = v == null ? '' : String(v); }",
            "  append(...ns) { ns.forEach((n) => { n.parentNode = this; this.children.push(n); }); } appendChild(n) { this.append(n); return n; }",
            "  removeChild(n) { const i = this.children.indexOf(n); if (i >= 0) { this.children.splice(i, 1); n.parentNode = null; } return n; }",
            "  getAttribute(k) { return k in this.attrs ? String(this.attrs[k]) : null; } setAttribute(k, v) { this.attrs[k] = String(v); } hasAttribute(k) { return k in this.attrs; }",
            "  addEventListener(ev, fn) { (this.listeners[ev] = this.listeners[ev] || []).push(fn); } dispatchEvent(ev) { (this.listeners[ev.type] || []).forEach((fn) => fn(ev)); }",
            "  focus() {} closest() { return null; }",
            "  querySelector(s) { return this.querySelectorAll(s)[0] || null; }",
            "  querySelectorAll(s) { const ps = s.split(',').map((x) => x.trim()).filter(Boolean), out = [], seen = new Set(); const m = (el, tok) => { const tm = tok.match(/^[a-z0-9-]+/i); if (tm && el.tag !== tm[0].toLowerCase()) return false; for (const am of tok.matchAll(/\\[([a-z0-9_-]+)(?:=\"([^\"]*)\")?\\]/gi)) if (!(am[1] in el.attrs) || (am[2] !== undefined && String(el.attrs[am[1]]) !== am[2])) return false; return true; }; const w = (n) => n.children.forEach((c) => { if (ps.some((p) => m(c, p)) && !seen.has(c)) { seen.add(c); out.push(c); } w(c); }); w(this); return out; }",
            "}",
            "const root = new El('div', { id: 'ep-agent-dock-root' });",
            "const panel = new El('section', { id: 'ep-agent-chat-panel', class: 'hidden', 'aria-hidden': 'true' });",
            "const chatDp = new El('img', { id: 'ep-chat-agent-dp', alt: 'EduCoach AI' }), nameEl = new El('h3', { id: 'ep-chat-agent-name' }, 'EduCoach AI'), roleEl = new El('p', { id: 'ep-chat-agent-role' }, 'Academic & Study Advisor');",
            "const clearBtn = new El('button', { id: 'ep-dock-clear-btn' }), closeBtn = new El('button', { id: 'ep-dock-close-btn' });",
            "const stream = new El('div', { id: 'ep-zig-zag-stream' }); stream.appendChild(new El('div', { 'data-dock-empty': 'true' }, 'Pick an EduPredict AI Agent'));",
            "panel.append(chatDp, nameEl, roleEl, clearBtn, closeBtn, stream);",
            "const dockBar = new El('div', { id: 'ep-message-dock', class: 'hidden', 'aria-hidden': 'true' });",
            "const mkDockBtn = (id) => { const b = new El('button', { 'data-dock-agent': id, 'aria-pressed': 'false' }); b.appendChild(new El('img', { 'data-dock-avatar': '', alt: id })); return b; };",
            "const bCoach = mkDockBtn('coach'), bAnalyst = mkDockBtn('analyst'), bOps = mkDockBtn('ops'), bDesk = mkDockBtn('desk');",
            "const form = new El('form', { id: 'ep-dock-form' }), input = new El('input', { id: 'ep-dock-input' }), sendBtn = new El('button', { id: 'ep-dock-send' });",
            "form.append(input, sendBtn); dockBar.append(bCoach, bAnalyst, bOps, bDesk, form);",
            "const toggleBtn = new El('button', { id: 'ep-agent-dock-toggle', 'aria-expanded': 'false' });",
            "root.append(panel, dockBar, toggleBtn);",
            "const body = new El('body'); body.append(root); const html = new El('html'); html.append(body);",
            "const findId = (n, id) => { if (n.attrs.id === id) return n; for (const c of n.children) { const f = findId(c, id); if (f) return f; } return null; };",
            "let localCalls = 0; const sessData = {};",
            "const localStore = { getItem() { localCalls += 1; return null; }, setItem() { localCalls += 1; }, removeItem() { localCalls += 1; } };",
            "const sessStore = { getItem: (k) => (k in sessData ? sessData[k] : null), setItem: (k, v) => { sessData[k] = String(v); }, removeItem: (k) => { delete sessData[k]; } };",
            "const doc = { readyState: 'complete', cookie: 'csrftoken=tok123', documentElement: html, body, createElement: (t) => new El(t), getElementById: (id) => findId(html, id), querySelector: (s) => html.querySelector(s), querySelectorAll: (s) => html.querySelectorAll(s), addEventListener: () => {} };",
            "const handoffResp = { ok: true, handoff: true, ephemeral: true, from_agent: { id: 'coach', name: 'EduCoach AI', role: 'Academic & Study Advisor', accent: '#16a34a' }, active_agent: { id: 'analyst', name: 'PulseML AI', role: 'Predictive Risk & Data Agent', accent: '#2563eb' }, handoff_message: 'Main aapka yeh kaam PulseML AI ko assign kar raha hoon.', task_preview: 'Check model accuracy and dropout risk', continue_prefix: 'Mujhe aapka task mil gaya hai:', reply: 'Live DB has 0 predictions yet.' };",
            "const fetchMock = () => Promise.resolve({ json: () => Promise.resolve(handoffResp) });",
            "const win = { document: doc, fetch: fetchMock, localStorage: localStore, sessionStorage: sessStore, location: { pathname: '/student-panel/', origin: 'http://localhost' }, showToast: () => {} }; win.window = win;",
            "const ctx = vm.createContext({ ...win, window: win, document: doc, fetch: fetchMock, localStorage: localStore, sessionStorage: sessStore, console, Math, Number, String, Boolean, Array, Object, JSON, Date, Set, decodeURIComponent, encodeURIComponent, URL });",
            "vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), ctx);",
            "toggleBtn.dispatchEvent({ type: 'click' });",
            "assert.ok(!dockBar.classList.contains('hidden') && dockBar.classList.contains('flex'));",
            "bCoach.dispatchEvent({ type: 'click' });",
            "assert.ok(!panel.classList.contains('hidden') && nameEl.textContent === 'EduCoach AI');",
            "assert.ok(chatDp.src.startsWith('data:image/svg+xml') && bCoach.querySelector('img[data-dock-avatar]').src.startsWith('data:image/svg+xml'));",
            "assert.strictEqual(stream.querySelectorAll('[data-dock-msg=\"agent\"]').length, 1);",
            "assert.ok(typeof sessData.ep_ai_active_session === 'string' && sessData.ep_ai_active_session.includes('coach'));",
            "input.value = 'Check model accuracy and dropout risk';",
            "form.dispatchEvent({ type: 'submit', preventDefault: () => {} });",
            "setImmediate(() => setImmediate(() => {",
            "  const uMsgs = stream.querySelectorAll('[data-dock-msg=\"user\"]');",
            "  assert.strictEqual(uMsgs.length, 1); assert.ok(uMsgs[0].classList.contains('justify-end') && uMsgs[0].textContent.includes('\u2713\u2713'));",
            "  const aMsgs = stream.querySelectorAll('[data-dock-msg=\"agent\"]');",
            "  assert.strictEqual(aMsgs.length, 3);",
            "  assert.ok(aMsgs[1].getAttribute('data-agent-id') === 'coach' && aMsgs[1].classList.contains('justify-start'));",
            "  const previews = stream.querySelectorAll('[data-handoff-preview=\"true\"]');",
            "  assert.strictEqual(previews.length, 1); assert.ok(previews[0].textContent.includes('EduCoach AI -> PulseML AI') && previews[0].textContent.includes('Task Preview: Check model accuracy'));",
            "  assert.strictEqual(nameEl.textContent, 'PulseML AI'); assert.strictEqual(bAnalyst.getAttribute('aria-pressed'), 'true');",
            "  assert.ok(aMsgs[2].getAttribute('data-agent-id') === 'analyst' && aMsgs[2].textContent.includes('Mujhe aapka task mil gaya hai:') && aMsgs[2].textContent.includes('Live DB has 0 predictions yet.'));",
            "  assert.ok(typeof sessData.ep_ai_active_session === 'string' && sessData.ep_ai_active_session.includes('Live DB has 0 predictions yet.'));",
            "  clearBtn.dispatchEvent({ type: 'click' });",
            "  assert.strictEqual(sessData.ep_ai_active_session, undefined);",
            "  assert.strictEqual(stream.querySelectorAll('[data-dock-msg], [data-handoff-preview]').length, 0);",
            "  assert.strictEqual(stream.querySelectorAll('[data-dock-empty=\"true\"]').length, 1);",
            "  bAnalyst.dispatchEvent({ type: 'click' }); assert.strictEqual(stream.querySelectorAll('[data-dock-msg]').length, 1);",
            "  assert.ok(typeof sessData.ep_ai_active_session === 'string');",
            "  closeBtn.dispatchEvent({ type: 'click' });",
            "  assert.strictEqual(sessData.ep_ai_active_session, undefined);",
            "  assert.ok(panel.classList.contains('hidden') && panel.getAttribute('aria-hidden') === 'true');",
            "  assert.strictEqual(stream.querySelectorAll('[data-dock-msg], [data-handoff-preview]').length, 0);",
            "  assert.strictEqual(localCalls, 0);",
            "  console.log('AI_DOCK_E2E_OK');",
            "}));",
        ])
        out = self._run_node_vm(node_script, base_dir / "static" / "js" / "ai_agent_dock.js")
        self.assertIn("AI_DOCK_E2E_OK", out)

    def test_real_signup_zero_dummy_records_student_empty_states_and_contour(self):
        self.cols["users"].insert_one({
            "user_id": "USR-T750", "full_name": "Prof. Phase75", "email": "t75@edupredict.edu",
            "role": "TEACHER", "department": "Software Engineering", "is_active": True, "approval_status": "APPROVED",
        })
        client = Client()
        reg_resp = client.post(reverse("accounts:auth_view"), {
            "action": "register", "full_name": "Ayesha Siddiqui", "email": "ayesha.new@edupredict.edu",
            "password": "password123", "confirm_password": "password123", "role": "STUDENT",
            "department": "Software Engineering", "batch": "2026-A",
        })
        self.assertEqual(reg_resp.status_code, 200)
        self.assertIn("class upload", reg_resp.content.decode("utf-8"))
        self.assertIsNone(self.cols["users"].find_one({"email": "ayesha.new@edupredict.edu"}))

        creds = provision_student_accounts([{"student_id": "STD-2026-750", "full_name": "Ayesha Siddiqui", "birth_date": "2004-05-12", "batch": "2026-A", "course_code": "CS-101"}], teacher_user={"user_id": "USR-T750", "full_name": "Prof. Phase75"})
        self.assertEqual(creds[0]["password"], "ayesha@2004-05-12")
        provisioned = self.cols["users"].find_one({"student_id": "STD-2026-750"})
        self.assertIsNotNone(provisioned)
        self.assertEqual((provisioned["is_active"], provisioned["approval_status"], provisioned["username"]), (True, "APPROVED", "ayesha"))
        login_resp = client.post(reverse("accounts:auth_view"), {"action": "login", "email": "STD-2026-750", "password": "ayesha@2004-05-12"})
        self.assertRedirects(login_resp, reverse("panels:student_dashboard"), fetch_redirect_response=False)
        self.assertIsNotNone(self.cols["users"].find_one({"student_id": "STD-2026-750"}).get("last_login_at"))
        for alt_id in ("ayesha", "Ayesha Siddiqui"):
            alt_resp = Client().post(reverse("accounts:auth_view"), {"action": "login", "email": alt_id, "password": "ayesha@2004-05-12"})
            self.assertRedirects(alt_resp, reverse("panels:student_dashboard"), fetch_redirect_response=False)
        self.assertEqual(self.cols["student_records"].count_documents({}), 0)

        created_doc, create_err = create_user_record("Bilal Ahmad", "bilal.std@edupredict.edu", "password123", "STUDENT", "IT", "2026-B")
        self.assertIsNone(create_err)
        self.assertTrue(str(created_doc.get("student_id") or "").startswith("STD-"))
        self.assertEqual(self.cols["student_records"].count_documents({}), 0)

        dash_resp = client.get(reverse("panels:student_dashboard"))
        self.assertEqual(dash_resp.status_code, 200)
        dash_html = dash_resp.content.decode("utf-8")
        self.assertIn("Hello, Ayesha Siddiqui!", dash_html)
        self.assertEqual(dash_resp.context["record"]["avg_attendance"], 0.0)
        self.assertEqual(dash_resp.context["tips"], [])
        self.assertIn("No course marks or attendance records have been uploaded for your Student ID yet.", dash_resp.context["insight"]["summary"])
        self.assertIn('id="accuracy-contour-data"', dash_html)

        self.assertEqual(_load_model_health()["contour_series"], {"labels": [], "values": []})
        now = datetime(2026, 11, 22, 12, 0, tzinfo=timezone.utc)
        self.cols["student_records"].insert_one({"student_id": "STD-1", "course_code": "CS-101", "attendance_pct": 80.0, "internal_marks": 70.0, "previous_gpa": 3.2, "updated_at": now})
        self.assertEqual(_load_model_health()["contour_series"], {"labels": [], "values": []})
        self.cols["student_records"].insert_one({"student_id": "STD-2", "course_code": "SE-201", "attendance_pct": 90.0, "internal_marks": 84.0, "previous_gpa": 3.5, "updated_at": now})
        health = _load_model_health()
        self.assertEqual(health["contour_series"], {"labels": ["CS-101", "SE-201"], "values": [75.0, 87.0], "attendance": [80.0, 90.0], "marks": [70.0, 84.0]})

    def test_academic_widgets_node_vm_empty_and_populated_real_data(self):
        base_dir = Path(settings.BASE_DIR)
        node_script = "\n".join([
            "const fs = require('fs'), vm = require('vm'), assert = require('assert');",
            "class CL { constructor(s = '') { this.s = new Set(String(s).split(/\\s+/).filter(Boolean)); } add(...x) { x.forEach((c) => c && this.s.add(c)); } remove(...x) { x.forEach((c) => this.s.delete(c)); } contains(c) { return this.s.has(c); } toggle(c, f) { const on = f === undefined ? !this.s.has(c) : Boolean(f); on ? this.s.add(c) : this.s.delete(c); return on; } }",
            "class El {",
            "  constructor(tag, attrs = {}, text = '') { this.tag = tag.toLowerCase(); this.attrs = { ...attrs }; this.children = []; this._text = String(text); this.parentElement = null; this.dataset = {}; this.style = {}; this.listeners = {}; this.value = attrs.value || ''; this.clientWidth = 540; this.clientHeight = 176; this.classList = new CL(attrs.class || ''); }",
            "  get textContent() { return this.children.length ? this.children.map((c) => c.textContent).join('') : this._text; } set textContent(v) { this.children = []; this._text = v == null ? '' : String(v); }",
            "  append(...ns) { ns.forEach((n) => { n.parentElement = this; this.children.push(n); }); } appendChild(n) { this.append(n); return n; }",
            "  getAttribute(k) { return k in this.attrs ? String(this.attrs[k]) : null; } setAttribute(k, v) { this.attrs[k] = String(v); }",
            "  addEventListener(ev, fn) { (this.listeners[ev] = this.listeners[ev] || []).push(fn); }",
            "  querySelector(s) { return this.querySelectorAll(s)[0] || null; }",
            "  querySelectorAll(s) { const ps = s.split(',').map((x) => x.trim()).filter(Boolean), out = [], seen = new Set(); const m = (el, tok) => { for (const am of tok.matchAll(/\\[([a-z0-9_-]+)(?:=\"([^\"]*)\")?\\]/gi)) if (!(am[1] in el.attrs) || (am[2] !== undefined && String(el.attrs[am[1]]) !== am[2])) return false; return true; }; const w = (n) => n.children.forEach((c) => { if (ps.some((p) => m(c, p)) && !seen.has(c)) { seen.add(c); out.push(c); } w(c); }); w(this); return out; }",
            "}",
            "const texts = [], shadows = []; let lineTos = 0;",
            "const ctx2d = () => { let sb = 0; return { get shadowBlur() { return sb; }, set shadowBlur(v) { shadows.push(v); sb = v; }, setTransform() {}, clearRect() {}, save() {}, restore() {}, beginPath() {}, moveTo() {}, lineTo() { lineTos += 1; }, stroke() {}, fill() {}, arc() {}, fillText(t) { texts.push(String(t)); }, setLineDash() {} }; };",
            "const root = new El('html'), body = new El('body'); root.append(body);",
            "const stage = new El('div'), canvas = new El('canvas', { id: 'academic-contour-canvas' }); canvas.getContext = ctx2d;",
            "const cData = new El('script', { id: 'accuracy-contour-data' }, JSON.stringify({ portal_settings: { min_attendance_pct: 75, high_risk_threshold: 70 }, labels: [], mine: [] }));",
            "const cMean = new El('strong', { id: 'contour-stat-mean' }), cPeak = new El('strong', { id: 'contour-stat-peak' }), cPin = new El('span', { id: 'contour-pin-status' });",
            "stage.append(canvas); body.append(stage, cData, cMean, cPeak, cPin);",
            "const orbit = new El('div', { id: 'orbit-goals-card', 'data-att': '0', 'data-hours': '0', 'data-marks': '0' });",
            "const oCenter = new El('span', { id: 'orbit-center-pct' }), oSpark = new El('div', { id: 'orbit-sparkline' }); orbit.append(oCenter, oSpark); body.append(orbit);",
            "const findId = (n, id) => { if (n.attrs.id === id) return n; for (const c of n.children) { const f = findId(c, id); if (f) return f; } return null; };",
            "const doc = { readyState: 'complete', documentElement: root, body, createElement: (t) => new El(t), getElementById: (id) => findId(root, id), querySelectorAll: (s) => root.querySelectorAll(s), addEventListener: () => {} };",
            "const win = { innerWidth: 1280, devicePixelRatio: 1, document: doc, addEventListener: () => {}, matchMedia: () => ({ matches: false }), getComputedStyle: () => ({ getPropertyValue: () => '' }) }; win.window = win;",
            "const ctx = vm.createContext({ ...win, window: win, document: doc, console, Math, Number, String, Boolean, Array, Object, JSON, Set, parseInt, parseFloat, isFinite });",
            "vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), ctx);",
            "assert.ok(texts.includes('No live course records available yet'));",
            "assert.strictEqual(cMean.textContent, '-');",
            "assert.ok(cPin.textContent.includes('At least 2 live courses'));",
            "assert.strictEqual(oCenter.textContent, '0%');",
            "assert.strictEqual(oSpark.children.length, 7);",
            "assert.ok(oSpark.children.every((col) => col.children[0].children[0].style.height === '12%'));",
            "shadows.length = 0; lineTos = 0;",
            "cData.textContent = JSON.stringify({ portal_settings: { min_attendance_pct: 75, high_risk_threshold: 70 }, labels: ['CS-101', 'MATH-201', 'SE-202'], mine: [82, 88, 76] });",
            "orbit.setAttribute('data-att', '88'); orbit.setAttribute('data-hours', '6'); orbit.setAttribute('data-marks', '82');",
            "ctx.window.initAcademicWidgets();",
            "assert.ok(shadows.length > 0 && shadows.every((v) => v === 0) && lineTos > 40);",
            "assert.strictEqual(cMean.textContent, '82.0%'); assert.ok(cPeak.textContent.includes('MATH-201'));",
            "assert.notStrictEqual(oCenter.textContent, '0%');",
            "console.log('ACADEMIC_WIDGETS_DUAL_OK');",
        ])
        out = self._run_node_vm(node_script, base_dir / "static" / "js" / "academic_widgets.js")
        self.assertIn("ACADEMIC_WIDGETS_DUAL_OK", out)

    def test_a4_monochrome_pdfs_print_css_single_toggle_viewport_fit_and_profile_untouched(self):
        base_dir = Path(settings.BASE_DIR)
        pdf_src = (base_dir / "panels" / "pdf_services.py").read_text(encoding="utf-8")
        self.assertIn("from reportlab.lib.pagesizes import A4", pdf_src)
        self.assertNotIn("#0F172A", pdf_src)

        student_pdf = generate_student_report_card_pdf({
            "record": {"student_id": "STD-2026-01", "full_name": "Zainab Raza", "batch": "2026-A", "department": "CS", "avg_attendance": 88.0, "avg_marks": 82.0, "predicted_gpa": 3.55, "risk_level": "LOW"},
            "subject_rows": [{"course_code": "CS-101", "my_marks": 82.0, "class_marks": 76.0, "my_attendance": 88.0, "class_attendance": 81.0, "status": {"text": "Excellent"}}],
            "tips": [],
        })
        roster_pdf = generate_teacher_roster_pdf({"batch": "2026-A", "course_code": "CS-101", "students": [{"student_id": "STD-2026-01", "full_name": "Zainab Raza", "batch": "2026-A", "course_code": "CS-101", "attendance_pct": 88.0, "internal_marks": 82.0, "predicted_gpa": 3.55, "status": "Excellent"}]})
        for pdf_bytes, title in ((student_pdf, b"OFFICIAL ACADEMIC TRANSCRIPT"), (roster_pdf, b"OFFICIAL CLASS PERFORMANCE ROSTER")):
            self.assertTrue(pdf_bytes.startswith(b"%PDF-"))
            mbox = re.search(rb"/MediaBox\s*\[\s*0\s+0\s+([0-9.]+)\s+([0-9.]+)\s*\]", pdf_bytes)
            self.assertIsNotNone(mbox)
            self.assertAlmostEqual(float(mbox.group(1)), 595.2756, places=1)
            self.assertTrue(841.0 <= float(mbox.group(2)) <= 842.5)
            self.assertIn(title, pdf_bytes)
            self.assertIn(b"Controller of Examinations", pdf_bytes)
            self.assertNotIn(b"0.058824 0.090196 0.164706", pdf_bytes)

        profile_src = (base_dir / "templates" / "panels" / "user_profile.html").read_text(encoding="utf-8")
        self.assertIn("Cloudinary Ready", profile_src)
        self.assertNotIn('truncate text-sm font-semibold text-[var(--text-primary)]">{% if cloudinary_ready %}', profile_src)

        sidebar_src = (base_dir / "templates" / "components" / "sidebar.html").read_text(encoding="utf-8")
        self.assertIn('id="mobile-sidebar-close" type="button" title="Hide menu" class="lg:hidden', sidebar_src)
        topbar_src = (base_dir / "templates" / "components" / "topbar.html").read_text(encoding="utf-8")
        self.assertNotIn('id="mobile-sidebar-toggle" type="button" class="lg:hidden', topbar_src)
        css_src = (base_dir / "static" / "css" / "global.css").read_text(encoding="utf-8")
        self.assertIn("@media print", css_src)
        self.assertIn("#ep-agent-dock-root", css_src)

        admin = self._login("ADMIN", "USR-1000", "admin@gmail.com", "System Administrator")
        notif_html = admin.get(reverse("panels:notifications_history")).content.decode("utf-8")
        self.assertIn('data-page-size="4"', notif_html)
        self.assertIn("Total 0 &middot; Unread 0 &middot; Replies 0", notif_html)
        self.assertIn("Admin Replies", notif_html)

        student = self._login("STUDENT", "USR-2001", "ayesha@edupredict.edu", "Ayesha Siddiqui", student_id="STD-2026-2001")
        st_dash = student.get(reverse("panels:student_dashboard")).content.decode("utf-8")
        for marker in ('data-student-tab="overview"', 'data-student-tab="courses"', 'data-chart-subtab="bars"', 'data-chart-subtab="contour"', 'id="student-subject-table"', 'id="ep-agent-dock-root"'):
            self.assertIn(marker, st_dash)

        analyst = self._login("ANALYST", "USR-1004", "analyst@edupredict.edu", "Data Analyst")
        health_html = analyst.get(reverse("panels:analyst_health")).content.decode("utf-8")
        for marker in ('data-health-tab="uploads"', 'data-health-tab="charts"', 'id="academic-contour-canvas"', 'id="health-demand-table"', 'id="health-dataset-logs-table"'):
            self.assertIn(marker, health_html)
