const DEFAULT_FORWARD_EMAIL = "segruotools@gmail.com";
const DEFAULT_FROM_EMAIL = "forwarder@segurotools.com";
const DEFAULT_INBOUND_DOMAIN = "segurotools.com";
const RESEND_API_BASE = "https://api.resend.com";

export async function onRequestPost({ request, env }) {
  if (!env.RESEND_API_KEY) {
    return json({ error: "Missing RESEND_API_KEY" }, 500);
  }

  if (!env.RESEND_WEBHOOK_SECRET) {
    return json({ error: "Missing RESEND_WEBHOOK_SECRET" }, 500);
  }

  const rawPayload = await request.text();

  try {
    await verifySvixSignature(rawPayload, request.headers, env.RESEND_WEBHOOK_SECRET);
  } catch (_error) {
    return json({ error: "Invalid webhook signature" }, 400);
  }

  let event;
  try {
    event = JSON.parse(rawPayload);
  } catch (_error) {
    return json({ error: "Invalid JSON" }, 400);
  }

  if (event.type !== "email.received") {
    return json({ ok: true, ignored: true });
  }

  const emailId = event.data?.email_id || event.data?.id;
  if (!emailId) {
    return json({ error: "Missing received email id" }, 400);
  }

  let email;
  try {
    email = await getReceivedEmail(env.RESEND_API_KEY, emailId);
  } catch (error) {
    return json({ error: "Failed to retrieve inbound email", detail: String(error.message || error) }, 502);
  }
  const inboundDomain = env.INBOUND_DOMAIN || DEFAULT_INBOUND_DOMAIN;

  if (!hasRecipientAtDomain(email.to, inboundDomain)) {
    return json({ ok: true, ignored: true, reason: "recipient_domain" });
  }

  const forwardTo = env.FORWARD_EMAIL || DEFAULT_FORWARD_EMAIL;
  const from = env.INBOUND_FROM_EMAIL || env.FROM_EMAIL || DEFAULT_FROM_EMAIL;

  try {
    await sendEmail(env.RESEND_API_KEY, {
      from,
      to: [forwardTo],
      subject: `Fwd: ${cleanSubject(email.subject || event.data?.subject || "(no subject)")}`,
      html: renderForwardHtml(email),
      text: renderForwardText(email),
      reply_to: email.from ? [email.from] : undefined,
    });
  } catch (error) {
    return json({ error: "Failed to forward inbound email", detail: String(error.message || error) }, 502);
  }

  return json({ ok: true });
}

export async function onRequestOptions() {
  return new Response(null, { status: 204, headers: corsHeaders() });
}

export async function onRequestGet() {
  return json({
    ok: false,
    endpoint: "/api/inbound-email",
    method: "POST",
    message: "This endpoint accepts signed Resend email.received webhooks. Browser GET requests are not processed.",
  }, 405, { Allow: "POST, OPTIONS" });
}

async function getReceivedEmail(apiKey, emailId) {
  const response = await fetch(`${RESEND_API_BASE}/emails/receiving/${encodeURIComponent(emailId)}`, {
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`Resend receiving lookup failed with ${response.status}`);
  }

  return response.json();
}

async function sendEmail(apiKey, message) {
  const body = Object.fromEntries(Object.entries(message).filter(([, value]) => value !== undefined));
  const response = await fetch(`${RESEND_API_BASE}/emails`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(`Resend forwarding failed with ${response.status}`);
  }
}

async function verifySvixSignature(payload, headers, secret) {
  const id = headers.get("svix-id");
  const timestamp = headers.get("svix-timestamp");
  const signatureHeader = headers.get("svix-signature");

  if (!id || !timestamp || !signatureHeader) {
    throw new Error("Missing Svix signature headers");
  }

  const signedPayload = `${id}.${timestamp}.${payload}`;
  const secretBytes = base64ToBytes(secret.startsWith("whsec_") ? secret.slice(6) : secret);
  const key = await crypto.subtle.importKey(
    "raw",
    secretBytes,
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const signature = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(signedPayload));
  const expected = bytesToBase64(new Uint8Array(signature));

  const valid = signatureHeader
    .split(" ")
    .map((part) => part.trim())
    .filter(Boolean)
    .map((part) => (part.startsWith("v1,") ? part.slice(3) : part))
    .some((candidate) => timingSafeEqual(candidate, expected));

  if (!valid) {
    throw new Error("Signature mismatch");
  }
}

function hasRecipientAtDomain(recipients, domain) {
  const expected = String(domain).toLowerCase();
  return asArray(recipients).some((recipient) => {
    const address = extractEmail(recipient).toLowerCase();
    return address.endsWith(`@${expected}`);
  });
}

function renderForwardHtml(email) {
  const attachmentList = attachmentSummary(email.attachments);
  const body = email.text || stripTags(email.html || "");
  return `
    <div style="font-family:Arial,sans-serif;line-height:1.55;color:#17202a">
      <h1 style="color:#12324a">Forwarded SeguroTools email</h1>
      <p><strong>From:</strong> ${clean(email.from || "")}</p>
      <p><strong>To:</strong> ${clean(asArray(email.to).join(", "))}</p>
      <p><strong>Subject:</strong> ${clean(email.subject || "")}</p>
      <p><strong>Message ID:</strong> ${clean(email.message_id || "")}</p>
      ${attachmentList}
      <hr>
      <pre style="white-space:pre-wrap;font-family:Arial,sans-serif">${clean(body)}</pre>
    </div>
  `;
}

function renderForwardText(email) {
  const lines = [
    "Forwarded SeguroTools email",
    `From: ${email.from || ""}`,
    `To: ${asArray(email.to).join(", ")}`,
    `Subject: ${email.subject || ""}`,
    `Message ID: ${email.message_id || ""}`,
  ];

  const attachments = asArray(email.attachments);
  if (attachments.length > 0) {
    lines.push(`Attachments: ${attachments.map((item) => item.filename || item.id || "attachment").join(", ")}`);
  }

  lines.push("", email.text || stripTags(email.html || ""));
  return lines.join("\n");
}

function attachmentSummary(attachments) {
  const items = asArray(attachments);
  if (items.length === 0) {
    return "";
  }

  const list = items
    .map((item) => `<li>${clean(item.filename || item.id || "attachment")} ${clean(item.content_type || "")}</li>`)
    .join("");
  return `<p><strong>Attachments received:</strong></p><ul>${list}</ul><p style="font-size:12px;color:#5b6777">Attachments are stored in Resend Receiving and are not re-attached by this lightweight forwarder.</p>`;
}

function asArray(value) {
  if (Array.isArray(value)) {
    return value;
  }
  if (value === undefined || value === null || value === "") {
    return [];
  }
  return [value];
}

function extractEmail(value) {
  const text = String(value || "");
  const match = text.match(/<([^>]+)>/);
  return match ? match[1] : text;
}

function stripTags(value) {
  return String(value || "")
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/<\/p>/gi, "\n\n")
    .replace(/<[^>]*>/g, "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function cleanSubject(value) {
  return String(value || "")
    .replace(/[\r\n]+/g, " ")
    .trim()
    .slice(0, 180);
}

function clean(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function base64ToBytes(value) {
  const normalized = String(value).replace(/-/g, "+").replace(/_/g, "/");
  const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, "=");
  const binary = atob(padded);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

function bytesToBase64(bytes) {
  let binary = "";
  for (let i = 0; i < bytes.length; i += 1) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

function timingSafeEqual(a, b) {
  const left = String(a);
  const right = String(b);
  if (left.length === 0 || right.length === 0) {
    return false;
  }

  let diff = left.length ^ right.length;
  const length = Math.max(left.length, right.length);

  for (let i = 0; i < length; i += 1) {
    diff |= left.charCodeAt(i % left.length) ^ right.charCodeAt(i % right.length);
  }

  return diff === 0;
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
    "Access-Control-Allow-Headers": "Content-Type, svix-id, svix-timestamp, svix-signature",
  };
}
