// Speaker carousel (simple fade rotator)
(function () {
  function initCarousel(root) {
    const slides = Array.from(root.querySelectorAll('.slide'));
    if (slides.length <= 1) return; // nothing to rotate

    let i = 0;
    const show = (idx) => {
      slides.forEach((el, n) => el.classList.toggle('active', n === idx));
    };
    show(i);

    // pre-load next images (browser will handle caching)
    slides.slice(1).forEach(img => {
      const a = new Image();
      a.src = img.src;
    });

    setInterval(() => {
      i = (i + 1) % slides.length;
      show(i);
    }, 4000); // 4s per slide
  }

  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.carousel-viewport').forEach(initCarousel);
  });
})();
