/*
  Small helpers shared by pages that need to know who's logged in, plus
  the header nav rendering used across citizen-facing pages.
*/

function renderCitizenHeader(activePage) {
  const token = getToken("citizen");
  const nav = document.getElementById("nav-links");
  if (!nav) return;

  const links = [
    { href: "index.html", label: "Public Feed" },
  ];

  if (token) {
    links.push({ href: "submit-report.html", label: "Report a Problem" });
    links.push({ href: "my-reports.html", label: "My Reports" });
  } else {
    links.push({ href: "login.html", label: "Citizen Login" });
    links.push({ href: "register.html", label: "Register" });
  }

  nav.innerHTML = links
    .map(
      (l) =>
        `<a href="${l.href}" ${l.href === activePage ? 'class="active"' : ""}>${l.label}</a>`
    )
    .join("");

  if (token) {
    const btn = document.createElement("button");
    btn.textContent = "Log out";
    btn.onclick = () => {
      clearToken("citizen");
      window.location.href = "index.html";
    };
    nav.appendChild(btn);
  }

  nav.innerHTML += `<a href="staff-login.html">Staff Login</a>`;
}

function requireCitizenLogin() {
  const token = getToken("citizen");
  if (!token) {
    window.location.href = "login.html";
  }
  return token;
}

function requireStaffLogin() {
  const token = getToken("staff");
  if (!token) {
    window.location.href = "staff-login.html";
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
