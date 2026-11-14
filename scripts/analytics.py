"""Google tag (Google Analytics via Tag Manager) with Consent Mode, shared by every page on nomadceuticals.com.

The tag id comes from data/release.json -> "googleTagId" (e.g. "GTM-N9HSS427"). Without it, pages get no analytics.

Privacy: this is a health site (page addresses and searches show which medicines and conditions someone looks
at), with visitors in the EU and other places with strict privacy laws. So analytics_storage starts "denied"
everywhere and is only granted after the visitor taps "Allow" on the banner. Advertising storage, ad user data and
ad personalisation are always denied. The choice is stored in localStorage ("nc-consent") and can be changed from
the "Privacy choices" link (window.NCConsent.open()).

    head(tag_id)        <script>s for <head>: consent defaults, then the Google tag
    banner()            consent banner (styles + markup + script), placed before </body>
    inject(html, tag)   adds both to a full HTML page
"""
import json

STRINGS = {
    "en": ["Can we use Google Analytics cookies to learn which pages help people? No analytics cookies are set unless you say yes.", "Allow", "No thanks"],
    "zh-Hans": ["我们可以使用 Google Analytics Cookie 来了解哪些页面对大家有帮助吗？除非您同意，否则不会设置任何分析 Cookie。", "允许", "不用了"],
    "zh-Hant": ["我們可以使用 Google Analytics Cookie 來了解哪些頁面對大家有幫助嗎？除非您同意，否則不會設定任何分析 Cookie。", "允許", "不用了"],
    "es": ["¿Podemos usar cookies de Google Analytics para saber qué páginas son útiles? No se instala ninguna cookie de análisis a menos que aceptes.", "Aceptar", "No, gracias"],
    "pt": ["Podemos usar cookies do Google Analytics para saber que páginas são úteis? Nenhum cookie de análise é instalado a menos que aceite.", "Aceitar", "Não, obrigado"],
    "th": ["เราขอใช้คุกกี้ของ Google Analytics เพื่อดูว่าหน้าไหนมีประโยชน์ได้ไหม ระบบจะไม่ตั้งค่าคุกกี้วิเคราะห์ใด ๆ หากคุณไม่อนุญาต", "อนุญาต", "ไม่เป็นไร"],
}


def head(tag_id):
    if not tag_id:
        return ""
    return f"""<script>
window.dataLayer = window.dataLayer || [];
function gtag(){{dataLayer.push(arguments);}}
gtag('consent', 'default', {{ad_storage: 'denied', ad_user_data: 'denied', ad_personalization: 'denied', analytics_storage: 'denied', wait_for_update: 500}});
try {{ if (localStorage.getItem('nc-consent') === 'granted') gtag('consent', 'update', {{analytics_storage: 'granted'}}); }} catch (e) {{}}
gtag('js', new Date());
</script>
<script async src="https://www.googletagmanager.com/gtm.js?id={tag_id}"></script>
"""


def banner():
    return """<style>
#nc-consent{position:fixed;left:0;right:0;bottom:0;z-index:1000;background:#000;color:#fff;font:16px/1.5 "Source Sans 3","Helvetica Neue",Arial,"Noto Sans Thai","PingFang SC","Microsoft YaHei",sans-serif;box-shadow:0 -4px 16px rgb(0 0 0 / .25)}
#nc-consent[hidden]{display:none}
#nc-consent .in{max-width:1040px;margin:0 auto;padding:14px 16px;display:flex;flex-wrap:wrap;gap:10px 20px;align-items:center;justify-content:space-between}
#nc-consent p{margin:0;flex:1 1 420px}
#nc-consent .b{display:flex;gap:8px}
#nc-consent button{font:600 15px inherit;font-family:inherit;padding:9px 16px;border:1px solid #fff;cursor:pointer;border-radius:0}
#nc-consent .yes{background:#92171A;border-color:#92171A;color:#fff}
#nc-consent .no{background:transparent;color:#fff}
#nc-consent button:focus-visible{outline:2px solid #fff;outline-offset:2px}
</style>
<div id="nc-consent" role="region" aria-label="Privacy" hidden><div class="in"><p id="nc-consent-text"></p><div class="b"><button type="button" class="yes" id="nc-consent-yes"></button><button type="button" class="no" id="nc-consent-no"></button></div></div></div>
<script>
(function () {
  var S = __STRINGS__;
  var box = document.getElementById("nc-consent");
  function lang() { var l = document.documentElement.lang || "en"; return S[l] ? l : (S[l.split("-")[0]] ? l.split("-")[0] : "en"); }
  function fill() { var s = S[lang()]; document.getElementById("nc-consent-text").textContent = s[0]; document.getElementById("nc-consent-yes").textContent = s[1]; document.getElementById("nc-consent-no").textContent = s[2]; }
  function choose(v) {
    try { localStorage.setItem("nc-consent", v); } catch (e) {}
    if (window.gtag) gtag("consent", "update", { analytics_storage: v === "granted" ? "granted" : "denied" });
    box.hidden = true;
  }
  document.getElementById("nc-consent-yes").addEventListener("click", function () { choose("granted"); });
  document.getElementById("nc-consent-no").addEventListener("click", function () { choose("denied"); });
  window.NCConsent = { open: function () { fill(); box.hidden = false; document.getElementById("nc-consent-yes").focus(); } };
  var saved = null; try { saved = localStorage.getItem("nc-consent"); } catch (e) {}
  if (!saved) { setTimeout(function () { fill(); box.hidden = false; }, 0); }
  new MutationObserver(function () { if (!box.hidden) fill(); }).observe(document.documentElement, { attributes: true, attributeFilter: ["lang"] });
})();
</script>
""".replace("__STRINGS__", json.dumps(STRINGS, ensure_ascii=False))


def inject(html, tag_id):
    """Adds the tag right after <meta charset> in <head> and the banner before </body>. No-op without a tag id."""
    if not tag_id or "googletagmanager.com" in html:
        return html
    anchor = '<meta charset="utf-8">'
    assert anchor in html and "</body>" in html, "page needs <meta charset=\"utf-8\"> and </body>"
    html = html.replace(anchor, anchor + "\n" + head(tag_id).rstrip("\n"), 1)
    i = html.rfind("</body>")
    return html[:i] + banner() + html[i:]


def tag_id_from_release(root):
    import os
    return json.load(open(os.path.join(root, "data", "release.json"), encoding="utf-8")).get("googleTagId")
