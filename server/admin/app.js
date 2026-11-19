/* NomadCeuticals admin: inbox for user reports + editor for provider listings (saved to GitHub). */
"use strict";
(function () {
  const app = document.getElementById("app");
  const S = { user: null, csrf: "", schema: null, cities: [], city: null, sha: null, providers: [], filter: { q: "", status: "", cond: "" }, inboxStatus: "new", reports: [], counts: {} };

  /* ---------- helpers ---------- */
  const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const $ = (sel, el = document) => el.querySelector(sel);
  const $$ = (sel, el = document) => Array.from(el.querySelectorAll(sel));
  const clone = x => JSON.parse(JSON.stringify(x));
  const today = () => { const d = new Date(); return new Date(d - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10); };
  const addDays = (iso, n) => { const d = new Date(iso + "T12:00:00Z"); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10); };
  const fmtTime = iso => { try { return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }); } catch (e) { return iso; } };
  const slug = s => String(s || "").normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 60);
  const label = k => LABELS[k] || String(k).replace(/_/g, " ").replace(/^./, c => c.toUpperCase());

  const LABELS = {
    public_hospital: "Public hospital", public_clinic: "Public clinic", bma_health_centre: "BMA health centre", ngo_clinic: "NGO clinic",
    key_population_clinic: "Key population clinic", private_clinic: "Private clinic", private_hospital: "Private hospital",
    government_national: "Government (national)", government_regional: "Government (regional)", government_local: "Government (local)",
    government_bma: "Government (BMA)", red_cross: "Red Cross", university: "University", ngo: "NGO", private: "Private",
    hiv: "HIV", adhd: "ADHD", diabetes: "Diabetes", msm: "MSM", lgbtqia: "LGBTQIA+", people_who_use_drugs: "People who use drugs", sex_workers: "Sex workers",
    hivTesting: "HIV testing", prep: "PrEP", pep: "PEP", art: "HIV treatment (ART)", stiTesting: "STI testing", genderAffirmingHormones: "Gender-affirming hormones",
    adhdAssessmentChildren: "ADHD assessment: children", adhdAssessmentAdults: "ADHD assessment: adults", adhdMedication: "Prescribes ADHD medicine",
    diabetesCare: "Diabetes care: adults", diabetesCareChildren: "Diabetes care: children", endocrinologist: "Endocrinologist", insulinPump: "Insulin pump",
    cgm: "Continuous glucose monitoring", diabetesEducation: "Diabetes education", diabeticFootCare: "Diabetic foot care",
    site: "This location", network: "Whole network", third_party: "Directory / news",
    free: "Free", low_cost: "Low cost", fee: "Fee", mixed: "Mixed",
    unverified: "Unverified", verified: "Verified", needs_review: "Needs review", closed: "Closed",
    phone: "Phone", email: "Email", in_person: "In person", official_registry: "Official registry",
    official_provider_site: "Provider's own site", government_announcement: "Government announcement", government_registry: "Government registry",
    third_party_directory: "Third-party directory", news: "News", phone_call: "Phone call",
    wrong_info: "Wrong or out-of-date info", site_bug: "Site problem", suggestion: "Suggestion", other: "Other", new: "New", in_progress: "In progress", done: "Done",
  };
  const SERVICES = {
    hiv: ["hivTesting", "prep", "pep", "art", "stiTesting", "genderAffirmingHormones"],
    adhd: ["adhdAssessmentChildren", "adhdAssessmentAdults", "adhdMedication"],
    diabetes: ["diabetesCare", "diabetesCareChildren", "endocrinologist", "insulinPump", "cgm", "diabetesEducation", "diabeticFootCare"],
  };
  const REQUIRED = { hiv: ["hivTesting", "prep", "pep", "art"], adhd: ["adhdAssessmentChildren", "adhdAssessmentAdults", "adhdMedication"], diabetes: ["diabetesCare", "diabetesCareChildren"] };
  const LANG_NAMES = { en: "English", th: "Thai", "zh-Hans": "Chinese (simplified)", "zh-Hant": "Chinese (traditional)", es: "Spanish", pt: "Portuguese" };

  function toast(html, kind = "ok", ms = 6000) {
    const t = document.getElementById("toast");
    t.className = "toast msg " + kind; t.innerHTML = html; t.hidden = false;
    clearTimeout(toast.timer); toast.timer = setTimeout(() => { t.hidden = true; }, ms);
  }

  async function api(a, { body, query = "" } = {}) {
    const opt = { method: body ? "POST" : "GET", credentials: "same-origin", headers: { Accept: "application/json" } };
    if (body) { opt.headers["Content-Type"] = "application/json"; opt.headers["X-CSRF-Token"] = S.csrf; opt.body = JSON.stringify(body); }
    let r, j;
    try { r = await fetch("api.php?a=" + a + query, opt); j = await r.json(); } catch (e) { throw { error: "network", message: "Couldn't reach the server. Check your connection." }; }
    if (r.status === 401 && a !== "login") { S.user = null; showLogin("Your session ended. Please log in again."); throw { error: "not_logged_in", silent: true }; }
    if (!r.ok || j.error) throw Object.assign({ status: r.status }, j);
    return j;
  }
  const errText = e => e.message || ({ wrong_login: "Wrong username or password.", locked: "Too many failed attempts. Wait 15 minutes and try again.",
    bad_csrf: "Your session expired. Reload the page.", network: "Couldn't reach the server." }[e.error]) || ("Something went wrong (" + (e.error || e.status) + ").");

  /* ---------- login ---------- */
  function showLogin(note) {
    $("#bar").hidden = true;
    app.innerHTML = `<form class="card narrow stack" id="login" autocomplete="on">
      <h1>Admin log in</h1>${note ? `<p class="msg warn">${esc(note)}</p>` : ""}
      <label>Username<input name="username" autocomplete="username" required></label>
      <label>Password<input name="password" type="password" autocomplete="current-password" required></label>
      <p class="msg err" id="loginerr" hidden></p>
      <button class="btn primary" type="submit">Log in</button></form>`;
    const f = $("#login");
    f.username.focus();
    f.onsubmit = async ev => {
      ev.preventDefault();
      const b = $("button", f); b.disabled = true;
      try {
        const j = await api("login", { body: { username: f.username.value, password: f.password.value } });
        S.user = j.user; S.csrf = j.csrf; await start();
      } catch (e) { const p = $("#loginerr"); p.hidden = false; p.textContent = errText(e); b.disabled = false; f.password.select(); }
    };
  }

  async function start() {
    const me = await api("me");
    if (!me.user) return showLogin();
    Object.assign(S, { user: me.user, csrf: me.csrf, repo: me.repo });
    setNew(me.newReports);
    $("#bar").hidden = false; $("#who").textContent = me.user;
    if (!S.schema) {
      const [schema, cities] = await Promise.all([fetch("/schema/provider.schema.json").then(r => r.json()), api("cities")]);
      S.schema = schema; S.cities = cities.cities;
    }
    route();
  }
  function setNew(n) { const b = $("#newcount"); b.hidden = !n; b.textContent = n || ""; }
  $("#logout").onclick = async () => { try { await api("logout", { body: {} }); } catch (e) {} S.user = null; location.hash = ""; showLogin(); };

  /* ---------- routing ---------- */
  let dirty = false;
  window.addEventListener("beforeunload", e => { if (dirty) { e.preventDefault(); e.returnValue = ""; } });
  window.addEventListener("hashchange", () => {
    if (dirty && !confirm("You have unsaved changes. Leave without saving?")) { history.replaceState(null, "", route.last); return; }
    dirty = false; route();
  });
  function route() {
    if (!S.user) return;
    route.last = location.hash || "#inbox";
    const h = (location.hash || "#inbox").slice(1).split("/").map(decodeURIComponent);
    const m = /^report-(\d+)$/.exec(h[0]);
    if (m) { location.replace("#inbox/" + m[1]); return; }
    $$("[data-nav]").forEach(a => a.setAttribute("aria-current", a.dataset.nav === h[0] ? "page" : "false"));
    window.scrollTo(0, 0);
    if (h[0] === "listings") return h[1] ? (h[2] ? showEditor(h[1], h[2]) : showCity(h[1])) : showCities();
    if (h[0] === "settings") return showSettings();
    return showInbox(h[1] ? +h[1] : null);
  }

  /* ---------- inbox ---------- */
  async function showInbox(openId) {
    app.innerHTML = `<div class="row" style="margin-bottom:14px"><h1 style="margin:0">Inbox</h1><span class="spacer"></span>
      <div class="seg" role="group" aria-label="Show">${["new", "in_progress", "done", "all"].map(s =>
        `<button type="button" data-st="${s}" aria-pressed="${s === S.inboxStatus}">${s === "all" ? "All" : label(s)}<span class="muted" data-count="${s}"></span></button>`).join("")}</div></div>
      <div class="inbox" id="inbox"><div class="list" id="ilist"><p class="empty">Loading…</p></div><div class="detail card" id="idetail"><p class="empty">Choose a report.</p></div></div>`;
    $$("[data-st]").forEach(b => b.onclick = () => { S.inboxStatus = b.dataset.st; showInbox(); });
    try {
      let j = await api("reports", { query: "&status=" + S.inboxStatus });
      if (openId && !j.reports.some(r => +r.id === openId)) { S.inboxStatus = "all"; $$("[data-st]").forEach(b => b.setAttribute("aria-pressed", b.dataset.st === "all")); j = await api("reports", { query: "&status=all" }); }
      S.reports = j.reports; S.counts = j.counts;
    } catch (e) { if (!e.silent) $("#ilist").innerHTML = `<p class="msg err">${esc(errText(e))}</p>`; return; }
    const total = Object.values(S.counts).reduce((a, b) => a + b, 0);
    $$("[data-count]").forEach(s => { const n = s.dataset.count === "all" ? total : (S.counts[s.dataset.count] || 0); s.textContent = n ? " " + n : ""; });
    setNew(S.counts.new || 0);
    const list = $("#ilist");
    if (!S.reports.length) { list.innerHTML = `<p class="empty">No ${S.inboxStatus === "all" ? "" : label(S.inboxStatus).toLowerCase() + " "}reports.</p>`; return; }
    list.innerHTML = S.reports.map(r => `<button type="button" class="item" data-id="${r.id}">
      <span class="top"><span class="chip ${esc(r.status)}">${esc(label(r.status))}</span>${esc(label(r.category))}<span class="spacer"></span>${esc(fmtTime(r.created))}</span>
      <span class="about">${esc(r.about || "General")}</span><span class="ex">${esc(r.details)}</span></button>`).join("");
    $$(".item", list).forEach(b => b.onclick = () => { history.replaceState(null, "", "#inbox/" + b.dataset.id); openReport(+b.dataset.id); });
    if (openId) openReport(openId);
  }

  function openReport(id) {
    const r = S.reports.find(x => +x.id === id);
    const d = $("#idetail");
    if (!r) { d.innerHTML = `<p class="empty">Report #${id} not found.</p>`; return; }
    $$(".item").forEach(b => b.setAttribute("aria-current", +b.dataset.id === id));
    $("#inbox").classList.add("has-detail");
    const city = r.record_id ? (r.record_id.split("-")[1] || "") : "";
    const subject = encodeURIComponent("Re: your NomadCeuticals report" + (r.about ? " about " + r.about : ""));
    const quote = encodeURIComponent("\n\n---\nYou wrote:\n" + r.details);
    d.innerHTML = `<button type="button" class="btn small quiet back-to-list" id="back">← All reports</button>
      <div class="row"><h2 style="margin:0">${esc(r.about || "General report")}</h2><span class="spacer"></span><span class="muted">#${r.id}</span></div>
      <p class="muted" style="margin:4px 0 0">${esc(label(r.category))} · ${esc(fmtTime(r.created))}</p>
      <div class="details">${esc(r.details)}</div>
      <dl>
        ${r.record_id ? `<dt>Listing</dt><dd><code>${esc(r.record_id)}</code></dd>` : ""}
        ${r.page ? `<dt>Page</dt><dd><a href="${esc(/^https?:\/\//.test(r.page) ? r.page : "#")}" target="_blank" rel="noopener noreferrer">${esc(r.page)}</a></dd>` : ""}
        ${r.lang ? `<dt>Language</dt><dd>${esc(LANG_NAMES[r.lang] || r.lang)}</dd>` : ""}
        <dt>Reply to</dt><dd>${r.email ? esc(r.email) : '<span class="muted">No email given</span>'}</dd>
        ${r.updated ? `<dt>Last changed</dt><dd>${esc(fmtTime(r.updated))}</dd>` : ""}
      </dl>
      <div class="row" style="margin-bottom:14px">
        ${r.record_id ? `<a class="btn primary" href="#listings/${esc(city)}/${esc(r.record_id)}">Edit listing</a>` : ""}
        ${r.email ? `<a class="btn" href="mailto:${esc(r.email)}?subject=${subject}&body=${quote}">Reply by email</a>` : ""}
      </div>
      <div class="stack">
        <div><strong>Status</strong><div class="seg" role="group" aria-label="Status" style="display:flex;margin-top:4px">${["new", "in_progress", "done"].map(s =>
          `<button type="button" data-set="${s}" aria-pressed="${r.status === s}">${label(s)}</button>`).join("")}</div></div>
        <label>Private note<textarea id="note" placeholder="Only you can see this">${esc(r.note || "")}</textarea></label>
        <div class="row"><button type="button" class="btn" id="savenote">Save note</button><span class="spacer"></span><button type="button" class="btn danger" id="del">Delete report</button></div>
      </div>`;
    $("#back").onclick = () => { $("#inbox").classList.remove("has-detail"); history.replaceState(null, "", "#inbox"); };
    $$("[data-set]", d).forEach(b => b.onclick = async () => {
      try { await api("report_update", { body: { id, status: b.dataset.set } }); r.status = b.dataset.set; toast("Marked as " + esc(label(r.status).toLowerCase()) + "."); showInbox(id); }
      catch (e) { if (!e.silent) toast(esc(errText(e)), "err"); }
    });
    $("#savenote").onclick = async () => {
      try { await api("report_update", { body: { id, note: $("#note").value } }); r.note = $("#note").value; toast("Note saved."); } catch (e) { if (!e.silent) toast(esc(errText(e)), "err"); }
    };
    $("#del").onclick = async () => {
      if (!confirm("Delete report #" + id + "? This can't be undone.")) return;
      try { await api("report_delete", { body: { id } }); toast("Report deleted."); history.replaceState(null, "", "#inbox"); showInbox(); } catch (e) { if (!e.silent) toast(esc(errText(e)), "err"); }
    };
  }

  /* ---------- listings ---------- */
  function showCities() {
    app.innerHTML = `<h1>Listings</h1><p class="muted">Choose a city. Changes are saved to GitHub and go live on the website about 2 minutes later.</p>
      <div class="grid">${S.cities.slice().sort((a, b) => a.name.localeCompare(b.name)).map(c =>
        `<a class="card" style="text-decoration:none;color:inherit" href="#listings/${esc(c.code)}"><h3 style="margin:0">${esc(c.name)}</h3><span class="muted">${esc(c.country)} · ${esc(c.code)}</span></a>`).join("")}</div>`;
  }

  async function loadCity(code, force) {
    if (!force && S.city && S.city.code === code && S.providers.length) return;
    const j = await api("providers", { query: "&city=" + encodeURIComponent(code) });
    S.city = j.city; S.sha = j.sha; S.providers = j.providers;
  }

  const isDue = p => (p.verification && (p.verification.status === "needs_review" || (p.verification.nextReviewDue && p.verification.nextReviewDue <= today())));

  async function showCity(code) {
    app.innerHTML = `<p class="muted">Loading listings from GitHub…</p>`;
    try { await loadCity(code, true); } catch (e) { if (!e.silent) app.innerHTML = `<p class="msg err">${esc(errText(e))}</p><p><a href="#listings">Back</a></p>`; return; }
    const f = S.filter;
    app.innerHTML = `<div class="crumbs"><a href="#listings">Listings</a> › ${esc(S.city.name)}</div>
      <div class="row" style="margin-bottom:14px"><h1 style="margin:0">${esc(S.city.name)} <span class="muted" style="font-size:18px" id="count"></span></h1><span class="spacer"></span>
        <a class="btn primary" href="#listings/${esc(code)}/new">+ Add listing</a></div>
      <div class="row" style="margin-bottom:12px">
        <input type="search" id="q" placeholder="Search name, district, organisation…" value="${esc(f.q)}" style="flex:1 1 260px;width:auto">
        <select id="fstatus" style="width:auto"><option value="">Any status</option>${["unverified", "verified", "needs_review", "closed", "due"].map(s =>
          `<option value="${s}" ${f.status === s ? "selected" : ""}>${s === "due" ? "Due for review" : label(s)}</option>`).join("")}</select>
        <select id="fcond" style="width:auto"><option value="">All conditions</option>${["hiv", "adhd", "diabetes"].map(c => `<option value="${c}" ${f.cond === c ? "selected" : ""}>${label(c)}</option>`).join("")}</select>
      </div>
      <div class="table-wrap"><table><thead><tr><th>Name</th><th>Type</th><th>For</th><th>Status</th><th>Last verified</th><th>Updated</th></tr></thead><tbody id="rows"></tbody></table></div>`;
    const draw = () => {
      const q = f.q.trim().toLowerCase();
      const rows = S.providers.filter(p => {
        const v = p.verification || {};
        if (f.status === "due" ? !isDue(p) : (f.status && v.status !== f.status)) return false;
        if (f.cond && !(p.conditions || []).includes(f.cond)) return false;
        if (q && !JSON.stringify([p.name, p.organization, p.location && p.location.district, p.location && p.location.area, p.id]).toLowerCase().includes(q)) return false;
        return true;
      }).sort((a, b) => (a.name.en || "").localeCompare(b.name.en || ""));
      $("#count").textContent = rows.length === S.providers.length ? `(${rows.length})` : `(${rows.length} of ${S.providers.length})`;
      $("#rows").innerHTML = rows.map(p => { const v = p.verification || {}; return `<tr data-id="${esc(p.id)}" tabindex="0">
        <td><a href="#listings/${esc(code)}/${esc(p.id)}">${esc(p.name.en)}</a><span class="sub">${esc([p.location && p.location.district, p.organization].filter(Boolean).join(" · "))}</span></td>
        <td>${esc(label(p.type))}</td><td>${(p.conditions || []).map(c => `<span class="chip">${esc(label(c))}</span>`).join(" ")}</td>
        <td><span class="chip ${esc(v.status)}">${esc(label(v.status))}</span>${isDue(p) && v.status !== "needs_review" ? ' <span class="chip due">Due</span>' : ""}</td>
        <td>${esc(v.lastVerified || "–")}</td><td>${esc(p.updated || "")}</td></tr>`; }).join("") || `<tr><td colspan="6" class="empty">No listings match.</td></tr>`;
      $$("#rows tr[data-id]").forEach(tr => { tr.onclick = e => { if (e.target.tagName !== "A") location.hash = `#listings/${code}/${tr.dataset.id}`; }; tr.onkeydown = e => { if (e.key === "Enter") tr.click(); }; });
    };
    $("#q").oninput = e => { f.q = e.target.value; draw(); };
    $("#fstatus").onchange = e => { f.status = e.target.value; draw(); };
    $("#fcond").onchange = e => { f.cond = e.target.value; draw(); };
    draw();
  }

  function blankProvider() {
    const c = S.city, ex = S.providers[0] || {};
    const loc = ex.location || {};
    return {
      id: "", conditions: ["hiv"], city: c.code, name: { en: "" }, organization: "", type: "public_clinic", operator: "government_national", network: null,
      location: { country: c.country, province: loc.province || "", city: loc.city || c.name, area: null, district: null, address: { en: null }, postcode: null, locationNote: null, nearestTransit: null, lat: null, lng: null },
      contact: { phone: [], line: null, website: null, email: null, booking: null }, hours: null,
      services: { hivTesting: null, prep: null, pep: null, art: null, basis: "site", note: null }, populationFocus: ["general"],
      access: { cost: null, walkIn: null, foreignersAccepted: null, languages: [] },
      sources: [{ url: "", title: "", publisher: "", type: "official_provider_site", accessed: today() }],
      verification: { status: "unverified", sourceChecked: today(), lastVerified: null, method: null, verifiedBy: null, nextReviewDue: null },
      notes: null, updated: today(),
    };
  }

  /* editor: form <-> record */
  const enumOf = path => { let s = S.schema.properties; const parts = path.split("."); let node = null;
    for (const k of parts) { node = s[k]; if (!node) return []; if (node.$ref) node = S.schema.$defs[node.$ref.split("/").pop()]; s = node.properties || {}; }
    return (node.enum || (node.items && node.items.enum) || []); };
  const opts = (values, cur, unknownLabel) => values.map(v => v === null ? `<option value="" ${cur == null ? "selected" : ""}>${esc(unknownLabel || "Unknown")}</option>` :
    `<option value="${esc(v)}" ${cur === v ? "selected" : ""}>${esc(label(v))}</option>`).join("");
  const tri = (name, v) => `<select data-tri="${name}"><option value="true" ${v === true ? "selected" : ""}>Yes</option><option value="false" ${v === false ? "selected" : ""}>No</option><option value="" ${v == null ? "selected" : ""}>Unknown</option></select>`;
  const txt = (path, v, attrs = "") => `<input data-p="${path}" value="${esc(v == null ? "" : v)}" ${attrs}>`;
  const area = (path, v, attrs = "") => `<textarea data-p="${path}" ${attrs}>${esc(v == null ? "" : v)}</textarea>`;

  async function showEditor(code, id) {
    app.innerHTML = `<p class="muted">Loading…</p>`;
    try { await loadCity(code); } catch (e) { if (!e.silent) app.innerHTML = `<p class="msg err">${esc(errText(e))}</p>`; return; }
    const isNew = id === "new";
    const orig = isNew ? blankProvider() : S.providers.find(p => p.id === id);
    if (!orig) { app.innerHTML = `<p class="msg err">Listing ${esc(id)} isn't in ${esc(S.city.name)} any more.</p><p><a href="#listings/${esc(code)}">Back to ${esc(S.city.name)}</a></p>`; return; }
    let rec = clone(orig), idTouched = !isNew, jsonMode = false;

    const render = () => {
      const v = rec.verification || {}, s = rec.services || {}, a = rec.access || {}, L = rec.location || {}, C = rec.contact || {};
      const nameLangs = Array.from(new Set(["en", ...Object.keys(rec.name || {}), ...(S.city.localLanguages || [])]));
      const svcRows = ["hiv", "adhd", "diabetes"].filter(c => (rec.conditions || []).includes(c)).map(c =>
        `<h4>${label(c)}</h4>` + SERVICES[c].map(k => `<span>${esc(label(k))}${REQUIRED[c].includes(k) ? "" : ' <small>(optional)</small>'}</span>${tri("services." + k, s[k])}`).join("")).join("");
      app.innerHTML = `<div class="crumbs"><a href="#listings">Listings</a> › <a href="#listings/${esc(code)}">${esc(S.city.name)}</a> › ${isNew ? "New listing" : esc(orig.name.en)}</div>
        <div class="row" style="margin-bottom:6px"><h1 style="margin:0">${isNew ? "New listing" : esc(orig.name.en)}</h1><span class="spacer"></span>
          ${isNew ? "" : `<span class="chip ${esc(v.status)}">${esc(label(v.status))}</span>`}
          <button type="button" class="btn small quiet" id="mode">${jsonMode ? "Back to form" : "Edit as JSON"}</button></div>
        <div id="problems"></div>
        ${jsonMode ? `<textarea class="json" id="json" spellcheck="false">${esc(JSON.stringify(rec, null, 2))}</textarea>` : `<form class="editor" id="ed" novalidate>
        ${isNew ? "" : `<div class="card row"><strong>Quick actions</strong><span class="muted">Called or checked an official source?</span><span class="spacer"></span>
          <select id="vmethod" style="width:auto" aria-label="How you checked">${opts(["phone", "email", "in_person", "official_registry"], v.method || "phone")}</select>
          <button type="button" class="btn" id="verify">Mark verified today</button><button type="button" class="btn danger" id="close">Mark closed</button></div>`}
        <fieldset><legend>Basics</legend><div class="grid">
          ${nameLangs.map(l => `<label>Name (${esc(LANG_NAMES[l] || l)})${l === "en" ? "" : " <small>optional</small>"}${txt("name." + l, (rec.name || {})[l], l === "en" ? "required" : "")}</label>`).join("")}
          <label>Organisation${txt("organization", rec.organization, "required")}</label>
          <label>Network <small>optional</small>${txt("network", rec.network)}</label>
          <label>Type<select data-p="type">${opts(enumOf("type"), rec.type)}</select></label>
          <label>Run by<select data-p="operator">${opts(enumOf("operator"), rec.operator)}</select></label>
          <div><strong>Listed for</strong><div class="checks" style="margin-top:8px">${["hiv", "adhd", "diabetes"].map(c =>
            `<label><input type="checkbox" data-cond="${c}" ${(rec.conditions || []).includes(c) ? "checked" : ""}>${label(c)}</label>`).join("")}</div></div>
          <label>ID <small>${isNew ? "made from the name; can't change later" : "permanent"}</small>${txt("id", rec.id, isNew ? 'required pattern="[a-z]{2}-[a-z]{3}-[a-z0-9-]+"' : "readonly")}</label>
        </div></fieldset>
        <fieldset><legend>Location</legend><div class="grid">
          <label class="wide">Address${area("location.address.en", (L.address || {}).en)}</label>
          <label>District${txt("location.district", L.district)}</label><label>Area${txt("location.area", L.area)}</label>
          <label>Postcode${txt("location.postcode", L.postcode)}</label><label>Nearest transit${txt("location.nearestTransit", L.nearestTransit)}</label>
          <label class="wide">Location note <small>e.g. which floor or entrance</small>${txt("location.locationNote", L.locationNote)}</label>
          <label>Latitude${txt("location.lat", L.lat, 'inputmode="decimal"')}</label><label>Longitude${txt("location.lng", L.lng, 'inputmode="decimal"')}</label>
          <label>City${txt("location.city", L.city, "required")}</label><label>Province / state${txt("location.province", L.province, "required")}</label>
        </div></fieldset>
        <fieldset><legend>Contact and hours</legend><div class="grid">
          <label>Phone numbers <small>one per line</small><textarea data-p="contact.phone" data-list="lines">${esc((C.phone || []).join("\n"))}</textarea></label>
          <label class="wide">Opening hours${area("hours", rec.hours)}</label>
          <label>Website${txt("contact.website", C.website, 'type="url" placeholder="https://"')}</label>
          <label>Booking link${txt("contact.booking", C.booking, 'type="url" placeholder="https://"')}</label>
          <label>Email${txt("contact.email", C.email)}</label><label>LINE ID${txt("contact.line", C.line)}</label>
        </div></fieldset>
        <fieldset><legend>Services</legend>
          <div class="svc">${svcRows || '<p class="muted">Tick at least one condition under Basics.</p>'}</div>
          <div class="grid" style="margin-top:14px">
            <label>Where this information comes from<select data-p="services.basis">${opts(enumOf("services.basis"), s.basis)}</select></label>
            <label class="wide">Service note <small>shown on the site</small>${area("services.note", s.note)}</label></div>
        </fieldset>
        <fieldset><legend>Access</legend><div class="grid">
          <label>Cost<select data-p="access.cost">${opts(["free", "low_cost", "fee", "mixed", null], a.cost)}</select></label>
          <label>Walk-in${tri("access.walkIn", a.walkIn)}</label><label>Sees foreigners / visitors${tri("access.foreignersAccepted", a.foreignersAccepted)}</label>
          <label>Languages <small>comma separated, e.g. en, th</small><input data-p="access.languages" data-list="comma" value="${esc((a.languages || []).join(", "))}"></label>
          <div class="wide"><strong>Focus</strong><div class="checks" style="margin-top:8px">${enumOf("populationFocus").map(pf =>
            `<label><input type="checkbox" data-pf="${pf}" ${(rec.populationFocus || []).includes(pf) ? "checked" : ""}>${esc(label(pf))}</label>`).join("")}</div></div>
          <label class="wide">Internal notes <small>shown on the site</small>${area("notes", rec.notes)}</label>
        </div></fieldset>
        <fieldset class="sources"><legend>Sources</legend><div id="srcs">${(rec.sources || []).map((x, i) => `<div class="src" data-src="${i}">
          <label class="wide">Link${`<input data-s="url" value="${esc(x.url)}" type="url" placeholder="https://" required>`}</label>
          <label>Title<input data-s="title" value="${esc(x.title || "")}"></label><label>Publisher<input data-s="publisher" value="${esc(x.publisher || "")}"></label>
          <label>Kind<select data-s="type">${opts(enumOf("sources").length ? enumOf("sources") : S.schema.properties.sources.items.properties.type.enum, x.type)}</select></label>
          <label>Checked on<input data-s="accessed" type="date" value="${esc(x.accessed || "")}"></label>
          <div class="wide"><button type="button" class="btn small danger" data-rmsrc="${i}">Remove source</button></div></div>`).join("")}</div>
          <button type="button" class="btn small" id="addsrc">+ Add source</button></fieldset>
        <fieldset><legend>Verification</legend><div class="grid">
          <label>Status<select data-p="verification.status">${opts(S.schema.properties.verification.properties.status.enum, v.status)}</select></label>
          <label>Sources checked on${txt("verification.sourceChecked", v.sourceChecked, 'type="date" required')}</label>
          <label>Last verified${txt("verification.lastVerified", v.lastVerified, 'type="date"')}</label>
          <label>How<select data-p="verification.method">${opts([...S.schema.properties.verification.properties.method.enum.filter(Boolean), null], v.method, "—")}</select></label>
          <label>Verified by${txt("verification.verifiedBy", v.verifiedBy)}</label>
          <label>Next review due${txt("verification.nextReviewDue", v.nextReviewDue, 'type="date"')}</label>
        </div></fieldset></form>`}
        <div class="savebar"><div class="in"><span class="muted" id="state">${isNew ? "New listing" : "Last updated " + esc(orig.updated || "")}</span><span class="spacer"></span>
          <a class="btn quiet" href="#listings/${esc(code)}">Cancel</a><button type="button" class="btn primary" id="save">${isNew ? "Add and publish" : "Save and publish"}</button></div></div>`;
      wire();
    };

    const collect = () => {
      if (jsonMode) { rec = JSON.parse($("#json").value); return rec; }
      const r = clone(rec), set = (path, val) => { const ks = path.split("."); let o = r; ks.slice(0, -1).forEach(k => { if (o[k] == null || typeof o[k] !== "object") o[k] = {}; o = o[k]; }); o[ks[ks.length - 1]] = val; };
      $$("[data-p]", app).forEach(el => {
        const p = el.dataset.p; let val = el.value.trim();
        if (el.dataset.list === "lines") val = val.split("\n").map(x => x.trim()).filter(Boolean);
        else if (el.dataset.list === "comma") val = val.split(",").map(x => x.trim()).filter(Boolean);
        else if (p === "location.lat" || p === "location.lng") val = val === "" ? null : (isNaN(+val) ? val : +val);
        else if (val === "") val = (p === "organization" || p === "location.city" || p === "location.province" || p === "id" || p === "name.en") ? "" : null;
        set(p, val);
      });
      Object.keys(r.name).forEach(k => { if (k !== "en" && r.name[k] == null) delete r.name[k]; });
      $$("[data-tri]", app).forEach(el => set(el.dataset.tri, el.value === "" ? null : el.value === "true"));
      r.conditions = $$("[data-cond]", app).filter(c => c.checked).map(c => c.dataset.cond);
      // services: required keys for chosen conditions always present; optional ones only when known or already there; other conditions' keys removed
      Object.entries(SERVICES).forEach(([c, keys]) => keys.forEach(k => {
        if (!r.conditions.includes(c)) delete r.services[k];
        else if (!REQUIRED[c].includes(k) && r.services[k] == null && !(rec.services && k in rec.services)) delete r.services[k];
        else if (!(k in r.services)) r.services[k] = null;
      }));
      const order = [...Object.values(SERVICES).flat().filter(k => k in r.services), "basis", "note"];
      r.services = Object.fromEntries(order.filter(k => k in r.services).map(k => [k, r.services[k]]));
      r.populationFocus = $$("[data-pf]", app).filter(c => c.checked).map(c => c.dataset.pf);
      r.sources = $$("[data-src]", app).map(d => { const o = {}; $$("[data-s]", d).forEach(el => { const val = el.value.trim(); if (val || ["url", "type", "accessed"].includes(el.dataset.s)) o[el.dataset.s] = val; }); return o; });
      return (rec = r);
    };

    const wire = () => {
      const form = $("#ed");
      $("#mode").onclick = () => {
        try { collect(); } catch (e) { return showProblems(["The JSON isn't valid: " + e.message]); }
        jsonMode = !jsonMode; render();
      };
      $("#save").onclick = () => save();
      if (!form) { $("#json").oninput = () => { dirty = true; }; return; }
      form.addEventListener("input", () => { dirty = true; $("#state").textContent = "Unsaved changes"; });
      form.addEventListener("change", () => { dirty = true; $("#state").textContent = "Unsaved changes"; });
      $$("[data-cond]", form).forEach(c => c.onchange = () => { collect(); render(); dirty = true; });
      const nameEn = $('[data-p="name.en"]', form), idEl = $('[data-p="id"]', form);
      if (isNew) {
        nameEn.addEventListener("input", () => { if (!idTouched) idEl.value = `${S.city.country.toLowerCase()}-${S.city.code}-${slug(nameEn.value)}`; });
        idEl.addEventListener("input", () => { idTouched = true; });
      }
      $("#addsrc").onclick = () => { collect(); rec.sources.push({ url: "", title: "", publisher: "", type: "official_provider_site", accessed: today() }); render(); dirty = true; };
      $$("[data-rmsrc]", form).forEach(b => b.onclick = () => { collect(); rec.sources.splice(+b.dataset.rmsrc, 1); render(); dirty = true; });
      if (!isNew) {
        $("#verify").onclick = () => {
          collect();
          const v = rec.verification; const t = today();
          Object.assign(v, { status: "verified", lastVerified: t, sourceChecked: v.sourceChecked || t, method: $("#vmethod").value, verifiedBy: v.verifiedBy || S.user, nextReviewDue: addDays(t, 90) });
          if (!confirm(`Mark "${rec.name.en}" as verified today (${t}) by ${v.method.replace("_", " ")}, next review ${v.nextReviewDue}, and publish?`)) { rec = clone(orig); return render(); }
          render(); save("verify");
        };
        $("#close").onclick = () => {
          collect();
          if (!confirm(`Mark "${rec.name.en}" as closed and publish? It will show as closed on the site.`)) return;
          Object.assign(rec.verification, { status: "closed", lastVerified: today(), sourceChecked: rec.verification.sourceChecked || today() });
          render(); save("close");
        };
      }
    };

    const showProblems = list => {
      $("#problems").innerHTML = list && list.length ? `<div class="msg err" role="alert">Please fix these before saving:<ul>${list.map(p => `<li>${esc(friendly(p))}</li>`).join("")}</ul></div>` : "";
      if (list && list.length) $("#problems").scrollIntoView({ block: "center" });
    };
    const friendly = p => p.replace(/^\/?([\w/]+):/, (m, path) => path.split("/").filter(Boolean).map(x => /^\d+$/.test(x) ? "#" + (+x + 1) : label(x)).join(" › ") + ":");

    async function save(action) {
      let r;
      try { r = collect(); } catch (e) { return showProblems(["The JSON isn't valid: " + e.message]); }
      const local = [];
      if (!r.name || !r.name.en) local.push("name/en: required");
      if (!r.organization) local.push("organization: required");
      if (!r.conditions || !r.conditions.length) local.push("conditions: tick at least one");
      if (!r.sources || !r.sources.length) local.push("sources: add at least one source");
      (r.sources || []).forEach((x, i) => { if (!/^https?:\/\//.test(x.url || "")) local.push(`sources/${i}/url: needs a link starting with https://`); });
      if (local.length) return showProblems(local);
      const b = $("#save"); b.disabled = true; $("#state").textContent = "Saving to GitHub…";
      try {
        const j = await api("provider_save", { body: { city: code, sha: S.sha, original_id: isNew ? null : orig.id, action: action || "update", record: r } });
        S.sha = j.sha;
        if (isNew) S.providers.push(j.record); else S.providers[S.providers.findIndex(p => p.id === orig.id)] = j.record;
        dirty = false;
        toast(`Saved. The live site updates in about 2 minutes.${j.commit ? ` <a href="${esc(j.commit)}" target="_blank" rel="noopener">See the change on GitHub</a>` : ""}`, "ok", 9000);
        location.hash = `#listings/${code}/${encodeURIComponent(j.record.id)}`;
        if (!isNew) showEditor(code, j.record.id);
      } catch (e) {
        b.disabled = false; $("#state").textContent = "Not saved";
        if (e.silent) return;
        if (e.error === "invalid") showProblems(e.problems);
        else if (e.error === "changed") { showProblems([e.message]); toast(esc(e.message) + ' <a href="#" id="reload">Reload this city</a>', "warn", 15000); const a = $("#reload"); if (a) a.onclick = ev => { ev.preventDefault(); dirty = false; S.providers = []; route(); }; }
        else showProblems([errText(e)]);
      }
    }
    render();
  }

  /* ---------- settings ---------- */
  function showSettings() {
    app.innerHTML = `<h1>Settings</h1><div class="stack" style="max-width:720px">
      <div class="card stack"><h2>Email notifications</h2><p>New reports are emailed to the address you entered during setup. Check your spam folder the first time.</p>
        <div class="row"><button class="btn" id="testmail" type="button">Send a test email</button><span id="mailres"></span></div></div>
      <div class="card stack"><h2>Saving to GitHub</h2><p>Edits are saved as commits to <code>${esc(S.repo || "")}</code> (branch main). GitHub then rebuilds the site and Hostinger publishes it, usually within 2 minutes.</p>
        <p class="muted">If you also edit files on your computer, run <code>git pull</code> before you start, so you have the admin's changes.</p></div>
      <div class="card stack"><h2>Password or GitHub token</h2><p>To change them: in Hostinger's File Manager, open the <code>nc-private</code> folder (next to <code>public_html</code>), delete <code>config.php</code>, then open <a href="setup.php">setup</a> again. The inbox is kept.</p></div>
    </div>`;
    $("#testmail").onclick = async () => {
      const out = $("#mailres"); out.textContent = "Sending…";
      try { const j = await api("test_email", { body: {} }); out.textContent = j.ok ? "Sent. It should arrive within a few minutes." : "The server couldn't send it. Check that email is enabled for your Hostinger plan."; }
      catch (e) { if (!e.silent) out.textContent = errText(e); }
    };
  }

  start().catch(e => { if (!e.silent) app.innerHTML = `<p class="msg err">${esc(e.error === "not_set_up" ? "The admin isn't set up yet." : errText(e))}</p>${e.error === "not_set_up" ? '<p><a class="btn primary" href="setup.php">Set up now</a></p>' : ""}`; });
})();
