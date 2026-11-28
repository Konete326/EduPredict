(function () {
  const MESSAGES = {
    unsupported: 'Voice input is not supported in this browser. Please use Chrome or Edge.',
    insecure: 'Voice input needs a secure connection. Open this site with https:// (or localhost) and try again.',
    blocked: 'Microphone is blocked. Allow microphone access in the browser address bar and try again.',
    nomic: 'No microphone found or it is turned off.',
    nospeech: 'No speech detected. Please try again.',
    network: 'Speech service unavailable (network).',
    busy: 'Microphone is busy or not readable. Close other apps using it and try again.'
  };
  const state = { rec: null, listening: false, starting: false, ctx: null };
  const toast = (msg) => { if (typeof window.showToast === 'function') window.showToast(msg, 'warning'); };
  function status(msg) {
    const n = state.ctx && state.ctx.statusEl;
    if (!n) return;
    n.textContent = msg || '';
    n.classList.toggle('hidden', !msg);
  }
  function warn(msg) { status(msg); toast(msg); }
  function setUi(active) {
    state.listening = Boolean(active);
    const c = state.ctx; if (!c) return;
    if (c.micBtn) { c.micBtn.setAttribute('aria-pressed', active ? 'true' : 'false'); c.micBtn.classList.toggle('ep-mic-listening', Boolean(active)); }
    if (c.input) c.input.placeholder = active ? 'Listening... speak now' : c.getPlaceholder();
  }
  function stop() {
    if (state.rec && state.listening) { try { state.rec.stop(); } catch (e) {} }
    setUi(false);
  }
  function errorMessage(code) {
    if (code === 'not-allowed' || code === 'service-not-allowed') return MESSAGES.blocked;
    if (code === 'audio-capture') return MESSAGES.nomic;
    if (code === 'no-speech') return MESSAGES.nospeech;
    if (code === 'network') return MESSAGES.network;
    if (code === 'aborted') return '';
    return 'Voice input failed (error: ' + (code || 'unknown') + '). Please try again.';
  }
  function mediaErrorMessage(err) {
    const name = err && err.name;
    if (name === 'NotAllowedError' || name === 'SecurityError' || name === 'PermissionDeniedError') return MESSAGES.blocked;
    if (name === 'NotFoundError' || name === 'DevicesNotFoundError' || name === 'OverconstrainedError') return MESSAGES.nomic;
    if (name === 'NotReadableError' || name === 'AbortError') return MESSAGES.busy;
    return 'Could not access the microphone (' + (name || 'unknown error') + ').';
  }
  function startRecognition(Rec) {
    let finalText = '', failed = false;
    try {
      const rec = new Rec();
      state.rec = rec; rec.interimResults = true; rec.continuous = false; rec.lang = 'en-US';
      rec.onstart = () => { status(''); setUi(true); };
      rec.onresult = (ev) => {
        let interim = '';
        for (let i = ev.resultIndex || 0; i < ev.results.length; i += 1) {
          const t = ev.results[i][0] ? String(ev.results[i][0].transcript || '') : '';
          if (ev.results[i].isFinal) finalText += t + ' '; else interim += t;
        }
        if (state.ctx.input) state.ctx.input.value = (finalText + interim).trim();
      };
      rec.onerror = (ev) => { failed = true; setUi(false); const m = errorMessage(ev && ev.error); if (m) warn(m); };
      rec.onend = () => {
        const wasListening = state.listening; setUi(false);
        if (!failed && wasListening && !finalText.trim() && !(state.ctx.input && state.ctx.input.value.trim())) warn(MESSAGES.nospeech);
        if (state.ctx.input && typeof state.ctx.input.focus === 'function') state.ctx.input.focus();
      };
      rec.start();
    } catch (err) { setUi(false); warn('Could not start voice input (' + ((err && err.name) || 'error') + '). Please try again.'); }
  }
  function preflight() {
    const md = navigator.mediaDevices;
    if (!md || typeof md.getUserMedia !== 'function') return Promise.resolve();
    return md.getUserMedia({ audio: true }).then((stream) => { stream.getTracks().forEach((t) => t.stop()); });
  }
  function onClick() {
    if (state.starting) return;
    if (state.listening) { stop(); status(''); return; }
    const Rec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Rec) { warn(MESSAGES.unsupported); return; }
    const secure = window.isSecureContext === true || /^(localhost|127\.0\.0\.1|\[::1\])$/.test((window.location && window.location.hostname) || '');
    if (!secure) { warn(MESSAGES.insecure); return; }
    state.starting = true; status('');
    preflight().then(() => { state.starting = false; startRecognition(Rec); }).catch((err) => { state.starting = false; setUi(false); warn(mediaErrorMessage(err)); });
  }
  function bind(ctx) {
    if (!ctx || !ctx.micBtn || ctx.micBtn.dataset.micBound === '1') return;
    ctx.micBtn.dataset.micBound = '1'; state.ctx = ctx;
    ctx.micBtn.addEventListener('click', () => { state.ctx = ctx; onClick(); });
  }
  window.EpDockVoice = { bind, stop, clearStatus: () => status('') };
})();
