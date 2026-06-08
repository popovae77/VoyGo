/* Voyago — editorial motion */
(function () {
  const style = document.createElement("style");
  style.textContent = `
    @keyframes pulseFab {
      0%, 100% { outline: 0 solid transparent; }
      50% { outline: 3px solid #2e5bff; outline-offset: 4px; }
    }
    @keyframes riseIn {
      from { opacity: 0; transform: translateY(12px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .hero, .search-panel, .results-shell {
      animation: riseIn .45s ease both;
    }
    input:focus-visible, select:focus-visible, button:focus-visible {
      outline: 2px solid #2e5bff;
      outline-offset: 2px;
    }
  `;
  document.head.appendChild(style);
})();
