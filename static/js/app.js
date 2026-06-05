const SESSION_ID = "default";

// ── Ollama status check ──────────────────

// async function checkOllama() {
//   try {
//     const r = await fetch("/api/health");
//     const data = await r.json();
//     const badge = document.getElementById("ollamaStatusBadge");
//     if (!badge) return;
//     if (data.ollama.ok && data.ollama.model_ready) {
//       badge.textContent = "● Ollama Online";
//       badge.className = "ms-3 badge";
//       badge.style.cssText = "background:rgba(74,222,128,.2);color:#4ade80;border:1px solid rgba(74,222,128,.4);";
//     } else if (data.ollama.ok) {
//       badge.textContent = "⚠ Model chưa tải";
//       badge.className = "ms-3 badge";
//       badge.style.cssText = "background:rgba(251,191,36,.2);color:#fbbf24;border:1px solid rgba(251,191,36,.4);";
//     } else {
//       badge.textContent = "✕ Ollama Offline";
//       badge.className = "ms-3 badge";
//       badge.style.cssText = "background:rgba(248,113,113,.2);color:#f87171;border:1px solid rgba(248,113,113,.4);";
//     }
//   } catch {}
// }

// ── Load documents ───────────────────────

async function loadDocuments() {
  try {
    const r = await fetch("/api/documents");
    const data = await r.json();
    renderDocsList(data.documents);
    updateStats(data.documents);
  } catch (e) {
    console.error("Load docs error", e);
  }
}

function updateStats(docs) {
  document.getElementById("statDocs").textContent  = docs.length;
  const words  = docs.reduce((s, d) => s + (d.word_count  || 0), 0);
  const chunks = docs.reduce((s, d) => s + (d.chunk_count || 0), 0);
  document.getElementById("statWords").textContent  = words.toLocaleString("vi-VN");
  document.getElementById("statChunks").textContent = chunks.toLocaleString("vi-VN");
}

function extIcon(ext) {
  const map = { pdf: "📄", docx: "📝", txt: "📃" };
  return map[ext] || "📎";
}
function extColor(ext) {
  const map = { pdf: "#f87171", docx: "#60a5fa", txt: "#4ade80" };
  return map[ext] || "#8892b0";
}

function renderDocsList(docs) {
  const el = document.getElementById("docsList");
  if (!el) return;
  if (!docs.length) {
    el.innerHTML = `<div class="empty-docs text-center"><i class="bi bi-inbox display-3" style="color:var(--text2)"></i><p class="mt-3" style="color:var(--text2)">Chưa có tài liệu nào. Hãy tải lên để bắt đầu!</p></div>`;
    return;
  }
  el.innerHTML = docs.map(d => `
    <div class="doc-card">
      <div class="doc-card-header">
        <div class="doc-icon">${extIcon(d.ext)}</div>
        <div>
          <div class="doc-name" title="${d.name}">${d.name}</div>
          <div class="doc-meta">${d.size_human} · ${new Date(d.uploaded_at).toLocaleString("vi-VN")}</div>
        </div>
      </div>
      <div class="doc-chips">
        <span class="doc-chip" style="color:${extColor(d.ext)}">.${d.ext.toUpperCase()}</span>
        <span class="doc-chip">${(d.word_count||0).toLocaleString()} từ</span>
        <span class="doc-chip">${d.chunk_count||0} đoạn</span>
      </div>
      <div class="doc-card-actions">
        <a href="/chat" class="btn-primary-custom" style="font-size:.8rem;padding:.35rem .8rem">
          <i class="bi bi-chat-text"></i> Chat
        </a>
        <button class="btn-icon btn-icon-danger" onclick="deleteDoc('${d.id}')" title="Xóa">
          <i class="bi bi-trash3"></i>
        </button>
      </div>
    </div>
  `).join("");
}

async function deleteDoc(id) {
  if (!confirm("Xóa tài liệu này?")) return;
  await fetch(`/api/documents/${id}`, { method: "DELETE" });
  loadDocuments();
}

// ── File Upload ──────────────────────────

function showUploadAlert(msg, type) {
  const el = document.getElementById("uploadAlert");
  if (!el) return;
  el.style.display = "block";
  el.innerHTML = `<div class="alert-custom alert-${type}"><i class="bi bi-${type==='success'?'check-circle':'exclamation-triangle'}"></i> ${msg}</div>`;
  setTimeout(() => { el.style.display = "none"; }, 4000);
}

async function uploadFiles(files) {
  if (!files.length) return;
  const prog = document.getElementById("uploadProgress");
  const msg  = document.getElementById("uploadMsg");
  prog.style.display = "block";
  let ok = 0, fail = 0;
  for (const file of files) {
    msg.textContent = `Đang xử lý: ${file.name}`;
    const fd = new FormData();
    fd.append("file", file);
    try {
      const r = await fetch("/api/upload", { method: "POST", body: fd });
      const data = await r.json();
      if (r.ok) ok++;
      else { fail++; console.error(data.error); }
    } catch { fail++; }
  }
  prog.style.display = "none";
  if (ok)   showUploadAlert(`✅ Đã tải lên ${ok} file thành công!`, "success");
  if (fail) showUploadAlert(`❌ ${fail} file thất bại.`, "danger");
  loadDocuments();
  document.getElementById("fileInput").value = "";
}

// Drag & drop
function initDropzone() {
  const zone = document.getElementById("dropzone");
  const input = document.getElementById("fileInput");
  if (!zone || !input) return;

  zone.addEventListener("click", () => input.click());
  input.addEventListener("change", () => uploadFiles([...input.files]));

  zone.addEventListener("dragover", e => { e.preventDefault(); zone.classList.add("dragover"); });
  zone.addEventListener("dragleave", () => zone.classList.remove("dragover"));
  zone.addEventListener("drop", e => {
    e.preventDefault();
    zone.classList.remove("dragover");
    uploadFiles([...e.dataTransfer.files]);
  });
}

// ── Init ─────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  // checkOllama();
  loadDocuments();
  initDropzone();
  // setInterval(checkOllama, 30000);
});