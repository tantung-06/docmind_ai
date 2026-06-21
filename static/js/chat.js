let selectedDocIds = new Set();
let isStreaming    = false;
let currentConvId  = null;   // active conversation id (null = guest / new)
let allConversations = [];   // cached list from server

// Conversation history sidebar 

async function loadConversations() {
  const user = window.AUTH?.getUser?.();
  const notice  = document.getElementById("hsbGuestNotice");
  const listEl  = document.getElementById("hsbList");

  if (!user) {
    notice?.style && (notice.style.display = "flex");
    if (listEl) listEl.innerHTML = "";
    allConversations = [];
    return;
  }
  notice && (notice.style.display = "none");

  try {
    const r    = await fetch("/api/conversations");
    const data = await r.json();
    allConversations = data.conversations || [];
    renderConvList();
  } catch {}
}

function renderConvList() {
  const listEl = document.getElementById("hsbList");
  if (!listEl) return;

  if (!allConversations.length) {
    listEl.innerHTML = `<div class="hsb-empty"><i class="bi bi-chat-square-dots"></i><span>Chưa có cuộc trò chuyện nào</span></div>`;
    return;
  }

  listEl.innerHTML = allConversations.map(c => {
    const date = formatConvDate(c.updated_at);
    const isActive = c.id === currentConvId;
    return `
      <div class="hsb-item ${isActive ? 'active' : ''}" id="hci_${c.id}" onclick="switchConversation('${c.id}')">
        <div class="hsb-item-body">
          <div class="hsb-item-title" title="${escapeHtml(c.title)}">${escapeHtml(c.title)}</div>
          <div class="hsb-item-meta">${c.msg_count} tin · ${date}</div>
        </div>
        <div class="hsb-item-actions">
          <button class="hsb-action-btn" title="Đổi tên" onclick="openRenameModal('${c.id}','${escapeHtml(c.title)}',event)">
            <i class="bi bi-pencil"></i>
          </button>
          <button class="hsb-action-btn danger" title="Xóa" onclick="deleteConversation('${c.id}',event)">
            <i class="bi bi-trash3"></i>
          </button>
        </div>
      </div>`;
  }).join("");
}

function formatConvDate(iso) {
  if (!iso) return "";
  const d   = new Date(iso);
  const now  = new Date();
  const diff = now - d;
  if (diff < 60000)   return "Vừa xong";
  if (diff < 3600000) return `${Math.floor(diff/60000)} phút trước`;
  if (diff < 86400000) return `${Math.floor(diff/3600000)} giờ trước`;
  return d.toLocaleDateString("vi-VN");
}

function escapeHtml(s) {
  return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")
                  .replace(/"/g,"&quot;").replace(/'/g,"&#39;");
}

// Switch conversation 

async function switchConversation(convId) {
  if (isStreaming) return;
  if (convId === currentConvId) return;

  currentConvId = convId;

  // Update active state in list
  document.querySelectorAll(".hsb-item").forEach(el => el.classList.remove("active"));
  document.getElementById(`hci_${convId}`)?.classList.add("active");

  // Find conv in cache
  const conv = allConversations.find(c => c.id === convId);
  updateChatTitle(conv?.title || "Cuộc trò chuyện");

  // Load messages
  try {
    const r    = await fetch(`/api/conversations/${convId}`);
    const data = await r.json();
    renderConversationMessages(data.conversation?.messages || []);
  } catch {
    renderConversationMessages([]);
  }
}

function renderConversationMessages(messages) {
  const msgs = document.getElementById("chatMessages");
  if (!msgs) return;

  if (!messages.length) {
    msgs.innerHTML = getWelcomeHTML();
    return;
  }

  msgs.innerHTML = "";
  messages.forEach(m => {
    if (m.role === "user" || m.role === "assistant") {
      const div = buildMessageDiv(m.role, m.content, m.timestamp);
      msgs.appendChild(div);
    }
  });
  msgs.scrollTop = msgs.scrollHeight;
}

function buildMessageDiv(role, text, timestamp) {
  const div = document.createElement("div");
  div.className = `message ${role}`;
  const avatar = role === "user"
    ? `<div class="message-avatar">👤</div>`
    : `<div class="message-avatar">⬡</div>`;
  const timeStr = timestamp
    ? new Date(timestamp).toLocaleTimeString("vi-VN",{hour:"2-digit",minute:"2-digit"})
    : nowStr();
  div.innerHTML = `${avatar}<div><div class="message-bubble">${escapeAndFormat(text)}</div>
    <div class="message-time">${timeStr}</div></div>`;
  return div;
}

// New conversation 

async function newConversation() {
  const user = window.AUTH?.getUser?.();
  if (!user) { AUTH.openModal(); return; }

  // Reset UI immediately
  currentConvId = null;
  document.querySelectorAll(".hsb-item").forEach(el => el.classList.remove("active"));
  updateChatTitle("💬 Cuộc trò chuyện mới");
  const msgs = document.getElementById("chatMessages");
  if (msgs) msgs.innerHTML = getWelcomeHTML();

  document.getElementById("chatInput")?.focus();
}

// Delete conversation 

async function deleteConversation(convId, e) {
  e.stopPropagation();
  if (!confirm("Xóa cuộc trò chuyện này?")) return;

  await fetch(`/api/conversations/${convId}`, { method: "DELETE" });

  if (currentConvId === convId) {
    currentConvId = null;
    updateChatTitle("💬 Trò chuyện với AI");
    const msgs = document.getElementById("chatMessages");
    if (msgs) msgs.innerHTML = getWelcomeHTML();
  }

  await loadConversations();
}

// Rename 

let _renamingId = null;

function openRenameModal(convId, currentTitle, e) {
  e.stopPropagation();
  _renamingId = convId;
  const input = document.getElementById("renameInput");
  if (input) input.value = currentTitle;
  document.getElementById("renameOverlay")?.classList.add("active");
  setTimeout(() => input?.focus(), 80);
}
function closeRenameModal() {
  document.getElementById("renameOverlay")?.classList.remove("active");
  _renamingId = null;
}
async function submitRename() {
  if (!_renamingId) return;
  const title = (document.getElementById("renameInput")?.value || "").trim();
  if (!title) return;
  await fetch(`/api/conversations/${_renamingId}`, {
    method: "PATCH", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title })
  });
  if (_renamingId === currentConvId) updateChatTitle(title);
  closeRenameModal();
  await loadConversations();
}
document.addEventListener("keydown", e => {
  if (e.key === "Escape") closeRenameModal();
  if (e.key === "Enter" && document.getElementById("renameOverlay")?.classList.contains("active"))
    submitRename();
});

// UI helpers

function updateChatTitle(title) {
  const el = document.getElementById("currentConvTitle");
  if (el) el.textContent = title;
  const renameBtn = document.getElementById("renameBtn");
  if (renameBtn) renameBtn.style.display = currentConvId ? "flex" : "none";
}

function getWelcomeHTML() {
  return `<div class="welcome-msg">
    <h4>Xin chào! Tôi là DocMind AI</h4>
    <p>Hãy tải lên tài liệu và đặt câu hỏi. Tôi sẽ đọc và phân tích giúp bạn.</p>
    <div class="welcome-hints">
      <div class="hint-chip" onclick="fillHint(this)">Tóm tắt nội dung chính của tài liệu</div>
      <div class="hint-chip" onclick="fillHint(this)">Liệt kê các điểm quan trọng nhất</div>
      <div class="hint-chip" onclick="fillHint(this)">Tài liệu này nói về chủ đề gì?</div>
      <div class="hint-chip" onclick="fillHint(this)">So sánh các nội dung trong tài liệu</div>
    </div>
  </div>`;
}

// Document sidebar 

async function loadSidebarDocs() {
  try {
    const r    = await fetch("/api/documents");
    const data = await r.json();
    renderSidebarDocs(data.documents);
  } catch {}
}

function extIcon(ext) { return { pdf:"📄", docx:"📝", txt:"📃" }[ext] || "📎"; }

function renderSidebarDocs(docs) {
  const el = document.getElementById("sidebarDocs");
  if (!el) return;
  if (!docs.length) {
    el.innerHTML = `<div class="sidebar-empty"><i class="bi bi-cloud-upload"></i><span>Tải lên tài liệu để bắt đầu</span></div>`;
    return;
  }
  el.innerHTML = docs.map(d => `
    <div class="sidebar-doc-item ${selectedDocIds.has(d.id)?'selected':''}"
         id="sdi_${d.id}" onclick="toggleDoc('${d.id}',this)">
      <span class="doc-item-icon">${extIcon(d.ext)}</span>
      <div style="flex:1;min-width:0">
        <div class="doc-item-name" title="${d.name}">${d.name}</div>
        <div class="doc-item-meta">${(d.word_count||0).toLocaleString()} từ</div>
      </div>
      <div class="doc-item-check"><i class="bi bi-check2"></i></div>
    </div>`).join("");
  updateSelectedBar();
}

function toggleDoc(id, el) {
  selectedDocIds.has(id) ? (selectedDocIds.delete(id), el.classList.remove("selected"))
                         : (selectedDocIds.add(id),    el.classList.add("selected"));
  updateSelectedBar();
}
function selectAllDocs() {
  document.querySelectorAll(".sidebar-doc-item").forEach(el => {
    selectedDocIds.add(el.id.replace("sdi_","")); el.classList.add("selected");
  }); updateSelectedBar();
}
function deselectAllDocs() {
  selectedDocIds.clear();
  document.querySelectorAll(".sidebar-doc-item").forEach(el => el.classList.remove("selected"));
  updateSelectedBar();
}
function updateSelectedBar() {
  const bar = document.getElementById("selectedDocsBar");
  const txt = document.getElementById("selectedDocsText");
  const n = selectedDocIds.size;
  if (bar) bar.style.display = n > 0 ? "flex" : "none";
  if (txt) txt.textContent = `${n} tài liệu được chọn`;
}

function initSidebarUpload() {
  const input = document.getElementById("sidebarFile");
  if (!input) return;
  input.addEventListener("change", async () => {
    const files = [...input.files];
    if (!files.length) return;
    const prog = document.getElementById("sidebarUploadProgress");
    const msg  = document.getElementById("sidebarUploadMsg");
    if (prog) prog.style.display = "block";
    for (const file of files) {
      if (msg) msg.textContent = `Xử lý: ${file.name}`;
      const fd = new FormData(); fd.append("file", file);
      try { await fetch("/api/upload", { method:"POST", body:fd }); } catch {}
    }
    if (prog) prog.style.display = "none";
    input.value = "";
    loadSidebarDocs();
  });
}

// Message rendering 

function nowStr() {
  return new Date().toLocaleTimeString("vi-VN",{hour:"2-digit",minute:"2-digit"});
}

function appendMessage(role, text, id=null) {
  const msgs = document.getElementById("chatMessages");
  const welcome = msgs?.querySelector(".welcome-msg");
  if (welcome) welcome.remove();
  const div = buildMessageDiv(role, text, null);
  if (id) div.id = id;
  msgs?.appendChild(div);
  if (msgs) msgs.scrollTop = msgs.scrollHeight;
  return div;
}

function appendTyping() {
  const msgs = document.getElementById("chatMessages");
  const div = document.createElement("div");
  div.className = "message assistant"; div.id = "typing_indicator";
  div.innerHTML = `<div class="message-avatar">⬡</div>
    <div><div class="message-bubble"><div class="typing-indicator"><span></span><span></span><span></span></div></div></div>`;
  msgs?.appendChild(div);
  if (msgs) msgs.scrollTop = msgs.scrollHeight;
  return div;
}

function escapeAndFormat(text) {
  return text
    .replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")
    .replace(/\*\*(.+?)\*\*/g,"<strong>$1</strong>")
    .replace(/\*(.+?)\*/g,"<em>$1</em>")
    .replace(/`(.+?)`/g,`<code style="background:rgba(108,99,255,.15);padding:.1em .4em;border-radius:3px;">$1</code>`)
    .replace(/\n/g,"<br>");
}

// Send message 

async function sendMessage() {
  if (isStreaming) return;
  const input = document.getElementById("chatInput");
  const btn   = document.getElementById("sendBtn");
  const text  = input?.value.trim();
  if (!text) return;

  if (input) { input.value = ""; input.style.height = "auto"; }
  isStreaming = true;
  if (btn) btn.disabled = true;

  appendMessage("user", text);
  appendTyping();

  try {
    const body = {
      message:  text,
      doc_ids:  [...selectedDocIds],
      conv_id:  currentConvId,   // null = server auto-creates
    };

    const response = await fetch("/api/chat", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response.ok) { const e = await response.json(); throw new Error(e.error||"Lỗi server"); }

    document.getElementById("typing_indicator")?.remove();
    const aiDiv  = appendMessage("assistant", "", "streaming_bubble");
    const bubble = aiDiv.querySelector(".message-bubble");

    const reader  = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "", fullText = "";

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
          const d = JSON.parse(json);
          if (d.token) {
            fullText += d.token;
            if (bubble) bubble.innerHTML = escapeAndFormat(fullText);
            const ms = document.getElementById("chatMessages");
            if (ms) ms.scrollTop = 9999;
          }
          if (d.done) {
            // Server assigned a conv_id (new session)
            if (d.conv_id && !currentConvId) {
              currentConvId = d.conv_id;
              document.getElementById("renameBtn")?.style && (document.getElementById("renameBtn").style.display = "flex");
              // Refresh sidebar list
              await loadConversations();
              // Mark active
              document.querySelectorAll(".hsb-item").forEach(e => e.classList.remove("active"));
              document.getElementById(`hci_${currentConvId}`)?.classList.add("active");
            } else if (d.conv_id) {
              // Update updated_at in cache
              await loadConversations();
              document.querySelectorAll(".hsb-item").forEach(e => e.classList.remove("active"));
              document.getElementById(`hci_${currentConvId}`)?.classList.add("active");
            }
            break;
          }
        } catch {}
      }
    }

    if (aiDiv) aiDiv.id = "";
    const ms = document.getElementById("chatMessages");
    if (ms) ms.scrollTop = ms.scrollHeight;

  } catch (err) {
    document.getElementById("typing_indicator")?.remove();
    appendMessage("assistant", `⚠️ Lỗi: ${err.message}`);
  } finally {
    isStreaming = false;
    if (btn) btn.disabled = false;
    input?.focus();
  }
}

// Clear current chat 

async function clearCurrentChat() {
  if (!currentConvId) {
    // Just reset UI
    const msgs = document.getElementById("chatMessages");
    if (msgs) msgs.innerHTML = getWelcomeHTML();
    return;
  }
  if (!confirm("Xóa cuộc trò chuyện này?")) return;
  await deleteConversation(currentConvId, { stopPropagation: ()=>{} });
}

// Export 

function exportChat() {
  const msgs    = document.getElementById("chatMessages");
  const bubbles = msgs?.querySelectorAll(".message");
  if (!bubbles?.length) { alert("Chưa có tin nhắn"); return; }
  let text = `DocMind AI - Lịch sử\n${"=".repeat(50)}\n`;
  bubbles.forEach(m => {
    const role   = m.classList.contains("user") ? "Bạn" : "AI";
    const bubble = m.querySelector(".message-bubble");
    const time   = m.querySelector(".message-time");
    text += `\n[${time?.textContent||""}] ${role}:\n${bubble?.innerText||""}\n`;
  });
  const a = document.createElement("a");
  a.href     = URL.createObjectURL(new Blob([text],{type:"text/plain;charset=utf-8"}));
  a.download = `docmind_${Date.now()}.txt`;
  a.click();
}

// Keyboard helpers 

function handleKeyDown(e) {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
}
function autoResize(el) {
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 150) + "px";
}
function fillHint(el) {
  const input = document.getElementById("chatInput");
  if (input) {
    input.value = el.textContent.trim();
    input.focus();
    autoResize(input); }
}

// Rename btn wiring 

function wireRenameBtn() {
  const btn = document.getElementById("renameBtn");
  if (!btn) return;
  btn.addEventListener("click", () => {
    if (!currentConvId) return;
    const conv = allConversations.find(c => c.id === currentConvId);
    openRenameModal(currentConvId, conv?.title || "", { stopPropagation: ()=>{} });
  });
}

// Auth state listener 

document.addEventListener("authStateChanged", async (e) => {
  if (e.detail) {
    // Just logged in → reload conversations
    currentConvId = null;
    updateChatTitle("💬 Trò chuyện với AI");
    const msgs = document.getElementById("chatMessages");
    if (msgs) msgs.innerHTML = getWelcomeHTML();
    await loadConversations();
  } else {
    // Logged out
    currentConvId = null;
    allConversations = [];
    renderConvList();
    updateChatTitle("💬 Trò chuyện với AI");
    const msgs = document.getElementById("chatMessages");
    if (msgs) msgs.innerHTML = getWelcomeHTML();
    document.getElementById("hsbGuestNotice").style.display = "flex";
  }
});

// Init 

document.addEventListener("DOMContentLoaded", () => {
  loadSidebarDocs();
  initSidebarUpload();
  wireRenameBtn();

  document.getElementById("newChatBtn")?.addEventListener("click", newConversation);

  // Rename overlay close on backdrop
  document.getElementById("renameOverlay")?.addEventListener("click", function(e) {
    if (e.target === this) closeRenameModal();
  });

  setInterval(loadSidebarDocs, 10000);
  document.getElementById("chatInput")?.focus();

  setTimeout(async () => {
    await loadConversations();
  }, 300);
});