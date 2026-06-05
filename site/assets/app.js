const money = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

const percent = new Intl.NumberFormat("en-US", {
  style: "percent",
  maximumFractionDigits: 1,
});

const labels = {
  en: {
    result: "Estimated planning range",
    send: "Send report",
    sending: "Sending...",
    sent: "Report sent. Check your inbox.",
    sendFail: "Could not send right now. The on-page result is still available.",
    sendFailDetail: "Could not send right now:",
    consentRequired: "Please confirm consent before sending the report.",
  },
  es: {
    result: "Rango estimado de planificación",
    send: "Enviar reporte",
    sending: "Enviando...",
    sent: "Reporte enviado. Revisa tu correo.",
    sendFail: "No se pudo enviar ahora. El resultado en pantalla sigue disponible.",
    sendFailDetail: "No se pudo enviar ahora:",
    consentRequired: "Confirma el consentimiento antes de enviar el reporte.",
  },
};

const fpl2026 = {
  contiguous: { base: 15960, add: 5680 },
  alaska: { base: 19950, add: 7100 },
  hawaii: { base: 18360, add: 6520 },
};

function numberValue(form, name) {
  const input = form.querySelector(`[name="${name}"]`);
  if (!input) return 0;
  const value = Number(String(input.value).replace(/,/g, ""));
  return Number.isFinite(value) ? value : 0;
}

function textValue(form, name) {
  const input = form.querySelector(`[name="${name}"]`);
  return input ? input.value : "";
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function calculate(form) {
  const type = form.dataset.calculator;
  if (type === "life") return calculateLife(form);
  if (type === "final-expense") return calculateFinalExpense(form);
  if (type === "aca") return calculateAca(form);
  if (type === "home") return calculateHome(form);
  if (type === "disability") return calculateDisability(form);
  if (type === "pet") return calculatePet(form);
  if (type === "auto") return calculateAuto(form);
  if (type === "business") return calculateBusiness(form);
  return { total: 0, rows: [], notes: [] };
}

function calculateLife(form) {
  const debt = numberValue(form, "debt");
  const income = numberValue(form, "income");
  const years = numberValue(form, "years");
  const mortgage = numberValue(form, "mortgage");
  const education = numberValue(form, "education");
  const finalCosts = numberValue(form, "finalCosts");
  const savings = numberValue(form, "savings");
  const existing = numberValue(form, "existing");
  const dime = Math.max(0, debt + income * years + mortgage + education + finalCosts - savings - existing);
  const hlv = Math.max(0, income * years * 0.72 - savings - existing);
  const total = Math.max(dime, hlv);
  return {
    total,
    rows: [
      ["DIME estimate", dime],
      ["Income replacement estimate", hlv],
      ["Existing coverage and liquid assets", savings + existing],
    ],
    notes: [
      "Use the higher of the two methods as a planning anchor.",
      "Round coverage to the nearest policy amount and revisit after major life changes.",
    ],
  };
}

function calculateFinalExpense(form) {
  const service = numberValue(form, "service");
  const cemetery = numberValue(form, "cemetery");
  const travel = numberValue(form, "travel");
  const debts = numberValue(form, "debts");
  const cushion = numberValue(form, "cushion");
  const assets = numberValue(form, "assets");
  const total = Math.max(0, service + cemetery + travel + debts + cushion - assets);
  return {
    total,
    rows: [
      ["Funeral and service items", service + cemetery],
      ["Family travel and immediate costs", travel + cushion],
      ["Debts to clear", debts],
      ["Cash or existing coverage", assets],
    ],
    notes: [
      "Ask funeral homes for an itemized General Price List before choosing a package.",
      "Separate funeral planning from investment or savings promises.",
    ],
  };
}

function calculateAca(form) {
  const household = clamp(numberValue(form, "household"), 1, 12);
  const income = numberValue(form, "income");
  const benchmark = numberValue(form, "benchmark");
  const region = textValue(form, "region") || "contiguous";
  const fpl = fpl2026[region].base + Math.max(0, household - 1) * fpl2026[region].add;
  const fplPct = income > 0 ? income / fpl : 0;
  let expectedRate = 0;
  if (fplPct <= 1.5) expectedRate = 0;
  else if (fplPct <= 2) expectedRate = 0.02;
  else if (fplPct <= 2.5) expectedRate = 0.04;
  else if (fplPct <= 3) expectedRate = 0.06;
  else if (fplPct <= 4) expectedRate = 0.085;
  else expectedRate = 0.085;
  const annualExpected = income * expectedRate;
  const subsidy = Math.max(0, benchmark * 12 - annualExpected);
  const monthlyAfterCredit = Math.max(0, benchmark - subsidy / 12);
  return {
    total: subsidy,
    displayTotal: `${money.format(subsidy)} / year`,
    rows: [
      ["Estimated FPL percentage", `${Math.round(fplPct * 100)}%`],
      ["Estimated annual household contribution", annualExpected],
      ["Estimated monthly benchmark after credit", monthlyAfterCredit],
    ],
    notes: [
      "This is a planning estimate, not an eligibility determination.",
      "Use your Marketplace SLCSP benchmark premium for a more accurate result.",
    ],
  };
}

function calculateHome(form) {
  const contents = numberValue(form, "contents");
  const rent = numberValue(form, "rent");
  const months = numberValue(form, "months");
  const liability = numberValue(form, "liability");
  const deductible = numberValue(form, "deductible");
  const flood = numberValue(form, "flood");
  const total = Math.max(0, contents + rent * months + liability + flood - deductible);
  return {
    total,
    rows: [
      ["Personal property / dwelling gap", contents],
      ["Additional living expenses", rent * months],
      ["Liability planning amount", liability],
      ["Flood gap estimate", flood],
      ["Deductible you can absorb", deductible],
    ],
    notes: [
      "Flood is usually separate from standard homeowners or renters coverage.",
      "Use replacement cost for belongings, not garage-sale value.",
    ],
  };
}

function calculateDisability(form) {
  const monthlyIncome = numberValue(form, "monthlyIncome");
  const replacement = clamp(numberValue(form, "replacement"), 30, 80) / 100;
  const months = numberValue(form, "months");
  const existing = numberValue(form, "existing");
  const emergency = numberValue(form, "emergency");
  const waiting = numberValue(form, "waiting");
  const monthlyNeed = Math.max(0, monthlyIncome * replacement - existing);
  const waitingGap = Math.max(0, monthlyIncome * replacement * (waiting / 30) - emergency);
  const total = monthlyNeed * months + waitingGap;
  return {
    total,
    rows: [
      ["Monthly income gap", monthlyNeed],
      ["Benefit period target", `${months} months`],
      ["Elimination-period cash gap", waitingGap],
    ],
    notes: [
      "A longer elimination period lowers premiums but requires more emergency cash.",
      "Coordinate employer coverage, private coverage, and Social Security assumptions separately.",
    ],
  };
}

function calculatePet(form) {
  const premium = numberValue(form, "premium") * 12;
  const deductible = numberValue(form, "deductible");
  const reimbursement = clamp(numberValue(form, "reimbursement"), 50, 100) / 100;
  const expected = numberValue(form, "expected");
  const emergency = numberValue(form, "emergency");
  const breakevenClaim = premium / reimbursement + deductible;
  const gap = Math.max(0, breakevenClaim - emergency - expected);
  return {
    total: breakevenClaim,
    rows: [
      ["Annual premium", premium],
      ["Claim size to break even", breakevenClaim],
      ["Expected routine care and emergency fund", expected + emergency],
      ["Unfunded emergency gap", gap],
    ],
    notes: [
      "Wellness add-ons should be judged separately from accident and illness coverage.",
      "Pre-existing conditions and waiting periods matter more than headline reimbursement rates.",
    ],
  };
}

function calculateAuto(form) {
  const assets = numberValue(form, "assets");
  const income = numberValue(form, "income");
  const stateMinimum = numberValue(form, "stateMinimum");
  const currentLimit = numberValue(form, "currentLimit");
  const rideshare = numberValue(form, "rideshare");
  const suggested = Math.max(stateMinimum, Math.min(500000, assets + income * 0.5 + rideshare));
  const gap = Math.max(0, suggested - currentLimit);
  return {
    total: gap,
    rows: [
      ["Suggested liability planning limit", suggested],
      ["Current liability limit", currentLimit],
      ["State minimum entered", stateMinimum],
      ["Rideshare / delivery gap allowance", rideshare],
    ],
    notes: [
      "State minimum coverage can be far below your practical liability exposure.",
      "Delivery and rideshare use may require an endorsement or commercial coverage.",
    ],
  };
}

function calculateBusiness(form) {
  const revenue = numberValue(form, "revenue");
  const contracts = numberValue(form, "contracts");
  const payroll = numberValue(form, "payroll");
  const equipment = numberValue(form, "equipment");
  const current = numberValue(form, "current");
  const suggested = Math.max(100000, contracts + equipment + payroll * 0.5 + revenue * 0.15);
  const gap = Math.max(0, suggested - current);
  return {
    total: gap,
    rows: [
      ["Planning liability / property target", suggested],
      ["Current insurance limit", current],
      ["Contract exposure entered", contracts],
      ["Equipment replacement amount", equipment],
    ],
    notes: [
      "Professional liability and general liability answer different problems.",
      "Home-based businesses often need coverage beyond a homeowners policy.",
    ],
  };
}

function renderResult(form, data) {
  const panel = document.querySelector(`[data-result-for="${form.id}"]`);
  if (!panel) return;
  const locale = document.documentElement.lang.startsWith("es") ? "es" : "en";
  const total = data.displayTotal || money.format(data.total || 0);
  panel.querySelector("[data-result-main]").textContent = total;
  const breakdown = panel.querySelector("[data-result-breakdown]");
  breakdown.innerHTML = data.rows.map(([label, value]) => {
    const formatted = typeof value === "number" ? money.format(value) : value;
    return `<div class="break-row"><span>${escapeHtml(label)}</span><strong>${escapeHtml(formatted)}</strong></div>`;
  }).join("");
  const notes = panel.querySelector("[data-result-notes]");
  notes.innerHTML = data.notes.map((note) => `<li>${escapeHtml(note)}</li>`).join("");
  panel.dataset.payload = JSON.stringify({
    calculator: form.dataset.calculator,
    title: form.dataset.title,
    locale,
    total,
    rows: data.rows,
    notes: data.notes,
    page: location.href,
  });
}

async function sendReport(form, panel) {
  const locale = document.documentElement.lang.startsWith("es") ? "es" : "en";
  const t = labels[locale];
  const email = panel.querySelector('[name="email"]').value.trim();
  const consent = panel.querySelector('[name="consent"]').checked;
  const status = panel.querySelector("[data-email-status]");
  const button = panel.querySelector("[data-send-report]");
  if (!consent) {
    status.textContent = t.consentRequired;
    status.className = "status err";
    return;
  }
  const payload = JSON.parse(panel.dataset.payload || "{}");
  button.disabled = true;
  button.textContent = t.sending;
  status.textContent = "";
  try {
    const response = await fetch("/api/send-report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, consent, payload, source: "calculator-report" }),
    });
    if (!response.ok) {
      const error = await readApiError(response);
      throw new Error(error);
    }
    status.textContent = t.sent;
    status.className = "status ok";
  } catch (error) {
    status.textContent = error.message && error.message !== "send failed"
      ? `${t.sendFailDetail} ${error.message}`
      : t.sendFail;
    status.className = "status err";
  } finally {
    button.disabled = false;
    button.textContent = t.send;
  }
}

async function readApiError(response) {
  try {
    const data = await response.json();
    return data.code || data.error || data.detail || "send failed";
  } catch (_error) {
    return "send failed";
  }
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function initCalculators() {
  document.querySelectorAll("[data-calculator]").forEach((form) => {
    const update = () => renderResult(form, calculate(form));
    form.addEventListener("input", update);
    form.addEventListener("change", update);
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      update();
    });
    update();
  });

  document.querySelectorAll("[data-send-report]").forEach((button) => {
    button.addEventListener("click", () => {
      const panel = button.closest("[data-result-for]");
      const form = document.getElementById(panel.dataset.resultFor);
      sendReport(form, panel);
    });
  });
}

document.addEventListener("DOMContentLoaded", initCalculators);
