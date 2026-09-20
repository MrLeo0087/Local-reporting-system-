/*
  Small helpers shared by pages that need to know who's logged in, plus
  the header nav rendering used across citizen-facing pages.
*/

/**
 * Renders the header nav on citizen-facing pages (public feed, report
 * detail, login/register). Session-aware: reporting/"My Reports" are
 * citizen-only features, so a staff/admin session (even alongside a
 * leftover citizen session in the same browser) never sees them here —
 * they get a link back to their own dashboard instead.
 */
function renderCitizenHeader(activePage) {
  const citizenToken = getToken("citizen");
  const staffToken = getToken("staff");
  const staffRole = localStorage.getItem("staff_role");
  const nav = document.getElementById("nav-links");
  if (!nav) return;

  const links = [
    { href: "feed.html", label: "Public Feed" },
  ];

  if (staffToken) {
    links.push(
      staffRole === "admin"
        ? { href: "admin-dashboard.html", label: "Admin Dashboard" }
        : { href: "staff-dashboard.html", label: "Staff Dashboard" }
    );
  } else if (citizenToken) {
    links.push({ href: "submit-report.html", label: "Report a Problem" });
    links.push({ href: "my-reports.html", label: "My Reports" });
  } else {
    links.push({ href: "login.html", label: "Citizen Login" });
    links.push({ href: "register.html", label: "Register" });
  }

  let html = links
    .map(
      (l) =>
        `<a href="${l.href}" ${l.href === activePage ? 'class="active"' : ""}>${l.label}</a>`
    )
    .join("");

  if (staffToken || citizenToken) {
    html += `<span id="whoami-badge" class="whoami-badge"></span>`;
    html += `<button type="button" data-logout-btn>Log out</button>`;
  }
  if (!staffToken) {
    html += `<a href="staff-login.html">Staff Login</a>`;
  }
  html += `<button type="button" class="theme-toggle" data-theme-toggle aria-label="Toggle dark mode"></button>`;

  // Set the whole nav in one assignment — building it piece by piece with
  // extra `nav.innerHTML += ...` calls after attaching a JS click handler
  // (as this used to) re-parses the DOM and silently drops that handler,
  // which is why "Log out" used to stop working.
  nav.innerHTML = html;

  const logoutBtn = nav.querySelector("[data-logout-btn]");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", () => {
      clearToken(staffToken ? "staff" : "citizen");
      window.location.href = "index.html";
    });
  }

  renderWhoAmI();
}

/**
 * Shows "Logged in as <name> (<role>)" wherever a #whoami-badge element
 * exists in the page's header — the shared nav (see renderCitizenHeader)
 * or a static dashboard header. Only a bare token/role was ever kept in
 * localStorage, so this fetches the actual profile from /citizens/me or
 * /staff/me rather than guessing from the stored role string.
 */
async function renderWhoAmI() {
  const el = document.getElementById("whoami-badge");
  if (!el) return;

  const staffToken = getToken("staff");
  const citizenToken = getToken("citizen");
  if (!staffToken && !citizenToken) {
    el.textContent = "";
    return;
  }

  try {
    if (staffToken) {
      const me = await apiFetch("/staff/me", { authKind: "staff" });
      el.textContent = `Logged in as ${me.full_name} (${me.role === "admin" ? "Admin" : "Staff"})`;
    } else {
      const me = await apiFetch("/citizens/me", { authKind: "citizen" });
      el.textContent = `Logged in as ${me.full_name}`;
    }
  } catch (err) {
    el.textContent = "";
  }
}

/**
 * For login.html/register.html: a citizen login/register form should never
 * be shown to someone already logged in as a citizen. Deliberately ignores
 * any staff/admin session — those are independent, so being logged in as
 * staff has no bearing on the citizen login page. Call at the top of the page.
 */
function redirectIfAlreadyLoggedInAsCitizen() {
  if (getToken("citizen")) {
    window.location.href = "my-reports.html";
    return true;
  }
  return false;
}

/**
 * For staff-login.html: same idea, but for an existing staff/admin session.
 * Deliberately ignores any citizen session — logging in as a citizen
 * elsewhere in the same browser has no bearing on the staff login page.
 */
function redirectIfAlreadyLoggedInAsStaff() {
  const token = getToken("staff");
  if (token) {
    const role = localStorage.getItem("staff_role");
    window.location.href = role === "admin" ? "admin-dashboard.html" : "staff-dashboard.html";
    return true;
  }
  return false;
}

function requireCitizenLogin() {
  const token = getToken("citizen");
  if (!token) {
    window.location.href = "login.html";
  }
  return token;
}

/**
 * For the staff dashboard: requires a logged-in staff token, AND blocks
 * admins from it — reviewing/resolving complaints is department staff's
 * job, admins only manage staff accounts (see admin-dashboard.html).
 */
function requireStaffOnlyLogin() {
  const token = getToken("staff");
  const role = localStorage.getItem("staff_role");
  if (!token) {
    window.location.href = "staff-login.html";
    return null;
  }
  if (role === "admin") {
    window.location.href = "admin-dashboard.html";
    return null;
  }
  return token;
}

function requireAdminLogin() {
  const token = getToken("staff");
  const role = localStorage.getItem("staff_role");
  if (!token || role !== "admin") {
    window.location.href = "staff-login.html";
  }
  return token;
}
