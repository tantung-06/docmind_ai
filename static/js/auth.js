/* ── auth.js — Auth modal + navbar user UI ─────────────────────── */

(function () {
  "use strict";

  // ── State ────────────────────────────────────────────────────────
  let currentUser = null;   // { id, username, display_name } | null

  // ── DOM helpers ──────────────────────────────────────────────────
  const $ = (sel, ctx = document) => ctx.querySelector(sel);
  const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];

  // ── Build HTML ───────────────────────────────────────────────────
  function injectModal() {
    const html = `
<div class="auth-overlay" id="authOverlay">
  <div class="auth-modal" role="dialog" aria-modal="true" aria-label="Đăng nhập / Đăng ký">
    <div class="auth-modal-header">
      <div class="auth-modal-logo">DocMind AI</div>
      <div class="auth-modal-tagline">Đăng nhập để lưu lịch sử trò chuyện</div>
    </div>

    <div class="auth-tabs">
      <div class="auth-tab active" id="tabLogin" onclick="AUTH.switchTab('login')">
        <i class="bi bi-box-arrow-in-right"></i> Đăng nhập
      </div>
      <div class="auth-tab" id="tabRegister" onclick="AUTH.switchTab('register')">
        <i class="bi bi-person-plus"></i> Đăng ký
      </div>
    </div>

    <div class="auth-form-area">

      <!-- Login form -->
      <div class="auth-form active" id="formLogin">
        <div class="auth-error" id="loginError"><i class="bi bi-exclamation-circle"></i> <span></span></div>
        <div class="auth-field">
          <label>Tên đăng nhập</label>
          <input class="auth-input" id="loginUsername" type="text"
                 placeholder="Nhập tên đăng nhập" autocomplete="username">
        </div>
        <div class="auth-field">
          <label>Mật khẩu</label>
          <div class="auth-input-wrap">
            <input class="auth-input" id="loginPassword" type="password"
                   placeholder="Nhập mật khẩu" autocomplete="current-password">
            <button class="auth-eye-btn" onclick="AUTH.togglePwd('loginPassword',this)" tabindex="-1">
              <i class="bi bi-eye"></i>
            </button>
          </div>
        </div>
        <button class="auth-submit-btn" id="loginBtn" onclick="AUTH.login()">
          <i class="bi bi-box-arrow-in-right"></i> Đăng nhập
        </button>
        <div class="auth-divider">hoặc</div>
        <button class="auth-guest-btn" onclick="AUTH.closeModal()">
          <i class="bi bi-person-dash"></i> Tiếp tục không lưu lịch sử
        </button>
      </div>

      <!-- Register form -->
      <div class="auth-form" id="formRegister">
        <div class="auth-error" id="registerError"><i class="bi bi-exclamation-circle"></i> <span></span></div>
        <div class="auth-success" id="registerSuccess"><i class="bi bi-check-circle"></i> <span></span></div>
        <div class="auth-field">
          <label>Tên hiển thị</label>
          <input class="auth-input" id="regDisplayName" type="text"
                 placeholder="Tên của bạn (tuỳ chọn)" autocomplete="name">
        </div>
        <div class="auth-field">
          <label>Tên đăng nhập <span style="color:var(--red)">*</span></label>
          <input class="auth-input" id="regUsername" type="text"
                 placeholder="Ít nhất 3 ký tự" autocomplete="username">
        </div>
        <div class="auth-field">
          <label>Mật khẩu <span style="color:var(--red)">*</span></label>
          <div class="auth-input-wrap">
            <input class="auth-input" id="regPassword" type="password"
                   placeholder="Ít nhất 6 ký tự" autocomplete="new-password">
            <button class="auth-eye-btn" onclick="AUTH.togglePwd('regPassword',this)" tabindex="-1">
              <i class="bi bi-eye"></i>
            </button>
          </div>
        </div>
        <button class="auth-submit-btn" id="registerBtn" onclick="AUTH.register()">
          <i class="bi bi-person-check"></i> Tạo tài khoản
        </button>
        <div class="auth-divider">hoặc</div>
        <button class="auth-guest-btn" onclick="AUTH.closeModal()">
          <i class="bi bi-person-dash"></i> Tiếp tục không lưu lịch sử
        </button>
      </div>

    </div>
  </div>
</div>`;
    document.body.insertAdjacentHTML("beforeend", html);

    // Close on backdrop click
    $("#authOverlay").addEventListener("click", function (e) {
      if (e.target === this) AUTH.closeModal();
    });

    // Enter key on inputs
    document.addEventListener("keydown", function (e) {
      if (e.key !== "Enter") return;
      const overlay = $("#authOverlay");
      if (!overlay || !overlay.classList.contains("active")) return;
      const activeTab = $(".auth-tab.active")?.id;
      if (activeTab === "tabLogin") AUTH.login();
      else AUTH.register();
    });
  }

  // ── Navbar injection ─────────────────────────────────────────────
  function renderNavbarAuth() {
    const targets = $$(".navbar .ms-auto, .navbar .navbar-nav + div, .navbar .d-flex.align-items-center");
    // Find the last flex container in navbar
    const navFlex = document.querySelector(".navbar .ms-auto.d-flex") ||
                    document.querySelector(".navbar .d-flex.align-items-center.gap-3") ||
                    document.querySelector(".navbar .ms-auto");
    if (!navFlex) return;

    // Remove previous auth widget if any
    const old = navFlex.querySelector(".nav-auth-widget");
    if (old) old.remove();

    const widget = document.createElement("div");
    widget.className = "nav-auth-widget";
    widget.style.cssText = "display:flex;align-items:center;";

    if (currentUser) {
      const initials = currentUser.display_name.slice(0, 2).toUpperCase();
      widget.innerHTML = `
        <div class="nav-user-area" id="navUserArea">
          <div class="nav-avatar">${initials}</div>
          <span class="nav-user-name">${currentUser.display_name}</span>
          <i class="bi bi-chevron-down" style="font-size:.65rem;color:var(--text2)"></i>
          <div class="nav-user-dropdown" id="navUserDropdown">
            <div style="padding:.6rem .9rem .4rem;font-size:.78rem;color:var(--text2)">
              <strong style="color:var(--text)">${currentUser.display_name}</strong><br>
              @${currentUser.username}
            </div>
            <div class="nav-dropdown-divider"></div>
            <div class="nav-dropdown-item" style="color:var(--accent);font-size:.78rem;cursor:default">
              <i class="bi bi-check-circle-fill"></i> Lịch sử được lưu
            </div>
            <div class="nav-dropdown-divider"></div>
            <button class="nav-dropdown-item danger" onclick="AUTH.logout()">
              <i class="bi bi-box-arrow-right"></i> Đăng xuất
            </button>
          </div>
        </div>`;

      // Toggle dropdown on click
      setTimeout(() => {
        const area = document.getElementById("navUserArea");
        const drop = document.getElementById("navUserDropdown");
        if (area && drop) {
          area.addEventListener("click", function (e) {
            e.stopPropagation();
            drop.classList.toggle("open");
          });
          document.addEventListener("click", () => drop.classList.remove("open"));
        }
      }, 0);
    } else {
      widget.innerHTML = `
        <button class="btn-nav-login" onclick="AUTH.openModal()">
          <i class="bi bi-person-circle"></i> Đăng nhập
        </button>`;
    }

    navFlex.appendChild(widget);
  }

  // ── History notice in chat ────────────────────────────────────────
  function updateHistoryNotice() {
    const inputArea = document.querySelector(".chat-input-area");
    if (!inputArea) return;

    const existing = inputArea.querySelector(".history-notice");
    if (existing) existing.remove();

    if (!currentUser) {
      const notice = document.createElement("div");
      notice.className = "history-notice";
      notice.innerHTML = `<i class="bi bi-info-circle"></i>
        Bạn đang dùng chế độ khách — lịch sử sẽ không được lưu.
        <a onclick="AUTH.openModal()">Đăng nhập để lưu</a>`;
      inputArea.insertBefore(notice, inputArea.firstChild);
    }
  }

  // ── API calls ─────────────────────────────────────────────────────
  async function checkMe() {
    try {
      const r = await fetch("/api/me");
      const d = await r.json();
      currentUser = d.logged_in ? d.user : null;
    } catch {
      currentUser = null;
    }
    renderNavbarAuth();
    updateHistoryNotice();
    window.AUTH_USER = currentUser;
    document.dispatchEvent(new CustomEvent("authStateChanged", { detail: currentUser }));
  }

  // ── Public API ────────────────────────────────────────────────────
  window.AUTH = {
    openModal() {
      $("#authOverlay")?.classList.add("active");
      setTimeout(() => $("#loginUsername")?.focus(), 80);
    },
    closeModal() {
      $("#authOverlay")?.classList.remove("active");
    },
    switchTab(tab) {
      $$(".auth-tab").forEach(t => t.classList.toggle("active", t.id === `tab${capitalize(tab)}`));
      $$(".auth-form").forEach(f => f.classList.toggle("active", f.id === `form${capitalize(tab)}`));
      clearErrors();
    },
    togglePwd(inputId, btn) {
      const inp = document.getElementById(inputId);
      if (!inp) return;
      const show = inp.type === "password";
      inp.type = show ? "text" : "password";
      btn.querySelector("i").className = show ? "bi bi-eye-slash" : "bi bi-eye";
    },
    async login() {
      const username = (document.getElementById("loginUsername")?.value || "").trim();
      const password = (document.getElementById("loginPassword")?.value || "").trim();
      if (!username || !password) { showError("loginError", "Vui lòng điền đầy đủ thông tin"); return; }
      clearErrors();
      setLoading("loginBtn", true);
      try {
        const r = await fetch("/api/login", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username, password })
        });
        const d = await r.json();
        if (!r.ok) { showError("loginError", d.error || "Đăng nhập thất bại"); return; }
        currentUser = d.user;
        window.AUTH_USER = currentUser;
        AUTH.closeModal();
        renderNavbarAuth();
        updateHistoryNotice();
        document.dispatchEvent(new CustomEvent("authStateChanged", { detail: currentUser }));
        loadUserHistory();
      } catch { showError("loginError", "Lỗi kết nối máy chủ"); }
      finally { setLoading("loginBtn", false); }
    },
    async register() {
      const username     = (document.getElementById("regUsername")?.value || "").trim();
      const password     = (document.getElementById("regPassword")?.value || "").trim();
      const display_name = (document.getElementById("regDisplayName")?.value || "").trim();
      if (!username || !password) { showError("registerError", "Vui lòng điền đầy đủ thông tin bắt buộc"); return; }
      clearErrors();
      setLoading("registerBtn", true);
      try {
        const r = await fetch("/api/register", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username, password, display_name })
        });
        const d = await r.json();
        if (!r.ok) { showError("registerError", d.error || "Đăng ký thất bại"); return; }
        currentUser = d.user;
        window.AUTH_USER = currentUser;
        AUTH.closeModal();
        renderNavbarAuth();
        updateHistoryNotice();
        document.dispatchEvent(new CustomEvent("authStateChanged", { detail: currentUser }));
      } catch { showError("registerError", "Lỗi kết nối máy chủ"); }
      finally { setLoading("registerBtn", false); }
    },
    async logout() {
      await fetch("/api/logout", { method: "POST" });
      currentUser = null;
      window.AUTH_USER = null;
      renderNavbarAuth();
      updateHistoryNotice();
      document.dispatchEvent(new CustomEvent("authStateChanged", { detail: null }));
      // Clear chat display if on chat page
      const msgs = document.getElementById("chatMessages");
      if (msgs) renderWelcome(msgs);
    },
    getUser() { return currentUser; },
    isLoggedIn() { return currentUser !== null; },
  };

  // ── Helpers ───────────────────────────────────────────────────────
  function capitalize(s) { return s.charAt(0).toUpperCase() + s.slice(1); }

  function showError(id, msg) {
    const el = document.getElementById(id);
    if (!el) return;
    el.querySelector("span").textContent = msg;
    el.classList.add("show");
  }
  function clearErrors() {
    $$(".auth-error, .auth-success").forEach(el => el.classList.remove("show"));
  }
  function setLoading(btnId, loading) {
    const btn = document.getElementById(btnId);
    if (!btn) return;
    if (loading) {
      btn.disabled = true;
      btn.dataset.origHtml = btn.innerHTML;
      btn.innerHTML = `<span class="btn-spinner"></span> Đang xử lý...`;
    } else {
      btn.disabled = false;
      btn.innerHTML = btn.dataset.origHtml || btn.innerHTML;
    }
  }

  // ── Load history into chat on login ──────────────────────────────
  async function loadUserHistory() {
    const msgs = document.getElementById("chatMessages");
    if (!msgs) return;
    try {
      const r = await fetch("/api/chat/history");
      const d = await r.json();
      if (!d.history || !d.history.length) return;

      // Clear welcome
      msgs.innerHTML = "";

      // Render existing messages
      d.history.forEach(m => {
        if (m.role === "user" || m.role === "assistant") {
          appendHistoryMessage(msgs, m.role, m.content, m.timestamp);
        }
      });
      msgs.scrollTop = msgs.scrollHeight;
    } catch {}
  }

  function appendHistoryMessage(container, role, text, timestamp) {
    const div = document.createElement("div");
    div.className = `message ${role}`;

    const avatar = role === "user"
      ? `<div class="message-avatar">👤</div>`
      : `<div class="message-avatar">⬡</div>`;

    const timeStr = timestamp
      ? new Date(timestamp).toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" })
      : "";

    const escaped = text
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.+?)\*/g, "<em>$1</em>")
      .replace(/`(.+?)`/g, `<code style="background:rgba(108,99,255,.15);padding:.1em .4em;border-radius:3px;">$1</code>`)
      .replace(/\n/g, "<br>");

    div.innerHTML = `${avatar}<div><div class="message-bubble">${escaped}</div>
      <div class="message-time">${timeStr}</div></div>`;
    container.appendChild(div);
  }

  function renderWelcome(msgs) {
    msgs.innerHTML = `
      <div class="welcome-msg">
        <h4>Xin chào! Tôi là DocMind AI</h4>
        <p>Hãy tải lên tài liệu và đặt câu hỏi. Tôi sẽ đọc và phân tích giúp bạn.</p>
        <div class="welcome-hints">
          <div class="hint-chip" onclick="fillHint&&fillHint(this)">Tóm tắt nội dung chính của tài liệu</div>
          <div class="hint-chip" onclick="fillHint&&fillHint(this)">Liệt kê các điểm quan trọng nhất</div>
          <div class="hint-chip" onclick="fillHint&&fillHint(this)">Tài liệu này nói về chủ đề gì?</div>
          <div class="hint-chip" onclick="fillHint&&fillHint(this)">So sánh các nội dung trong tài liệu</div>
        </div>
      </div>`;
  }

  // ── Init ──────────────────────────────────────────────────────────
  document.addEventListener("DOMContentLoaded", () => {
    injectModal();
    checkMe();
  });

})();