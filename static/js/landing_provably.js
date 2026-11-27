(function () {
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
    initTargoVideos();
    initTargoMenu();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
