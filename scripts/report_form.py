""""Report a problem" form, shared by every page on nomadceuticals.com.

Reports go to the site's own server (/report.php, see server/), which stores them in the admin inbox
(nomadceuticals.com/admin/) and emails the admin. No third-party form service; the admin's email address never
appears in the page.

Pages call  ncReport({about: "Chai Wan Social Hygiene Clinic", id: "hk-hkg-shc-chai-wan"})  (both optional).

    inject(html)   adds the dialog styles and script before </body>
"""
import json

CATEGORIES = ["wrong_info", "closed", "site_bug", "suggestion", "other"]  # same order as the labels below; must match server/report.php

# title, intro, category label, categories (5), details label, details hint, email label, email hint,
# send, cancel, sending, thanks, error, about-prefix, privacy note
STRINGS = {
    "en": ["Report a problem", "Tell us what's wrong or out of date and we'll check it.", "What kind of problem?",
           ["Wrong or out-of-date information", "Closed, moved or no longer offers this", "Something on the site doesn't work", "Suggestion", "Something else"],
           "What's wrong?", "For example: the phone number has changed, or they no longer offer PrEP.",
           "Your email (optional)", "Only if you'd like a reply.", "Send report", "Cancel", "Sending…",
           "Thank you. We've received your report and will check it.", "Sorry, the report couldn't be sent. Please try again later.",
           "About", "Please don't include personal health details."],
    "zh-Hans": ["报告问题", "告诉我们哪里有误或已过时，我们会核实。", "问题类型", ["信息有误或已过时", "已关闭、已搬迁或不再提供此服务", "网站功能有问题", "建议", "其他"],
                "哪里有问题？", "例如：电话号码已更改，或不再提供 PrEP。", "您的电子邮箱（选填）", "如需回复请填写。", "发送报告", "取消", "正在发送…",
                "谢谢！我们已收到您的报告，会尽快核实。", "抱歉，报告未能发送，请稍后再试。", "关于", "请不要填写个人健康信息。"],
    "zh-Hant": ["回報問題", "告訴我們哪裡有誤或已過時，我們會核實。", "問題類型", ["資訊有誤或已過時", "已關閉、已搬遷或不再提供此服務", "網站功能有問題", "建議", "其他"],
                "哪裡有問題？", "例如：電話號碼已更改，或不再提供 PrEP。", "您的電子郵件（選填）", "如需回覆請填寫。", "送出回報", "取消", "正在送出…",
                "謝謝！我們已收到您的回報，會盡快核實。", "抱歉，回報未能送出，請稍後再試。", "關於", "請不要填寫個人健康資訊。"],
    "es": ["Informar de un problema", "Cuéntanos qué está mal o desactualizado y lo revisaremos.", "¿Qué tipo de problema?",
           ["Información incorrecta o desactualizada", "Cerrado, se mudó o ya no ofrece esto", "Algo del sitio no funciona", "Sugerencia", "Otra cosa"],
           "¿Qué está mal?", "Por ejemplo: el teléfono ha cambiado o ya no ofrecen PrEP.", "Tu correo (opcional)", "Solo si quieres una respuesta.",
           "Enviar", "Cancelar", "Enviando…", "Gracias. Hemos recibido tu informe y lo revisaremos.",
           "No se pudo enviar el informe. Inténtalo de nuevo más tarde.", "Sobre", "No incluyas datos personales de salud."],
    "pt": ["Comunicar um problema", "Diga-nos o que está errado ou desatualizado e vamos verificar.", "Que tipo de problema?",
           ["Informação errada ou desatualizada", "Fechou, mudou de morada ou já não oferece isto", "Algo no site não funciona", "Sugestão", "Outro"],
           "O que está errado?", "Por exemplo: o telefone mudou ou já não oferecem PrEP.", "O seu email (opcional)", "Só se quiser uma resposta.",
           "Enviar", "Cancelar", "A enviar…", "Obrigado. Recebemos a sua comunicação e vamos verificar.",
           "Não foi possível enviar. Tente novamente mais tarde.", "Sobre", "Não inclua dados pessoais de saúde."],
    "th": ["แจ้งปัญหา", "บอกเราว่าข้อมูลใดผิดหรือล้าสมัย แล้วเราจะตรวจสอบ", "ประเภทของปัญหา",
           ["ข้อมูลผิดหรือล้าสมัย", "ปิดแล้ว ย้ายแล้ว หรือไม่มีบริการนี้แล้ว", "บางอย่างในเว็บไซต์ใช้งานไม่ได้", "ข้อเสนอแนะ", "อื่น ๆ"],
           "มีอะไรผิด", "เช่น เบอร์โทรเปลี่ยนแล้ว หรือไม่มีบริการ PrEP แล้ว", "อีเมลของคุณ (ไม่บังคับ)", "กรอกเฉพาะเมื่อต้องการให้เราตอบกลับ",
           "ส่งรายงาน", "ยกเลิก", "กำลังส่ง…", "ขอบคุณ เราได้รับรายงานของคุณแล้วและจะตรวจสอบ",
           "ขออภัย ส่งรายงานไม่สำเร็จ โปรดลองอีกครั้งภายหลัง", "เกี่ยวกับ", "โปรดอย่าใส่ข้อมูลสุขภาพส่วนตัว"],
}

CSS = """
#nc-report{border:0;padding:0;max-width:min(560px,calc(100vw - 32px));width:100%;background:#fff;color:#15202B;box-shadow:0 12px 40px rgb(0 0 0 / .35);
  font:16px/1.5 "Source Sans 3","Helvetica Neue",Arial,"Noto Sans Thai","PingFang SC","Microsoft YaHei",sans-serif}
#nc-report::backdrop{background:rgb(0 0 0 / .55)}
#nc-report form{padding:22px 24px 20px;display:flex;flex-direction:column;gap:12px}
#nc-report h2{margin:0;font:600 26px/1.15 "Source Serif 4",Georgia,serif;padding-bottom:10px;border-bottom:1px solid #15202B}
#nc-report p{margin:0}
#nc-report .nc-about{background:#E9EDF1;padding:8px 12px;font-weight:600}
#nc-report label{display:flex;flex-direction:column;gap:4px;font-weight:600}
#nc-report small{font-weight:400;color:#5A6774}
#nc-report select,#nc-report textarea,#nc-report input[type=email]{font:inherit;font-weight:400;padding:9px 10px;border:1px solid #B7C1CB;border-radius:0;background:#fff;color:#15202B;width:100%;box-sizing:border-box}
#nc-report textarea{min-height:110px;resize:vertical}
#nc-report .nc-warn{color:#8A5A00;font-size:14px}
#nc-report .nc-row{display:flex;gap:8px;justify-content:flex-end;flex-wrap:wrap;margin-top:4px}
#nc-report button{font-family:inherit;font-weight:600;font-size:16px;padding:10px 18px;border:1px solid #92171A;cursor:pointer;border-radius:0}
#nc-report .nc-send{background:#92171A;color:#fff}
#nc-report .nc-cancel{background:#fff;color:#92171A}
#nc-report button:disabled{opacity:.6;cursor:default}
#nc-report .nc-msg{padding:10px 12px;font-weight:600}
#nc-report .nc-msg.nc-ok{background:#E2F3E6;color:#1F7A35}
#nc-report .nc-msg.nc-err{background:#FDE8EB;color:#A3122A}
#nc-report .nc-hp{position:absolute;left:-9999px;width:1px;height:1px;overflow:hidden}
"""

JS = """/*nc-report-form*/
(function () {
  var S = __STRINGS__, CATS = __CATS__;
  function L() { var l = document.documentElement.lang || "en"; return S[l] || S[l.split("-")[0]] || S.en; }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) { return {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]; }); }
  window.ncReport = function (ctx) {
    ctx = ctx || {};
    var s = L(), d = document.getElementById("nc-report");
    if (!d) { d = document.createElement("dialog"); d.id = "nc-report"; document.body.appendChild(d); }
    d.setAttribute("aria-labelledby", "nc-report-title");
    d.innerHTML = '<form method="dialog" novalidate>' +
      '<h2 id="nc-report-title">' + esc(s[0]) + '</h2><p>' + esc(s[1]) + '</p>' +
      (ctx.about ? '<p class="nc-about">' + esc(s[13]) + ': ' + esc(ctx.about) + '</p>' : '') +
      '<label>' + esc(s[2]) + '<select name="category">' + s[3].map(function (c, i) { return '<option value="' + CATS[i] + '">' + esc(c) + '</option>'; }).join("") + '</select></label>' +
      '<label>' + esc(s[4]) + ' <small>' + esc(s[5]) + '</small><textarea name="details" required maxlength="4000"></textarea></label>' +
      '<p class="nc-warn">' + esc(s[14]) + '</p>' +
      '<label>' + esc(s[6]) + ' <small>' + esc(s[7]) + '</small><input type="email" name="email" autocomplete="email" maxlength="200"></label>' +
      '<label class="nc-hp" aria-hidden="true">Website<input type="text" name="website" tabindex="-1" autocomplete="off"></label>' +
      '<div class="nc-msg" role="status" hidden></div>' +
      '<div class="nc-row"><button type="button" class="nc-cancel">' + esc(s[9]) + '</button><button type="submit" class="nc-send">' + esc(s[8]) + '</button></div></form>';
    var f = d.querySelector("form"), msg = d.querySelector(".nc-msg"), send = d.querySelector(".nc-send"), cancel = d.querySelector(".nc-cancel");
    cancel.onclick = function () { d.close(); };
    f.onsubmit = function (e) {
      e.preventDefault();
      if (!f.details.value.trim()) { f.details.focus(); return; }
      if (f.email.value && !f.email.checkValidity()) { f.email.focus(); return; }
      send.disabled = true; send.textContent = s[10];
      var body = { category: f.category.value, details: f.details.value.trim(), email: f.email.value.trim(), website: f.website.value,
                   about: ctx.about || "", record_id: ctx.id || "", page: location.href, lang: document.documentElement.lang || "" };
      fetch("/report.php", { method: "POST", headers: { "Content-Type": "application/json", "Accept": "application/json" }, body: JSON.stringify(body) })
        .then(function (r) { return r.json().catch(function () { return {}; }).then(function (j) { if (!r.ok || !j.ok) throw new Error(j.error || r.status); }); })
        .then(function () {
          msg.hidden = false; msg.className = "nc-msg nc-ok"; msg.textContent = s[11];
          f.querySelectorAll("label, .nc-warn, .nc-about, p:not(.nc-msg)").forEach(function (el) { el.hidden = true; el.style.display = "none"; });
          send.hidden = true; cancel.textContent = "OK"; cancel.focus();
        })
        .catch(function () { msg.hidden = false; msg.className = "nc-msg nc-err"; msg.textContent = s[12]; send.disabled = false; send.textContent = s[8]; });
    };
    d.showModal();
    f.details.focus();
    return false;
  };
})();
"""


def inject(html):
    if "/*nc-report-form*/" in html:
        return html
    i = html.rfind("</body>")
    assert i > 0, "page needs </body>"
    block = (f"<style>{CSS}</style>\n<script>"
             + JS.replace("__STRINGS__", json.dumps(STRINGS, ensure_ascii=False)).replace("__CATS__", json.dumps(CATEGORIES))
             + "</script>\n")
    return html[:i] + block + html[i:]
