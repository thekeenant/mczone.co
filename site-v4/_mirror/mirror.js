(function () {
  var tip = document.createElement("div");
  tip.textContent = "Sorry, this link is broken. It's not part of the archive.";
  tip.style.cssText = "position:fixed;z-index:100000;display:none;pointer-events:none;" +
    "background:#222;color:#fff;font:12px/1.4 Helvetica,Arial,sans-serif;padding:5px 9px;" +
    "border-radius:4px;box-shadow:0 2px 6px rgba(0,0,0,.3);white-space:nowrap";
  var css = document.createElement("style");
  css.textContent = "a[data-mz-missing]{cursor:not-allowed}";
  document.head.appendChild(css);
  document.body.appendChild(tip);
  function missing(el) { return el && el.closest && el.closest("a[data-mz-missing]"); }
  document.addEventListener("mousemove", function (e) {
    if (missing(e.target)) {
      tip.style.display = "block";
      tip.style.left = Math.min(e.clientX + 12, window.innerWidth - tip.offsetWidth - 8) + "px";
      tip.style.top = (e.clientY + 16) + "px";
    } else {
      tip.style.display = "none";
    }
  });
  document.addEventListener("click", function (e) {
    if (missing(e.target)) { e.preventDefault(); e.stopPropagation(); }
  }, true);
})();
