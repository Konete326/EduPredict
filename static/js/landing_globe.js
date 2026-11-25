(function () {
  function readTestimonialsData() {
    try {
      const node = document.getElementById('ep-landing-testimonials-data');
      const parsed = node ? JSON.parse(node.textContent || '[]') : [];
      if (Array.isArray(parsed) && parsed.length) return parsed;
    } catch (e) {}
    return [{
      name: 'EduPredict Portal',
      role: 'Live Campus Feed',
      org: 'MongoDB Atlas',
      city: 'Karachi',
      country: 'PK',
      lat: 24.8607,
      lng: 67.0011,
      rating: 5,
      initials: 'EP',
      tone: '#2563eb',
      quote: 'No campus feedback submitted yet. Submit an inquiry on the Contact page or inside any role panel to appear here live.'
    }];
  }
  const TESTIMONIALS = readTestimonialsData();

  function makeAvatarDataUri(initials, bgHex) {
    const svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="32" fill="' + bgHex + '"/><text x="32" y="39" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="22" font-weight="700" fill="#ffffff">' + initials + '</text></svg>';
    return 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg);
  }

  function buildSpherePoints(count) {
    const pts = [];
    const golden = Math.PI * (3 - Math.sqrt(5));
    for (let i = 0; i < count; i++) {
      const y = 1 - (i / (count - 1)) * 2;
      const r = Math.sqrt(Math.max(0, 1 - y * y));
      const theta = golden * i;
      pts.push({ x: Math.cos(theta) * r, y: y, z: Math.sin(theta) * r, major: i % 11 === 0 });
    }
    return pts;
  }

  function latLngToUnit(latDeg, lngDeg) {
    const lat = (latDeg * Math.PI) / 180;
    const lng = (lngDeg * Math.PI) / 180;
    return {
      x: Math.cos(lat) * Math.sin(lng),
      y: -Math.sin(lat),
      z: Math.cos(lat) * Math.cos(lng)
    };
  }

  function rotateVec(v, rotY, rotX) {
    const cy = Math.cos(rotY), sy = Math.sin(rotY);
    const x1 = v.x * cy + v.z * sy;
    const z1 = -v.x * sy + v.z * cy;
    const cx = Math.cos(rotX), sx = Math.sin(rotX);
    const y2 = v.y * cx - z1 * sx;
    const z2 = v.y * sx + z1 * cx;
    return { x: x1, y: y2, z: z2 };
  }

  function targetAnglesFor(latDeg, lngDeg) {
    return {
      rotY: -(lngDeg * Math.PI) / 180,
      rotX: Math.max(-0.65, Math.min(0.65, (latDeg * Math.PI) / 180 * 0.55))
    };
  }

  function initTestimonialGlobe() {
    const root = document.getElementById('ep-testimonial-globe');
    const stage = document.getElementById('ep-globe-stage');
    const canvas = document.getElementById('ep-globe-canvas');
    const pinsHost = document.getElementById('ep-globe-pins');
    if (!root || !stage || !canvas || !pinsHost) return;

    const quoteEl = document.getElementById('ep-globe-quote');
    const starsEl = document.getElementById('ep-globe-stars');
    const avatarEl = document.getElementById('ep-globe-avatar');
    const authorEl = document.getElementById('ep-globe-author');
    const roleEl = document.getElementById('ep-globe-role');
    const locEl = document.getElementById('ep-globe-loc');
    const indexEl = document.getElementById('ep-globe-index');
    const prevBtn = document.getElementById('ep-globe-prev');
    const nextBtn = document.getElementById('ep-globe-next');

    const reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const spherePts = buildSpherePoints(580);
    let activeIdx = 0;
    const initialAngles = targetAnglesFor(TESTIMONIALS[0].lat, TESTIMONIALS[0].lng);
    let rotY = initialAngles.rotY;
    let rotX = initialAngles.rotX;
    let velY = 0;
    let velX = 0;
    let animTarget = null;
    let dragging = false;
    let hovered = false;

    const pinNodes = TESTIMONIALS.map((item, idx) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'ep-globe-pin';
      btn.setAttribute('aria-label', item.name + ' from ' + item.city);
      const img = document.createElement('img');
      img.src = makeAvatarDataUri(item.initials, item.tone);
      img.alt = item.name;
      img.className = 'h-full w-full rounded-full object-cover';
      btn.appendChild(img);
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        selectItem(idx, true);
      });
      pinsHost.appendChild(btn);
      return { btn: btn, unit: latLngToUnit(item.lat, item.lng) };
    });

    function renderQuoteCard(idx) {
      const item = TESTIMONIALS[idx];
      if (quoteEl) quoteEl.textContent = '"' + item.quote + '"';
      if (authorEl) authorEl.textContent = item.name;
      if (roleEl) roleEl.textContent = item.role + ' · ' + item.org;
      if (locEl) locEl.textContent = item.city + ', ' + item.country;
      if (indexEl) indexEl.textContent = String(idx + 1).padStart(2, '0') + ' / ' + String(TESTIMONIALS.length).padStart(2, '0');
      if (avatarEl) {
        avatarEl.src = makeAvatarDataUri(item.initials, item.tone);
        avatarEl.alt = item.name;
      }
      if (starsEl) {
        starsEl.innerHTML = '';
        for (let s = 0; s < item.rating; s++) {
          const icon = document.createElement('i');
          icon.className = 'fa-solid fa-star text-xs text-[var(--status-warning)]';
          icon.setAttribute('aria-hidden', 'true');
          starsEl.appendChild(icon);
        }
      }
      pinNodes.forEach((p, i) => p.btn.classList.toggle('is-active', i === idx));
    }

    function selectItem(idx, turnGlobe) {
      activeIdx = ((idx % TESTIMONIALS.length) + TESTIMONIALS.length) % TESTIMONIALS.length;
      renderQuoteCard(activeIdx);
      if (turnGlobe) {
        const tgt = targetAnglesFor(TESTIMONIALS[activeIdx].lat, TESTIMONIALS[activeIdx].lng);
        let dY = (tgt.rotY - rotY) % (Math.PI * 2);
        if (dY > Math.PI) dY -= Math.PI * 2;
        if (dY < -Math.PI) dY += Math.PI * 2;
        animTarget = { startY: rotY, startX: rotX, endY: rotY + dY, endX: tgt.rotX, startTs: performance.now(), dur: reduced ? 1 : 650 };
        velY = 0;
        velX = 0;
      }
    }

    function drawFrame(now) {
      if (animTarget) {
        const t = Math.min(1, (now - animTarget.startTs) / animTarget.dur);
        const ease = 1 - Math.pow(1 - t, 3);
        rotY = animTarget.startY + (animTarget.endY - animTarget.startY) * ease;
        rotX = animTarget.startX + (animTarget.endX - animTarget.startX) * ease;
        if (t >= 1) animTarget = null;
      } else if (!dragging) {
        rotY += velY;
        rotX = Math.max(-0.72, Math.min(0.72, rotX + velX));
        velY *= 0.92;
        velX *= 0.92;
        if (!hovered && !reduced && Math.abs(velY) < 0.0005) rotY += 0.0022;
      }

      const w = Math.max(240, stage.clientWidth || 360);
      const h = Math.max(240, stage.clientHeight || 360);
      const dpr = Math.min(2, window.devicePixelRatio || 1);
      if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {
        canvas.width = Math.round(w * dpr);
        canvas.height = Math.round(h * dpr);
      }
      const ctx = canvas.getContext('2d');
      if (ctx) {
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        ctx.clearRect(0, 0, w, h);
        const cx = w / 2, cy = h / 2, radius = Math.min(w, h) * 0.41;
        const dark = document.documentElement.classList.contains('dark');
        const accent = getComputedStyle(document.documentElement).getPropertyValue('--accent-primary').trim() || '#2563eb';

        const halo = ctx.createRadialGradient(cx, cy, radius * 0.45, cx, cy, radius * 1.12);
        halo.addColorStop(0, dark ? 'rgba(59,130,246,0.12)' : 'rgba(37,99,235,0.08)');
        halo.addColorStop(1, 'transparent');
        ctx.fillStyle = halo;
        ctx.beginPath();
        ctx.arc(cx, cy, radius * 1.12, 0, Math.PI * 2);
        ctx.fill();

        ctx.strokeStyle = dark ? 'rgba(255,255,255,0.10)' : 'rgba(15,23,42,0.10)';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.arc(cx, cy, radius, 0, Math.PI * 2);
        ctx.stroke();

        for (let i = 0; i < spherePts.length; i++) {
          const pt = rotateVec(spherePts[i], rotY, rotX);
          const depth = (pt.z + 1) * 0.5;
          const px = cx + pt.x * radius;
          const py = cy + pt.y * radius;
          ctx.fillStyle = spherePts[i].major && pt.z > 0.15 ? accent : (dark ? 'rgba(244,244,245,0.85)' : 'rgba(15,23,42,0.75)');
          ctx.globalAlpha = pt.z > 0 ? 0.18 + depth * 0.62 : 0.05 + depth * 0.08;
          ctx.beginPath();
          ctx.arc(px, py, spherePts[i].major && pt.z > 0 ? 1.85 : 1.15, 0, Math.PI * 2);
          ctx.fill();
        }
        ctx.globalAlpha = 1;

        pinNodes.forEach((p, i) => {
          const rv = rotateVec(p.unit, rotY, rotX);
          const px = cx + rv.x * radius;
          const py = cy + rv.y * radius;
          const front = rv.z > -0.18;
          const scale = i === activeIdx ? 1.14 : (0.76 + ((rv.z + 1) * 0.5) * 0.24);
          p.btn.style.left = px.toFixed(1) + 'px';
          p.btn.style.top = py.toFixed(1) + 'px';
          p.btn.style.opacity = front ? (rv.z > 0.05 ? '1' : '0.45') : '0';
          p.btn.style.pointerEvents = front ? 'auto' : 'none';
          p.btn.style.zIndex = String(Math.round((rv.z + 2) * 10) + (i === activeIdx ? 20 : 0));
          p.btn.style.transform = 'translate(-50%, -50%) scale(' + scale.toFixed(2) + ')';
        });
      }

      window.requestAnimationFrame(drawFrame);
    }

    let dragPtr = null;
    stage.addEventListener('pointerdown', (e) => {
      if (e.target.closest('.ep-globe-pin')) return;
      dragging = true;
      animTarget = null;
      dragPtr = { id: e.pointerId, x: e.clientX, y: e.clientY };
      stage.setPointerCapture(e.pointerId);
    });
    stage.addEventListener('pointermove', (e) => {
      if (!dragPtr || e.pointerId !== dragPtr.id) return;
      const dx = e.clientX - dragPtr.x;
      const dy = e.clientY - dragPtr.y;
      dragPtr.x = e.clientX;
      dragPtr.y = e.clientY;
      velY = dx * 0.0055;
      velX = dy * 0.0045;
      rotY += velY;
      rotX = Math.max(-0.72, Math.min(0.72, rotX + velX));
    });
    const endGlobeDrag = (e) => { if (dragPtr && e.pointerId === dragPtr.id) { dragging = false; dragPtr = null; } };
    stage.addEventListener('pointerup', endGlobeDrag);
    stage.addEventListener('pointercancel', endGlobeDrag);
    stage.addEventListener('mouseenter', () => { hovered = true; });
    stage.addEventListener('mouseleave', () => { hovered = false; });

    if (prevBtn) prevBtn.addEventListener('click', () => selectItem(activeIdx - 1, true));
    if (nextBtn) nextBtn.addEventListener('click', () => selectItem(activeIdx + 1, true));
    root.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowLeft') { e.preventDefault(); selectItem(activeIdx - 1, true); }
      else if (e.key === 'ArrowRight') { e.preventDefault(); selectItem(activeIdx + 1, true); }
    });

    selectItem(0, true);
    window.requestAnimationFrame(drawFrame);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initTestimonialGlobe);
  else initTestimonialGlobe();
})();
