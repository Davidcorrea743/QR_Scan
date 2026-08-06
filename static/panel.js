function getToken() { return localStorage.getItem("token") || ""; }
function getRol() { return localStorage.getItem("rol") || ""; }
function getUsername() { return localStorage.getItem("username") || ""; }

function logout() {
  localStorage.removeItem("token");
  localStorage.removeItem("rol");
  localStorage.removeItem("username");
  localStorage.removeItem("debe_cambiar_password");
  window.location.href = "/login";
}

function api(url, opts) {
  opts = opts || {};
  opts.headers = Object.assign({}, opts.headers || {});
  if (opts.body && !(opts.body instanceof FormData) && !opts.headers["Content-Type"]) {
    opts.headers["Content-Type"] = "application/json";
  }
  if (getToken()) opts.headers["Authorization"] = "Bearer " + getToken();
  return fetch(url, opts).then(function (r) {
    if (r.status === 401) { logout(); throw new Error("Sesión expirada"); }
    return r.json().then(function (data) {
      if (!r.ok) throw new Error(data.detail || r.statusText);
      return data;
    });
  });
}

function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
  });
}

function requiereLogin() {
  if (!getToken()) { window.location.href = "/login"; return false; }
  return true;
}

function esAdmin() { return getRol() === "admin"; }
