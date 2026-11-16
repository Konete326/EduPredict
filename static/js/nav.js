(function () {
  const CACHE_PREFIX = 'ep_page_cache:';
  const CACHE_TTL_MS = 45000;
  const GROUPS_KEY = 'edupredict_nav_groups';
  const ACTIVE_CLS = ['bg-[var(--accent-soft)]', 'text-[var(--accent-primary)]', 'font-medium'];
  const INACTIVE_CLS = ['text-[var(--text-secondary)]', 'hover:bg-[var(--bg-elevated)]', 'hover:text-[var(--text-primary)]'];
  const memCache = new Map();
  const inFlight = new Map();
  let navId = 0;

  const normPath = (p) => (p && p.length > 1 && p.endsWith('/') ? p.slice(0, -1) : (p || '/'));
  const cacheKey = (url) => url.pathname + url.search;

  function readGroupPrefs() {
    try { return JSON.parse(localStorage.getItem(GROUPS_KEY) || '{}') || {}; } catch (e) { return {}; }
  }
  function writeGroupPrefs(prefs) {
    try { localStorage.setItem(GROUPS_KEY, JSON.stringify(prefs)); } catch (e) {}
  }
  function applyGroupState(key, expanded) {
    const btn = document.querySelector('[data-nav-group-toggle="' + key + '"]');
    const items = document.querySelector('[data-nav-group-body="' + key + '"], [data-nav-group-items="' + key + '"]');
    const chevron = btn ? btn.querySelector('.nav-group-chevron, [data-nav-chevron]') : null;
    if (btn) btn.setAttribute('aria-expanded', expanded ? 'true' : 'false');
    if (items) items.classList.toggle('hidden', !expanded);
    if (chevron) chevron.classList.toggle('-rotate-90', !expanded);
  }
  function initNavGroups() {
    const prefs = readGroupPrefs();
    document.querySelectorAll('[data-nav-group-toggle]').forEach((btn) => {
      const key = btn.getAttribute('data-nav-group-toggle');
      if (!key) return;
      applyGroupState(key, prefs[key] !== false);
      if (btn.dataset.navGroupBound === '1') return;
      btn.dataset.navGroupBound = '1';
      btn.addEventListener('click', () => {
        const cur = readGroupPrefs();
        const nextExpanded = btn.getAttribute('aria-expanded') !== 'true';
        cur[key] = nextExpanded;
        writeGroupPrefs(cur);
        applyGroupState(key, nextExpanded);
      });
    });
  }

  function readCache(key) {
    const now = Date.now();
    const mem = memCache.get(key);
    if (mem) {
      if (now - mem.ts <= CACHE_TTL_MS) return mem.html;
      memCache.delete(key);
    }
    try {
      const raw = sessionStorage.getItem(CACHE_PREFIX + key);
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed.html === 'string' && (now - parsed.ts <= CACHE_TTL_MS)) {
        memCache.set(key, parsed);
        return parsed.html;
      }
      sessionStorage.removeItem(CACHE_PREFIX + key);
    } catch (e) {}
    return null;
  }
  function writeCache(key, html) {
    const entry = { ts: Date.now(), html: html };
    memCache.set(key, entry);
    try { sessionStorage.setItem(CACHE_PREFIX + key, JSON.stringify(entry)); } catch (e) {}
  }
  function clearPageCache() {
    memCache.clear();
    try {
      const removeKeys = [];
      for (let i = 0; i < sessionStorage.length; i += 1) {
        const k = sessionStorage.key(i);
        if (k && k.startsWith(CACHE_PREFIX)) removeKeys.push(k);
      }
      removeKeys.forEach((k) => sessionStorage.removeItem(k));
    } catch (e) {}
  }

  function getSpaUrl(link) {
    if (!link || link.hasAttribute('data-coming-soon') || link.hasAttribute('data-no-spa') || link.hasAttribute('download')) return null;
    if (link.target && link.target !== '_self') return null;
    const raw = (link.getAttribute('href') || '').trim();
    if (!raw || raw.startsWith('#') || raw.startsWith('mailto:') || raw.startsWith('tel:') || raw.startsWith('javascript:')) return null;
    let url;
    try { url = new URL(link.href, window.location.href); } catch (e) { return null; }
    if (url.origin !== window.location.origin) return null;
    if (url.pathname.startsWith('/auth') || url.pathname.includes('/backup/') || url.searchParams.has('export')) return null;
    return url;
  }

  function syncActiveSidebarLink(targetUrl) {
    const links = Array.from(document.querySelectorAll('#mobile-sidebar-drawer nav a[href]:not([data-coming-soon])'));
    const targetPath = normPath(targetUrl.pathname), targetHash = targetUrl.hash || '';
    const hasHashMatch = Boolean(targetHash) && links.some((a) => {
      try { const u = new URL(a.href, window.location.href); return normPath(u.pathname) === targetPath && u.hash === targetHash; } catch (e) { return false; }
    });
    links.forEach((a) => {
      let active = false;
      try {
        const u = new URL(a.href, window.location.href);
        active = hasHashMatch ? (normPath(u.pathname) === targetPath && u.hash === targetHash) : (normPath(u.pathname) === targetPath && !u.hash);
      } catch (e) {}
      ACTIVE_CLS.forEach((c) => a.classList.toggle(c, active));
      INACTIVE_CLS.forEach((c) => a.classList.toggle(c, !active));
    });
  }

  function fetchPageHtml(url, bypassCache) {
    const key = cacheKey(url);
    if (!bypassCache) {
      const cached = readCache(key);
      if (cached) return Promise.resolve({ html: cached, finalUrl: url.href });
    }
    if (!bypassCache && inFlight.has(key)) return inFlight.get(key);
    const req = fetch(url.href, { method: 'GET', credentials: 'same-origin', headers: { 'X-Requested-With': 'EduPredict-SPA' } })
      .then((resp) => {
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        const dest = new URL(resp.url, window.location.href);
        if (dest.pathname.startsWith('/auth')) return { redirect: resp.url };
        return resp.text().then((html) => {
          writeCache(cacheKey(dest), html);
          if (key !== cacheKey(dest)) writeCache(key, html);
          return { html: html, finalUrl: resp.url };
        });
      })
      .finally(() => { inFlight.delete(key); });
    if (!bypassCache) inFlight.set(key, req);
    return req;
  }

  function runExtraScripts(nextExtra) {
    const curExtra = document.getElementById('page-extra-js');
    if (!curExtra) return;
    curExtra.innerHTML = '';
    if (!nextExtra) return;
    Array.from(nextExtra.childNodes).forEach((node) => {
      if (node.nodeType === 1 && node.tagName === 'SCRIPT') {
        const type = (node.getAttribute('type') || '').trim().toLowerCase();
        if (type && type !== 'text/javascript' && type !== 'application/javascript' && type !== 'module') {
          curExtra.appendChild(document.importNode(node, true));
          return;
        }
        const s = document.createElement('script');
        Array.from(node.attributes).forEach((attr) => s.setAttribute(attr.name, attr.value));
        s.textContent = node.textContent;
        curExtra.appendChild(s);
        return;
      }
      curExtra.appendChild(document.importNode(node, true));
    });
  }

  function scrollForUrl(url) {
    if (url.hash) {
      const el = document.getElementById(url.hash.slice(1));
      if (el) { el.scrollIntoView({ behavior: 'smooth', block: 'start' }); return; }
    }
    window.scrollTo({ top: 0, behavior: 'auto' });
  }

  function applyPageSwap(html, targetUrl, pushState) {
    const doc = new DOMParser().parseFromString(html, 'text/html');
    const nextShell = doc.getElementById('app-shell-main');
    const curShell = document.getElementById('app-shell-main');
    if (!nextShell || !curShell) { window.location.assign(targetUrl.href); return; }
    if ((curShell.dataset.activeRole || '') !== (nextShell.dataset.activeRole || '')) {
      clearPageCache();
      window.location.assign(targetUrl.href);
      return;
    }
    document.title = doc.title || document.title;
    curShell.innerHTML = nextShell.innerHTML;
    const mainEl = curShell.querySelector('main');
    if (mainEl) {
      mainEl.classList.remove('spa-page-enter');
      void mainEl.offsetWidth;
      mainEl.classList.add('spa-page-enter');
    }
    if (pushState) history.pushState({ spaUrl: targetUrl.href }, '', targetUrl.href);
    syncActiveSidebarLink(targetUrl);
    if (typeof window.reinitEduPredictUI === 'function') window.reinitEduPredictUI();
    runExtraScripts(doc.getElementById('page-extra-js'));
    scrollForUrl(targetUrl);
  }

  function navigateTo(targetUrl, options) {
    const opts = options || {};
    const token = ++navId;
    return fetchPageHtml(targetUrl, Boolean(opts.bypassCache))
      .then((res) => {
        if (token !== navId) return;
        if (res.redirect) { clearPageCache(); window.location.assign(res.redirect); return; }
        const finalUrl = new URL(res.finalUrl || targetUrl.href, window.location.href);
        if (targetUrl.hash && !finalUrl.hash) finalUrl.hash = targetUrl.hash;
        applyPageSwap(res.html, finalUrl, opts.pushState !== false);
      })
      .catch(() => {
        if (token === navId) window.location.assign(targetUrl.href);
      });
  }

  function bindNavigationEvents() {
    initNavGroups();
    if (history.replaceState) history.replaceState({ spaUrl: window.location.href }, '', window.location.href);
    const prefetchHandler = (e) => {
      const link = e.target && e.target.closest ? e.target.closest('a[href]') : null;
      const url = getSpaUrl(link);
      if (url && (url.pathname + url.search) !== (window.location.pathname + window.location.search)) {
        fetchPageHtml(url, false).catch(function () {});
      }
    };
    document.addEventListener('mouseover', prefetchHandler, { passive: true });
    document.addEventListener('focusin', prefetchHandler, { passive: true });
    document.addEventListener('click', (e) => {
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      const link = e.target && e.target.closest ? e.target.closest('a[href]') : null;
      const url = getSpaUrl(link);
      if (!url) return;
      e.preventDefault();
      if (window.innerWidth < 1024 && typeof window.closeMobileSidebar === 'function') window.closeMobileSidebar();
      if (url.pathname === window.location.pathname && url.search === window.location.search) {
        if (url.hash) {
          if (window.location.hash !== url.hash) history.pushState({ spaUrl: url.href }, '', url.href);
          syncActiveSidebarLink(url);
          scrollForUrl(url);
          return;
        }
        navigateTo(url, { pushState: false, bypassCache: true });
        return;
      }
      navigateTo(url, { pushState: true, bypassCache: false });
    });
    window.addEventListener('popstate', () => {
      navigateTo(new URL(window.location.href), { pushState: false, bypassCache: false });
    });
    document.addEventListener('submit', clearPageCache, true);
  }

  window.clearEduPredictPageCache = clearPageCache;
  window.eduPredictNavigate = navigateTo;
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bindNavigationEvents);
  else bindNavigationEvents();
})();
