(function () {
  const PAGE_GUIDES = {
    '/admin-panel/': { title: 'Admin Overview', bullets: ['Monitor active students, teachers, high-risk counts, and open tickets.', 'Click any KPI card to jump or inspect live institutional trends.', 'Use the sidebar to manage Users, Courses, Help Tickets, and Settings.'], overview: 'View school-wide totals for active users, courses, student predictions, and open support tickets at a glance.', howTo: '1. Check top KPI cards for quick counts.\n2. Review charts and open support tickets.\n3. Use sidebar links for Users, Courses, or Logs.', faqs: [{ q: 'How often do dashboard numbers refresh?', a: 'KPI counts load live from MongoDB with short TTL caching.' }, { q: 'Where do I customize portal theme colors?', a: 'Open Portal Settings in the sidebar to launch the Live Theme Studio.' }] },
    '/admin-panel/users/': { title: 'User Management', bullets: ['Create, edit, approve, or toggle Admin, Teacher, Student, and Analyst accounts.', 'Pending Teacher signups show a badge until approved by an Admin.', 'Your own Admin row is locked against self-deletion or self-downgrade.'], overview: 'Create, edit, approve, or deactivate portal accounts safely.', howTo: '1. Click Add User to create an account.\n2. Search by name, email, or role.\n3. Approve pending Teachers or update user status.', faqs: [{ q: 'Why are delete controls hidden on my row?', a: 'Admins cannot delete or deactivate their own active account.' }, { q: 'How do pending Teachers gain access?', a: 'Click Approve on any pending Teacher row.' }] },
    '/admin-panel/courses/': { title: 'Course Management', bullets: ['Add or update courses, batch assignments, and instructors.', 'Course code prefixes automatically suggest matching departments.', 'Filter courses using the topbar Search bar or Ctrl+K.'], overview: 'Manage active courses, batch codes, and instructors across the portal.', howTo: '1. Click Add Course to register a subject.\n2. Sort or filter the 5-row table.\n3. Edit or archive courses anytime.', faqs: [{ q: 'Can I search courses by code?', a: 'Yes, type the code in Search to filter rows immediately.' }, { q: 'Can courses be assigned per batch?', a: 'Yes, specify the Batch value when creating or editing.' }] },
    '/admin-panel/tickets/': { title: 'Help & Support Tickets', bullets: ['Read feedback sent by Teachers, Students, and Analysts.', 'Reply directly to send an instant alert notification to the user.', 'Filter between All, Open, and Resolved tickets with 1 click.'], overview: 'Review support requests and send direct replies.', howTo: '1. Filter by All, Open, or Resolved.\n2. Click Reply to answer and mark resolved.\n3. Edit or delete replies anytime.', faqs: [{ q: 'Does replying notify the user?', a: 'Yes, a notification appears in their topbar bell automatically.' }, { q: 'Can a resolved ticket be reopened?', a: 'Yes, toggle its status back to Open.' }] },
    '/admin-panel/logs/': { title: 'Activity & Audit Logs', bullets: ['Inspect logins, user updates, password changes, and backups chronologically.', 'Click category KPI cards to filter audit events instantly.', 'Export filtered audit records to CSV whenever needed.'], overview: 'Track important system, security, and data events with timestamps.', howTo: '1. Filter by category or Search.\n2. Add manual system notes if needed.\n3. Download CSV audit snapshots.', faqs: [{ q: 'Are plain passwords logged?', a: 'Never; only safe action summaries are stored.' }, { q: 'Who can read audit logs?', a: 'Only Admin accounts have access.' }] },
    '/admin-panel/settings/': { title: 'Portal Settings', bullets: ['Configure school name, current term, passing GPA, and risk thresholds.', 'Launch Theme & Appearance Live Studio directly from Portal Settings.', 'Reset settings back to defaults safely anytime.'], overview: 'Configure portal defaults, risk thresholds, and institutional branding.', howTo: '1. Edit academic or ML risk rules.\n2. Open Live Studio to set official theme tokens.\n3. Save Settings to apply across panels.', faqs: [{ q: 'Who can customize theme presets?', a: 'Only Admins control full Theme Studio from Portal Settings.' }, { q: 'Do term changes affect PDFs?', a: 'Portal defaults keep term and risk rules consistent.' }] },
    '/teacher-panel/': { title: 'Teacher Dashboard', bullets: ['Track class attendance average, marks, and at-risk student alerts.', 'Upload 3-column CSV/Excel mark sheets or enter scores quickly.', 'Click High Risk or Needs Help KPIs to inspect flagged students.'], overview: 'Monitor class attendance, marks, and flagged risk students.', howTo: '1. Review class KPIs and risk charts.\n2. Jump to Upload Marks to update scores.\n3. Follow up on flagged students.', faqs: [{ q: 'Which file columns work for upload?', a: 'student_id, marks, and attendance in CSV or Excel.' }, { q: 'Can I switch Light and Dark mode?', a: 'Yes, use the topbar Light/Dark button anytime.' }] },
    '/teacher-panel/students/': { title: 'Class Student List', bullets: ['Filter students by batch, course, risk level, or Search bar.', 'Update student marks inline or send direct help alerts.', 'Export clean printable PDF rosters in one click.'], overview: 'Inspect student marks, attendance percentages, and predicted risk.', howTo: '1. Filter using dropdowns or Search.\n2. Click Update Marks to adjust scores.\n3. Export PDF rosters anytime.', faqs: [{ q: 'How are risk levels calculated?', a: 'Predicted from attendance and internal marks via ML models.' }, { q: 'Can I export a class list?', a: 'Yes, click Export PDF Roster.' }] },
    '/teacher-panel/alerts/': { title: 'High-Risk Alerts', bullets: ['View students flagged for low attendance or sudden score drops.', 'Click KPI cards to filter High Risk or Medium Risk warnings.', 'Send personalized guidance notifications directly to students.'], overview: 'Focus on struggling students needing early academic intervention.', howTo: '1. Review flagged students.\n2. Click Send Alert to message a student.\n3. Alerts update as fresh marks arrive.', faqs: [{ q: 'Do alerts reach the student bell?', a: 'Yes, unread alerts appear immediately in their portal.' }, { q: 'When do risk alerts clear?', a: 'When updated attendance/marks lower risk score.' }] },
    '/teacher-panel/ingest/': { title: 'Marks & Attendance Upload', bullets: ['Enter single-student scores cleanly with smart Student ID autocomplete.', 'Upload 3-column CSV/Excel files with a 1.2s cancelable grace window.', 'Download the sample CSV template if formatting a fresh sheet.'], overview: 'Enter individual marks or upload batch CSV/Excel mark sheets.', howTo: '1. Use Quick Entry for one student.\n2. Drop a CSV/Excel file for batch updates.\n3. Cancel within 1.2s if you dropped the wrong file.', faqs: [{ q: 'Which column names are accepted?', a: 'student_id (or roll_no), marks (or score), attendance (or att).' }, { q: 'What happens if I drop the wrong file?', a: 'Click Cancel in the toast within 1.2 seconds.' }] },
    '/student-panel/': { title: 'Student Home', bullets: ['View your current attendance, predicted GPA, credits, and batch rank.', 'Read tailored AI study tips to keep grades above passing targets.', 'Download your official PDF transcript from My Report Card.'], overview: 'See attendance, predicted GPA, standing, and recent alerts.', howTo: '1. Review your 4 academic KPI cards.\n2. Check comparison chart vs class average.\n3. Open My Report Card for PDF download.', faqs: [{ q: 'Who can view my marks?', a: 'Only you, your teachers, and Admins.' }, { q: 'How do I report a score issue?', a: 'Use Need Help in the sidebar to open a support ticket.' }] },
    '/student-panel/report/': { title: 'My Academic Report', bullets: ['Inspect subject-wise marks against class averages clearly.', 'Download an official Letter-Grade PDF transcript in 1 click.', 'Review your current risk badge and prediction standing.'], overview: 'Review subject performance, attendance, and downloadable PDF transcript.', howTo: '1. Inspect subject rows and charts.\n2. Click Download PDF Transcript.\n3. Send feedback if anything looks incorrect.', faqs: [{ q: 'Is the PDF official format?', a: 'Yes, generated cleanly with credits, GPA, and letter grades.' }, { q: 'What if a subject mark looks wrong?', a: 'Send a Help Ticket to your teacher or Admin.' }] },
    '/student-panel/tips/': { title: 'Study Tips & Guidance', bullets: ['Follow clear weekly targets tailored to your attendance and marks.', 'Keep attendance above your portal threshold to avoid warnings.', 'Review weak subjects before assessment deadlines.'], overview: 'Actionable weekly study recommendations tailored to your records.', howTo: '1. Check your current study goals.\n2. Focus on subjects below class average.\n3. Track attendance consistency weekly.', faqs: [{ q: 'Do tips refresh automatically?', a: 'Yes, whenever teachers upload new marks.' }, { q: 'What is the target attendance?', a: 'Usually 75% minimum or 85% recommended.' }] },
    '/student-panel/notifications/': { title: 'Alerts & Support', bullets: ['Read alerts from teachers and Admin replies to your tickets.', 'Submit a new support request right from this page or sidebar.', 'Notifications sync automatically in the topbar bell.'], overview: 'Read system notifications, teacher alerts, and support replies.', howTo: '1. Review recent alerts and Admin replies.\n2. Submit feedback when you need assistance.', faqs: [{ q: 'How quickly do replies appear?', a: 'The bell refreshes alerts automatically every 15 seconds.' }, { q: 'Can Admins see my ticket?', a: 'Yes, Admin Help Tickets receives it immediately.' }] },
    '/analyst-panel/': { title: 'Analyst Workbench', bullets: ['Upload educational CSV/Excel datasets for automated cleaning.', 'Run Ridge, RandomForest, and IsolationForest ML predictions.', 'Filter predicted records and export clean analytics CSVs.'], overview: 'Clean datasets, train fast ML pipelines, and explore predictions.', howTo: '1. Upload a dataset CSV/Excel.\n2. Click Run Predictions to evaluate risk & GPA.\n3. Review charts and flagged anomalies.', faqs: [{ q: 'Are missing values handled cleanly?', a: 'Yes, numeric gaps use median and categorical use mode.' }, { q: 'Is evaluation leakage-free?', a: 'Yes, train/test splits stay strictly separated.' }] },
    '/analyst-panel/accuracy/': { title: 'Model Accuracy & Health', bullets: ['Inspect MAE, RMSE, precision, recall, F1, and confusion matrices.', 'Check dataset label coverage before trusting accuracy claims.', 'Re-run predictions from Workbench after uploading fresh labeled data.'], overview: 'Compare evaluation metrics and dataset health diagnostics.', howTo: '1. Check dataset coverage status.\n2. Inspect confusion matrix & regression MAE.\n3. Retrain after new labeled cohorts arrive.', faqs: [{ q: 'Why do unlabelled records show partial metrics?', a: 'True labels are needed for supervised accuracy scoring.' }, { q: 'Which algorithms are used?', a: 'RandomForest, Ridge Regression, and IsolationForest.' }] },
    '/notifications/': { title: 'Notifications & Alert History', bullets: ['Browse all unread alerts, past notifications, and admin replies.', 'Filter between All, Unread, Read, and Admin Replies in one click.', 'Mark individual alerts or all notifications as read anytime.'], overview: 'View full alert history, academic warnings, and ticket replies.', howTo: '1. Switch filter tabs or use Search.\n2. Click Open to jump to the alert target page.\n3. Mark alerts read individually or all at once.', faqs: [{ q: 'Are read alerts preserved here?', a: 'Yes, read notifications stay accessible under Read History.' }, { q: 'Do Admin replies appear here?', a: 'Yes, check the Admin Replies filter tab.' }] },
    '/profile/': { title: 'My Profile & Security', bullets: ['Update your name, contact details, or profile picture safely.', 'Your assigned role badge stays read-only and protected.', 'Use Change Password to update credentials via secure modal.'], overview: 'Manage personal details, avatar, and password security.', howTo: '1. Edit contact details and save.\n2. Drop an image to update your avatar.\n3. Click Change Password for password updates.', faqs: [{ q: 'What image limit applies to avatars?', a: 'JPG, PNG, or WebP images up to 5 MB.' }, { q: 'Can I change my role here?', a: 'No, roles are protected by Admin RBAC.' }] }
  };
  const DEFAULT_GUIDE = {
    title: 'EduPredict Portal Guide',
    bullets: ['Use the collapsible sidebar to switch between your panel pages.', 'Press Ctrl+K anytime to filter records or jump to another page.', 'Use the Light/Dark toggle in the topbar for comfortable viewing.'],
    overview: 'Navigate your role-specific workspace using the sidebar, Search (Ctrl+K), and notification bell.',
    howTo: '1. Open sections from the left menu.\n2. Use Ctrl+K to filter tables or jump pages.\n3. Click ? anytime for quick tips.',
    faqs: [{ q: 'How do I report an issue?', a: 'Use Need Help in the sidebar to contact an Admin.' }, { q: 'Where can I update my password?', a: 'Open My Profile from the topbar or sidebar.' }]
  };

  let currentStep = 0, currentGuide = DEFAULT_GUIDE, globalsBound = false;
  const byId = (id) => document.getElementById(id);
  const normalizePath = (p) => { const s = String(p || '/'); return s.endsWith('/') ? s : s + '/'; };

  function renderInstantHelpPopover(guide) {
    if (byId('help-popover-title')) byId('help-popover-title').textContent = guide.title;
    const ul = byId('help-popover-bullets');
    if (ul) {
      ul.textContent = '';
      (guide.bullets || []).slice(0, 3).forEach((text) => {
        const li = document.createElement('li');
        li.textContent = text;
        ul.appendChild(li);
      });
    }
    const faqsEl = byId('help-popover-faqs');
    if (faqsEl) {
      faqsEl.textContent = '';
      (guide.faqs || []).slice(0, 2).forEach((item) => {
        const row = document.createElement('div');
        row.className = 'text-[11px] leading-snug';
        const q = document.createElement('p');
        q.className = 'font-semibold text-[var(--text-primary)]';
        q.textContent = item.q || '';
        const a = document.createElement('p');
        a.className = 'text-[var(--text-muted)]';
        a.textContent = item.a || '';
        row.append(q, a);
        faqsEl.appendChild(row);
      });
    }
  }

  function openInstantHelpPopover() {
    const pop = byId('instant-help-popover'), btn = byId('open-page-guide-btn');
    if (!pop) return;
    currentGuide = PAGE_GUIDES[normalizePath(window.location.pathname)] || DEFAULT_GUIDE;
    renderInstantHelpPopover(currentGuide);
    pop.classList.remove('hidden');
    if (btn) btn.setAttribute('aria-expanded', 'true');
  }

  function closeInstantHelpPopover() {
    const pop = byId('instant-help-popover'), btn = byId('open-page-guide-btn');
    if (pop) pop.classList.add('hidden');
    if (btn) btn.setAttribute('aria-expanded', 'false');
  }

  function toggleInstantHelpPopover(e) {
    if (e) e.stopPropagation();
    const pop = byId('instant-help-popover');
    if (!pop) { openPageGuideModal(); return; }
    if (pop.classList.contains('hidden')) openInstantHelpPopover();
    else closeInstantHelpPopover();
  }

  function renderFaqs(faqs) {
    const list = byId('page-guide-faq-list');
    if (!list) return;
    list.textContent = '';
    (Array.isArray(faqs) ? faqs : []).forEach((f, i) => {
      const box = document.createElement('div');
      box.className = 'rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-canvas)] overflow-hidden';
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'flex w-full items-center justify-between gap-2 px-3.5 py-2.5 text-left text-xs font-semibold text-[var(--text-primary)] hover:bg-[var(--bg-elevated)] transition-colors';
      const qSpan = document.createElement('span'); qSpan.textContent = f.q || '';
      const icon = document.createElement('i'); icon.className = 'fa-solid fa-chevron-down text-[10px] text-[var(--text-muted)] transition-transform';
      btn.append(qSpan, icon);
      const ans = document.createElement('div');
      ans.className = (i === 0 ? '' : 'hidden ') + 'border-t border-[var(--border-subtle)] px-3.5 py-2.5 text-xs leading-relaxed text-[var(--text-secondary)]';
      ans.textContent = f.a || '';
      if (i === 0) icon.classList.add('rotate-180');
      btn.addEventListener('click', () => { const hide = !ans.classList.contains('hidden'); ans.classList.toggle('hidden', hide); icon.classList.toggle('rotate-180', !hide); });
      box.append(btn, ans);
      list.appendChild(box);
    });
  }

  function renderStep(step) {
    currentStep = Math.max(0, Math.min(2, step));
    const headings = ['Step 1: Page Overview', 'Step 2: How to Use This Page', 'Step 3: Quick FAQs'];
    const texts = [currentGuide.overview, currentGuide.howTo, 'Browse common questions for this page below:'];
    if (byId('page-guide-step-heading')) byId('page-guide-step-heading').textContent = headings[currentStep];
    if (byId('page-guide-step-counter')) byId('page-guide-step-counter').textContent = 'Step ' + (currentStep + 1) + ' of 3';
    document.querySelectorAll('[data-guide-step]').forEach((pill) => {
      const active = Number(pill.getAttribute('data-guide-step')) === currentStep;
      pill.className = 'inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ' + (active ? 'bg-[var(--accent-primary)] text-white' : 'border border-[var(--border-subtle)] bg-[var(--bg-surface)] text-[var(--text-secondary)] hover:bg-[var(--bg-elevated)]');
    });
    const tw = byId('page-guide-typewriter');
    if (tw) tw.textContent = String(texts[currentStep] || '');
    const faqList = byId('page-guide-faq-list');
    if (faqList) faqList.classList.toggle('hidden', currentStep !== 2);
    if (currentStep === 2) renderFaqs(currentGuide.faqs);
    const prevBtn = byId('page-guide-prev-btn'), nextBtn = byId('page-guide-next-btn');
    if (prevBtn) prevBtn.disabled = currentStep === 0;
    if (nextBtn) nextBtn.textContent = currentStep === 2 ? 'Done' : 'Next';
  }

  function bindGuideControlsOnce() {
    const modal = byId('page-guide-modal');
    if (!modal || modal.dataset.guideBound === '1') return;
    modal.dataset.guideBound = '1';
    modal.querySelectorAll('[data-guide-step]').forEach((b) => b.addEventListener('click', () => renderStep(Number(b.getAttribute('data-guide-step')))));
    if (byId('page-guide-prev-btn')) byId('page-guide-prev-btn').addEventListener('click', () => { if (currentStep > 0) renderStep(currentStep - 1); });
    if (byId('page-guide-next-btn')) byId('page-guide-next-btn').addEventListener('click', () => { if (currentStep < 2) renderStep(currentStep + 1); else closePageGuideModal(); });
  }

  function openPageGuideModal() {
    const modal = byId('page-guide-modal');
    if (!modal) return;
    bindGuideControlsOnce();
    currentGuide = PAGE_GUIDES[normalizePath(window.location.pathname)] || DEFAULT_GUIDE;
    if (byId('page-guide-title')) byId('page-guide-title').textContent = currentGuide.title;
    modal.classList.remove('hidden'); modal.classList.add('flex'); modal.setAttribute('aria-hidden', 'false');
    if (typeof window.syncBodyScrollLock === 'function') window.syncBodyScrollLock();
    renderStep(0);
  }

  function closePageGuideModal() {
    const modal = byId('page-guide-modal');
    if (!modal) return;
    modal.classList.add('hidden'); modal.classList.remove('flex'); modal.setAttribute('aria-hidden', 'true');
    if (typeof window.syncBodyScrollLock === 'function') window.syncBodyScrollLock();
  }

  function renderCommandResults(query) {
    const box = byId('command-search-results');
    if (!box) return;
    const q = String(query || '').trim().toLowerCase();
    box.textContent = '';
    const entries = Array.from(document.querySelectorAll('#mobile-sidebar-drawer nav a[href]')).map((a) => ({
      label: a.textContent.trim(),
      href: a.getAttribute('href')
    })).concat([
      { href: '/notifications/', label: 'Notifications & Alert History' },
      { href: '/profile/', label: 'My Profile' }
    ]);
    const seen = new Set();
    let count = 0;
    entries.forEach(({ label, href }) => {
      if (!label || !href || seen.has(href)) return;
      if (q && label.toLowerCase().indexOf(q) === -1 && href.toLowerCase().indexOf(q) === -1) return;
      seen.add(href);
      count += 1;
      const item = document.createElement('a');
      item.href = href;
      item.className = 'flex items-center justify-between gap-3 rounded-xl px-3 py-2 text-xs text-[var(--text-primary)] hover:bg-[var(--bg-elevated)] transition-colors';
      const left = document.createElement('span');
      left.className = 'font-medium';
      left.textContent = label;
      const right = document.createElement('span');
      right.className = 'font-mono text-[11px] text-[var(--text-muted)]';
      right.textContent = href;
      item.append(left, right);
      item.addEventListener('click', closeCommandSearchModal);
      box.appendChild(item);
    });
    if (count === 0) {
      const empty = document.createElement('p');
      empty.className = 'px-3 py-4 text-center text-xs text-[var(--text-muted)]';
      empty.textContent = 'No matching pages found.';
      box.appendChild(empty);
    }
  }

  function openCommandSearchModal(initialQuery) {
    const modal = byId('command-search-modal'), input = byId('command-search-input');
    if (!modal) return;
    closeInstantHelpPopover();
    modal.classList.remove('hidden'); modal.classList.add('flex'); modal.setAttribute('aria-hidden', 'false');
    if (typeof window.syncBodyScrollLock === 'function') window.syncBodyScrollLock();
    const pageSearch = document.querySelector('input[data-table-search]');
    if (input) {
      if (typeof initialQuery === 'string' && initialQuery) input.value = initialQuery;
      else if (pageSearch && pageSearch.value) input.value = pageSearch.value;
      if (input.dataset.cmdBound !== '1') {
        input.dataset.cmdBound = '1';
        input.addEventListener('input', () => {
          const val = input.value;
          renderCommandResults(val);
          const ps = document.querySelector('input[data-table-search]');
          if (ps) { ps.value = val; ps.dispatchEvent(new Event('input', { bubbles: true })); }
        });
      }
      renderCommandResults(input.value);
      setTimeout(() => { input.focus(); input.select(); }, 20);
    }
  }

  function closeCommandSearchModal() {
    const modal = byId('command-search-modal');
    if (!modal) return;
    modal.classList.add('hidden'); modal.classList.remove('flex'); modal.setAttribute('aria-hidden', 'true');
    if (typeof window.syncBodyScrollLock === 'function') window.syncBodyScrollLock();
  }

  function syncTopbarScroll() {
    const topbar = document.querySelector('header.ep-topbar');
    if (topbar) topbar.classList.toggle('is-scrolled', window.scrollY > 10);
  }

  function initPageGuidesShell() {
    closeInstantHelpPopover();
    closeCommandSearchModal();
    syncTopbarScroll();
    if (globalsBound) return;
    globalsBound = true;
    window.addEventListener('scroll', syncTopbarScroll, { passive: true });
    document.addEventListener('click', (e) => {
      const pop = byId('instant-help-popover'), btn = byId('open-page-guide-btn');
      if (pop && !pop.classList.contains('hidden') && !pop.contains(e.target) && (!btn || !btn.contains(e.target))) closeInstantHelpPopover();
    });
    document.addEventListener('keydown', (e) => {
      if (e.isComposing || e.keyCode === 229) return;
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        openCommandSearchModal();
      } else if (e.key === 'Escape') {
        closeInstantHelpPopover();
        closeCommandSearchModal();
      }
    });
  }

  Object.assign(window, {
    toggleInstantHelpPopover,
    openInstantHelpPopover,
    closeInstantHelpPopover,
    openPageGuideModal,
    closePageGuideModal,
    openCommandSearchModal,
    closeCommandSearchModal,
    initPageGuidesShell
  });
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initPageGuidesShell);
  else initPageGuidesShell();
})();
