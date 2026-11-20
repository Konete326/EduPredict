(function () {
  const PAGE_GUIDES = {
    '/admin-panel/': { title: 'Admin Overview', overview: 'View school-wide totals for active users, courses, student predictions, and open support tickets at a glance.', howTo: '1. Check the top KPI cards for quick counts.\n2. Review the risk trend chart and recent activity.\n3. Use the quick action buttons or sidebar to jump into Users, Courses, or Tickets.', faqs: [{ q: 'How often do dashboard numbers refresh?', a: 'KPI counts and charts load live from MongoDB with short caching and update immediately after edits.' }, { q: 'Can I customize the dashboard colors?', a: 'Yes, open Theme & Colors in the sidebar to switch between Light, Dark, and custom accents.' }] },
    '/admin-panel/users/': { title: 'User Management', overview: 'Create, edit, approve, or deactivate Admin, Teacher, Student, and Analyst accounts.', howTo: '1. Click Add User to create a new account.\n2. Use Quick Search to find users by name, email, or role.\n3. Use row actions to edit details, approve teachers, or toggle active status.', faqs: [{ q: 'Why are some actions hidden on my own row?', a: 'For safety, admins cannot delete, deactivate, or downgrade their own active account.' }, { q: 'How do pending teachers get approved?', a: 'Click Approve on any pending teacher row to unlock their Teacher Panel access.' }] },
    '/admin-panel/courses/': { title: 'Course Management', overview: 'Manage active courses, batch codes, and assigned teachers across the portal.', howTo: '1. Click Add Course to register a new subject or batch.\n2. Search or sort the 5-row table to locate courses.\n3. Edit or remove courses using the row action buttons.', faqs: [{ q: 'Can courses be searched by code?', a: 'Yes, the Quick Search bar filters course codes, titles, and instructor names instantly.' }] },
    '/admin-panel/tickets/': { title: 'Help & Support Tickets', overview: 'Review feedback and help requests sent by teachers, students, and analysts, and send direct replies.', howTo: '1. Filter tickets by All, Open, or Resolved.\n2. Click Reply on any ticket to send a direct answer and optionally mark it Resolved.\n3. Use Edit Reply or Delete Reply to update your response anytime.', faqs: [{ q: 'Does the user get notified when I reply?', a: 'Yes, sending a reply automatically creates a targeted alert in the user notification bell.' }, { q: 'Can I reopen a resolved ticket?', a: 'Yes, click Reopen on any resolved ticket to move it back to Open.' }] },
    '/admin-panel/logs/': { title: 'Activity & Audit Logs', overview: 'Track important system actions including logins, user updates, password changes, and ticket replies.', howTo: '1. Browse the chronological log table.\n2. Use Quick Search to filter by actor, action type, or target.', faqs: [{ q: 'Are password changes logged?', a: 'Yes, security events are recorded with timestamps without ever storing plain-text passwords.' }] },
    '/admin-panel/settings/': { title: 'Portal Settings', overview: 'Configure portal-wide defaults, risk thresholds, and system preferences.', howTo: '1. Update the desired setting fields.\n2. Click Save Settings to apply changes across all panels.', faqs: [{ q: 'Who can access Portal Settings?', a: 'Only Admin accounts can view and modify portal-wide configuration.' }] },
    '/teacher-panel/': { title: 'Teacher Dashboard', overview: 'Monitor your class attendance, average marks, and students flagged as medium or high academic risk.', howTo: '1. Review class KPI cards and risk distribution.\n2. Use Quick Actions to add marks or upload a 3-column sheet.\n3. Follow up with flagged students in High-Risk Alerts.', faqs: [{ q: 'What format does sheet upload accept?', a: 'Upload a CSV or Excel file with 3 columns: student_id, marks, and attendance.' }] },
    '/teacher-panel/students/': { title: 'Class Student List', overview: 'Inspect individual student marks, attendance percentages, and predicted risk levels.', howTo: '1. Search or sort by marks, attendance, or risk.\n2. Open student details or update records as needed.', faqs: [{ q: 'How is risk level calculated?', a: 'EduPredict combines attendance and marks trends using the trained ML model.' }] },
    '/teacher-panel/alerts/': { title: 'High-Risk Alerts', overview: 'Focus on students who need early academic support due to low attendance or declining scores.', howTo: '1. Review flagged students sorted by urgency.\n2. Check their attendance and marks breakdown to plan an intervention.', faqs: [{ q: 'When do alerts clear?', a: 'Alerts update automatically once new marks or improved attendance are uploaded.' }] },
    '/teacher-panel/ingest/': { title: 'Marks & Attendance Upload', overview: 'Enter single-student marks quickly or upload a batch CSV/Excel file in seconds.', howTo: '1. For one student, fill in Student ID, Marks, and Attendance.\n2. For a class batch, drop a CSV/Excel file into the uploader (1.2s cancelable auto-upload).', faqs: [{ q: 'Can I cancel an accidental file drop?', a: 'Yes, a 1.2-second cancel button appears before the file is submitted.' }] },
    '/student-panel/': { title: 'Student Home', overview: 'See your current attendance, latest marks, academic standing, and recent alerts in one place.', howTo: '1. Check your KPI cards for attendance and score summary.\n2. Read personalized study tips or open your full report.', faqs: [{ q: 'Who can see my grades?', a: 'Only you, your assigned teachers, and portal admins can view your academic records.' }] },
    '/student-panel/report/': { title: 'My Academic Report', overview: 'Review your full subject performance, attendance history, and prediction insights.', howTo: '1. Inspect your score trends and status badges.\n2. Download or print your report when needed.', faqs: [{ q: 'What should I do if a mark looks wrong?', a: 'Send a help ticket or contact your teacher so they can verify and re-upload your score.' }] },
    '/student-panel/tips/': { title: 'Study Tips & Guidance', overview: 'Actionable study habits and attendance goals tailored to keep you on track.', howTo: '1. Read the recommended focus areas.\n2. Aim to keep attendance above 85% and review weak topics early.', faqs: [{ q: 'Are these tips updated automatically?', a: 'Yes, guidance adapts as your attendance and marks change.' }] },
    '/student-panel/notifications/': { title: 'My Notifications', overview: 'Read all system alerts, risk notices, and direct replies from admins to your feedback.', howTo: '1. Browse unread and past alerts.\n2. Check Admin Reply boxes for answers to your support tickets.', faqs: [{ q: 'Do notifications update in real time?', a: 'Yes, the topbar bell checks for new alerts every 15 seconds while the tab is active.' }] },
    '/analyst-panel/': { title: 'Analyst Workbench', overview: 'Clean student datasets, run ML risk predictions, and inspect model feature importance.', howTo: '1. Upload or select a dataset.\n2. Run the cleaning and prediction pipeline.\n3. Review accuracy metrics and exported summaries.', faqs: [{ q: 'Where are cleaned datasets logged?', a: 'Every run is recorded in MongoDB datasets_log for auditability.' }] },
    '/analyst-panel/accuracy/': { title: 'Model Accuracy & Metrics', overview: 'Compare precision, recall, F1 score, and confusion matrix results for the prediction engine.', howTo: '1. Inspect the evaluation charts and metric cards.\n2. Re-run training from the workbench after major dataset updates.', faqs: [{ q: 'Which model powers EduPredict?', a: 'EduPredict uses scikit-learn classification pipelines tuned on student attendance and marks.' }] },
    '/profile/': { title: 'My Profile & Security', overview: 'Update your display name, upload a profile photo, change your password, or browse quick FAQs.', howTo: '1. Edit your name and save.\n2. Drop a photo in the uploader to set your avatar.\n3. Click Change Password to update your credentials securely.', faqs: [{ q: 'What image size is allowed for avatars?', a: 'Upload JPG, PNG, or WebP images up to 5 MB.' }] }
  };
  const DEFAULT_GUIDE = { title: 'EduPredict Portal Guide', overview: 'Navigate your role-specific tools using the collapsible sidebar, topbar search, and live notification bell.', howTo: '1. Use the left sidebar to switch pages.\n2. Use Quick Search to filter tables.\n3. Click Theme & Colors anytime to personalize your workspace.', faqs: [{ q: 'How do I get help?', a: 'Use the Feedback or Help button to send a ticket to the Admin team.' }] };

  let currentStep = 0, currentGuide = DEFAULT_GUIDE, typeTimer = null, fullText = '';
  const byId = (id) => document.getElementById(id);
  const stopTyping = () => { if (typeTimer) { clearInterval(typeTimer); typeTimer = null; } };
  const normalizePath = (p) => { const s = String(p || '/'); return s.endsWith('/') ? s : s + '/'; };

  function finishTyping() {
    stopTyping();
    const tw = byId('page-guide-typewriter'), cur = byId('page-guide-cursor'), skip = byId('page-guide-skip-btn');
    if (tw) tw.textContent = fullText;
    if (cur) cur.classList.add('hidden');
    if (skip) skip.classList.add('hidden');
  }
  function startTyping(text) {
    stopTyping();
    fullText = String(text || '');
    const tw = byId('page-guide-typewriter'), cur = byId('page-guide-cursor'), skip = byId('page-guide-skip-btn');
    if (!tw) return;
    if ((window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) || !fullText) { finishTyping(); return; }
    tw.textContent = '';
    if (cur) cur.classList.remove('hidden');
    if (skip) skip.classList.remove('hidden');
    let idx = 0;
    typeTimer = setInterval(() => { idx += 2; tw.textContent = fullText.slice(0, idx); if (idx >= fullText.length) finishTyping(); }, 16);
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
    const faqList = byId('page-guide-faq-list');
    if (faqList) faqList.classList.toggle('hidden', currentStep !== 2);
    if (currentStep === 2) renderFaqs(currentGuide.faqs);
    const prevBtn = byId('page-guide-prev-btn'), nextBtn = byId('page-guide-next-btn');
    if (prevBtn) prevBtn.disabled = currentStep === 0;
    if (nextBtn) nextBtn.textContent = currentStep === 2 ? 'Done' : 'Next';
    startTyping(texts[currentStep]);
  }
  function bindGuideControlsOnce() {
    const modal = byId('page-guide-modal');
    if (!modal || modal.dataset.guideBound === '1') return;
    modal.dataset.guideBound = '1';
    modal.querySelectorAll('[data-guide-step]').forEach((b) => b.addEventListener('click', () => renderStep(Number(b.getAttribute('data-guide-step')))));
    if (byId('page-guide-skip-btn')) byId('page-guide-skip-btn').addEventListener('click', finishTyping);
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
    stopTyping();
    const modal = byId('page-guide-modal');
    if (!modal) return;
    modal.classList.add('hidden'); modal.classList.remove('flex'); modal.setAttribute('aria-hidden', 'true');
    if (typeof window.syncBodyScrollLock === 'function') window.syncBodyScrollLock();
  }
  window.openPageGuideModal = openPageGuideModal;
  window.closePageGuideModal = closePageGuideModal;
})();
