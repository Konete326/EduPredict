(function () {
  var W = 1440;
  var H = 1036;
  var STORY = 2600;

  function run(root, scroller) {
    var $ = function (id) { return root.querySelector('#' + id); };
    var D = scroller;
    var all = function (q) { return [].slice.call(root.querySelectorAll(q)); };
    var hero = $('hero'), scene = $('scene'), nav = $('nav'), logo = $('logo'), badge = $('badge');
    var h1s = [].slice.call($('h1').children), cta = $('cta'), hint = $('hint'), crm = $('crm'), cur = $('cur'), spin = $('spin');
    var fps = [].slice.call($('found').children), h2s = [].slice.call($('h2').children), h2 = $('h2');
    var panel = $('panel'), tabs = $('tabs'), tab0 = $('tab0'), tab1 = $('tab1');
    var bar0 = $('bar0').firstElementChild, bar1 = $('bar1').firstElementChild, copyA = $('copyA'), copyB = $('copyB');
    var pic = $('pic'), rock = $('rock'), rockfg = $('rockfg'), glass = $('glass');
    var gmsg = $('gmsg'), glook = $('glook'), spin2 = $('spin2'), gfound = $('gfound'), gfs = [].slice.call(gfound.children);
    var ints = all('.int'), wire = $('wire'), ai = $('ai');

    function cl(x) { return x < 0 ? 0 : x > 1 ? 1 : x; }
    function p(t, a, b) { return cl((t - a) / (b - a)); }
    function eo(x) { return 1 - Math.pow(1 - x, 3); }
    function eio(x) { return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; }
    function blur(el, k, amt, dy, o) {
      el.style.opacity = (o == null ? k : k * o).toFixed(3);
      el.style.filter = 'blur(' + ((1 - k) * (amt || 14)).toFixed(2) + 'px)';
      el.style.transform = 'translateY(' + ((1 - k) * 10 + (dy || 0)).toFixed(2) + 'px)';
    }
    function reveal(el, k) {
      el.style.opacity = k.toFixed(3);
      el.style.maxHeight = (k * 40).toFixed(1) + 'px';
      el.style.marginTop = el.previousElementSibling ? (k * 12).toFixed(1) + 'px' : '0';
      el.style.filter = 'blur(' + ((1 - k) * 4).toFixed(2) + 'px)';
    }

    var INTRO = 2.6, SPLIT = 0.74;
    function render(t, s) {
      var grow = eo(p(t, 0.1, 0.9)), collapse = eio(p(s, 0.2, 0.32));
      hero.style.height = (1000 * grow - 636 * collapse).toFixed(1) + 'px';
      nav.style.opacity = eo(p(t, 0.72, 1)).toFixed(3);
      logo.style.transform = 'scale(' + (0.86 + 0.14 * eo(p(t, 0.72, 1.15))).toFixed(3) + ')';

      var out = 1 - eio(p(s, 0.015, 0.1)), lift = -110 * eio(p(s, 0, 0.12));
      blur(badge, eo(p(t, 0.95, 1.3)), 14, lift * 1.2, out);
      blur(h1s[0], eo(p(t, 1.1, 1.65)), 14, lift, out);
      blur(h1s[1], eo(p(t, 1.32, 1.87)), 14, lift * 0.9, out);
      blur(h1s[2], eo(p(t, 1.55, 2.1)), 14, lift * 0.8, out);
      blur(cta, eo(p(t, 1.85, 2.25)), 14, lift * 0.7, out);

      var up = eo(p(t, 1.3, 2.05)), climb = eio(p(s, 0.02, 0.13)), sink = eio(p(s, 0.17, 0.24));
      crm.style.transform = 'translateY(' + (150 * (1 - up) - 250 * climb + 330 * sink).toFixed(1) + 'px) scale(' + (1 + climb * 0.04).toFixed(4) + ')';
      crm.style.opacity = (up * (1 - p(s, 0.2, 0.25))).toFixed(3);
      scene.style.transform = 'scale(' + (1 + 0.045 * climb * (1 - collapse)).toFixed(4) + ')';
      reveal(fps[1], eo(p(s, 0.07, 0.1)));
      reveal(fps[2], eo(p(s, 0.1, 0.13)));
      spin.style.transform = 'rotate(' + (s * 2400).toFixed(0) + 'deg)';

      var ck = eio(p(s, 0.05, 0.16));
      cur.style.opacity = (eo(p(s, 0.04, 0.07)) * (1 - p(s, 0.17, 0.2))).toFixed(3);
      cur.style.transform = 'translate(' + (612 - 92 * ck).toFixed(1) + 'px,' + (40 + 266 * ck).toFixed(1) + 'px)';
      hint.style.opacity = (p(t, 2.2, 2.6) * (1 - p(s, 0, 0.015))).toFixed(3);

      h2.style.opacity = s > 0.27 ? 1 : 0;
      blur(h2s[0], eo(p(s, 0.28, 0.33)));
      blur(h2s[1], eo(p(s, 0.3, 0.35)));
      var pk = eo(p(s, 0.32, 0.4));
      pic.style.opacity = pk.toFixed(3);
      pic.style.filter = 'blur(' + ((1 - pk) * 10).toFixed(2) + 'px) brightness(' + (1 + (1 - pk) * 0.25).toFixed(3) + ')';
      panel.style.opacity = eo(p(s, 0.34, 0.4)).toFixed(3);
      tabs.style.opacity = eo(p(s, 0.36, 0.42)).toFixed(3);

      var sw = eio(p(s, SPLIT - 0.035, SPLIT + 0.035));
      var ak = eo(p(s, 0.38, 0.44));
      copyA.style.opacity = (ak * (1 - sw)).toFixed(3);
      copyA.style.transform = 'translateY(' + ((1 - ak) * 10 - sw * 14).toFixed(1) + 'px)';
      copyA.style.filter = 'blur(' + ((1 - ak) * 6 + sw * 8).toFixed(2) + 'px)';
      copyB.style.opacity = sw.toFixed(3);
      copyB.style.transform = 'translateY(' + ((1 - sw) * 14).toFixed(1) + 'px)';
      copyB.style.filter = 'blur(' + ((1 - sw) * 8).toFixed(2) + 'px)';
      tab0.classList.toggle('off', sw > 0.5);
      tab1.classList.toggle('off', sw <= 0.5);

      var gk = eo(p(s, 0.4, 0.47)), go = 1 - sw;
      glass.style.opacity = (gk * go).toFixed(3);
      glass.style.transform = 'translateY(' + ((1 - gk) * 16).toFixed(1) + 'px) scale(' + (0.97 + gk * 0.03 - sw * 0.03).toFixed(4) + ')';
      glass.style.filter = 'blur(' + ((1 - gk) * 8 + sw * 8).toFixed(2) + 'px)';
      blur(gmsg, eo(p(s, 0.45, 0.49)), 6, -2);
      blur(glook, eo(p(s, 0.5, 0.53)), 6, -4);
      var fk = eo(p(s, 0.54, 0.58));
      gfound.style.opacity = fk.toFixed(3);
      gfound.style.transform = 'translateY(' + ((1 - fk) * 8).toFixed(1) + 'px)';
      reveal(gfs[1], eo(p(s, 0.59, 0.63)));
      reveal(gfs[2], eo(p(s, 0.64, 0.68)));
      spin2.style.transform = 'rotate(' + (s * 2400).toFixed(0) + 'deg)';

      ints.forEach(function (el, i) {
        var k = eo(p(s, SPLIT + 0.02 + i * 0.022, SPLIT + 0.09 + i * 0.022));
        el.style.opacity = k.toFixed(3);
        el.style.transform = 'translateY(' + ((1 - k) * 14).toFixed(1) + 'px) scale(' + (0.96 + k * 0.04).toFixed(4) + ')';
        el.style.filter = 'blur(' + ((1 - k) * 6).toFixed(2) + 'px)';
      });
      var wk = eo(p(s, 0.9, 0.94));
      wire.style.opacity = wk.toFixed(3);
      wire.style.transform = 'scaleY(' + wk.toFixed(3) + ')';
      var mk = eo(p(s, 0.92, 0.98));
      ai.style.opacity = mk.toFixed(3);
      ai.style.transform = 'translateY(' + ((1 - mk) * 10).toFixed(1) + 'px)';
      ai.style.filter = 'blur(' + ((1 - mk) * 6).toFixed(2) + 'px)';

      bar0.style.width = (p(s, 0.4, SPLIT) * 100).toFixed(2) + '%';
      bar0.style.background = sw > 0.5 ? 'var(--olive)' : 'var(--olive-d)';
      bar1.style.width = (p(s, SPLIT, 1) * 100).toFixed(2) + '%';
      var rz = 'scale(' + (1 + 0.04 * p(s, 0.4, 1)).toFixed(4) + ')';
      rock.style.transform = rz;
      rockfg.style.transform = rz;
    }

    var reducedMq = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;
    if (navigator.webdriver || (reducedMq && reducedMq.matches)) {
      root.classList.add('still');
      render(9, 0);
      return function () {};
    }

    var t0 = performance.now(), sT = 0, sC = 0, raf = 0;
    function max() { return Math.max(1, D.scrollHeight - D.clientHeight); }
    function tick(now) {
      var t = (now - t0) / 1000;
      sT = cl(D.scrollTop / max());
      sC += (sT - sC) * 0.12;
      if (Math.abs(sT - sC) < 0.0003) sC = sT;
      render(t, sC);
      raf = (t < INTRO || sC !== sT) ? requestAnimationFrame(tick) : 0;
    }
    function wake() { if (!raf) raf = requestAnimationFrame(tick); }
    D.addEventListener('scroll', wake, { passive: true });
    window.addEventListener('resize', wake);
    function go(s) { D.scrollTo({ top: s * max(), behavior: 'smooth' }); }
    tab0.onclick = function () { go(0.66); };
    tab1.onclick = function () { go(1); };
    raf = requestAnimationFrame(tick);
    return function () {
      cancelAnimationFrame(raf);
      D.removeEventListener('scroll', wake);
      window.removeEventListener('resize', wake);
      tab0.onclick = tab1.onclick = null;
    };
  }

  function boot() {
    var el = document.getElementById('fld-root');
    var pg = document.getElementById('fld-body');
    if (!el || !pg) return;
    var fit = function () {
      var z = Math.min(el.clientWidth / W, el.clientHeight / H) || 1;
      var vh = el.clientHeight / z;
      pg.style.zoom = String(z);
      pg.style.height = (STORY + Math.max(vh, H)) + 'px';
      pg.style.setProperty('--st', Math.max(0, (vh - H) / 2) + 'px');
    };
    if (typeof ResizeObserver === 'function') {
      var ro = new ResizeObserver(fit);
      ro.observe(el);
    }
    window.addEventListener('resize', fit, { passive: true });
    fit();
    run(el, el);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
