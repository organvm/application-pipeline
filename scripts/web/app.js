"use strict";

const $ = (sel) => document.querySelector(sel);

async function api(path, opts) {
  const res = await fetch(path, opts);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json();
}

function scoreClass(s) {
  if (s == null) return "";
  if (s >= 7) return "score-good";
  if (s >= 5) return "score-mid";
  return "score-low";
}

function kpiCard(value, label, sub) {
  return `<div class="kpi"><div class="v">${value}</div><div class="l">${label}</div>${
    sub ? `<div class="sub">${sub}</div>` : ""
  }</div>`;
}

async function loadSummary() {
  const s = await api("/api/summary");
  const statusBits = Object.entries(s.by_status)
    .map(([k, v]) => `${k} ${v}`)
    .join(" · ");
  const trackBits = Object.entries(s.by_track)
    .map(([k, v]) => `${k} ${v}`)
    .join(" · ");
  $("#kpis").innerHTML = [
    kpiCard(s.total, "Total entries", statusBits),
    kpiCard(s.actionable, "Actionable", "qualified + drafting + staged"),
    kpiCard(s.submitted, "Submitted", "lifetime"),
    kpiCard(s.avg_score ?? "—", "Avg fit score", `${s.scored} scored`),
    kpiCard(Object.keys(s.by_track).length, "Tracks", trackBits),
  ].join("");

  const badge = $("#writeBadge");
  if (s.writes_allowed) {
    badge.textContent = "writes enabled";
    badge.classList.add("live");
  }

  // populate filters once
  const sf = $("#statusFilter");
  if (sf.options.length <= 1) {
    Object.keys(s.by_status).forEach((st) => sf.add(new Option(st, st)));
    const tf = $("#trackFilter");
    Object.keys(s.by_track).forEach((tk) => tf.add(new Option(tk, tk)));
  }
}

function entryRow(e) {
  const score = e.score == null ? "—" : e.score.toFixed(1);
  return `<tr>
    <td>${e.name ?? e.id ?? ""}</td>
    <td>${e.organization ?? ""}</td>
    <td>${e.track ?? ""}</td>
    <td><span class="pill s-${e.status}">${e.status ?? ""}</span></td>
    <td class="num ${scoreClass(e.score)}">${score}</td>
    <td>${e.deadline ?? "—"}</td>
    <td>
      <button class="act" data-act="detail" data-id="${e.id}">View</button>
      <button class="act" data-act="score" data-id="${e.id}">Score</button>
      <button class="act" data-act="validate" data-id="${e.id}">Validate</button>
    </td>
  </tr>`;
}

async function loadEntries() {
  const status = $("#statusFilter").value;
  const track = $("#trackFilter").value;
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (track) params.set("track", track);
  const rows = await api("/api/entries?" + params.toString());
  $("#entriesBody").innerHTML = rows.map(entryRow).join("") ||
    `<tr><td colspan="7" class="loading">No entries match.</td></tr>`;
}

async function loadStandup() {
  try {
    const r = await api("/api/standup");
    $("#standup").textContent = r.output || r.error || "(no output)";
  } catch (err) {
    $("#standup").textContent = String(err);
  }
}

function showDetail(obj) {
  $("#detail").textContent = JSON.stringify(obj, null, 2);
}

async function onAction(act, id) {
  $("#detail").textContent = `Running ${act} on ${id}…`;
  try {
    if (act === "detail") return showDetail(await api(`/api/entries/${id}`));
    if (act === "score") return showDetail(await api(`/api/entries/${id}/score`, { method: "POST" }));
    if (act === "validate") return showDetail(await api(`/api/entries/${id}/validate`, { method: "POST" }));
  } catch (err) {
    showDetail({ error: String(err) });
  }
}

function wire() {
  $("#refreshBtn").addEventListener("click", refresh);
  $("#statusFilter").addEventListener("change", loadEntries);
  $("#trackFilter").addEventListener("change", loadEntries);
  $("#entriesBody").addEventListener("click", (ev) => {
    const btn = ev.target.closest("button.act");
    if (btn) onAction(btn.dataset.act, btn.dataset.id);
  });
}

function railChip(o) {
  const note = o.recurring ? "recurring" : "one-time";
  return `<a class="rail" href="${o.url}" target="_blank" rel="noopener" title="${o.description}">
    ${o.label} <span class="rail-kind">${o.kind} · ${note}</span>
  </a>`;
}

async function loadRails(tier) {
  try {
    const r = await api("/api/billing/options?tier=" + encodeURIComponent(tier));
    $("#rails").innerHTML =
      `<div class="rails-head">Ways to pay for <b>${r.tier}</b> ($${r.price_usd_month}/mo):</div>` +
      r.rails.map(railChip).join("");
  } catch (err) {
    $("#rails").textContent = String(err);
  }
}

async function loadPlans() {
  try {
    const plans = await api("/api/billing/plans");
    $("#plans").innerHTML = plans
      .map(
        (p) => `<button class="plan" data-tier="${p.tier}">
          <span class="plan-name">${p.tier}</span>
          <span class="plan-price">${p.price_usd_month ? "$" + p.price_usd_month + "/mo" : "—"}</span>
          <span class="plan-desc">${p.description}</span>
        </button>`
      )
      .join("");
    $("#plans").addEventListener("click", (ev) => {
      const btn = ev.target.closest("button.plan");
      if (btn) loadRails(btn.dataset.tier);
    });
    const paid = plans.find((p) => p.price_usd_month > 0);
    if (paid) loadRails(paid.tier);
  } catch (err) {
    $("#plans").textContent = String(err);
  }
}

async function refresh() {
  await loadSummary();
  await loadEntries();
}

wire();
refresh();
loadStandup();
loadPlans();
