/* 站点共享脚本：顶栏激活态 / 下拉互斥 / 移动端侧栏 / 目录滚动跟随 */
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
  // 5. 登录遮罩(当前页弹窗,不跳转) + 登录态三按钮(登录/宝多六花/退出登录)
  var RUN_API = window.__RUN_API__ || "http://127.0.0.1:8090";
  var homeBtn = document.querySelector(".topbar-home");
  var loginBtn = document.querySelector(".topbar-login");
  var logoutBtn = document.querySelector(".topbar-logout");
  function refreshAuthState() {
    var logged = !!sessionStorage.getItem("lab_token");
    if (homeBtn) homeBtn.style.display = logged ? "inline-flex" : "none";
    if (loginBtn) loginBtn.style.display = logged ? "none" : "inline-flex";
    if (logoutBtn) logoutBtn.style.display = logged ? "inline-flex" : "none";
  }
  refreshAuthState();
  if (logoutBtn) {
    logoutBtn.addEventListener("click", function () {
      var token = sessionStorage.getItem("lab_token");
      sessionStorage.removeItem("lab_token");
      sessionStorage.removeItem("lab_user");
      refreshAuthState();
      if (token) {
        fetch(RUN_API + "/api/v1/logout", {
          method: "POST",
          headers: { Authorization: "Bearer " + token, "Content-Type": "application/json" },
        }).catch(function () { /* 服务端注销尽力而为,本地会话已清 */ });
      }
      if (location.pathname !== "/") location.href = "/";
    });
  }

  var loginBtn = document.querySelector(".topbar-login");
  if (loginBtn) {
    loginBtn.setAttribute("title", "登录后可:按固定题号发起对照批次、跟踪与取消运行、查看单次运行的完整明细");
    var mask = document.createElement("div");
    mask.className = "login-mask";
    mask.innerHTML =
      '<div class="login-dialog" role="dialog" aria-label="所有者登录">' +
      "<h3>所有者登录</h3>" +
      '<p class="login-sub">仅项目所有者；密码连续输错 5 次将锁定 15 分钟。登录后可：</p>' +
      '<ul class="login-caps">' +
      "<li>按固定题号发起对照批次（重复次数 / 模型 / 冻结数据集 / 工具可见集 / Token 上限）</li>" +
      "<li>跟踪批次进度，运行中可协作取消</li>" +
      "<li>查看每次运行的完整明细：逐步事件流、模型与工具调用记录、护栏检查结果、耗时与 Token 消耗</li>" +
      "</ul>" +
      '<label>用户名<input class="login-user" type="text" autocomplete="username"></label>' +
      '<label>密码<input class="login-pass" type="password" autocomplete="current-password"></label>' +
      '<p class="login-err" aria-live="polite"></p>' +
      '<div class="login-row"><button type="button" class="login-cancel">取消</button>' +
      '<button type="button" class="login-go">登录</button></div></div>';
    document.body.appendChild(mask);
    var user = mask.querySelector(".login-user");
    var pass = mask.querySelector(".login-pass");
    var err = mask.querySelector(".login-err");

    function open() {
      err.textContent = "";
      mask.classList.add("show");
      user.focus();
    }
    function close() {
      mask.classList.remove("show");
      pass.value = "";
    }
    loginBtn.addEventListener("click", function (e) {
      e.preventDefault(); // 不跳转登录页,当前页遮罩
      open();
    });
    mask.addEventListener("click", function (e) {
      if (e.target === mask) close();
    });
    mask.querySelector(".login-cancel").addEventListener("click", close);
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") close();
    });
    pass.addEventListener("keydown", function (e) {
      if (e.key === "Enter") submit();
    });
    mask.querySelector(".login-go").addEventListener("click", submit);

    function submit() {
      if (!user.value.trim() || !pass.value) {
        err.textContent = "请输入用户名与密码";
        return;
      }
      err.textContent = "登录中…";
      fetch(RUN_API + "/api/v1/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: user.value.trim(), password: pass.value }),
      })
        .then(function (res) {
          return res.json().then(function (body) {
            return { status: res.status, body: body };
          });
        })
        .then(function (outcome) {
          if (outcome.status === 200 && outcome.body.token) {
            sessionStorage.setItem("lab_token", outcome.body.token);
            sessionStorage.setItem("lab_user", outcome.body.username || "");
            refreshAuthState();
            err.textContent = "登录成功，正在进入公告页…";
            setTimeout(function () {
              close();
              location.href = "/";
            }, 600);
          } else if (outcome.status === 423) {
            err.textContent = "账号已锁定，请稍后再试";
          } else {
            err.textContent = "用户名或密码错误（连续失败会锁定）";
          }
        })
        .catch(function () {
          err.textContent = "无法连接运行 API（服务未启动，或当前为无登录能力的公开部署）";
        });
    }
  }
})();
