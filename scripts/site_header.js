/* NomadCeuticals site header: the one top bar on every page (home, OTC finder, API docs, 404).
   Source of truth: scripts/site_header.js + scripts/site_header.css, inlined into each page by scripts/site_header.py.
   To add or change a menu item, edit NAV below (and its label in i18n/ui.json), then rebuild: every page picks it up.

   NCHeader.render({ base, active, lang, t, onLang })
     base   where the home page is, relative to this page: "" (the home page itself), "./", "../" or "/"
     active which item is current: "med", "prov" or "otc"
     lang   interface language; t(key) translates (defaults to the labels built in from i18n/ui.json)
     onLang called when the visitor picks a language (the home page re-renders itself; other pages just relabel the bar) */
const NCHeader = (() => {
  const C = __SITE_HEADER_CFG__;
  const NAV = [
    { id: "med", key: "navMedicines", hash: "#medicines", count: C.counts.medicines },
    { id: "prov", key: "navProviders", hash: "#providers", count: C.counts.providers },
    { id: "otc", key: "navOtc", page: "otc-finder.html" },
  ];
  const TS = [["tsDefault", 1], ["tsLarge", 1.15], ["tsLarger", 1.3]];
  const ICON_TS = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5" fill="none" stroke="currentColor" stroke-width="2"/><path d="M15.5 15.5 21 21" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"/><path d="M7.6 12.6 10.5 7.4l2.9 5.2M8.5 11h4" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  const ICON_GLOBE = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M3 12h18M12 3c2.5 2.6 3.7 5.6 3.7 9s-1.2 6.4-3.7 9c-2.5-2.6-3.7-5.6-3.7-9S9.5 5.6 12 3z" fill="none" stroke="currentColor" stroke-width="1.8"/></svg>';
  const store = { get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }, set(k, v) { try { localStorage.setItem(k, v); } catch (e) {} } };
  const esc = s => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  function pickLang() {
    const ok = l => C.langs.some(x => x[0] === l);
    const q = new URLSearchParams(location.search).get("lang");
    if (ok(q)) return q;
    const s = store.get("pf-lang");
    if (ok(s)) return s;
    for (const n of (navigator.languages || [navigator.language || "en"])) {
      const l = String(n).toLowerCase();
      if (/^zh-(tw|hk|mo|hant)/.test(l)) return "zh-Hant";
      if (l.startsWith("zh")) return "zh-Hans";
      for (const c of ["es", "pt", "th", "en"]) if (l.startsWith(c)) return c;
    }
    return "en";
  }

  const applyTs = v => document.documentElement.style.setProperty("--ts", v);
  applyTs(TS.some(x => String(x[1]) === store.get("nc-ts")) ? store.get("nc-ts") : 1);

  let opts = { base: "", active: "", lang: "en" };
  const label = k => { const e = C.labels[k] || {}; return e[opts.lang] || e.en || k; };
  const href = item => opts.base === ""
    ? (item.hash || item.page)                   // home page: in-page routes, sibling pages
    : opts.base + (item.hash || item.page);     // other pages: back to the home page / sibling

  function render(o) {
    opts = Object.assign(opts, o || {});
    const t = opts.t || label;
    const el = document.getElementById("sitebar");
    if (!el) return "";
    const cur = getComputedStyle(document.documentElement).getPropertyValue("--ts").trim() || "1";
    el.innerHTML = `<div class="topbar">
    <a class="brand" href="${opts.base === "" ? "#medicines" : opts.base}" aria-label="NomadCeuticals">${C.logo}</a>
    <div class="topbar-end">
    <nav class="nav" aria-label="Sections">
      ${NAV.map(i => `<a href="${href(i)}"${opts.active === i.id ? ' aria-current="page"' : ""}>${esc(t(i.key))}${i.count != null ? `<span>${i.count}</span>` : ""}</a>`).join("\n      ")}
    </nav>
    <div class="tsel"><button type="button" class="tsbtn" id="tsbtn" aria-haspopup="true" aria-expanded="false" aria-controls="tsmenu" aria-label="${esc(t("textSize"))}" title="${esc(t("textSize"))}">${ICON_TS}</button>
      <div class="tsmenu" id="tsmenu" role="group" aria-label="${esc(t("textSize"))}" hidden>
        ${TS.map(([k, v], i) => `<button type="button" data-ts="${v}" aria-pressed="${String(v) === cur}"><span class="tsA" style="font-size:${16 + i * 4}px" aria-hidden="true">A</span>${esc(t(k))}</button>`).join("")}
      </div></div>
    <label class="langsel"><span class="sr">${esc(t("language"))}</span>${ICON_GLOBE}
      <select id="lang" aria-label="${esc(t("language"))}">${C.langs.map(([c, n]) => `<option value="${c}" ${c === opts.lang ? "selected" : ""}>${n}</option>`).join("")}</select>
    </label>
    </div>
  </div>`;
    return "";
  }

  document.addEventListener("click", e => {
    const btn = e.target.closest("#tsbtn"), menu = document.getElementById("tsmenu"), pick = e.target.closest("#tsmenu [data-ts]");
    if (pick) {
      applyTs(pick.dataset.ts); store.set("nc-ts", pick.dataset.ts);
      menu.querySelectorAll("[data-ts]").forEach(b => b.setAttribute("aria-pressed", String(b === pick)));
      return;
    }
    if (btn) { const open = menu.hidden; menu.hidden = !open; btn.setAttribute("aria-expanded", String(open)); if (open) menu.querySelector('[aria-pressed="true"]')?.focus(); return; }
    if (menu && !menu.hidden && !e.target.closest(".tsel")) { menu.hidden = true; document.getElementById("tsbtn").setAttribute("aria-expanded", "false"); }
  });
  document.addEventListener("keydown", e => {
    const menu = document.getElementById("tsmenu");
    if (e.key === "Escape" && menu && !menu.hidden) { menu.hidden = true; const b = document.getElementById("tsbtn"); b.setAttribute("aria-expanded", "false"); b.focus(); }
  });
  document.addEventListener("change", e => {
    if (!e.target || e.target.id !== "lang") return;
    const l = e.target.value;
    if (opts.onLang) return opts.onLang(l);
    store.set("pf-lang", l);
    render({ lang: l });
  });

  return { render, pickLang, store, langs: C.langs };
})();
