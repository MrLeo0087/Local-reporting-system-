/*
  Shared API helper functions. Every frontend page includes this file.

  API_BASE_URL picks itself automatically: when you're viewing the site on
  localhost/127.0.0.1 (running it for development), it talks to your local
  backend; anywhere else (the deployed site), it talks to the deployed
  Render backend. Update RENDER_API_BASE_URL below once you know your
  Render backend's URL — nothing else needs to change between dev and prod.
*/
const RENDER_API_BASE_URL = "https://local-reporting-system.onrender.com";
const isLocalHost = ["localhost", "127.0.0.1"].includes(window.location.hostname);
const API_BASE_URL = isLocalHost ? "http://localhost:8000" : RENDER_API_BASE_URL;

const CATEGORIES = [
  { value: "road", label: "Road" },
  { value: "electric", label: "Electric Line" },
  { value: "water_supply", label: "Water Supply" },
  { value: "public_property", label: "Public Property" },
  { value: "other", label: "Other" },
];

const REJECTION_REASONS = [
  { value: "duplicate", label: "Duplicate report" },
  { value: "not_enough_info", label: "Not enough information" },
  { value: "false_report", label: "False report" },
];

function getToken(kind) {
  // kind is "citizen" or "staff"
  return localStorage.getItem(`${kind}_token`);
}

function setToken(kind, token, role) {
  localStorage.setItem(`${kind}_token`, token);
  if (role) localStorage.setItem(`${kind}_role`, role);
}

function clearToken(kind) {
  localStorage.removeItem(`${kind}_token`);
  localStorage.removeItem(`${kind}_role`);
}

/**
 * Wraps fetch(). Automatically attaches Authorization header if a token
 * is present for the given kind ("citizen" or "staff"). Throws an Error
 * with the backend's detail message on non-2xx responses.
 */
async function apiFetch(path, { method = "GET", body, isFormData = false, authKind = null } = {}) {
  const headers = {};
  if (!isFormData) headers["Content-Type"] = "application/json";

  if (authKind) {
    const token = getToken(authKind);
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: isFormData ? body : body ? JSON.stringify(body) : undefined,
  });

  let data = null;
  const text = await response.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch (e) {
      data = null;
    }
  }

  if (!response.ok) {
    const detail = (data && data.detail) || `Request failed (${response.status})`;
    const message = Array.isArray(detail)
      ? detail.map((d) => d.msg || JSON.stringify(d)).join(", ")
      : detail;
    throw new Error(message);
  }

  return data;
}

function photoUrl(photoPath) {
  if (!photoPath) return "";
  return photoPath.startsWith("http") ? photoPath : `${API_BASE_URL}${photoPath}`;
}

function formatDate(isoString) {
  if (!isoString) return "";
  const d = new Date(isoString);
  return d.toLocaleString();
}

function categoryLabel(value) {
  const found = CATEGORIES.find((c) => c.value === value);
  return found ? found.label : value;
}

const CATEGORY_ICONS = {
  road: "🛣️",
  electric: "⚡",
  water_supply: "🚰",
  public_property: "🏛️",
  other: "🗂️",
};

function categoryIcon(value) {
  return CATEGORY_ICONS[value] || "📍";
}

function statusLabel(value) {
  return value.replace("_", " ");
}

function showBox(el, message) {
  el.textContent = message;
  el.style.display = message ? "block" : "none";
}

/**
 * Toggles a submit button between normal and "working" state — disables
 * it and shows a small spinner in place of its label. Call with (btn, true)
 * before an await, and (btn, false) in a finally block after.
 */
function setButtonLoading(btn, loading) {
  if (!btn) return;
  btn.disabled = loading;
  btn.classList.toggle("loading", loading);
}

function spinnerHtml() {
  return `<div class="spinner-center"><div class="spinner"></div></div>`;
}

/**
 * Wires up every "Show/Hide password" toggle button on the page. Runs
 * automatically once the page loads — pages just need the markup:
 *   <div class="password-field">
 *     <input type="password" id="x" />
 *     <button type="button" class="password-toggle" data-target="x">👁</button>
 *   </div>
 */
function wirePasswordToggles() {
  document.querySelectorAll(".password-toggle").forEach((btn) => {
    btn.addEventListener("click", () => {
      const input = document.getElementById(btn.dataset.target);
      if (!input) return;
      const nowShowing = input.type === "password";
      input.type = nowShowing ? "text" : "password";
      btn.textContent = nowShowing ? "🙈" : "👁";
      btn.setAttribute("aria-label", nowShowing ? "Hide password" : "Show password");
    });
  });
}

document.addEventListener("DOMContentLoaded", wirePasswordToggles);

/**
 * Dark mode. localStorage["theme"] is "dark", "light", or unset — unset
 * always means light (the site does not follow the OS/browser setting; only
 * the toggle button changes it). The <head> of every page also runs a tiny
 * inline copy of the "apply" half of this before the stylesheet paints, so
 * there's no flash of the wrong theme on load — this just keeps it in sync
 * and wires up the toggle button(s).
 */
function currentEffectiveTheme() {
  return localStorage.getItem("theme") === "dark" ? "dark" : "light";
}

function updateThemeToggleIcons() {
  const isDark = currentEffectiveTheme() === "dark";
  document.querySelectorAll("[data-theme-toggle]").forEach((btn) => {
    btn.textContent = isDark ? "☀️" : "🌙";
    btn.setAttribute("aria-label", isDark ? "Switch to light mode" : "Switch to dark mode");
  });
}

function initThemeToggles() {
  const saved = localStorage.getItem("theme");
  if (saved === "dark" || saved === "light") {
    document.documentElement.setAttribute("data-theme", saved);
  }
  updateThemeToggleIcons();

  document.querySelectorAll("[data-theme-toggle]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const next = currentEffectiveTheme() === "dark" ? "light" : "dark";
      localStorage.setItem("theme", next);
      document.documentElement.setAttribute("data-theme", next);
      updateThemeToggleIcons();
    });
  });
}

document.addEventListener("DOMContentLoaded", initThemeToggles);

/**
 * Scroll-reveal: any element with class="reveal" fades/slides into view the
 * first time it scrolls into the viewport. Add reveal-stagger alongside it
 * on a group of siblings for a staggered cascade (see style.css).
 */
function initScrollReveal() {
  const els = document.querySelectorAll(".reveal");
  if (!els.length) return;

  if (!("IntersectionObserver" in window)) {
    els.forEach((el) => el.classList.add("revealed"));
    return;
  }

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("revealed");
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.15 }
  );
  els.forEach((el) => observer.observe(el));
}

document.addEventListener("DOMContentLoaded", initScrollReveal);

/**
 * Staggered entrance animation for a freshly-rendered list of cards/rows —
 * call right after setting a container's innerHTML to a batch of items
 * (report cards, staff/citizen table rows, etc).
 */
function animateCardsIn(container, selector = ":scope > *") {
  if (!container) return;
  container.querySelectorAll(selector).forEach((el, i) => {
    el.classList.add("card-anim-in");
    el.style.animationDelay = `${Math.min(i, 8) * 45}ms`;
  });
}
