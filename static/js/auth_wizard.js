window.switchAuthTab = function (tab) {
  const isReg = tab === 'register';
  const loginPanel = document.getElementById('panel-login'), regPanel = document.getElementById('panel-register');
  const loginBtn = document.getElementById('tab-login-btn'), regBtn = document.getElementById('tab-register-btn');
  const activeCls = ['bg-[var(--bg-surface)]', 'text-[var(--accent-primary)]', 'shadow-sm', 'border-[var(--border-subtle)]'];
  const inactiveCls = ['text-[var(--text-secondary)]', 'border-transparent'];
  if (loginPanel) loginPanel.classList.toggle('hidden', isReg);
  if (regPanel) regPanel.classList.toggle('hidden', !isReg);
  [[loginBtn, !isReg], [regBtn, isReg]].forEach(function (pair) {
    const btn = pair[0], on = pair[1];
    if (!btn) return;
    btn.setAttribute('aria-selected', String(on));
    activeCls.forEach(function (c) { btn.classList.toggle(c, on); });
    inactiveCls.forEach(function (c) { btn.classList.toggle(c, !on); });
  });
};

window.togglePasswordVisibility = function (inputId, btn) {
  const input = document.getElementById(inputId);
  if (!input) return;
  const show = input.type === 'password';
  input.type = show ? 'text' : 'password';
  const icon = btn ? btn.querySelector('i') : null;
  if (icon) { icon.classList.toggle('fa-eye', !show); icon.classList.toggle('fa-eye-slash', show); }
};

window.fillDefaultAdmin = function () {
  window.switchAuthTab('login');
  const emailEl = document.getElementById('login-email'), passEl = document.getElementById('login-password');
  if (emailEl) emailEl.value = 'admin@gmail.com';
  if (passEl) passEl.value = 'admin123';
  if (typeof showToast === 'function') showToast('Default admin credentials filled.', 'info');
};

function initCapsLockListeners() {
  [['login-password', 'login-caps-warn'], ['reg-password', 'reg-caps-warn']].forEach(function (pair) {
    const inp = document.getElementById(pair[0]), wrn = document.getElementById(pair[1]);
    if (!inp || !wrn) return;
    const upd = function (e) { if (typeof e.getModifierState === 'function') wrn.classList.toggle('hidden', !e.getModifierState('CapsLock')); };
    inp.addEventListener('keyup', upd);
    inp.addEventListener('keydown', upd);
    inp.addEventListener('blur', function () { wrn.classList.add('hidden'); });
  });
}

function initAuthStepper() {
  const form = document.querySelector('[data-auth-stepper]');
  if (!form) return;
  const steps = Array.from(form.querySelectorAll('[data-wizard-step]'));
  const triggers = Array.from(form.querySelectorAll('[data-step-trigger]'));
  const lines = Array.from(form.querySelectorAll('.ep-step-line'));
  const prevBtn = form.querySelector('[data-wizard-prev]');
  const nextBtn = form.querySelector('[data-wizard-next]');
  const submitBtn = form.querySelector('[data-wizard-submit]');
  const roleSelect = document.getElementById('reg-role');
  const teacherNotice = document.getElementById('teacher-approval-notice');
  const batchInput = document.getElementById('reg-batch');
  const summaryBox = document.getElementById('wizard-review-summary');
  const passInput = document.getElementById('reg-password');
  const confirmInput = document.getElementById('reg-confirm-password');
  let currentStep = 0;
  let batchEdited = Boolean(batchInput && batchInput.value.trim());

  function syncRoleDefaults() {
    if (!roleSelect) return;
    if (teacherNotice) teacherNotice.classList.remove('hidden');
    if (batchInput && !batchEdited) batchInput.value = 'ALL';
  }

  function renderReviewSummary() {
    if (!summaryBox) return;
    summaryBox.textContent = '';
    const title = document.createElement('p');
    title.className = 'text-[11px] font-semibold uppercase tracking-wider text-[var(--text-muted)] mb-1.5';
    title.textContent = 'Account Summary';
    summaryBox.appendChild(title);
    const grid = document.createElement('div');
    grid.className = 'grid grid-cols-2 gap-x-3 gap-y-1 text-[11px]';
    const roleLabel = roleSelect && roleSelect.selectedOptions[0] ? roleSelect.selectedOptions[0].textContent : '';
    const val = function (id) { return (document.getElementById(id) || {}).value || '-'; };
    const items = [['Name', val('reg-full-name')], ['Email', val('reg-email')], ['Role', roleLabel || '-'], ['Department', val('reg-department')], ['Batch / Term', val('reg-batch')]];
    const phoneVal = ((document.getElementById('reg-phone') || {}).value || '').trim();
    if (phoneVal) items.push(['Phone', phoneVal]);
    items.forEach(function (pair) {
      const row = document.createElement('div');
      row.className = 'truncate text-[var(--text-secondary)]';
      const k = document.createElement('span'); k.className = 'text-[var(--text-muted)]'; k.textContent = pair[0] + ': ';
      const v = document.createElement('span'); v.className = 'font-medium text-[var(--text-primary)]'; v.textContent = pair[1];
      row.append(k, v);
      grid.appendChild(row);
    });
    summaryBox.appendChild(grid);
  }

  function showStep(target) {
    const prevStep = currentStep;
    currentStep = Math.max(0, Math.min(steps.length - 1, target));
    steps.forEach(function (el, idx) {
      el.classList.remove('ep-step-slide-next', 'ep-step-slide-prev');
      const isActive = idx === currentStep;
      el.classList.toggle('hidden', !isActive);
      if (isActive && target > prevStep) el.classList.add('ep-step-slide-next');
      else if (isActive && target < prevStep) el.classList.add('ep-step-slide-prev');
    });
    triggers.forEach(function (btn, idx) {
      const ind = btn.querySelector('.ep-step-indicator');
      const state = idx < currentStep ? 'complete' : (idx === currentStep ? 'current' : 'upcoming');
      if (idx === currentStep) btn.setAttribute('aria-current', 'step'); else btn.removeAttribute('aria-current');
      if (ind) {
        ind.setAttribute('data-state', state);
        ind.textContent = '';
        if (state === 'complete') { const ic = document.createElement('i'); ic.className = 'fa-solid fa-check text-[10px]'; ind.appendChild(ic); }
        else ind.textContent = String(idx + 1);
      }
    });
    lines.forEach(function (line, idx) { line.setAttribute('data-complete', idx < currentStep ? 'true' : 'false'); });
    if (prevBtn) prevBtn.classList.toggle('hidden', currentStep === 0);
    if (nextBtn) nextBtn.classList.toggle('hidden', currentStep === steps.length - 1);
    if (submitBtn) submitBtn.classList.toggle('hidden', currentStep !== steps.length - 1);
    if (currentStep === steps.length - 1) renderReviewSummary();
  }

  function validateStep(idx) {
    const fields = steps[idx].querySelectorAll('input, select, textarea');
    for (let i = 0; i < fields.length; i++) {
      if (!fields[i].checkValidity()) { fields[i].reportValidity(); return false; }
    }
    return true;
  }

  if (nextBtn) nextBtn.addEventListener('click', function () { if (validateStep(currentStep)) showStep(currentStep + 1); });
  if (prevBtn) prevBtn.addEventListener('click', function () { showStep(currentStep - 1); });
  triggers.forEach(function (btn) {
    btn.addEventListener('click', function () {
      const idx = Number(btn.getAttribute('data-step-trigger'));
      if (idx < currentStep) showStep(idx);
      else if (idx === currentStep + 1 && validateStep(currentStep)) showStep(idx);
    });
  });
  form.addEventListener('keydown', function (e) {
    if (e.isComposing || e.keyCode === 229) return;
    if (e.key === 'Enter' && currentStep < steps.length - 1 && e.target.tagName !== 'TEXTAREA') {
      e.preventDefault();
      if (validateStep(currentStep)) showStep(currentStep + 1);
    }
  });
  if (batchInput) batchInput.addEventListener('input', function () { batchEdited = true; });
  if (roleSelect) roleSelect.addEventListener('change', syncRoleDefaults);
  if (passInput) passInput.addEventListener('input', function () { passInput.setCustomValidity(''); });
  if (confirmInput) confirmInput.addEventListener('input', function () { confirmInput.setCustomValidity(''); });
  form.addEventListener('submit', function (e) {
    if (!passInput || !confirmInput) return;
    if (passInput.value.length < 6) {
      e.preventDefault();
      passInput.setCustomValidity('Password must be at least 6 characters.');
      passInput.reportValidity();
      if (typeof showToast === 'function') showToast('Password must be at least 6 characters.', 'error');
    } else if (passInput.value !== confirmInput.value) {
      e.preventDefault();
      confirmInput.setCustomValidity('Passwords do not match.');
      confirmInput.reportValidity();
      if (typeof showToast === 'function') showToast('Passwords do not match.', 'error');
    }
  });
  syncRoleDefaults();
  showStep(0);
}

function initFloatingPaths() {
  const container = document.getElementById('ep-floating-paths') || document.querySelector('[data-floating-paths]');
  if (!container) return;
  const svgNs = 'http://www.w3.org/2000/svg';
  container.textContent = '';
  [1, -1].forEach(function (position) {
    const svg = document.createElementNS(svgNs, 'svg');
    svg.setAttribute('class', 'pointer-events-none absolute inset-0 h-full w-full text-[var(--accent-primary)]');
    svg.setAttribute('viewBox', '0 0 696 316');
    svg.setAttribute('fill', 'none');
    svg.setAttribute('preserveAspectRatio', 'xMidYMid slice');
    for (let i = 0; i < 36; i++) {
      const path = document.createElementNS(svgNs, 'path');
      const xOff = i * 5 * position;
      const yOff = i * 6;
      const d = 'M-' + (380 - xOff) + ' -' + (189 + yOff) +
        'C-' + (380 - xOff) + ' -' + (189 + yOff) + ' -' + (312 - xOff) + ' ' + (216 - yOff) + ' ' + (152 - xOff) + ' ' + (343 - yOff) +
        'C' + (616 - xOff) + ' ' + (470 - yOff) + ' ' + (684 - xOff) + ' ' + (875 - yOff) + ' ' + (684 - xOff) + ' ' + (875 - yOff);
      path.setAttribute('d', d);
      path.setAttribute('stroke', 'currentColor');
      path.setAttribute('stroke-width', String((0.5 + i * 0.03).toFixed(2)));
      path.setAttribute('stroke-opacity', String((0.08 + i * 0.015).toFixed(3)));
      path.setAttribute('class', 'ep-floating-path');
      path.style.setProperty('--ep-path-dur', String(20 + (i % 7) * 3) + 's');
      svg.appendChild(path);
    }
    container.appendChild(svg);
  });
}
window.initFloatingPaths = initFloatingPaths;

window.evaluatePasswordStrength = function (val) {
  const s = typeof val === 'string' ? val : '';
  if (s.length < 6) return { score: 0, label: 'Enter at least 6 characters' };
  const checks = (s.length >= 8 ? 1 : 0) + (/[a-z]/.test(s) && /[A-Z]/.test(s) ? 1 : 0) + (/\d/.test(s) ? 1 : 0) + (/[^A-Za-z0-9]/.test(s) ? 1 : 0);
  const score = Math.max(1, Math.min(4, checks || 1));
  return { score: score, label: ['Enter at least 6 characters', 'Weak', 'Fair', 'Good', 'Strong'][score] };
};

function initPasswordStrengthMeter() {
  const passInput = document.getElementById('reg-password');
  const labelEl = document.getElementById('reg-password-strength-label');
  const bars = Array.from(document.querySelectorAll('[data-strength-bar]'));
  if (!passInput || !labelEl || !bars.length) return;
  const palette = ['var(--border-subtle)', 'var(--status-danger)', 'var(--status-warning)', 'var(--accent-primary)', 'var(--status-success)'];
  function update() {
    const res = window.evaluatePasswordStrength(passInput.value);
    const activeColor = palette[res.score] || palette[0];
    bars.forEach(function (bar, idx) {
      bar.style.backgroundColor = res.score >= (Number(bar.getAttribute('data-strength-bar')) || (idx + 1)) ? activeColor : 'var(--border-subtle)';
    });
    labelEl.textContent = res.label;
    labelEl.style.color = res.score > 0 ? activeColor : 'var(--text-muted)';
  }
  passInput.addEventListener('input', update);
  update();
}
window.initPasswordStrengthMeter = initPasswordStrengthMeter;

function initPendingApprovalPoll() {
  const card = document.getElementById('teacher-pending-status-card');
  if (!card || card.classList.contains('hidden')) return;
  const statusUrl = card.getAttribute('data-approval-status-url');
  if (!statusUrl) return;
  const poll = function () {
    fetch(statusUrl, { credentials: 'same-origin', headers: { 'X-Requested-With': 'XMLHttpRequest' } })
      .then(function (res) { return res.ok ? res.json() : null; })
      .then(function (data) {
        if (!data) return;
        if (data.status === 'APPROVED' && data.redirect_url) {
          window.location.href = data.redirect_url;
        } else if (data.status === 'REJECTED') {
          window.location.reload();
        }
      })
      .catch(function () {});
  };
  window.setInterval(poll, 5000);
}

function bootAuthWizard() {
  initCapsLockListeners();
  initAuthStepper();
  initFloatingPaths();
  initPasswordStrengthMeter();
  initPendingApprovalPoll();
}
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bootAuthWizard);
else bootAuthWizard();
