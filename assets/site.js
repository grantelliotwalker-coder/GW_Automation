/* GW Automation - site behaviour. No third-party code, no tracking. */
(function () {
  'use strict';
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var reduceMotion = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* Year */
  var yr = $('#yr'); if (yr) yr.textContent = new Date().getFullYear();

  /* Mobile menu */
  var btn = $('#menuBtn'), nav = $('#nav');
  if (btn && nav) {
    btn.addEventListener('click', function () {
      var open = nav.classList.toggle('open');
      btn.setAttribute('aria-expanded', open);
    });
    nav.addEventListener('click', function (e) { if (e.target.tagName === 'A') nav.classList.remove('open'); });
  }

  /* Lightbox - click a screenshot to view it full size; click / Esc / Close to dismiss */
  var lb = $('#lightbox'), lbImg = $('#lbImg'), lbCap = $('#lbCap');
  function openLightbox(src, alt, cap) {
    if (!lb || !src) return;
    lbImg.src = src; lbImg.alt = alt || ''; lbCap.textContent = cap || '';
    lb.classList.add('open');
  }
  function closeLightbox() { if (lb) { lb.classList.remove('open'); lbImg.src = ''; } }
  $$('.shot').forEach(function (shot) {
    shot.addEventListener('click', function () {
      var img = $('img', shot);
      if (!img || !img.naturalWidth) return;
      var viewer = shot.closest('.viewer');
      var tab = viewer && $('[aria-selected="true"]', viewer);
      var cap = tab ? tab.textContent : (shot.parentNode.querySelector('.shot-cap') || {}).textContent;
      openLightbox(img.src, img.alt, cap);
    });
  });
  if (lb) {
    lb.addEventListener('click', closeLightbox);
    lbImg.addEventListener('click', function (e) { e.stopPropagation(); closeLightbox(); });
    $('#lbClose').addEventListener('click', closeLightbox);
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeLightbox(); });
  }

  /* Screenshot viewers - tabs swap one large screenshot */
  $$('[data-viewer]').forEach(function (v) {
    var tabs = $$('[role="tab"]', v), img = $('.shot img', v);
    function show(t) {
      tabs.forEach(function (x) { x.setAttribute('aria-selected', x === t ? 'true' : 'false'); x.tabIndex = x === t ? 0 : -1; });
      if (img.getAttribute('src') !== t.dataset.src) {
        img.style.opacity = '0';
        var pre = new Image();
        pre.onload = pre.onerror = function () { img.src = t.dataset.src; img.alt = t.dataset.alt || ''; img.style.opacity = '1'; };
        pre.src = t.dataset.src;
      }
    }
    tabs.forEach(function (t, i) {
      t.addEventListener('click', function () { show(t); });
      t.addEventListener('keydown', function (e) {
        var d = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0;
        if (!d) return;
        e.preventDefault();
        var n = tabs[(i + d + tabs.length) % tabs.length]; n.focus(); show(n);
      });
    });
    /* warm the cache for the other tabs once the page has settled */
    window.addEventListener('load', function () {
      setTimeout(function () { tabs.forEach(function (t) { var i = new Image(); i.src = t.dataset.src; }); }, 1500);
    });
  });

  /* Reveal on scroll */
  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) { if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); } });
    }, { threshold: 0.12 });
    $$('.rv').forEach(function (el) { io.observe(el); });

    /* Nav: highlight the section on screen */
    var links = $$('#nav a[href^="#"]');
    var map = {}; links.forEach(function (a) { map[a.getAttribute('href').slice(1)] = a; });
    var navIo = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting && map[en.target.id]) {
          links.forEach(function (a) { a.classList.remove('on'); });
          map[en.target.id].classList.add('on');
        }
      });
    }, { rootMargin: '-45% 0px -50% 0px' });
    Object.keys(map).forEach(function (id) { var el = document.getElementById(id); if (el) navIo.observe(el); });
  } else {
    $$('.rv').forEach(function (el) { el.classList.add('in'); });
  }

  /* Hero background - three slow trend lines in the product's chart colours */
  var cv = $('#heroLines');
  if (cv && cv.getContext) {
    var ctx = cv.getContext('2d'), W = 0, H = 0, dpr = 1, running = false, visible = true, last = 0, t0 = performance.now();
    var series = [
      { c: '27,161,214', a: 0.42, f: 1.7, p: 0.0, s: 0.050, y: 0.885, amp: 0.045 },
      { c: '224,179,26', a: 0.32, f: 1.2, p: 2.1, s: 0.035, y: 0.905, amp: 0.040 },
      { c: '25,201,138', a: 0.36, f: 2.3, p: 4.0, s: 0.065, y: 0.895, amp: 0.045 }
    ];
    /* fixed pseudo-random wobble so the lines look like real process data, not pure sines */
    var noise = []; var seed = 7;
    for (var i = 0; i < 512; i++) { seed = (seed * 9301 + 49297) % 233280; noise.push(seed / 233280 - 0.5); }
    function nz(x) { var i0 = Math.floor(x) & 511, f = x - Math.floor(x); return noise[i0] * (1 - f) + noise[(i0 + 1) & 511] * f; }
    function size() {
      var r = cv.getBoundingClientRect();
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      W = r.width; H = r.height;
      cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    function draw(now) {
      var t = (now - t0) / 1000;
      ctx.clearRect(0, 0, W, H);
      ctx.lineWidth = 1.6; ctx.lineJoin = 'round';
      series.forEach(function (sr) {
        ctx.strokeStyle = 'rgba(' + sr.c + ',' + sr.a + ')';
        ctx.beginPath();
        var step = Math.max(4, W / 260);
        for (var x = 0; x <= W + step; x += step) {
          var u = x / W, ph = u * Math.PI * 2 * sr.f + sr.p + t * sr.s * 6;
          var y = H * (sr.y + sr.amp * Math.sin(ph) + 0.010 * nz(u * 90 + t * sr.s * 40 + sr.p * 10));
          if (x === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
        }
        ctx.stroke();
      });
    }
    function frame(now) {
      if (!running) return;
      if (now - last > 33) { last = now; draw(now); }  /* ~30 fps is plenty for slow lines */
      requestAnimationFrame(frame);
    }
    function start() { if (!running && visible && !document.hidden && !reduceMotion) { running = true; requestAnimationFrame(frame); } }
    function stop() { running = false; }
    size(); draw(performance.now());
    window.addEventListener('resize', function () { size(); draw(performance.now()); });
    document.addEventListener('visibilitychange', function () { document.hidden ? stop() : start(); });
    if ('IntersectionObserver' in window) {
      new IntersectionObserver(function (e) { visible = e[0].isIntersecting; visible ? start() : stop(); }).observe(cv);
    }
    start();
  }
})();
