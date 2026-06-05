const SESSION_ID = `sess_${Date.now()}`;
let selectedDocIds = new Set();
let isStreaming = false;

// ── Ollama status ────────────────────────

// async function checkOllama() {
//   try {
//     const r = await fetch("/api/health");
//     const data = await r.json();
//     const badge = document.getElementById("ollamaStatusBadge");
//     if (!badge) return;
//     if (data.ollama.ok && data.ollama.model_ready) {
//       badge.textContent = "● Online";
//       badge.style.cssText = "background:rgba(74,222,128,.2);color:#4ade80;border:1px solid rgba(74,222,128,.4);padding:.25rem .6rem;border-radius:12px;font-size:.75rem;";
//     } else {
//       badge.textContent = "✕ Offline";
//       badge.style.cssText = "background:rgba(248,113,113,.2);color:#f87171;border:1px solid rgba(248,113,113,.4);padding:.25rem .6rem;border-radius:12px;font-size:.75rem;";
//     }
//   } catch {}
// }

// ── Load Docs into Sidebar ───────────────

async function loadSidebarDocs() {
  try {
    const r = await fetch("/api/documents");
    const data = await r.json();
    renderSidebarDocs(data.documents);
  } catch {}
}

function extIcon(ext) {
  return { pdf: "📄", docx: "📝", txt: "📃" }[ext] || "📎";
}

function renderSidebarDocs(docs) {
  const el = document.getElementById("sidebarDocs");
  if (!el) return;

  if (!docs.length) {
    el.innerHTML = `<div class="sidebar-empty"><i class="bi bi-cloud-upload"></i><span>Tải lên tài liệu để bắt đầu</span></div>`;
    return;
  }

  el.innerHTML = docs.map(d => `
    <div class="sidebar-doc-item ${selectedDocIds.has(d.id) ? 'selected' : ''}"
         id="sdi_${d.id}" onclick="toggleDoc('${d.id}', this)">
      <span class="doc-item-icon">${extIcon(d.ext)}</span>
      <div style="flex:1;min-width:0">
        <div class="doc-item-name" title="${d.name}">${d.name}</div>
        <div class="doc-item-meta">${d.word_count?.toLocaleString() ?? 0} từ</div>
      </div>
      <div class="doc-item-check"><i class="bi bi-check2"></i></div>
    </div>
  `).join("");

  updateSelectedBar();
}

function toggleDoc(id, el) {
  if (selectedDocIds.has(id)) {
    selectedDocIds.delete(id);
    el.classList.remove("selected");
  } else {
    selectedDocIds.add(id);
    el.classList.add("selected");
  }
  updateSelectedBar();
}

function selectAllDocs() {
  document.querySelectorAll(".sidebar-doc-item").forEach(el => {
    const id = el.id.replace("sdi_", "");
    selectedDocIds.add(id);
    el.classList.add("selected");
  });
  updateSelectedBar();
}
function deselectAllDocs() {
  selectedDocIds.clear();
  document.querySelectorAll(".sidebar-doc-item").forEach(el => el.classList.remove("selected"));
  updateSelectedBar();
}

function updateSelectedBar() {
  const bar  = document.getElementById("selectedDocsBar");
  const text = document.getElementById("selectedDocsText");
  const n = selectedDocIds.size;
  if (n > 0) {
    bar.style.display = "flex";
    text.textContent = `${n} tài liệu được chọn`;
  } else {
    bar.style.display = "none";
  }
}

// ── Sidebar file upload ──────────────────

function initSidebarUpload() {
  const input = document.getElementById("sidebarFile");
  if (!input) return;
  input.addEventListener("change", async () => {
    const files = [...input.files];
    if (!files.length) return;
    const prog = document.getElementById("sidebarUploadProgress");
    const msg  = document.getElementById("sidebarUploadMsg");
    prog.style.display = "block";
    for (const file of files) {
      msg.textContent = `Xử lý: ${file.name}`;
      const fd = new FormData();
      fd.append("file", file);
      try {
        await fetch("/api/upload", { method: "POST", body: fd });
      } catch {}
    }
    prog.style.display = "none";
    input.value = "";
    loadSidebarDocs();
  });
}

// ── Chat message rendering ───────────────

function nowStr() {
  return new Date().toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
}

function appendMessage(role, text, id = null) {
  const msgs = document.getElementById("chatMessages");

  // Remove welcome screen on first message
  const welcome = msgs.querySelector(".welcome-msg");
  if (welcome) welcome.remove();

  const div = document.createElement("div");
  div.className = `message ${role}`;
  if (id) div.id = id;

  const avatar = role === "user"
    ? `<div class="message-avatar">👤</div>`
    : `<div class="message-avatar">⬡</div>`;

  div.innerHTML = `
    ${avatar}
    <div>
      <div class="message-bubble">${escapeAndFormat(text)}</div>
      <div class="message-time">${nowStr()}</div>
    </div>
  `;

  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
  return div;
}

function appendTyping() {
  const msgs = document.getElementById("chatMessages");
  const div = document.createElement("div");
  div.className = "message assistant";
  div.id = "typing_indicator";
  div.innerHTML = `
    <div class="message-avatar">⬡</div>
    <div>
      <div class="message-bubble">
        <div class="typing-indicator"><span></span><span></span><span></span></div>
      </div>
    </div>
  `;
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
  return div;
}

function escapeAndFormat(text) {
  // Escape HTML then do basic markdown-ish formatting
  const escaped = text
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  return escaped
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/`(.+?)`/g, `<code style="background:rgba(108,99,255,.15);padding:.1em .4em;border-radius:3px;">$1</code>`)
    .replace(/\n/g, "<br>");
}

// ── Send message ─────────────────────────

async function sendMessage() {
  if (isStreaming) return;
  const input = document.getElementById("chatInput");
  const btn   = document.getElementById("sendBtn");
  const text  = input.value.trim();
  if (!text) return;

  input.value = "";
  input.style.height = "auto";
  isStreaming = true;
  btn.disabled = true;

  // User bubble
  appendMessage("user", text);

  // Typing indicator
  appendTyping();

  try {
    const body = {
      session_id: SESSION_ID,
      message:    text,
      doc_ids:    [...selectedDocIds],
    };

    const response = await fetch("/api/chat", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(body),
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.error || "Lỗi server");
    }

    // Remove typing, add streaming bubble
    document.getElementById("typing_indicator")?.remove();
    const aiDiv = appendMessage("assistant", "", "streaming_bubble");
    const bubble = aiDiv.querySelector(".message-bubble");

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let fullText = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop();

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const json = line.slice(6).trim();
        if (!json) continue;
        try {
          const data = JSON.parse(json);
          if (data.token) {
            fullText += data.token;
            bubble.innerHTML = escapeAndFormat(fullText);
            document.getElementById("chatMessages").scrollTop = 9999;
          }
          if (data.done) break;
        } catch {}
      }
    }

    aiDiv.id = "";
    const msgs = document.getElementById("chatMessages");
    msgs.scrollTop = msgs.scrollHeight;

  } catch (err) {
    document.getElementById("typing_indicator")?.remove();
    appendMessage("assistant", `⚠️ Lỗi: ${err.message}`);
  } finally {
    isStreaming = false;
    btn.disabled = false;
    input.focus();
  }
}

// ── Keyboard & UI helpers ────────────────

function handleKeyDown(e) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
}

function autoResize(el) {
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 150) + "px";
}

function fillHint(el) {
  const input = document.getElementById("chatInput");
  input.value = el.textContent.replace(/^[^\s]+\s/, "");
  input.focus();
  autoResize(input);
}

// ── Export & Clear ───────────────────────

function exportChat() {
  const msgs = document.getElementById("chatMessages");
  const bubbles = msgs.querySelectorAll(".message");
  if (!bubbles.length) { alert("Chưa có tin nhắn"); return; }

  let text = `DocMind AI - Lịch sử trò chuyện\n${"=".repeat(50)}\n`;
  bubbles.forEach(m => {
    const role   = m.classList.contains("user") ? "Bạn" : "AI";
    const bubble = m.querySelector(".message-bubble");
    const time   = m.querySelector(".message-time");
    text += `\n[${time?.textContent ?? ""}] ${role}:\n${bubble?.innerText ?? ""}\n`;
  });

  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement("a");
  a.href = url;
  a.download = `docmind_chat_${Date.now()}.txt`;
  a.click();
  URL.revokeObjectURL(url);
}

async function clearChat() {
  if (!confirm("Xóa toàn bộ lịch sử?")) return;
  await fetch(`/api/chat/clear/${SESSION_ID}`, { method: "DELETE" });
  const msgs = document.getElementById("chatMessages");
  msgs.innerHTML = `
    <div class="welcome-msg">
      <h4>Xin chào! Tôi là DocMind AI</h4>
      <p>Hãy tải lên tài liệu và đặt câu hỏi. Tôi sẽ đọc và phân tích giúp bạn.</p>
      <div class="welcome-hints">
        <div class="hint-chip" onclick="fillHint(this)">Tóm tắt nội dung chính của tài liệu</div>
        <div class="hint-chip" onclick="fillHint(this)">Liệt kê các điểm quan trọng nhất</div>
        <div class="hint-chip" onclick="fillHint(this)">Tài liệu này nói về chủ đề gì?</div>
        <div class="hint-chip" onclick="fillHint(this)">So sánh các nội dung trong tài liệu</div>
      </div>
    </div>
  `;
}

// ── Init ─────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  // checkOllama();
  loadSidebarDocs();
  initSidebarUpload();
  // setInterval(checkOllama, 30000);
  setInterval(loadSidebarDocs, 10000);
  document.getElementById("chatInput")?.focus();
});