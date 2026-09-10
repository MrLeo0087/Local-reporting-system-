/*
  Shared API helper functions. Every frontend page includes this file.
  Change API_BASE_URL to point at your running backend.
*/
const API_BASE_URL = "https://local-reporting-system.onrender.com/";

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

function statusLabel(value) {
  return value.replace("_", " ");
}

function showBox(el, message) {
  el.textContent = message;
  el.style.display = message ? "block" : "none";
}
