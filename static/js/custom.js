/* ================================================
   RECRUTO — custom.js
   All UI interactions — mapped to original HTML
   ================================================ */
'use strict';

document.addEventListener('DOMContentLoaded', function () {

  /* ─── 1. Loading Screen ───────────────────── */
  var loader = document.getElementById('page-loader');
  if (loader) {
    setTimeout(function () { loader.classList.add('done'); }, 1550);
  }

  /* ─── 2. Custom Cursor ────────────────────── */
  var dot  = document.createElement('div'); dot.className  = 'c-dot';
  var ring = document.createElement('div'); ring.className = 'c-ring';
  document.body.appendChild(dot);
  document.body.appendChild(ring);

  var mx = 0, my = 0, rx = 0, ry = 0;

  document.addEventListener('mousemove', function (e) {
    mx = e.clientX; my = e.clientY;
    dot.style.left = mx + 'px';
    dot.style.top  = my + 'px';
  });

  (function trackRing() {
    rx += (mx - rx) * 0.11;
    ry += (my - ry) * 0.11;
    ring.style.left = rx + 'px';
    ring.style.top  = ry + 'px';
    requestAnimationFrame(trackRing);
  })();

  var hoverEls = document.querySelectorAll('a, button, .team-block-wrap, .menu-block-wrap');
  hoverEls.forEach(function (el) {
    el.addEventListener('mouseenter', function () {
      ring.style.width  = '54px';
      ring.style.height = '54px';
      ring.style.borderColor = 'rgba(0,212,255,0.75)';
      dot.style.transform = 'translate(-50%,-50%) scale(0.35)';
    });
    el.addEventListener('mouseleave', function () {
      ring.style.width  = '34px';
      ring.style.height = '34px';
      ring.style.borderColor = 'rgba(0,212,255,0.45)';
      dot.style.transform = 'translate(-50%,-50%) scale(1)';
    });
  });

  if ('ontouchstart' in window) {
    dot.style.display = ring.style.display = 'none';
  }

  /* ─── 3. Navbar scroll ────────────────────── */
  var navbar = document.querySelector('.navbar');

  function onScroll() {
    if (!navbar) return;
    if (window.scrollY > 55) navbar.classList.add('scrolled');
    else                     navbar.classList.remove('scrolled');
    setActiveNav();
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  /* ─── 4. Active nav on scroll ─────────────── */
  var sections = document.querySelectorAll('section[id]');
  var navLinks = document.querySelectorAll('.nav-link.click-scroll');

  function setActiveNav() {
    var current = '';
    sections.forEach(function (sec) {
      if (window.scrollY >= sec.offsetTop - 110) current = sec.getAttribute('id');
    });
    navLinks.forEach(function (lnk) {
      lnk.classList.remove('active');
      if (lnk.getAttribute('href') === '#' + current) lnk.classList.add('active');
    });
  }

  /* ─── 5. Smooth scroll — .click-scroll & .smoothscroll ── */
  document.querySelectorAll('a.click-scroll, a.smoothscroll').forEach(function (a) {
    a.addEventListener('click', function (e) {
      var href = this.getAttribute('href');
      if (href && href.charAt(0) === '#') {
        e.preventDefault();
        var target = document.querySelector(href);
        if (target) {
          window.scrollTo({ top: target.offsetTop - 75, behavior: 'smooth' });
          // close mobile menu
          var collapse = document.querySelector('.navbar-collapse.show');
          if (collapse) {
            var tog = document.querySelector('.navbar-toggler');
            if (tog) tog.click();
          }
        }
      }
    });
  });

  /* ─── 6. Scroll reveal ────────────────────── */
  var revealTargets = [
    '.about-section .col-lg-6',
    '.about-section .col-lg-5',
    '.team-block-wrap',
    '.menu-block-wrap',
    '.contact-section .col-lg-6',
    '.contact-section .col-lg-12',
    '.site-footer .col-lg-4',
    '.site-footer .col-lg-3',
  ];
  revealTargets.forEach(function (sel) {
    document.querySelectorAll(sel).forEach(function (el, i) {
      el.classList.add('reveal');
      el.style.transitionDelay = (i * 0.1) + 's';
    });
  });

  var revealObs = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        revealObs.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1, rootMargin: '0px 0px -36px 0px' });

  document.querySelectorAll('.reveal').forEach(function (el) { revealObs.observe(el); });

  /* ─── 7. Hero text entrance ───────────────── */
  var h1 = document.querySelector('.hero-section h1');
  if (h1) {
    h1.style.cssText += 'opacity:0;transform:translateY(28px);transition:opacity .8s cubic-bezier(.4,0,.2,1),transform .8s cubic-bezier(.4,0,.2,1);';
    setTimeout(function () { h1.style.opacity = '1'; h1.style.transform = 'translateY(0)'; }, 180);
  }

  var heroSubs = document.querySelectorAll('.hero-section .btn, .hero-section p');
  heroSubs.forEach(function (el, i) {
    el.style.cssText += 'opacity:0;transform:translateY(18px);transition:opacity .65s cubic-bezier(.4,0,.2,1),transform .65s cubic-bezier(.4,0,.2,1);';
    setTimeout(function () { el.style.opacity = '1'; el.style.transform = 'translateY(0)'; }, 380 + i * 110);
  });

  /* ─── 8. Particle canvas on hero ─────────── */
  var heroSec = document.querySelector('.hero-section');
  if (heroSec) {
    var cvs = document.createElement('canvas');
    cvs.style.cssText = 'position:absolute;inset:0;z-index:1;pointer-events:none;opacity:0.45;';
    heroSec.appendChild(cvs);
    var ctx = cvs.getContext('2d');
    var W, H, pts;

    function initPts() {
      W = cvs.width  = heroSec.offsetWidth;
      H = cvs.height = heroSec.offsetHeight;
      pts = Array.from({ length: 52 }, function () {
        return {
          x: Math.random() * W, y: Math.random() * H,
          r: Math.random() * 1.4 + 0.4,
          vx: (Math.random() - 0.5) * 0.38,
          vy: (Math.random() - 0.5) * 0.38,
          a: Math.random() * 0.55 + 0.18
        };
      });
    }

    function drawPts() {
      ctx.clearRect(0, 0, W, H);
      pts.forEach(function (p) {
        p.x += p.vx; p.y += p.vy;
        if (p.x < 0 || p.x > W) p.vx *= -1;
        if (p.y < 0 || p.y > H) p.vy *= -1;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(0,212,255,' + p.a + ')';
        ctx.fill();
      });
      for (var i = 0; i < pts.length; i++) {
        for (var j = i + 1; j < pts.length; j++) {
          var dx = pts[i].x - pts[j].x, dy = pts[i].y - pts[j].y;
          var d  = Math.sqrt(dx * dx + dy * dy);
          if (d < 95) {
            ctx.beginPath();
            ctx.moveTo(pts[i].x, pts[i].y);
            ctx.lineTo(pts[j].x, pts[j].y);
            ctx.strokeStyle = 'rgba(0,212,255,' + (0.11 * (1 - d / 95)) + ')';
            ctx.lineWidth = 0.5;
            ctx.stroke();
          }
        }
      }
      requestAnimationFrame(drawPts);
    }

    initPts(); drawPts();
    window.addEventListener('resize', initPts);
  }

  /* ─── 9. Parallax hero on scroll ─────────── */
  var heroCont = document.querySelector('.hero-section .container');
  window.addEventListener('scroll', function () {
    if (!heroCont || window.scrollY > window.innerHeight) return;
    heroCont.style.transform = 'translateY(' + (window.scrollY * 0.22) + 'px)';
    heroCont.style.opacity   = String(Math.max(0, 1 - window.scrollY / (window.innerHeight * 0.55)));
  }, { passive: true });

  /* ─── 10. Feature cards — 3D tilt ────────── */
  document.querySelectorAll('.team-block-wrap').forEach(function (card) {
    card.addEventListener('mousemove', function (e) {
      var r  = this.getBoundingClientRect();
      var rx = ((e.clientY - r.top  - r.height / 2) / (r.height / 2)) * -7;
      var ry = ((e.clientX - r.left - r.width  / 2) / (r.width  / 2)) * 7;
      this.style.transform = 'translateY(-6px) rotateX(' + rx + 'deg) rotateY(' + ry + 'deg)';
    });
    card.addEventListener('mouseleave', function () {
      this.style.transform = '';
    });
  });

  /* ─── 11. Ripple on buttons ───────────────── */
  document.querySelectorAll('.btn-primary, .btn-success, .custom-btn').forEach(function (btn) {
    btn.style.position = 'relative';
    btn.style.overflow = 'hidden';
    btn.addEventListener('click', function (e) {
      var r = this.getBoundingClientRect();
      var size = Math.max(r.width, r.height);
      var ripple = document.createElement('span');
      ripple.style.cssText = [
        'position:absolute',
        'border-radius:50%',
        'background:rgba(255,255,255,0.18)',
        'pointer-events:none',
        'transform:scale(0)',
        'animation:ripple .52s linear',
        'width:' + size + 'px',
        'height:' + size + 'px',
        'left:' + (e.clientX - r.left - size / 2) + 'px',
        'top:' + (e.clientY - r.top  - size / 2) + 'px',
      ].join(';');
      this.appendChild(ripple);
      setTimeout(function () { ripple.remove(); }, 540);
    });
  });

  /* ─── 12. Contact form feedback ───────────── */
  var form = document.querySelector('.contact-form');
  if (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var btn = this.querySelector('button[type="submit"]');
      var orig = btn.textContent;
      btn.textContent = '✓ Message Sent!';
      btn.style.background = 'linear-gradient(135deg,#10b981,#047857)';
      setTimeout(function () {
        btn.textContent = orig;
        btn.style.background = '';
        form.reset();
      }, 3000);
    });
  }

  /* ─── 13. Inject ripple keyframe ─────────── */
  var style = document.createElement('style');
  style.textContent = '@keyframes ripple{to{transform:scale(2.6);opacity:0}}';
  document.head.appendChild(style);

  /* ─── 14. Logo letter hover effect ───────── */
  var brand = document.querySelector('.navbar-brand');
  if (brand) {
    var lastNode = brand.lastChild;
    if (lastNode && lastNode.nodeType === 3 && lastNode.textContent.trim()) {
      var letters = lastNode.textContent.trim().split('');
      var wrap = document.createElement('span');
      letters.forEach(function (ch, i) {
        var s = document.createElement('span');
        s.textContent = ch;
        s.style.cssText = 'display:inline-block;transition:color .18s,transform .18s;transition-delay:' + (i * 0.028) + 's';
        s.addEventListener('mouseenter', function () {
          this.style.color = 'var(--accent)';
          this.style.transform = 'translateY(-3px)';
        });
        s.addEventListener('mouseleave', function () {
          this.style.color = '';
          this.style.transform = '';
        });
        wrap.appendChild(s);
      });
      lastNode.replaceWith(wrap);
    }
  }

  console.log('%c RECRUTO %c loaded ✓', 'background:#00d4ff;color:#07090f;font-weight:800;padding:3px 8px;border-radius:4px','color:#5a6a80');
});