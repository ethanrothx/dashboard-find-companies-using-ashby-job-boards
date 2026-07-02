from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .models import CompanyJobs

_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
  :root {
    --ink: #16181d;
    --muted: #667085;
    --paper: #f7f8fa;
    --surface: #ffffff;
    --border: #e5e7eb;
    --border-strong: #d0d5dd;
    --accent: #4f46e5;
    --accent-soft: #eef2ff;
    --good: #12805c;
    --good-soft: #e6f4ee;
    --warn: #b45309;
    --warn-soft: #fdf2e3;
    --crit: #b42318;
    --crit-soft: #fde7e5;
    --bar: #c7d2fe;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    background: var(--paper);
    color: var(--ink);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    font-size: 14px;
    line-height: 1.5;
    -webkit-font-smoothing: antialiased;
  }
  .wrap { max-width: 1180px; margin: 0 auto; padding: 32px 24px 64px; }
  header .eyebrow {
    text-transform: uppercase; letter-spacing: .12em; font-size: 11px;
    font-weight: 600; color: var(--accent);
  }
  header h1 {
    margin: 6px 0 4px; font-size: 26px; font-weight: 650;
    letter-spacing: -.01em; text-wrap: balance;
  }
  header p.sub { margin: 0; color: var(--muted); }
  .stats {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 12px; margin: 24px 0;
  }
  .stat {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 10px; padding: 14px 16px;
  }
  .stat .num {
    font-size: 24px; font-weight: 650; letter-spacing: -.02em;
    font-variant-numeric: tabular-nums;
  }
  .stat .lab { font-size: 12px; color: var(--muted); margin-top: 2px; }
  .controls {
    display: flex; flex-wrap: wrap; gap: 10px; align-items: center;
    margin-bottom: 14px;
  }
  .controls input[type="search"], .controls select {
    font: inherit; padding: 8px 11px; border: 1px solid var(--border-strong);
    border-radius: 8px; background: var(--surface); color: var(--ink);
  }
  .controls input[type="search"] { flex: 1 1 260px; min-width: 200px; }
  .controls label { font-size: 12px; color: var(--muted); display: inline-flex; gap: 6px; align-items: center; }
  .controls .count { margin-left: auto; font-size: 12px; color: var(--muted); }
  .table-scroll { overflow-x: auto; border: 1px solid var(--border); border-radius: 12px; background: var(--surface); }
  table { border-collapse: collapse; width: 100%; min-width: 900px; }
  thead th {
    position: sticky; top: 0; background: var(--surface);
    text-align: left; font-size: 11px; text-transform: uppercase;
    letter-spacing: .06em; color: var(--muted); font-weight: 600;
    padding: 12px 14px; border-bottom: 1px solid var(--border-strong);
    cursor: pointer; white-space: nowrap; user-select: none;
  }
  thead th.num, tbody td.num { text-align: right; font-variant-numeric: tabular-nums; }
  thead th .arrow { color: var(--accent); font-size: 10px; }
  tbody td { padding: 11px 14px; border-bottom: 1px solid var(--border); vertical-align: top; }
  tbody tr.company:hover { background: var(--accent-soft); }
  tbody tr.company { cursor: pointer; }
  .cname { font-weight: 600; }
  .cname a { color: var(--accent); text-decoration: none; }
  .cname a:hover { text-decoration: underline; }
  .cslug { color: var(--muted); font-size: 12px; }
  .cell-sub { color: var(--muted); font-size: 12px; margin-top: 2px; max-width: 320px; }
  .bar-cell { display: flex; align-items: center; gap: 8px; justify-content: flex-end; }
  .bar { height: 7px; border-radius: 4px; background: var(--bar); min-width: 2px; }
  .pill {
    display: inline-block; font-size: 11px; font-weight: 600; padding: 2px 8px;
    border-radius: 999px; white-space: nowrap;
  }
  .pill.ok { background: var(--good-soft); color: var(--good); }
  .pill.empty { background: var(--warn-soft); color: var(--warn); }
  .pill.error { background: var(--crit-soft); color: var(--crit); }
  .pill.remote { background: var(--accent-soft); color: var(--accent); }
  .jobs-row td { background: #fbfcfe; padding: 0; }
  .jobs-inner { padding: 4px 14px 14px 14px; }
  .jobs-inner table { min-width: 0; }
  .jobs-inner thead th { position: static; background: transparent; }
  .jobs-inner td { border-bottom: 1px dashed var(--border); }
  .empty-state { padding: 48px; text-align: center; color: var(--muted); }
  footer { margin-top: 22px; font-size: 12px; color: var(--muted); }
  a.plain { color: var(--accent); text-decoration: none; }
  @media (prefers-reduced-motion: no-preference) {
    .bar { transition: width .2s ease; }
  }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div class="eyebrow">Ashby Hiring Intelligence</div>
    <h1>Companies Hiring on Ashby</h1>
    <p class="sub">__SUBTITLE__</p>
  </header>

  <section class="stats" id="stats"></section>

  <div class="controls">
    <input type="search" id="q" placeholder="Search company, location, or department…" aria-label="Search">
    <label>Status
      <select id="statusFilter">
        <option value="">All</option>
        <option value="OK">Hiring</option>
        <option value="EMPTY">No open roles</option>
        <option value="ERROR">Fetch error</option>
      </select>
    </label>
    <label>Min jobs
      <select id="minJobs">
        <option value="0">Any</option>
        <option value="1">1+</option>
        <option value="5">5+</option>
        <option value="10">10+</option>
        <option value="25">25+</option>
        <option value="50">50+</option>
      </select>
    </label>
    <label><input type="checkbox" id="remoteOnly"> Remote-friendly only</label>
    <span class="count" id="count"></span>
  </div>

  <div class="table-scroll">
    <table id="tbl">
      <thead>
        <tr>
          <th data-key="company_name" data-type="str">Company</th>
          <th data-key="job_count" data-type="num" class="num">Open&nbsp;jobs</th>
          <th data-key="remote_job_count" data-type="num" class="num">Remote</th>
          <th data-key="location_count" data-type="num" class="num">Locations</th>
          <th data-key="top_location" data-type="str">Top location</th>
          <th data-key="department_count" data-type="num" class="num">Depts</th>
          <th data-key="top_department" data-type="str">Top department</th>
          <th data-key="fetch_status" data-type="str">Status</th>
        </tr>
      </thead>
      <tbody id="tbody"></tbody>
    </table>
  </div>

  <footer>
    __FOOTER__ &middot; Data from the public Ashby job-board API.
    Click any row to expand its open roles.
  </footer>
</div>

<script>
const COMPANIES = __COMPANIES_JSON__;
const JOBS = __JOBS_JSON__;

const jobsBySlug = {};
for (const j of JOBS) { (jobsBySlug[j.company_slug] = jobsBySlug[j.company_slug] || []).push(j); }

const maxJobs = Math.max(1, ...COMPANIES.map(c => c.job_count || 0));
let sortKey = "job_count", sortType = "num", sortDir = -1;
const expanded = new Set();

const $ = id => document.getElementById(id);
const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

function renderStats() {
  const hiring = COMPANIES.filter(c => c.job_count > 0);
  const totalJobs = COMPANIES.reduce((a, c) => a + (c.job_count || 0), 0);
  const remoteCos = COMPANIES.filter(c => c.remote_job_count > 0).length;
  const errors = COMPANIES.filter(c => c.fetch_status === "ERROR").length;
  const stats = [
    ["Companies", COMPANIES.length],
    ["Actively hiring", hiring.length],
    ["Total open roles", totalJobs.toLocaleString()],
    ["Remote-friendly", remoteCos],
    ["Fetch errors", errors],
  ];
  $("stats").innerHTML = stats.map(([lab, num]) =>
    `<div class="stat"><div class="num">${num}</div><div class="lab">${lab}</div></div>`).join("");
}

function currentRows() {
  const q = $("q").value.trim().toLowerCase();
  const status = $("statusFilter").value;
  const minJobs = +$("minJobs").value;
  const remoteOnly = $("remoteOnly").checked;
  let rows = COMPANIES.filter(c => {
    if (status && c.fetch_status !== status) return false;
    if ((c.job_count || 0) < minJobs) return false;
    if (remoteOnly && !(c.remote_job_count > 0)) return false;
    if (q) {
      const hay = `${c.company_name} ${c.slug} ${c.locations} ${c.departments}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
  rows.sort((a, b) => {
    let x = a[sortKey], y = b[sortKey];
    if (sortType === "num") { x = +x || 0; y = +y || 0; return (x - y) * sortDir; }
    x = String(x || "").toLowerCase(); y = String(y || "").toLowerCase();
    return x < y ? -sortDir : x > y ? sortDir : 0;
  });
  return rows;
}

function jobsPanel(slug) {
  const list = jobsBySlug[slug] || [];
  if (!list.length) return `<div class="jobs-inner" style="color:var(--muted)">No open roles listed.</div>`;
  const rows = list.map(j => `<tr>
      <td>${esc(j.title)}</td>
      <td>${esc(j.location)}${j.is_remote ? ' <span class="pill remote">remote</span>' : ""}</td>
      <td>${esc(j.department)}</td>
      <td>${esc(j.employment_type)}</td>
    </tr>`).join("");
  return `<div class="jobs-inner"><table>
      <thead><tr><th>Role</th><th>Location</th><th>Department</th><th>Type</th></tr></thead>
      <tbody>${rows}</tbody></table></div>`;
}

function render() {
  const rows = currentRows();
  $("count").textContent = `${rows.length} of ${COMPANIES.length} companies`;
  document.querySelectorAll("thead th").forEach(th => {
    const base = th.textContent.replace(/[▲▼]\\s*$/, "").trim();
    th.innerHTML = th.dataset.key === sortKey
      ? `${base} <span class="arrow">${sortDir < 0 ? "▼" : "▲"}</span>` : base;
  });
  if (!rows.length) {
    $("tbody").innerHTML = `<tr><td colspan="8"><div class="empty-state">No companies match these filters.</div></td></tr>`;
    return;
  }
  $("tbody").innerHTML = rows.map(c => {
    const w = Math.round(((c.job_count || 0) / maxJobs) * 90);
    const statusCls = c.fetch_status === "OK" ? "ok" : c.fetch_status === "ERROR" ? "error" : "empty";
    const statusTxt = c.fetch_status === "OK" ? "Hiring" : c.fetch_status === "ERROR" ? "Error" : "No roles";
    const isOpen = expanded.has(c.slug);
    const main = `<tr class="company" data-slug="${esc(c.slug)}">
        <td>
          <div class="cname"><a href="${esc(c.ashby_url)}" target="_blank" rel="noopener" onclick="event.stopPropagation()">${esc(c.company_name)}</a></div>
          <div class="cslug">${esc(c.slug)}</div>
        </td>
        <td class="num"><div class="bar-cell"><span>${c.job_count || 0}</span><span class="bar" style="width:${w}px"></span></div></td>
        <td class="num">${c.remote_job_count || 0}</td>
        <td class="num">${c.location_count || 0}</td>
        <td>${esc(c.top_location)}${c.location_count > 1 ? `<div class="cell-sub">+${c.location_count - 1} more</div>` : ""}</td>
        <td class="num">${c.department_count || 0}</td>
        <td>${esc(c.top_department)}</td>
        <td><span class="pill ${statusCls}">${statusTxt}</span></td>
      </tr>`;
    const drawer = isOpen ? `<tr class="jobs-row"><td colspan="8">${jobsPanel(c.slug)}</td></tr>` : "";
    return main + drawer;
  }).join("");
}

document.querySelectorAll("thead th").forEach(th => th.addEventListener("click", () => {
  const key = th.dataset.key;
  if (key === sortKey) { sortDir *= -1; }
  else { sortKey = key; sortType = th.dataset.type; sortDir = sortType === "num" ? -1 : 1; }
  render();
}));
$("tbody").addEventListener("click", e => {
  const tr = e.target.closest("tr.company");
  if (!tr) return;
  const slug = tr.dataset.slug;
  if (expanded.has(slug)) expanded.delete(slug); else expanded.add(slug);
  render();
});
["input", "change"].forEach(ev => {
  $("q").addEventListener(ev, render);
  $("statusFilter").addEventListener(ev, render);
  $("minJobs").addEventListener(ev, render);
  $("remoteOnly").addEventListener(ev, render);
});

renderStats();
render();
</script>
</body>
</html>
"""


def render_report(
    companies: Iterable[CompanyJobs],
    *,
    title: str = "Companies Hiring on Ashby",
    generated_at: str = "",
    source: str = "",
) -> str:
    companies = list(companies)
    company_rows = [c.to_row() for c in companies]
    job_rows = [
        {
            "company_slug": p.company_slug,
            "title": p.title,
            "location": p.location,
            "is_remote": p.is_remote,
            "employment_type": p.employment_type,
            "department": p.department,
        }
        for c in companies
        for p in c.postings
    ]

    total_jobs = sum(c.job_count for c in companies)
    subtitle = (
        f"{len(companies)} discovered companies &middot; "
        f"{total_jobs:,} open roles. Sort any column, filter, and click a row to see the roles."
    )
    footer_bits = []
    if source:
        footer_bits.append(f"Source: {source}")
    if generated_at:
        footer_bits.append(f"Generated {generated_at}")
    footer = " &middot; ".join(footer_bits) if footer_bits else "Ashby job-board scrape"

    return (
        _TEMPLATE.replace("__TITLE__", title)
        .replace("__SUBTITLE__", subtitle)
        .replace("__FOOTER__", footer)
        .replace("__COMPANIES_JSON__", json.dumps(company_rows, ensure_ascii=False))
        .replace("__JOBS_JSON__", json.dumps(job_rows, ensure_ascii=False))
    )


def save_report(
    companies: Iterable[CompanyJobs],
    output_path: Path,
    **kwargs,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_report(companies, **kwargs), encoding="utf-8")
    return output_path
