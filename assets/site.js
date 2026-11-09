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

  var root = document.documentElement;

  /* Status strip: wrap the items and add a hidden copy, so on phones it can loop as a ticker */
  var strip = $('#txt-status-strip');
  if (strip && !strip.querySelector('.ticker')) {
    var tk = document.createElement('div'); tk.className = 'ticker';
    while (strip.firstChild) tk.appendChild(strip.firstChild);
    strip.appendChild(tk);
    var copy = tk.cloneNode(true); copy.setAttribute('aria-hidden', 'true');
    strip.appendChild(copy);
  }

  /* ── 3D trend-field background ──────────────────────────────────────────
     A perspective landscape of process-trend lines, pinned to the viewport so it
     stays behind the content all the way down the page. It drifts forward on its
     own, and scrolling pushes the camera further along, so the field flies toward
     you as you scroll. Static for reduced-motion visitors, paused in hidden tabs. */
  var redrawBg = function () {};
  (function () {
    var cv = document.createElement('canvas');
    cv.id = 'bg3d'; cv.setAttribute('aria-hidden', 'true');
    document.body.insertBefore(cv, document.body.firstChild);
    var ctx = cv.getContext && cv.getContext('2d');
    if (!ctx) return;

    var small = Math.min(innerWidth, innerHeight) < 700;
    var ROWS = small ? 20 : 30;          /* depth rows on screen */
    var STEP = small ? 16 : 12;          /* px between line vertices */
    var DOT = 1.6;                       /* world units between sample dots */
    var CAM = 1.5;                       /* camera height above the field */
    var FRAME = small ? 50 : 33;         /* ms per frame: ~20 fps phone, ~30 fps desktop */
    var SCROLL = 0.0045;                 /* rows travelled per px scrolled */
    var PAL = {                          /* the product's trend colours */
      dark:  { line: ['0,200,255', '224,179,26', '25,201,138'], a: 0.26 },
      light: { line: ['0,105,150', '150,110,0', '10,125,85'],   a: 0.24 }
    };
    var W = 0, H = 0, dpr = 1, raf = 0, last = 0, t0 = performance.now();
    var scrollPos = window.scrollY || 0;

    /* fixed pseudo-random wobble so the lines read as real process data, not pure sines */
    var noise = [], seed = 7;
    for (var k = 0; k < 512; k++) { seed = (seed * 9301 + 49297) % 233280; noise.push(seed / 233280 - 0.5); }
    function nz(x) { var f = Math.floor(x), u = x - f, i0 = f & 511; u = u * u * (3 - 2 * u);
      return noise[i0] * (1 - u) + noise[(i0 + 1) & 511] * u; }
    function field(x, z, t) {
      return 1.05 * Math.sin(x * 0.21 + z * 0.09 + t * 0.25) * Math.cos(z * 0.16 - x * 0.07)
           + 0.5 * Math.sin(x * 0.55 - z * 0.31 + t * 0.4)
           + 0.9 * nz(x * 0.9 + z * 1.7) + 0.5 * nz(x * 2.3 - z * 0.6 + 40);
    }

    function size() {
      dpr = Math.min(window.devicePixelRatio || 1, 1.5);
      W = innerWidth; H = innerHeight;
      cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    function draw(now) {
      var t = reduceMotion ? 0 : (now - t0) / 1000;
      var target = window.scrollY || 0;
      scrollPos += (target - scrollPos) * (reduceMotion ? 1 : 0.12);   /* glide, don't jump */
      var cam = t * 0.5 + (reduceMotion ? 0 : scrollPos * SCROLL);
      var pal = PAL[root.getAttribute('data-theme') === 'light' ? 'light' : 'dark'];
      var horizon = H * 0.42, F = Math.min(W, 1400) * 0.75;
      var z0 = Math.floor(cam), frac = cam - z0;

      ctx.clearRect(0, 0, W, H);
      ctx.lineWidth = 1; ctx.lineJoin = 'round';
      for (var i = ROWS; i >= 1; i--) {                 /* far to near */
        var wz = z0 + i, d = 1.2 + (i - frac);
        var n = 1 - d / (ROWS + 1.2); if (n <= 0) continue;
        var alpha = pal.a * n * n;
        var col = pal.line[wz % 4 === 1 ? 1 : wz % 4 === 3 ? 2 : 0];   /* mostly cyan, with amber and green rows */
        var s = F / d;
        if (horizon + (CAM - 1.6) * s > H + 40) continue;              /* entirely below the screen */

        ctx.strokeStyle = 'rgba(' + col + ',' + alpha.toFixed(3) + ')';
        ctx.beginPath();
        for (var sx = -STEP; sx <= W + STEP; sx += STEP) {
          var X = (sx - W / 2) / s;
          var y = horizon + (CAM - field(X, wz, t) * 0.55) * s;
          if (sx === -STEP) ctx.moveTo(sx, y); else ctx.lineTo(sx, y);
        }
        ctx.stroke();

        /* sample dots, fixed in the world so they ride along with their line */
        ctx.fillStyle = 'rgba(' + col + ',' + Math.min(1, alpha * 1.7).toFixed(3) + ')';
        var r = 0.6 + 1.8 * n, xm = (W / 2 + 10) / s;
        for (var X2 = Math.ceil(-xm / DOT) * DOT; X2 <= xm; X2 += DOT) {
          var px = W / 2 + X2 * s, py = horizon + (CAM - field(X2, wz, t) * 0.55) * s;
          ctx.fillRect(px - r / 2, py - r / 2, r, r);
        }
      }
    }

    function frame(now) {
      raf = 0;
      if (document.hidden) return;
      if (now - last >= FRAME) { last = now; draw(now); }
      raf = requestAnimationFrame(frame);
    }
    function start() { if (!raf && !reduceMotion && !document.hidden) raf = requestAnimationFrame(frame); }

    redrawBg = function () { draw(performance.now()); };
    size(); redrawBg();
    window.addEventListener('resize', function () { size(); redrawBg(); });
    document.addEventListener('visibilitychange', start);
    start();
  })();

  /* ── Light / dark theme ─────────────────────────────────────────────────
     The inline script in <head> sets data-theme before first paint (saved choice,
     else the OS setting). This wires up the toggle and keeps following the OS
     until the visitor picks a theme themselves. */
  var tBtn = $('#themeBtn'), tIcon = $('#themeIcon'), tMeta = $('meta[name="theme-color"]');
  var SUN = '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>';
  var MOON = '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/>';
  function curTheme() { return root.getAttribute('data-theme') === 'light' ? 'light' : 'dark'; }
  function showTheme() {
    var dark = curTheme() === 'dark';
    if (tIcon) tIcon.innerHTML = dark ? SUN : MOON;
    if (tBtn) tBtn.setAttribute('aria-label', dark ? 'Switch to light mode' : 'Switch to dark mode');
    if (tMeta) tMeta.setAttribute('content', dark ? '#080c10' : '#eef3f6');
    redrawBg();
  }
  function setTheme(t, remember) {
    root.setAttribute('data-theme', t); showTheme();
    if (remember) { try { localStorage.setItem('gw-theme', t); } catch (e) {} }
  }
  showTheme();
  if (tBtn) tBtn.addEventListener('click', function () { setTheme(curTheme() === 'dark' ? 'light' : 'dark', true); });
  if (window.matchMedia) {
    var mq = matchMedia('(prefers-color-scheme: light)');
    var follow = function (e) {
      var saved = null; try { saved = localStorage.getItem('gw-theme'); } catch (x) {}
      if (saved !== 'light' && saved !== 'dark') setTheme(e.matches ? 'light' : 'dark', false);
    };
    if (mq.addEventListener) mq.addEventListener('change', follow); else if (mq.addListener) mq.addListener(follow);
  }
})();
