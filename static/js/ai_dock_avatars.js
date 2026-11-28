(function () {
  const SPECS = {
    coach: { accent: '#16a34a', ink: '#14532d', extra: '<path d="M27 18q1-8 9-6q-4 1-3 6z" fill="#14532d"/>', front: '' },
    analyst: { accent: '#2563eb', ink: '#1e3a8a', extra: '<path d="M32 17V9" stroke="#1e3a8a" stroke-width="2.4" stroke-linecap="round"/><circle class="ep-av-antenna" cx="32" cy="8" r="3.2" fill="#1e3a8a"/>', front: '' },
    ops: { accent: '#d97706', ink: '#78350f', extra: '', front: '<path d="M15 25a17 17 0 0 1 34 0z" fill="#78350f"/><rect x="12" y="24" width="40" height="4" rx="2" fill="#78350f"/><rect x="29" y="11" width="6" height="6" rx="2" fill="#78350f"/>' },
    desk: { accent: '#dc2626', ink: '#7f1d1d', extra: '<path d="M13 33a19 19 0 0 1 38 0" fill="none" stroke="#7f1d1d" stroke-width="3" stroke-linecap="round"/><rect x="9" y="30" width="6" height="11" rx="3" fill="#7f1d1d"/><rect x="49" y="30" width="6" height="11" rx="3" fill="#7f1d1d"/>', front: '<path d="M52 40q0 8-10 9" fill="none" stroke="#7f1d1d" stroke-width="2.2" stroke-linecap="round"/><circle cx="41" cy="49" r="2.4" fill="#7f1d1d"/>' }
  };
  const ENTRY_ORDER = ['coach', 'analyst', 'ops', 'desk'];
  const eyeY = (id) => (id === 'ops' ? 35 : 32);
  function markup(id) {
    const s = SPECS[id] || SPECS.coach, ey = eyeY(id), my = ey + 9;
    const eye = (cx) => '<ellipse class="ep-av-eye" cx="' + cx + '" cy="' + ey + '" rx="3" ry="3.6" fill="' + s.ink + '"/>';
    return '<svg class="ep-av" viewBox="0 0 64 64" role="img" aria-hidden="true" focusable="false"><circle cx="32" cy="32" r="32" fill="' + s.accent + '"/>'
      + '<g class="ep-av-head">' + s.extra + '<rect x="14" y="17" width="36" height="32" rx="14" fill="#ffffff"/>' + s.front
      + eye(25) + eye(39)
      + '<circle cx="19.5" cy="' + (ey + 6) + '" r="2.8" fill="' + s.accent + '" fill-opacity="0.28"/><circle cx="44.5" cy="' + (ey + 6) + '" r="2.8" fill="' + s.accent + '" fill-opacity="0.28"/>'
      + '<path class="ep-av-mouth" d="M26 ' + my + 'q6 6 12 0" fill="none" stroke="' + s.ink + '" stroke-width="2.4" stroke-linecap="round"/></g></svg>';
  }
  function fill(node, id, extraClass) {
    if (!node) return;
    node.setAttribute('data-avatar-agent', id);
    node.innerHTML = markup(id);
    const svg = node.firstChild;
    if (svg && extraClass && svg.classList) extraClass.split(' ').forEach((c) => { if (c) svg.classList.add(c); });
  }
  function create(id, sizeClass) {
    const span = document.createElement('span');
    span.className = 'ep-av-wrap inline-flex shrink-0 rounded-full ' + (sizeClass || 'h-5 w-5');
    fill(span, id);
    return span;
  }
  function hydrate(root) {
    (root || document).querySelectorAll('[data-avatar-agent]').forEach((n) => { if (!n.firstChild) fill(n, n.getAttribute('data-avatar-agent')); });
  }
  window.EpAvatars = { order: ENTRY_ORDER, markup, fill, create, hydrate };
})();
