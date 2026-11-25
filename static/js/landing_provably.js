(function () {
  const CREDENTIALS = [
    {
      id: 'CERT-CS101-8821',
      program: 'BS / Computer Science',
      course: 'CS-101 · Intro to Computer Science',
      student: 'STD-2026-001 · Amina Tariq',
      gpa: '3.82',
      risk: 'LOW RISK',
      term: 'Fall 2026',
      issuer: 'Registrar & Dr. Ayesha Khan'
    },
    {
      id: 'CERT-DS301-4419',
      program: 'BS / Data Analytics',
      course: 'DS-301 · Applied Data Analytics',
      student: 'STD-2026-014 · Bilal Ahmed',
      gpa: '3.64',
      risk: 'LOW RISK',
      term: 'Fall 2026',
      issuer: 'Registrar & Prof. Zain Malik'
    },
    {
      id: 'CERT-SE210-1904',
      program: 'BS / Software Engineering',
      course: 'SE-210 · Software Engineering',
      student: 'STD-2026-029 · Sara Noor',
      gpa: '3.41',
      risk: 'LOW RISK',
      term: 'Fall 2026',
      issuer: 'Registrar & Dr. Omar Raza'
    }
  ];

  function initProvablyHero() {
    const hero = document.getElementById('cv-hero');
    const wave = document.getElementById('cv-wave');
    const toggle = document.getElementById('cv-verify-toggle');
    if (!hero || !wave || !toggle) return;

    const statsCard = document.getElementById('cv-stats-card');
    const statsState = document.getElementById('cv-stats-state');
    const statsCount = document.getElementById('cv-stats-count');
    const certStack = document.getElementById('cv-cert-stack');
    const certCards = Array.from(hero.querySelectorAll('.cv-cert-card'));
    const certPrev = document.getElementById('cv-cert-prev');
    const certNext = document.getElementById('cv-cert-next');
    const certLabel = document.getElementById('cv-cert-index');
    const waxSeal = document.getElementById('cv-wax-seal');
    const waxLabel = document.getElementById('cv-wax-label');
    const hintEl = document.getElementById('cv-hero-hint');

    const dialog = document.getElementById('cv-credential-dialog');
    const dlgPanel = document.getElementById('cv-credential-panel');
    const dlgClose = document.getElementById('cv-dialog-close');
    const dlgCopy = document.getElementById('cv-dialog-copy');
    const dlgVerify = document.getElementById('cv-dialog-verify');

    const reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const targetCount = parseInt((statsCount && statsCount.getAttribute('data-target-count')) || '62', 10) || 62;
    let verified = false;
    let frontIdx = 0;
    let userInteracted = false;
    let waveRaf = 0;
    let countRaf = 0;
    let autoTimer = 0;
    let activeDialogCred = CREDENTIALS[0];

    const animateCount = (fromVal, toVal, durationMs) => {
      if (!statsCount) return;
      if (countRaf) window.cancelAnimationFrame(countRaf);
      if (reduced || durationMs <= 0) {
        statsCount.textContent = String(toVal);
        return;
      }
      const start = performance.now();
      const step = (now) => {
        const t = Math.min(1, (now - start) / durationMs);
        const eased = 1 - Math.pow(1 - t, 3);
        statsCount.textContent = String(Math.round(fromVal + (toVal - fromVal) * eased));
        if (t < 1) countRaf = window.requestAnimationFrame(step);
      };
      countRaf = window.requestAnimationFrame(step);
    };

    const syncStampedUi = (isOn) => {
      toggle.setAttribute('aria-checked', isOn ? 'true' : 'false');
      toggle.style.setProperty('--cv-knob-x', isOn ? '110%' : '0%');
      if (statsCard) statsCard.classList.toggle('is-stamped', isOn);
      if (certStack) certStack.classList.toggle('is-stamped', isOn);
      if (waxSeal) waxSeal.classList.toggle('is-stamped', isOn);
      if (statsState) statsState.textContent = isOn ? 'verified' : 'tracked';
      if (waxLabel) waxLabel.textContent = isOn ? 'OFFICIALLY VERIFIED' : 'READY TO VERIFY';
      if (hintEl) hintEl.textContent = isOn ? 'Color verified · press V or click switch to reset' : 'Click or drag the switch, or press V to verify';
      if (dlgVerify) dlgVerify.textContent = isOn ? 'Verified Active' : 'Verify Live Record';
      hero.querySelectorAll('.cv-cert-stamp-text').forEach((el) => {
        el.textContent = isOn ? 'VERIFIED' : 'PENDING';
      });
      animateCount(isOn ? Math.max(0, Math.round(targetCount * 0.45)) : targetCount, isOn ? targetCount : Math.max(1, Math.round(targetCount * 0.45)), 650);
    };

    const runColorWave = (nextVerified) => {
      if (waveRaf) window.cancelAnimationFrame(waveRaf);
      const heroRect = hero.getBoundingClientRect();
      const togRect = toggle.getBoundingClientRect();
      const wx = Math.round(togRect.left - heroRect.left + togRect.width / 2);
      const wy = Math.round(togRect.top - heroRect.top + togRect.height / 2);
      hero.style.setProperty('--cv-wx', wx + 'px');
      hero.style.setProperty('--cv-wy', wy + 'px');

      const maxDx = Math.max(wx, heroRect.width - wx);
      const maxDy = Math.max(wy, heroRect.height - wy);
      const maxR = Math.ceil(Math.hypot(maxDx, maxDy) + 120);

      if (reduced) {
        wave.setAttribute('data-state', nextVerified ? 'clear' : 'mono');
        syncStampedUi(nextVerified);
        return;
      }

      wave.setAttribute('data-state', 'moving');
      const start = performance.now();
      const dur = 820;
      const tick = (now) => {
        const p = Math.min(1, (now - start) / dur);
        const eased = 1 - Math.pow(1 - p, 3);
        const r = nextVerified ? eased * maxR : (1 - eased) * maxR;
        hero.style.setProperty('--cv-r0', Math.max(0, r - 110).toFixed(0) + 'px');
        hero.style.setProperty('--cv-r1', (r + 40).toFixed(0) + 'px');
        if (p < 1) {
          waveRaf = window.requestAnimationFrame(tick);
        } else {
          wave.setAttribute('data-state', nextVerified ? 'clear' : 'mono');
          waveRaf = 0;
        }
      };
      waveRaf = window.requestAnimationFrame(tick);
      syncStampedUi(nextVerified);
    };

    const setVerified = (nextVal, manual) => {
      if (manual) {
        userInteracted = true;
        if (autoTimer) { window.clearTimeout(autoTimer); autoTimer = 0; }
      }
      const target = Boolean(nextVal);
      if (target === verified && wave.getAttribute('data-state') !== 'moving') {
        syncStampedUi(verified);
        return;
      }
      verified = target;
      runColorWave(verified);
    };

    let dragState = null;
    toggle.addEventListener('pointerdown', (e) => {
      userInteracted = true;
      if (autoTimer) { window.clearTimeout(autoTimer); autoTimer = 0; }
      const rect = toggle.getBoundingClientRect();
      dragState = { id: e.pointerId, startX: e.clientX, moved: false, maxMove: Math.max(12, rect.width * 0.52), baseOn: verified };
      toggle.setPointerCapture(e.pointerId);
    });
    toggle.addEventListener('pointermove', (e) => {
      if (!dragState || e.pointerId !== dragState.id) return;
      const dx = e.clientX - dragState.startX;
      if (Math.abs(dx) > 4) dragState.moved = true;
      const basePct = dragState.baseOn ? 110 : 0;
      const deltaPct = (dx / dragState.maxMove) * 110;
      const clamped = Math.max(0, Math.min(110, basePct + deltaPct));
      toggle.style.setProperty('--cv-knob-x', clamped.toFixed(1) + '%');
    });
    const endToggleDrag = (e) => {
      if (!dragState || e.pointerId !== dragState.id) return;
      const dx = e.clientX - dragState.startX;
      const moved = dragState.moved;
      const wasOn = dragState.baseOn;
      dragState = null;
      if (!moved) {
        setVerified(!wasOn, true);
      } else {
        const nextOn = wasOn ? dx > -12 : dx > 12;
        setVerified(nextOn, true);
      }
    };
    toggle.addEventListener('pointerup', endToggleDrag);
    toggle.addEventListener('pointercancel', endToggleDrag);

    const layoutStack = () => {
      const total = certCards.length;
      if (!total) return;
      certCards.forEach((card, i) => {
        const pos = ((i - frontIdx) % total + total) % total;
        card.setAttribute('data-pos', String(pos));
        card.setAttribute('tabindex', pos === 0 ? '0' : '-1');
      });
      if (certLabel) certLabel.textContent = String(frontIdx + 1) + ' / ' + String(total);
    };

    const cycleCert = (delta) => {
      const total = certCards.length;
      if (!total) return;
      frontIdx = ((frontIdx + delta) % total + total) % total;
      layoutStack();
    };

    const openDialog = (credIdx) => {
      if (!dialog) return;
      const cred = CREDENTIALS[credIdx] || CREDENTIALS[0];
      activeDialogCred = cred;
      const setField = (id, text) => { const el = document.getElementById(id); if (el) el.textContent = text; };
      setField('cv-dlg-id', cred.id);
      setField('cv-dlg-program', cred.program);
      setField('cv-dlg-course', cred.course);
      setField('cv-dlg-student', cred.student);
      setField('cv-dlg-gpa', cred.gpa);
      setField('cv-dlg-risk', cred.risk);
      setField('cv-dlg-term', cred.term);
      setField('cv-dlg-issuer', cred.issuer);
      if (dlgCopy) dlgCopy.textContent = 'Copy Verification ID';
      dialog.classList.remove('hidden');
      dialog.classList.add('flex');
      document.body.classList.add('modal-open');
    };

    const closeDialog = () => {
      if (!dialog) return;
      dialog.classList.add('hidden');
      dialog.classList.remove('flex');
      document.body.classList.remove('modal-open');
    };

    if (certStack && certCards.length) {
      let cDrag = null;
      certStack.addEventListener('pointerdown', (e) => {
        const card = e.target.closest('.cv-cert-card');
        if (!card) return;
        cDrag = { id: e.pointerId, x: e.clientX, dx: 0, card: card };
      });
      certStack.addEventListener('pointermove', (e) => {
        if (!cDrag || e.pointerId !== cDrag.id) return;
        cDrag.dx = e.clientX - cDrag.x;
        if (Math.abs(cDrag.dx) > 6 && cDrag.card.getAttribute('data-pos') === '0') {
          cDrag.card.style.transform = 'translate3d(' + (cDrag.dx * 0.45).toFixed(0) + 'px, 0, 0) rotate(' + (cDrag.dx * 0.03).toFixed(1) + 'deg)';
        }
      });
      const finishCardDrag = (e) => {
        if (!cDrag || e.pointerId !== cDrag.id) return;
        const { dx, card } = cDrag;
        cDrag = null;
        card.style.transform = '';
        if (Math.abs(dx) >= 52) {
          cycleCert(dx < 0 ? 1 : -1);
        } else if (Math.abs(dx) < 8) {
          if (card.getAttribute('data-pos') === '0') {
            openDialog(parseInt(card.getAttribute('data-cert-idx') || '0', 10));
          } else {
            cycleCert(1);
          }
        }
      };
      certStack.addEventListener('pointerup', finishCardDrag);
      certStack.addEventListener('pointercancel', () => { if (cDrag) { cDrag.card.style.transform = ''; cDrag = null; } });
      certStack.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowRight') { e.preventDefault(); cycleCert(1); }
        else if (e.key === 'ArrowLeft') { e.preventDefault(); cycleCert(-1); }
        else if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openDialog(frontIdx); }
      });
    }

    if (certPrev) certPrev.addEventListener('click', () => cycleCert(-1));
    if (certNext) certNext.addEventListener('click', () => cycleCert(1));

    if (dialog) {
      let backdropDown = false;
      dialog.addEventListener('pointerdown', (e) => { backdropDown = e.target === dialog; });
      dialog.addEventListener('click', (e) => { if (backdropDown && e.target === dialog) closeDialog(); backdropDown = false; });
      if (dlgClose) dlgClose.addEventListener('click', closeDialog);
      if (dlgVerify) dlgVerify.addEventListener('click', () => setVerified(!verified, true));
      if (dlgCopy) {
        dlgCopy.addEventListener('click', () => {
          const text = activeDialogCred.id + ' · ' + activeDialogCred.course + ' · GPA ' + activeDialogCred.gpa;
          if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(text).catch(() => {});
          }
          dlgCopy.textContent = 'Copied to Clipboard';
        });
      }
      if (dlgPanel) dlgPanel.addEventListener('click', (e) => e.stopPropagation());
    }

    if (waxSeal) {
      waxSeal.addEventListener('click', () => waxSeal.classList.toggle('is-flipped'));
      waxSeal.addEventListener('pointermove', (e) => {
        const r = waxSeal.getBoundingClientRect();
        waxSeal.style.setProperty('--sx', Math.round(((e.clientX - r.left) / r.width) * 100) + '%');
        waxSeal.style.setProperty('--sy', Math.round(((e.clientY - r.top) / r.height) * 100) + '%');
      });
    }

    let glintRaf = 0;
    hero.addEventListener('pointermove', (e) => {
      if (glintRaf) return;
      glintRaf = window.requestAnimationFrame(() => {
        glintRaf = 0;
        const r = hero.getBoundingClientRect();
        hero.style.setProperty('--cv-mx', Math.round(e.clientX - r.left) + 'px');
        hero.style.setProperty('--cv-my', Math.round(e.clientY - r.top) + 'px');
      });
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        if (dialog && !dialog.classList.contains('hidden')) closeDialog();
        if (waxSeal && waxSeal.classList.contains('is-flipped')) waxSeal.classList.remove('is-flipped');
        return;
      }
      const tag = document.activeElement && document.activeElement.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.key === 'v' || e.key === 'V') setVerified(!verified, true);
    });

    layoutStack();
    syncStampedUi(false);
    wave.setAttribute('data-state', 'mono');
    if (!reduced) {
      autoTimer = window.setTimeout(() => {
        if (!userInteracted && !verified) setVerified(true, false);
      }, 2600);
    }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initProvablyHero);
  else initProvablyHero();
})();
