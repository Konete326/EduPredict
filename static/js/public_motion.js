(function () {
  function initPublicHeader() {
    const header = document.getElementById('ep-public-header');
    const toggleBtn = document.getElementById('ep-public-menu-btn');
    const mobileMenu = document.getElementById('ep-public-mobile-menu');
    const iconOpen = document.getElementById('ep-menu-icon-open');
    const iconClose = document.getElementById('ep-menu-icon-close');
    if (header) {
      const onScroll = () => header.classList.toggle('shadow-sm', window.scrollY > 10);
      window.addEventListener('scroll', onScroll, { passive: true });
      onScroll();
    }
    if (!toggleBtn || !mobileMenu) return;
    const setOpen = (open) => {
      mobileMenu.classList.toggle('hidden', !open);
      mobileMenu.classList.toggle('flex', open);
      toggleBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
      if (iconOpen) iconOpen.classList.toggle('hidden', open);
      if (iconClose) iconClose.classList.toggle('hidden', !open);
      document.body.style.overflow = open ? 'hidden' : '';
    };
    toggleBtn.addEventListener('click', () => setOpen(mobileMenu.classList.contains('hidden')));
    mobileMenu.querySelectorAll('a').forEach((a) => a.addEventListener('click', () => setOpen(false)));
    window.addEventListener('resize', () => { if (window.innerWidth >= 768) setOpen(false); });
  }

  function initHeroKineticGrid() {
    const canvas = document.getElementById('ep-hero-kinetic-grid');
    if (!canvas || typeof canvas.getContext !== 'function') return;
    const wrap = canvas.parentElement;
    let mx = -999, my = -999, raf = 0;
    const draw = () => {
      raf = 0;
      const w = Math.max(320, (wrap && wrap.clientWidth) || window.innerWidth);
      const h = Math.max(320, (wrap && wrap.clientHeight) || 520);
      const dpr = Math.min(2, window.devicePixelRatio || 1);
      canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr);
      const ctx = canvas.getContext('2d');
      if (!ctx) return;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, w, h);
      const dark = document.documentElement.classList.contains('dark');
      const accent = getComputedStyle(document.documentElement).getPropertyValue('--accent-primary').trim() || '#2563eb';
      ctx.strokeStyle = dark ? 'rgba(255,255,255,0.055)' : 'rgba(15,23,42,0.055)';
      ctx.lineWidth = 1;
      const step = 52;
      for (let x = 0; x <= w; x += step) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke(); }
      for (let y = 0; y <= h; y += step) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }
      for (let x = 26; x <= w; x += step) {
        for (let y = 26; y <= h; y += step) {
          const dist = Math.hypot(x - mx, y - my);
          const near = dist < 170;
          ctx.fillStyle = near ? accent : (dark ? 'rgba(255,255,255,0.08)' : 'rgba(15,23,42,0.08)');
          ctx.globalAlpha = near ? Math.max(0.15, 0.55 * (1 - dist / 170)) : 1;
          ctx.beginPath(); ctx.arc(x, y, near ? 1.8 : 0.9, 0, Math.PI * 2); ctx.fill();
        }
      }
      ctx.globalAlpha = 1;
    };
    const schedule = () => { if (!raf) raf = window.requestAnimationFrame(draw); };
    if (wrap) {
      wrap.addEventListener('mousemove', (e) => { const r = wrap.getBoundingClientRect(); mx = e.clientX - r.left; my = e.clientY - r.top; schedule(); });
      wrap.addEventListener('mouseleave', () => { mx = -999; my = -999; schedule(); });
    }
    window.addEventListener('resize', schedule);
    window.addEventListener('themeChanged', schedule);
    draw();
  }

  function initRolePreviewTabs() {
    const tabs = Array.from(document.querySelectorAll('[data-hero-role-tab]'));
    const panels = Array.from(document.querySelectorAll('[data-hero-role-panel]'));
    if (!tabs.length) return;
    const activate = (key) => {
      tabs.forEach((b) => {
        const on = b.getAttribute('data-hero-role-tab') === key;
        b.setAttribute('aria-selected', on ? 'true' : 'false');
        b.classList.toggle('bg-[var(--accent-primary)]', on);
        b.classList.toggle('text-white', on);
        b.classList.toggle('text-[var(--text-secondary)]', !on);
      });
      panels.forEach((p) => p.classList.toggle('hidden', p.getAttribute('data-hero-role-panel') !== key));
    };
    tabs.forEach((b) => b.addEventListener('click', () => activate(b.getAttribute('data-hero-role-tab'))));
  }

  function initMotionPlayer() {
    const root = document.getElementById('ep-motion-player');
    if (!root) return;
    const beats = Array.from(root.querySelectorAll('[data-motion-beat]'));
    const scenes = Array.from(root.querySelectorAll('[data-motion-scene]'));
    const playBtn = document.getElementById('ep-motion-play');
    const playIcon = document.getElementById('ep-motion-play-icon');
    const progressEl = document.getElementById('ep-motion-progress');
    const timeEl = document.getElementById('ep-motion-time');
    if (!beats.length || !scenes.length) return;
    const reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const totalMs = 8000;
    let playing = !reduced, idx = 0, elapsed = 0, lastTs = 0, raf = 0;

    const showScene = (nextIdx) => {
      idx = ((nextIdx % scenes.length) + scenes.length) % scenes.length;
      beats.forEach((b, i) => {
        const on = i === idx;
        b.setAttribute('aria-pressed', on ? 'true' : 'false');
        b.classList.toggle('border-[var(--accent-primary)]', on);
        b.classList.toggle('bg-[var(--accent-soft)]', on);
        b.classList.toggle('border-[var(--border-subtle)]', !on);
      });
      scenes.forEach((s, i) => s.classList.toggle('hidden', i !== idx));
    };

    const syncUi = () => {
      const pct = Math.min(100, (elapsed / totalMs) * 100);
      if (progressEl) progressEl.style.width = pct.toFixed(1) + '%';
      if (timeEl) {
        const sec = Math.floor(elapsed / 1000);
        const frame = Math.floor((elapsed % 1000) / 33.3) % 30;
        timeEl.textContent = '00:0' + sec + ' · f' + String(frame).padStart(2, '0');
      }
      if (playIcon) {
        playIcon.classList.toggle('fa-pause', playing);
        playIcon.classList.toggle('fa-play', !playing);
      }
    };

    const tick = (ts) => {
      if (!playing) { raf = 0; return; }
      if (!lastTs) lastTs = ts;
      elapsed = (elapsed + Math.min(100, ts - lastTs)) % totalMs;
      lastTs = ts;
      const targetIdx = Math.min(scenes.length - 1, Math.floor((elapsed / totalMs) * scenes.length));
      if (targetIdx !== idx) showScene(targetIdx);
      syncUi();
      raf = window.requestAnimationFrame(tick);
    };

    if (playBtn) {
      playBtn.addEventListener('click', () => {
        playing = !playing;
        lastTs = 0;
        syncUi();
        if (playing && !raf) raf = window.requestAnimationFrame(tick);
      });
    }
    beats.forEach((b, i) => {
      b.addEventListener('click', () => {
        elapsed = Math.round((i / scenes.length) * totalMs);
        showScene(i);
        syncUi();
      });
    });
    showScene(0);
    syncUi();
    if (playing) raf = window.requestAnimationFrame(tick);
  }

  function boot() {
    initPublicHeader();
    initHeroKineticGrid();
    initRolePreviewTabs();
    initMotionPlayer();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
