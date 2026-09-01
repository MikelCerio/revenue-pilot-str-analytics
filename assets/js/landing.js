/* ═══════════════════════════════════════════════════════════════
   RevenuePilot — Landing Page JavaScript
   Scroll animations, counter animations, navigation effects
   ═══════════════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {

  // ── Navbar scroll effect ──────────────────────────────────
  const nav = document.querySelector('.nav');
  window.addEventListener('scroll', () => {
    nav.classList.toggle('scrolled', window.scrollY > 40);
  });

  // ── Scroll fade-in animation ──────────────────────────────
  const fadeEls = document.querySelectorAll('.fade-in');
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry, i) => {
      if (entry.isIntersecting) {
        setTimeout(() => entry.target.classList.add('visible'), i * 80);
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.15, rootMargin: '0px 0px -40px 0px' });

  fadeEls.forEach(el => observer.observe(el));

  // ── Animated counters ─────────────────────────────────────
  const counters = document.querySelectorAll('[data-count]');
  let countersAnimated = false;

  const counterObserver = new IntersectionObserver((entries) => {
    if (countersAnimated) return;
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        countersAnimated = true;
        animateCounters();
        counterObserver.disconnect();
      }
    });
  }, { threshold: 0.3 });

  const statsBar = document.querySelector('.stats-bar');
  if (statsBar) counterObserver.observe(statsBar);

  function animateCounters() {
    counters.forEach(counter => {
      const target = counter.getAttribute('data-count');
      const prefix = counter.getAttribute('data-prefix') || '';
      const suffix = counter.getAttribute('data-suffix') || '';
      const isDecimal = target.includes('.');
      const end = parseFloat(target.replace(/,/g, ''));
      const duration = 2000;
      const start = performance.now();

      function step(timestamp) {
        const elapsed = timestamp - start;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        const current = eased * end;

        if (isDecimal) {
          counter.textContent = prefix + current.toFixed(1) + suffix;
        } else if (end >= 1000) {
          counter.textContent = prefix + Math.floor(current).toLocaleString('en-US') + suffix;
        } else {
          counter.textContent = prefix + Math.floor(current) + suffix;
        }

        if (progress < 1) requestAnimationFrame(step);
      }
      requestAnimationFrame(step);
    });
  }

  // ── Smooth scroll for nav links ───────────────────────────
  document.querySelectorAll('a[href^="#"]').forEach(link => {
    link.addEventListener('click', e => {
      e.preventDefault();
      const target = document.querySelector(link.getAttribute('href'));
      if (target) {
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });

  // ── Parallax for hero glow ────────────────────────────────
  const glow = document.querySelector('.hero-glow');
  if (glow) {
    window.addEventListener('mousemove', e => {
      const x = (e.clientX / window.innerWidth - 0.5) * 30;
      const y = (e.clientY / window.innerHeight - 0.5) * 30;
      glow.style.transform = `translate(calc(-50% + ${x}px), calc(-50% + ${y}px))`;
    });
  }
});
