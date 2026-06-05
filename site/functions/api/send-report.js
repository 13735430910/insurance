const OWNER_EMAIL = "segruotools@gmail.com";

export async function onRequestPost({ request, env }) {
  let body;
  try {
    body = await request.json();
  } catch (_error) {
    return json({ error: "Invalid JSON" }, 400);
  }

  const email = String(body.email || "").trim().toLowerCase();
  const payload = body.payload || {};
  const consent = body.consent === true;

  if (!isEmail(email)) {
    return json({ error: "Invalid email" }, 400);
  }

  if (!consent) {
    return json({ error: "Consent is required" }, 400);
  }

  const from = formatFrom(env.FROM_EMAIL || "reports@segurotools.com");
  const replyTo = env.REPLY_TO_EMAIL || "support@segurotools.com";
  const owner = env.OWNER_EMAIL || OWNER_EMAIL;
  const title = clean(payload.title || "Insurance planning report");
  const locale = payload.locale === "es" ? "es" : "en";
  const subject = locale === "es"
    ? `Reporte de SeguroTools: ${title}`
    : `SeguroTools report: ${title}`;

  const userHtml = renderUserEmail({ email, payload, locale });
  const userText = renderUserText({ payload, locale });
  const ownerHtml = renderOwnerEmail({ email, payload, consent });
  const ownerText = renderOwnerText({ email, payload, consent });

  try {
    await sendEmail(env, {
      from,
      to: email,
      replyTo,
      subject,
      html: userHtml,
      text: userText,
    });
    if (email !== owner.toLowerCase()) {
      await sendEmail(env, {
        from,
        to: owner,
        replyTo,
        subject: `SeguroTools calculator lead: ${title}`,
        html: ownerHtml,
        text: ownerText,
      });
    }
  } catch (error) {
    return json({
      error: "Email provider failed",
      code: error.code || "email_provider_failed",
      detail: String(error.message || error),
    }, 424);
  }

  return json({ ok: true });
}

export async function onRequestOptions() {
  return new Response(null, { status: 204, headers: corsHeaders() });
}

export async function onRequestGet() {
  return json({
    ok: false,
    endpoint: "/api/send-report",
    method: "POST",
    message: "Send calculator reports with POST JSON. Browser GET requests do not send email.",
  }, 405, { Allow: "POST, OPTIONS" });
}

async function sendEmail(env, message) {
  if (env.EMAIL && typeof env.EMAIL.send === "function") {
    await env.EMAIL.send(message);
    return;
  }

  if (env.RESEND_API_KEY) {
    const response = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${env.RESEND_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        from: message.from,
        to: message.to,
        subject: message.subject,
        html: message.html,
        text: message.text,
        reply_to: message.replyTo,
        headers: {
          "List-Unsubscribe": "<mailto:privacy@segurotools.com?subject=unsubscribe>",
        },
      }),
    });
    if (!response.ok) {
      const detail = await safeResponseText(response);
      throw providerError("resend_request_failed", `Resend failed with ${response.status}: ${detail}`);
    }
    return;
  }

  throw providerError("missing_email_provider", "Configure an EMAIL binding or RESEND_API_KEY in Cloudflare Pages production settings");
}

async function safeResponseText(response) {
  try {
    return (await response.text()).slice(0, 500);
  } catch (_error) {
    return "";
  }
}

function providerError(code, message) {
  const error = new Error(message);
  error.code = code;
  return error;
}

function formatFrom(address) {
  if (String(address).includes("<")) {
    return address;
  }
  return `SeguroTools Reports <${address}>`;
}

function renderUserEmail({ payload, locale }) {
  const intro = locale === "es"
    ? "Solicitaste este reporte educativo en SeguroTools. No reemplaza asesoría profesional ni una cotización oficial."
    : "You requested this educational report from SeguroTools. It does not replace professional advice or an official quote.";
  const rows = Array.isArray(payload.rows) ? payload.rows : [];
  const notes = Array.isArray(payload.notes) ? payload.notes : [];
  return `
    <div style="display:none;max-height:0;overflow:hidden;color:transparent">SeguroTools calculator report requested from segurotools.com.</div>
    <div style="font-family:Arial,sans-serif;line-height:1.55;color:#17202a;max-width:640px">
      <p style="font-size:13px;color:#5b6777;margin:0 0 16px">SeguroTools | segurotools.com</p>
      <h1 style="color:#12324a;font-size:24px;line-height:1.25;margin:0 0 16px">${clean(payload.title || "Insurance report")}</h1>
      <p>${intro}</p>
      <p><strong>${locale === "es" ? "Resultado" : "Result"}:</strong> ${clean(payload.total || "")}</p>
      <h2 style="font-size:18px;margin-top:24px">${locale === "es" ? "Desglose" : "Breakdown"}</h2>
      <table cellpadding="8" cellspacing="0" style="border-collapse:collapse;border:1px solid #dbe3ea">
        ${rows.map(([label, value]) => `<tr><td style="border:1px solid #dbe3ea">${clean(label)}</td><td style="border:1px solid #dbe3ea"><strong>${clean(formatValue(value))}</strong></td></tr>`).join("")}
      </table>
      <h2 style="font-size:18px;margin-top:24px">${locale === "es" ? "Notas" : "Notes"}</h2>
      <ul>${notes.map((note) => `<li>${clean(note)}</li>`).join("")}</ul>
      <p><a href="${clean(payload.page || "")}">${locale === "es" ? "Volver a la calculadora" : "Return to the calculator"}</a></p>
      <hr style="border:none;border-top:1px solid #dbe3ea;margin:24px 0">
      <p style="font-size:12px;color:#5b6777">${locale === "es" ? "Recibes este correo porque pediste un resultado de calculadora en SeguroTools. Puedes responder a este correo para pedir que eliminemos tu información de contacto." : "You are receiving this email because you requested a calculator result on SeguroTools. You can reply to request deletion of your contact information."}</p>
      <p style="font-size:12px;color:#5b6777"><a href="https://segurotools.com/${locale}/contact/">${locale === "es" ? "Contacto" : "Contact"}</a> | <a href="https://segurotools.com/${locale}/privacy/">${locale === "es" ? "Privacidad" : "Privacy"}</a> | <a href="https://segurotools.com/${locale}/disclaimer/">${locale === "es" ? "Aviso" : "Disclaimer"}</a></p>
    </div>
  `;
}

function renderUserText({ payload, locale }) {
  const rows = Array.isArray(payload.rows) ? payload.rows : [];
  const notes = Array.isArray(payload.notes) ? payload.notes : [];
  const lines = [
    "SeguroTools | segurotools.com",
    "",
    payload.title || "Insurance report",
    "",
    locale === "es"
      ? "Solicitaste este reporte educativo en SeguroTools. No reemplaza asesoría profesional ni una cotización oficial."
      : "You requested this educational report from SeguroTools. It does not replace professional advice or an official quote.",
    "",
    `${locale === "es" ? "Resultado" : "Result"}: ${payload.total || ""}`,
    "",
    locale === "es" ? "Desglose:" : "Breakdown:",
    ...rows.map(([label, value]) => `${label}: ${formatValue(value)}`),
    "",
    locale === "es" ? "Notas:" : "Notes:",
    ...notes.map((note) => `- ${note}`),
    "",
    `${locale === "es" ? "Calculadora" : "Calculator"}: ${payload.page || "https://segurotools.com/"}`,
    locale === "es"
      ? "Recibes este correo porque pediste un resultado de calculadora en SeguroTools. Responde a este correo para pedir que eliminemos tu información de contacto."
      : "You are receiving this email because you requested a calculator result on SeguroTools. Reply to request deletion of your contact information.",
    `https://segurotools.com/${locale}/contact/`,
    `https://segurotools.com/${locale}/privacy/`,
  ];
  return lines.join("\n");
}

function renderOwnerEmail({ email, payload, consent }) {
  return `
    <div style="font-family:Arial,sans-serif;line-height:1.55;color:#17202a">
      <h1>New calculator lead</h1>
      <p><strong>Email:</strong> ${clean(email)}</p>
      <p><strong>Consent:</strong> ${consent ? "yes" : "no"}</p>
      <p><strong>Calculator:</strong> ${clean(payload.title || payload.calculator || "")}</p>
      <p><strong>Result:</strong> ${clean(payload.total || "")}</p>
      <p><strong>Locale:</strong> ${clean(payload.locale || "")}</p>
      <p><strong>Page:</strong> <a href="${clean(payload.page || "")}">${clean(payload.page || "")}</a></p>
    </div>
  `;
}

function renderOwnerText({ email, payload, consent }) {
  return [
    "New SeguroTools calculator lead",
    `Email: ${email}`,
    `Consent: ${consent ? "yes" : "no"}`,
    `Calculator: ${payload.title || payload.calculator || ""}`,
    `Result: ${payload.total || ""}`,
    `Locale: ${payload.locale || ""}`,
    `Page: ${payload.page || ""}`,
  ].join("\n");
}

function formatValue(value) {
  if (typeof value === "number" && Number.isFinite(value)) {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 0,
    }).format(value);
  }
  return value;
}

function isEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) && email.length <= 254;
}

function clean(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function json(data, status = 200, extraHeaders = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      ...corsHeaders(),
      ...extraHeaders,
    },
  });
}

function corsHeaders() {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  };
}
