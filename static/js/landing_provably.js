(function () {
  const STORY = 2600;
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
  const lerp = (a, b, t) => a + (b - a) * t;
  const smooth = (t) => t * t * (3 - 2 * t);

  const TAB_DATA = {
    'ai-agents': {
      badge: '4 Ephemeral AI Agents',
      title: 'Role-aware campus assistants',
      desc: 'Zero saved chat clutter. Auto-handoff across academic coaching, ML diagnostics, course ops, and support.',
      items: [
        { key: 'educoach', label: 'EduCoach AI', role: 'Student Mentor', route: '/student-panel/', summary: 'Interprets predicted GPA, course marks, and attendance thresholds into clear study priorities.' },
        { key: 'pulseml', label: 'PulseML AI', role: 'ML Analyst', route: '/analyst-panel/accuracy/', summary: 'Monitors Ridge, RandomForest, and IsolationForest runs plus live LMS stream accuracy.' },
        { key: 'courseops', label: 'CourseOps AI', role: 'Faculty & Admin', route: '/teacher-panel/ingest/', summary: 'Guides 3-column CSV/Excel marks uploads, course mapping, and student risk alerts.' },
        { key: 'helpdesk', label: 'HelpDesk AI', role: 'Support Triage', route: '/contact/', summary: 'Routes staff approval questions and portal access inquiries directly to Admin tickets.' }
      ]
    },
    'role-panels': {
      badge: 'Strict Role Isolation',
      title: '4 Purpose-Built Role Panels',
      desc: 'Every user sees only their authorized workspace, KPIs, and A4 PDF tools.',
      items: [
        { key: 'admin', label: 'Admin Panel', role: 'Governance', route: '/admin-panel/', summary: 'Creates courses, maps Teachers, approves Teacher & Analyst signups, and handles support tickets.' },
        { key: 'teacher', label: 'Teacher Panel', role: 'Marks & Alerts', route: '/teacher-panel/', summary: 'Uploads .csv/.xlsx/.json/.tsv marks sheets, auto-provisions students, and sends alerts.' },
        { key: 'student', label: 'Student Panel', role: 'Forecast & PDF', route: '/student-panel/', summary: 'Tracks live GPA forecasts, attendance warnings, study tips, and monochrome A4 transcripts.' },
        { key: 'analyst', label: 'Analyst Panel', role: 'ML Pipeline', route: '/analyst-panel/', summary: 'Cleans batch datasets, runs Scikit-Learn predictions, and audits anomaly flags.' }
      ]
    }
  };

  function initFlooStory() {
    const story = document.getElementById('floo-story');
    const sticky = document.getElementById('floo-sticky');
    const stage = document.getElementById('floo-stage');
    if (!story || !sticky || !stage) return;

    const fold = document.getElementById('floo-fold');
    const grass = document.getElementById('floo-grass');
    const crm = document.getElementById('floo-crm');
    const panel = document.getElementById('floo-panel');
    const cue = document.getElementById('floo-scroll-cue');

    const reducedMq = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;
    const isReduced = () => Boolean(reducedMq && reducedMq.matches);
    const isMobile = () => window.innerWidth < 768;

    const scaleStage = () => {
      if (isReduced() || isMobile()) {
        stage.style.transform = '';
        return;
      }
      const rect = sticky.getBoundingClientRect();
      const s = Math.min(rect.width / 1440, rect.height / 1036);
      stage.style.transform = 'scale(' + Math.max(0.45, Math.min(1.12, s)).toFixed(4) + ')';
    };

    const applyProgress = (p) => {
      story.style.setProperty('--floo-p', p.toFixed(4));
      if (isReduced() || isMobile()) {
        if (fold) { fold.style.transform = ''; fold.style.opacity = '1'; }
        if (grass) { grass.style.transform = ''; grass.style.opacity = '0'; }
        if (crm) { crm.style.transform = ''; crm.style.opacity = '1'; }
        if (panel) { panel.style.transform = ''; panel.style.opacity = '1'; }
        if (cue) cue.style.opacity = '0';
        return;
      }

      const foldT = smooth(clamp(p / 0.36, 0, 1));
      if (fold) {
        fold.style.transform = 'translate3d(0, ' + lerp(0, -140, foldT).toFixed(1) + 'px, 0) scale(' + lerp(1, 0.9, foldT).toFixed(3) + ')';
        fold.style.opacity = lerp(1, 0, clamp(p / 0.3, 0, 1)).toFixed(3);
      }

      const grassT = smooth(clamp((p - 0.04) / 0.36, 0, 1));
      if (grass) {
        grass.style.transform = 'translate3d(0, ' + lerp(0, 260, grassT).toFixed(1) + 'px, 0)';
        grass.style.opacity = lerp(1, 0.08, grassT).toFixed(3);
      }

      const crmEnter = smooth(clamp((p - 0.14) / 0.32, 0, 1));
      const crmShift = smooth(clamp((p - 0.48) / 0.28, 0, 1));
      if (crm) {
        const crmY = lerp(520, 48, crmEnter);
        const crmX = lerp(268, 0, crmShift);
        const crmS = lerp(0.92, 1, crmEnter);
        crm.style.transform = 'translate3d(' + crmX.toFixed(1) + 'px, ' + crmY.toFixed(1) + 'px, 0) scale(' + crmS.toFixed(3) + ')';
        crm.style.opacity = clamp((p - 0.12) / 0.16, 0, 1).toFixed(3);
      }

      const panelEnter = smooth(clamp((p - 0.46) / 0.32, 0, 1));
      if (panel) {
        const pY = lerp(260, 48, panelEnter);
        const pX = lerp(64, 0, panelEnter);
        panel.style.transform = 'translate3d(' + pX.toFixed(1) + 'px, ' + pY.toFixed(1) + 'px, 0)';
        panel.style.opacity = panelEnter.toFixed(3);
      }

      if (cue) cue.style.opacity = lerp(1, 0, clamp(p / 0.12, 0, 1)).toFixed(3);
    };

    const updateFromScroll = () => {
      if (isReduced() || isMobile()) {
        applyProgress(1);
        return;
      }
      const rect = story.getBoundingClientRect();
      const totalTravel = Math.max(1, Math.min(STORY, story.offsetHeight - sticky.offsetHeight));
      const p = clamp(-rect.top / totalTravel, 0, 1);
      applyProgress(p);
    };

    if (typeof ResizeObserver === 'function') {
      const ro = new ResizeObserver(() => {
        scaleStage();
        updateFromScroll();
      });
      ro.observe(sticky);
    }
    window.addEventListener('resize', () => { scaleStage(); updateFromScroll(); }, { passive: true });
    if (!isReduced()) {
      window.addEventListener('scroll', updateFromScroll, { passive: true });
    }
    if (reducedMq && typeof reducedMq.addEventListener === 'function') {
      reducedMq.addEventListener('change', () => { scaleStage(); updateFromScroll(); });
    }

    scaleStage();
    updateFromScroll();
  }

  function initShowcaseTabs() {
    const root = document.getElementById('floo-panel');
    if (!root) return;
    const tabs = Array.from(root.querySelectorAll('[data-floo-tab]'));
    const subWrap = document.getElementById('floo-sub-list');
    const picBadge = document.getElementById('floo-pic-badge');
    const picTitle = document.getElementById('floo-pic-title');
    const picRoute = document.getElementById('floo-pic-route');
    const picDesc = document.getElementById('floo-pic-desc');
    const panelTitle = document.getElementById('floo-panel-title');
    const panelDesc = document.getElementById('floo-panel-desc');

    let activeTab = 'ai-agents';
    let activeItemIdx = 0;

    const renderSub = () => {
      const cfg = TAB_DATA[activeTab] || TAB_DATA['ai-agents'];
      if (panelTitle) panelTitle.textContent = cfg.title;
      if (panelDesc) panelDesc.textContent = cfg.desc;
      if (subWrap) {
        subWrap.innerHTML = '';
        cfg.items.forEach((item, idx) => {
          const btn = document.createElement('button');
          btn.type = 'button';
          btn.className = 'floo-sub-btn rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-canvas)] px-3 py-2 text-left transition-colors cursor-pointer hover:border-[var(--accent-primary)]';
          btn.setAttribute('aria-pressed', idx === activeItemIdx ? 'true' : 'false');
          const top = document.createElement('p');
          top.className = 'text-xs font-semibold text-[var(--text-primary)]';
          top.textContent = item.label;
          const sub = document.createElement('p');
          sub.className = 'text-[11px] text-[var(--text-muted)]';
          sub.textContent = item.role;
          btn.append(top, sub);
          btn.addEventListener('click', () => {
            activeItemIdx = idx;
            renderSub();
          });
          subWrap.appendChild(btn);
        });
      }
      const chosen = cfg.items[activeItemIdx] || cfg.items[0];
      if (picBadge) picBadge.textContent = chosen.role;
      if (picTitle) picTitle.textContent = chosen.label;
      if (picRoute) picRoute.textContent = chosen.route;
      if (picDesc) picDesc.textContent = chosen.summary;
    };

    tabs.forEach((btn) => {
      btn.addEventListener('click', () => {
        activeTab = btn.getAttribute('data-floo-tab') || 'ai-agents';
        activeItemIdx = 0;
        tabs.forEach((b) => b.setAttribute('aria-selected', b === btn ? 'true' : 'false'));
        renderSub();
      });
    });

    renderSub();
  }

  function boot() {
    initFlooStory();
    initShowcaseTabs();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
