/* Touchstone 文档站共享脚本：顶栏激活态 / 下拉互斥 / 移动端侧栏 / 目录滚动跟随 */
(function () {
  "use strict";

  // 1. 顶栏激活态：按当前路径标记本页链接与其所属分组
  var path = location.pathname.replace(/\.html$/, "").replace(/\/$/, "") || "/docs";
  document.querySelectorAll(".topnav a").forEach(function (a) {
    var href = (a.getAttribute("href") || "").replace(/\/$/, "");
    if (!href) return;
    if (path === href || (href !== "/docs" && path.indexOf(href) === 0)) {
      a.classList.add("active");
      var group = a.closest(".topnav-group");
      if (group) group.classList.add("here");
    }
  });

  // 2. 下拉互斥 + 点击外部收起
  var groups = Array.prototype.slice.call(document.querySelectorAll(".topnav-group"));
  groups.forEach(function (g) {
    var summary = g.querySelector("summary");
    if (summary) {
      summary.addEventListener("click", function (e) {
        e.preventDefault();
        var wasOpen = g.hasAttribute("open");
        groups.forEach(function (x) { x.removeAttribute("open"); });
        if (!wasOpen) g.setAttribute("open", "");
      });
    }
  });
  document.addEventListener("click", function (e) {
    groups.forEach(function (g) {
      if (!g.contains(e.target)) g.removeAttribute("open");
    });
  });

  // 3. 移动端：本页目录开合
  var btn = document.getElementById("sideBtn");
  var side = document.getElementById("docsSide");
  if (btn && side) {
    btn.addEventListener("click", function () { side.classList.toggle("open"); });
    side.addEventListener("click", function (e) {
      if (e.target.closest("a")) side.classList.remove("open");
    });
  }

  // 4. 目录滚动跟随（scroll-spy）
  var links = Array.prototype.slice.call(document.querySelectorAll('.docs-side a[href^="#"]'));
  var targets = links
    .map(function (a) { return document.getElementById(a.getAttribute("href").slice(1)); })
    .filter(Boolean);
  if (links.length && targets.length) {
    var spy = function () {
      var pos = window.scrollY + 140;
      var current = targets[0];
      targets.forEach(function (t) { if (t.offsetTop <= pos) current = t; });
      links.forEach(function (a) {
        a.classList.toggle("active", a.getAttribute("href") === "#" + current.id);
      });
    };
    window.addEventListener("scroll", spy, { passive: true });
    spy();
  }
})();
