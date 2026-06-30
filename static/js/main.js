/* ── Theme ─────────────────────────────────────────────────────────── */
const savedTheme = localStorage.getItem("theme") || "light";
document.documentElement.setAttribute("data-theme", savedTheme);

function toggleTheme() {
  const current = document.documentElement.getAttribute("data-theme");
  const next = current === "dark" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", next);
  localStorage.setItem("theme", next);
  document.querySelectorAll(".theme-icon-sun, .theme-icon-moon").forEach(el => el.classList.toggle("hidden"));
}

/* ── Toast ─────────────────────────────────────────────────────────── */
function showToast(message, type = "info", duration = 4000) {
  let container = document.querySelector(".toast-container");
  if (!container) {
    container = document.createElement("div");
    container.className = "toast-container";
    document.body.appendChild(container);
  }
  const icons = {
    success: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>`,
    error: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`,
    info: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`,
  };
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `${icons[type] || icons.info}<span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => { toast.style.opacity = "0"; toast.style.transform = "translateX(20px)"; toast.style.transition = "all 0.3s"; setTimeout(() => toast.remove(), 300); }, duration);
}

/* ── API Helper ────────────────────────────────────────────────────── */
async function apiFetch(url, options = {}) {
  const defaults = { headers: { "Content-Type": "application/json" }, credentials: "same-origin" };
  const merged = { ...defaults, ...options, headers: { ...defaults.headers, ...(options.headers || {}) } };
  try {
    const res = await fetch(url, merged);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Request failed");
    return data;
  } catch (err) {
    throw err;
  }
}

/* ── Button Loading ────────────────────────────────────────────────── */
function setLoading(btn, loading) {
  if (loading) { btn.classList.add("btn-loading"); btn.disabled = true; }
  else { btn.classList.remove("btn-loading"); btn.disabled = false; }
}

/* ── Sidebar toggle (mobile) ───────────────────────────────────────── */
function initSidebar() {
  const hamburger = document.querySelector(".hamburger");
  const sidebar = document.querySelector(".sidebar");
  const overlay = document.querySelector(".sidebar-overlay");
  if (!hamburger || !sidebar) return;
  hamburger.addEventListener("click", () => {
    sidebar.classList.toggle("open");
    overlay?.classList.toggle("open");
  });
  overlay?.addEventListener("click", () => {
    sidebar.classList.remove("open");
    overlay.classList.remove("open");
  });
}

/* ── Theme button init ─────────────────────────────────────────────── */
function initThemeToggle() {
  document.querySelectorAll(".theme-toggle").forEach(btn => {
    btn.addEventListener("click", toggleTheme);
    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    btn.querySelector(".theme-icon-sun")?.classList.toggle("hidden", !isDark);
    btn.querySelector(".theme-icon-moon")?.classList.toggle("hidden", isDark);
  });
}

/* ── Tabs ──────────────────────────────────────────────────────────── */
function initTabs(container) {
  const target = container || document;
  target.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const group = btn.closest("[data-tabs]");
      if (!group) return;
      group.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
      group.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
      btn.classList.add("active");
      const panel = group.querySelector(`[data-panel="${btn.dataset.tab}"]`);
      panel?.classList.add("active");
    });
  });
}

/* ── Score Circle ──────────────────────────────────────────────────── */
function animateScoreCircle(el, score) {
  const fill = el.querySelector(".score-circle-fill");
  const numEl = el.querySelector(".score-number");
  if (!fill || !numEl) return;
  const r = 70;
  const circumference = 2 * Math.PI * r;
  fill.style.strokeDasharray = circumference;
  fill.style.strokeDashoffset = circumference;
  const colorClass = score >= 71 ? "score-green" : score >= 41 ? "score-yellow" : "score-red";
  fill.classList.add(colorClass);
  numEl.classList.add(colorClass);
  setTimeout(() => {
    fill.style.strokeDashoffset = circumference - (score / 100) * circumference;
    let current = 0;
    const step = score / 60;
    const timer = setInterval(() => {
      current = Math.min(current + step, score);
      numEl.textContent = Math.round(current);
      if (current >= score) clearInterval(timer);
    }, 16);
  }, 300);
}

/* ── Progress Bars ─────────────────────────────────────────────────── */
function animateProgressBars() {
  document.querySelectorAll(".progress-fill[data-value]").forEach(el => {
    const val = parseInt(el.dataset.value, 10);
    el.style.width = "0%";
    setTimeout(() => { el.style.width = val + "%"; }, 100);
    const colorClass = val >= 71 ? "#16a34a" : val >= 41 ? "#ca8a04" : "#dc2626";
    el.style.background = colorClass;
  });
}

/* ── Logout ────────────────────────────────────────────────────────── */
async function logout() {
  try {
    await apiFetch("/auth/logout", { method: "POST" });
  } catch (e) {}
  window.location.href = "/";
}

/* ── Confirm delete ────────────────────────────────────────────────── */
function confirmDelete(analysisId) {
  if (!confirm("Delete this analysis? This cannot be undone.")) return;
  apiFetch(`/analysis/${analysisId}`, { method: "DELETE" })
    .then(() => { showToast("Analysis deleted", "success"); document.getElementById(`row-${analysisId}`)?.remove(); })
    .catch(err => showToast(err.message, "error"));
}

/* ── Init ──────────────────────────────────────────────────────────── */
document.addEventListener("DOMContentLoaded", () => {
  initSidebar();
  initThemeToggle();
  initTabs();
  animateProgressBars();
  // Score circles
  document.querySelectorAll(".score-circle[data-score]").forEach(el => {
    animateScoreCircle(el, parseInt(el.dataset.score, 10));
  });
  // Active nav link
  const path = window.location.pathname;
  document.querySelectorAll(".nav-link").forEach(link => {
    if (link.getAttribute("href") === path) link.classList.add("active");
  });
});
