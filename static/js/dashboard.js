/* ── dashboard.js ─────────────────────── */

let allDocs = [];

async function checkOllama() {
  try {
    const r = await fetch("/api/health");
    const data = await r.json();
    // const badge = document.getElementById("ollamaStatusBadge");
    // if (badge) {
    //   if (data.ollama.ok && data.ollama.model_ready) {
    //     badge.textContent = "● Online";
    //     badge.style.cssText = "background:rgba(74,222,128,.2);color:#4ade80;border:1px solid rgba(74,222,128,.4);padding:.25rem .6rem;border-radius:12px;font-size:.75rem;";
    //   } else {
    //     badge.textContent = "✕ Offline";
    //     badge.style.cssText = "background:rgba(248,113,113,.2);color:#f87171;border:1px solid rgba(248,113,113,.4);padding:.25rem .6rem;border-radius:12px;font-size:.75rem;";
    //   }
    // }

    // Fill model info table
    document.getElementById("infModel").textContent  = data.ollama.target_model ?? "—";
    document.getElementById("infUrl").textContent    = "http://localhost:11434";
    document.getElementById("infStatus").innerHTML   = data.ollama.model_ready
      ? `<span style="color:#4ade80">● Sẵn sàng</span>`
      : `<span style="color:#f87171">✕ Chưa tải model</span>`;
    document.getElementById("infTime").textContent   = new Date(data.timestamp).toLocaleString("vi-VN");

    // KPI ollama
    document.getElementById("kpiOllama").textContent = data.ollama.model_ready ? "✔" : "✘";
    document.getElementById("kpiOllama").style.color = data.ollama.model_ready ? "#4ade80" : "#f87171";
  } catch {}
}

async function loadDashboard() {
  try {
    const r = await fetch("/api/documents");
    const data = await r.json();
    allDocs = data.documents || [];
    renderKPIs(allDocs);
    renderFileTypes(allDocs);
    renderTable(allDocs);
  } catch {}
}

function renderKPIs(docs) {
  document.getElementById("kpiDocs").textContent   = docs.length;
  const words  = docs.reduce((s, d) => s + (d.word_count  || 0), 0);
  const chunks = docs.reduce((s, d) => s + (d.chunk_count || 0), 0);
  document.getElementById("kpiWords").textContent  = words.toLocaleString("vi-VN");
  document.getElementById("kpiChunks").textContent = chunks.toLocaleString("vi-VN");
}

function renderFileTypes(docs) {
  const counts = docs.reduce((acc, d) => {
    acc[d.ext] = (acc[d.ext] || 0) + 1;
    return acc;
  }, {});
  const icons = { pdf: "📄", docx: "📝", txt: "📃" };
  const el = document.getElementById("fileTypePie");
  if (!el) return;
  if (!Object.keys(counts).length) {
    el.innerHTML = `<span style="color:var(--text2);font-size:.85rem">Không có dữ liệu</span>`;
    return;
  }
  el.innerHTML = Object.entries(counts).map(([ext, n]) => `
    <div class="file-type-item">
      <div class="ft-icon">${icons[ext] || "📎"}</div>
      <div class="ft-count">${n}</div>
      <div class="ft-label">.${ext.toUpperCase()}</div>
    </div>
  `).join("");
}

function extBadge(ext) {
  return `<span class="ext-badge ext-${ext}">.${ext.toUpperCase()}</span>`;
}

function renderTable(docs) {
  const tbody = document.getElementById("dashDocsTable");
  if (!tbody) return;
  if (!docs.length) {
    tbody.innerHTML = `<tr><td colspan="7" class="text-center py-4" style="color:var(--text2)">Chưa có tài liệu nào</td></tr>`;
    return;
  }
  tbody.innerHTML = docs.map(d => `
    <tr>
      <td>
        <div style="font-weight:600;font-size:.88rem;max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${d.name}">${d.name}</div>
      </td>
      <td>${extBadge(d.ext)}</td>
      <td style="color:var(--text2);font-size:.85rem">${d.size_human}</td>
      <td style="font-size:.85rem">${(d.word_count||0).toLocaleString("vi-VN")}</td>
      <td style="font-size:.85rem">${d.chunk_count||0}</td>
      <td style="color:var(--text2);font-size:.82rem">${new Date(d.uploaded_at).toLocaleString("vi-VN")}</td>
      <td>
        <div style="display:flex;gap:.3rem">
          <a href="/chat" class="btn-primary-custom" style="font-size:.78rem;padding:.25rem .65rem;text-decoration:none">
            <i class="bi bi-chat-dots"></i>
          </a>
          <button class="btn-icon btn-icon-danger" onclick="deleteDoc('${d.id}')" title="Xóa">
            <i class="bi bi-trash3"></i>
          </button>
        </div>
      </td>
    </tr>
  `).join("");
}

function filterDocs() {
  const q = document.getElementById("searchDocs").value.toLowerCase();
  const filtered = allDocs.filter(d => d.name.toLowerCase().includes(q));
  renderTable(filtered);
}

async function deleteDoc(id) {
  if (!confirm("Xóa tài liệu này?")) return;
  await fetch(`/api/documents/${id}`, { method: "DELETE" });
  loadDashboard();
}

document.addEventListener("DOMContentLoaded", () => {
  checkOllama();
  loadDashboard();
  setInterval(checkOllama, 30000);
  setInterval(loadDashboard, 15000);
});