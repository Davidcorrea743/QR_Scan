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

function esSuperAdmin() { return getRol() === "super_admin"; }

function esAdmin() { var r = getRol(); return r === "admin" || r === "super_admin"; }

// Renderiza controles de paginación con botones numéricos, página activa
// resaltada y elipsis para rangos largos. Se oculta si solo hay una página.
function renderPaginacion(elId, page, pages, onGo) {
  var el = document.getElementById(elId);
  if (!el) return;
  if (!pages || pages <= 1) { el.innerHTML = ""; return; }

  function btn(p, label, opts) {
    opts = opts || {};
    var cls = "pag-btn" + (opts.active ? " pag-activo" : "");
    return '<button class="' + cls + '"' +
      (opts.disabled ? " disabled" : "") +
      ' onclick="' + onGo + "(" + p + ')">' + label + "</button>";
  }

  // Rango de páginas a mostrar, con elipsis si hay saltos.
  var nums = [];
  if (pages <= 7) {
    for (var i = 1; i <= pages; i++) nums.push(i);
  } else {
    nums.push(1);
    if (page > 3) nums.push("...");
    var desde = Math.max(2, page - 1);
    var hasta = Math.min(pages - 1, page + 1);
    for (var j = desde; j <= hasta; j++) nums.push(j);
    if (page < pages - 2) nums.push("...");
    nums.push(pages);
  }

  var html = btn(Math.max(1, page - 1), "‹", { disabled: page <= 1 });
  for (var k = 0; k < nums.length; k++) {
    var n = nums[k];
    if (n === "...") html += '<span class="pag-puntos">…</span>';
    else html += btn(n, n, { active: n === page });
  }
  html += btn(Math.min(pages, page + 1), "›", { disabled: page >= pages });
  html += '<span class="pag-info">Página ' + page + " de " + pages + "</span>";
  el.innerHTML = html;
}
