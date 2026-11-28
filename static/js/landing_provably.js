(function () {
  function initEduPredictPreloader() {
    var preloader = document.getElementById('ep-preloader');
    if (!preloader) return;
    var skipBtn = document.getElementById('ep-preloader-skip');
    var dismissed = false;
    var holdTimer = null;
    var removeTimer = null;

    function finishNow() {
      document.body.classList.remove('ep-preloader-active');
      if (preloader && preloader.parentNode) {
        preloader.parentNode.removeChild(preloader);
      }
    }

    function dismiss(instant) {
      if (dismissed) return;
      dismissed = true;
      if (holdTimer) window.clearTimeout(holdTimer);
      if (removeTimer) window.clearTimeout(removeTimer);
      document.body.classList.remove('ep-preloader-active');
      if (instant) {
        finishNow();
        return;
      }
      preloader.classList.add('is-leaving');
      removeTimer = window.setTimeout(finishNow, 580);
    }

    var reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduced) {
      dismiss(true);
      return;
    }

    document.body.classList.add('ep-preloader-active');
    holdTimer = window.setTimeout(function () {
      dismiss(false);
    }, 2250);

    if (skipBtn) {
      skipBtn.addEventListener('click', function () {
        dismiss(false);
      });
    }

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && !dismissed) {
        dismiss(false);
      }
    });
  }

  function tryPlay(video) {
    if (!video) return;
    video.muted = true;
    video.playsInline = true;
    try {
      var res = video.play();
      if (res && typeof res.catch === 'function') {
        res.catch(function () {});
      }
    } catch (err) {}
  }

  function initTargoVideos() {
    var videos = [].slice.call(document.querySelectorAll('video[data-targo-video]'));
    if (!videos.length) return;
    videos.forEach(tryPlay);

    var retryTimer = window.setInterval(function () {
      var anyPaused = false;
      videos.forEach(function (v) {
        if (v.paused) {
          anyPaused = true;
          tryPlay(v);
        }
      });
      if (!anyPaused) {
        window.clearInterval(retryTimer);
      }
    }, 1000);

    var unlock = function () {
      videos.forEach(tryPlay);
    };
    document.addEventListener('click', unlock, { once: true, passive: true });
    document.addEventListener('touchstart', unlock, { once: true, passive: true });
  }

  function initTargoMenu() {
    var btn = document.getElementById('targo-menu-toggle');
    var menu = document.getElementById('targo-mobile-menu');
    if (!btn || !menu) return;

    btn.addEventListener('click', function () {
      var open = menu.classList.toggle('is-open');
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    });

    window.addEventListener('resize', function () {
      if (window.innerWidth > 768 && menu.classList.contains('is-open')) {
        menu.classList.remove('is-open');
        btn.setAttribute('aria-expanded', 'false');
      }
    }, { passive: true });
  }

  function boot() {
    initEduPredictPreloader();
    initTargoVideos();
    initTargoMenu();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
