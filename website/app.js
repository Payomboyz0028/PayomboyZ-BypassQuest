/* app.js — KeyBypass Website Frontend Logic */

const API_BASE = window.location.origin;

let bulkUrls = [];

// ─────────────────────────────────────────────────────────────
// Toggle Bulk Mode
// ─────────────────────────────────────────────────────────────
function toggleBulkMode() {
  const isBulk = document.getElementById("bulkToggle").checked;
  document.getElementById("singleMode").style.display = isBulk ? "none" : "flex";
  document.getElementById("bulkMode").style.display = isBulk ? "flex" : "none";
  const hint = document.getElementById("modeHint");
  hint.textContent = isBulk
    ? "วางลิงค์ทีละบรรทัด หรือแนบไฟล์ .txt • รองรับมากกว่า 4000 บรรทัด"
    : "กด Enter หรือคลิก Bypass Now • ผลลัพธ์จะปรากฏด้านล่าง";
  document.getElementById("resultBox").className = "result-box hidden";
  document.querySelectorAll(".bulk-results").forEach(el => el.remove());
}

// ─────────────────────────────────────────────────────────────
// File Upload Handler
// ─────────────────────────────────────────────────────────────
function handleFileUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  const fileNameEl = document.getElementById("fileName");
  fileNameEl.textContent = `📄 ${file.name}`;

  const reader = new FileReader();
  reader.onload = function(e) {
    const text = e.target.result;
    const textarea = document.getElementById("bulkTextarea");
    textarea.value = text;
    updateLineCount();
  };
  reader.readAsText(file);
}

function updateLineCount() {
  const textarea = document.getElementById("bulkTextarea");
  const lines = textarea.value.split("\n").filter(l => l.trim().length > 0 && (l.trim().startsWith("http://") || l.trim().startsWith("https://")));
  document.getElementById("lineCount").textContent = lines.length;
}

function clearBulk() {
  document.getElementById("bulkTextarea").value = "";
  document.getElementById("fileName").textContent = "";
  document.getElementById("fileInput").value = "";
  document.getElementById("lineCount").textContent = "0";
  document.getElementById("resultBox").className = "result-box hidden";
  document.querySelectorAll(".bulk-results").forEach(el => el.remove());
}

// Auto-update line count
document.addEventListener("DOMContentLoaded", () => {
  const textarea = document.getElementById("bulkTextarea");
  if (textarea) {
    textarea.addEventListener("input", updateLineCount);
  }
});

// ─────────────────────────────────────────────────────────────
// Get selected engine
// ─────────────────────────────────────────────────────────────
function getEngine() {
  const select = document.getElementById("engineSelect");
  return select ? select.value : "auto";
}

// ─────────────────────────────────────────────────────────────
// Single Bypass
// ─────────────────────────────────────────────────────────────
async function doBypass() {
  const input = document.getElementById("urlInput");
  const btn = document.getElementById("bypassBtn");
  const btnText = document.getElementById("btnText");
  const btnSpinner = document.getElementById("btnSpinner");
  const resultBox = document.getElementById("resultBox");

  const url = input.value.trim();
  if (!url) { input.focus(); return; }
  if (!url.startsWith("http://") && !url.startsWith("https://")) {
    showResult({ success: false, error: "URL ต้องขึ้นต้นด้วย http:// หรือ https://" });
    return;
  }

  // Loading state
  btn.disabled = true;
  btnText.textContent = "Bypassing...";
  btnSpinner.classList.remove("hidden");
  resultBox.className = "result-box hidden";

  const engine = getEngine();

  try {
    const res = await fetch(`${API_BASE}/api/bypass`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, engine })
    });
    const data = await res.json();
    showResult(data);
  } catch (e) {
    showResult({ success: false, error: "ไม่สามารถเชื่อมต่อ API Server ได้ — ตรวจสอบว่า server รันอยู่" });
  } finally {
    btn.disabled = false;
    btnText.textContent = "Bypass Now";
    btnSpinner.classList.add("hidden");
  }
}

function showResult(data) {
  const box = document.getElementById("resultBox");
  box.classList.remove("hidden", "success", "error");

  if (data.success) {
    const dest = data.destination || "";
    const isKey = data.is_key;
    const chain = data.chain ? `<span class="result-tag">⛓️ ${data.chain}</span>` : "";
    const endpoint = data.endpoint ? `<span class="result-tag">🔌 ${data.endpoint}</span>` : "";
    const time = data.processingTime ? `<span class="result-tag">⏱️ ${data.processingTime}ms</span>` : "";
    const service = data.service ? `<span class="result-tag">${data.service}</span>` : "";

    box.innerHTML = `
      <div class="result-header">${isKey ? "🔑 ได้ Key สำเร็จ!" : "✅ Bypass สำเร็จ!"}</div>
      <div class="result-url" id="resultUrl">${dest}</div>
      <div class="result-meta">${service}${endpoint}${chain}${time}</div>
      <button class="copy-btn" onclick="copyResult()">📋 Copy ${isKey ? "Key" : "Link"}</button>
    `;
    box.className = "result-box success";
  } else {
    box.innerHTML = `
      <div class="result-header">❌ Bypass ไม่สำเร็จ</div>
      <p style="color:#aaa;font-size:.9rem;margin-top:.25rem">${data.error || "Unknown error"}</p>
      <p style="color:#666;font-size:.8rem;margin-top:.5rem">ลิงค์อาจหมดอายุ หรือค่ายนี้ยังไม่รองรับ</p>
    `;
    box.className = "result-box error";
  }
}

function copyResult() {
  const el = document.getElementById("resultUrl");
  if (!el) return;
  navigator.clipboard.writeText(el.textContent).then(() => {
    const btn = document.querySelector(".copy-btn");
    if (btn) {
      btn.textContent = "✅ Copied!";
      setTimeout(() => btn.textContent = "📋 Copy Link", 2000);
    }
  });
}

// ─────────────────────────────────────────────────────────────
// Bulk Bypass
// ─────────────────────────────────────────────────────────────
async function doBulkBypass() {
  const textarea = document.getElementById("bulkTextarea");
  const btn = document.getElementById("bulkBypassBtn");
  const btnText = document.getElementById("bulkBtnText");
  const btnSpinner = document.getElementById("bulkBtnSpinner");
  const resultBox = document.getElementById("resultBox");

  // Parse URLs (no limit — supports >4000 lines)
  const lines = textarea.value.split("\n")
    .map(l => l.trim())
    .filter(l => l.startsWith("http://") || l.startsWith("https://"));

  if (lines.length === 0) {
    showResult({ success: false, error: "ไม่มี URL ที่ถูกต้องในช่องข้อความ — วางลิงค์ที่ขึ้นต้นด้วย http:// หรือ https://" });
    return;
  }

  // Loading
  btn.disabled = true;
  btnText.textContent = `Bypassing ${lines.length} URLs...`;
  btnSpinner.classList.remove("hidden");
  resultBox.className = "result-box hidden";
  document.querySelectorAll(".bulk-results").forEach(el => el.remove());

  const engine = getEngine();
  const results = [];
  let successCount = 0;
  let failCount = 0;

  // Create results container
  const container = document.createElement("div");
  container.className = "bulk-results";
  container.innerHTML = `
    <div class="bulk-result-summary">
      <div class="bulk-stat"><span class="num" id="bulkProgress">0/${lines.length}</span><span class="label">Progress</span></div>
      <div class="bulk-stat success"><span class="num" id="bulkSuccess">0</span><span class="label">Success</span></div>
      <div class="bulk-stat fail"><span class="num" id="bulkFail">0</span><span class="label">Failed</span></div>
    </div>
    <div class="bulk-result-list" id="bulkResultList"></div>
    <button class="bulk-export-btn" onclick="exportBulkResults()">📥 Export Results (.txt)</button>
  `;
  resultBox.parentNode.insertBefore(container, resultBox.nextSibling);

  const listEl = document.getElementById("bulkResultList");

  // Process each URL with a small delay to avoid rate limits
  for (let i = 0; i < lines.length; i++) {
    const url = lines[i];
    try {
      const res = await fetch(`${API_BASE}/api/bypass`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url, engine })
      });
      const data = await res.json();

      const item = document.createElement("div");
      item.className = "bulk-result-item";

      if (data.success) {
        successCount++;
        item.innerHTML = `
          <span class="status">✅</span>
          <span class="url">${url}</span>
          <span class="result-link" onclick="navigator.clipboard.writeText('${data.destination.replace(/'/g, "\\'")}')">→ ${data.destination}</span>
        `;
        results.push({ url, success: true, destination: data.destination });
      } else {
        failCount++;
        item.innerHTML = `
          <span class="status">❌</span>
          <span class="url">${url}</span>
          <span class="error-text">${data.error || "Failed"}</span>
        `;
        results.push({ url, success: false, error: data.error || "Failed" });
      }
      listEl.appendChild(item);
      listEl.scrollTop = listEl.scrollHeight;

      // Update stats
      document.getElementById("bulkProgress").textContent = `${i + 1}/${lines.length}`;
      document.getElementById("bulkSuccess").textContent = successCount;
      document.getElementById("bulkFail").textContent = failCount;
    } catch (e) {
      failCount++;
      const item = document.createElement("div");
      item.className = "bulk-result-item";
      item.innerHTML = `
        <span class="status">❌</span>
        <span class="url">${url}</span>
        <span class="error-text">Connection error</span>
      `;
      listEl.appendChild(item);
      results.push({ url, success: false, error: "Connection error" });
      document.getElementById("bulkFail").textContent = failCount;
    }

    // Small delay between requests to be nice to the server
    if (i < lines.length - 1) {
      await new Promise(r => setTimeout(r, 300));
    }
  }

  // Store results for export
  window._bulkResults = results;

  btn.disabled = false;
  btnText.textContent = "🚀 Bypass All";
  btnSpinner.classList.add("hidden");
}

function exportBulkResults() {
  const results = window._bulkResults || [];
  if (results.length === 0) return;

  let text = "# KeyBypass Bulk Results\n";
  text += `# Date: ${new Date().toISOString()}\n`;
  text += `# Total: ${results.length} | Success: ${results.filter(r => r.success).length} | Failed: ${results.filter(r => !r.success).length}\n\n`;

  results.forEach(r => {
    if (r.success) {
      text += `${r.url} -> ${r.destination}\n`;
    } else {
      text += `${r.url} -> FAILED: ${r.error}\n`;
    }
  });

  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `keybypass-bulk-results-${Date.now()}.txt`;
  a.click();
  URL.revokeObjectURL(a.href);
}

// ─────────────────────────────────────────────────────────────
// Enter key for single mode
// ─────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("urlInput").addEventListener("keydown", e => {
    if (e.key === "Enter") doBypass();
  });

  // Support Ctrl+Enter for bulk textarea
  document.getElementById("bulkTextarea").addEventListener("keydown", e => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") doBulkBypass();
  });

  loadStats();
  loadServices();
});

// ─────────────────────────────────────────────────────────────
// Stats
// ─────────────────────────────────────────────────────────────
async function loadStats() {
  try {
    const res = await fetch(`${API_BASE}/api/stats`);
    const data = await res.json();
    const s = data.stats || {};

    const totalEl = document.getElementById("statTotal");
    const rateEl = document.getElementById("statRate");
    const uptimeEl = document.getElementById("statUptime");

    if (totalEl) animateCount(totalEl, s.total_bypassed || 0);
    if (rateEl) rateEl.textContent = s.success_rate || "—";
    if (uptimeEl) {
      const sec = s.uptime_seconds || 0;
      const h = Math.floor(sec / 3600);
      const m = Math.floor((sec % 3600) / 60);
      uptimeEl.textContent = h > 0 ? `${h}h ${m}m` : `${m}m`;
    }
  } catch (e) {
    // Server not reachable — show dashes
  }
}

function animateCount(el, target) {
  let current = 0;
  const duration = 1200;
  const step = target / (duration / 16);
  const timer = setInterval(() => {
    current = Math.min(current + step, target);
    el.textContent = Math.floor(current).toLocaleString();
    if (current >= target) clearInterval(timer);
  }, 16);
}

// ─────────────────────────────────────────────────────────────
// Services Grid
// ─────────────────────────────────────────────────────────────
const CATEGORY_EMOJI = {
  "Key System": "🗝️",
  "Ad-link": "⚡",
  "Social Unlock": "🔓",
  "File Host": "📁",
  "General": "🔗"
};

async function loadServices() {
  try {
    const res = await fetch(`${API_BASE}/api/supported`);
    const data = await res.json();
    const grid = document.getElementById("servicesGrid");
    if (!grid) return;

    // Group by name (deduplicate)
    const seen = new Set();
    const services = (data.services || []).filter(s => {
      if (seen.has(s.name)) return false;
      seen.add(s.name);
      return true;
    });

    // Key systems first
    const sorted = [
      ...services.filter(s => s.category === "Key System"),
      ...services.filter(s => s.category !== "Key System"),
    ];

    grid.innerHTML = sorted.map(s => `
      <div class="service-chip ${s.category === 'Key System' ? 'key-system' : ''}" title="${s.category}">
        ${s.emoji || CATEGORY_EMOJI[s.category] || "🔗"} ${s.name}
      </div>
    `).join("");
  } catch (e) {
    const grid = document.getElementById("servicesGrid");
    if (grid) grid.innerHTML = `<p style="color:#666">ไม่สามารถโหลด services ได้</p>`;
  }
}