const API = '/api';

// ── Utilities ──────────────────────────────────────────────────────────────
function $(id) { return document.getElementById(id); }

function toast(msg, type = 'info') {
  const c = $('toast-container');
  const t = document.createElement('div');
  t.className = `toast toast-${type}`;
  t.innerHTML = `<span>${msg}</span>`;
  c.appendChild(t);
  setTimeout(() => t.remove(), 3500);
}

function badge(status) {
  const s = (status || 'unknown').toLowerCase();
  return `<span class="badge badge-${s}">${s}</span>`;
}

function priorityBadge(p) {
  const s = (p || 'normal').toLowerCase();
  return `<span class="badge badge-${s}">${s}</span>`;
}

function formatId(id) {
  return `<span class="req-id">${id}</span>`;
}

// ── Clock ──────────────────────────────────────────────────────────────────
function startClock() {
  const el = $('clock');
  function tick() {
    el.textContent = new Date().toLocaleTimeString('en-US', { hour12: false });
  }
  tick();
  setInterval(tick, 1000);
}

// ── API Health ─────────────────────────────────────────────────────────────
async function checkHealth() {
  const dot = $('status-dot');
  const txt = $('status-text');
  try {
    const r = await fetch('/health');
    if (r.ok) {
      dot.className = 'status-dot online';
      txt.textContent = 'API Online';
    } else throw new Error();
  } catch {
    dot.className = 'status-dot offline';
    txt.textContent = 'API Offline';
  }
}

// ── Navigation ─────────────────────────────────────────────────────────────
const pages = { dashboard: 'Dashboard', submit: 'Submit Ticket', lookup: 'Lookup Request', rules: 'Rules Manager' };
const subtitles = { dashboard: 'Real-time platform overview', submit: 'Create a new AI decision request', lookup: 'Trace & explain any request', rules: 'Manage decision rules' };

function navigate(page) {
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  const nav = document.querySelector(`[data-page="${page}"]`);
  if (nav) nav.classList.add('active');
  const pg = $(`page-${page}`);
  if (pg) pg.classList.add('active');
  $('page-title').textContent = pages[page] || page;
  $('page-subtitle').textContent = subtitles[page] || '';
  if (page === 'dashboard') loadDashboard();
}

document.querySelectorAll('.nav-item').forEach(n => {
  n.addEventListener('click', e => { e.preventDefault(); navigate(n.dataset.page); });
});

// ── Dashboard ──────────────────────────────────────────────────────────────
const recentIds = [];

async function loadDashboard() {
  // We'll fetch the last submitted IDs stored locally and try to get status for each
  renderStats();
  renderRecentTable();
}

function renderStats() {
  const counts = { total: 0, success: 0, manual_review: 0, failed: 0 };
  dashboardData.forEach(d => {
    counts.total++;
    const st = (d.status || '').toLowerCase();
    if (st === 'success') counts.success++;
    else if (st === 'manual_review') counts.manual_review++;
    else if (st === 'failed') counts.failed++;
  });
  $('sv-total').textContent = counts.total;
  $('sv-success').textContent = counts.success;
  $('sv-review').textContent = counts.manual_review;
  $('sv-failed').textContent = counts.failed;
}

let dashboardData = [];

async function fetchDashboardData() {
  const results = [];
  for (const id of recentIds) {
    try {
      const r = await fetch(`${API}/requests/${id}`);
      if (r.ok) results.push(await r.json());
    } catch {}
  }
  dashboardData = results;
  renderStats();
  renderRecentTable();
  $('recent-count').textContent = results.length;
}

function renderRecentTable() {
  const tbody = $('recent-tbody');
  if (dashboardData.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" class="empty-row">No requests yet. Submit a ticket to get started.</td></tr>`;
    return;
  }
  tbody.innerHTML = dashboardData.map(d => `
    <tr>
      <td>${formatId(d.request_id)}</td>
      <td style="color:var(--text-dim);font-size:12px;max-width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${d.input?.subject || '—'}</td>
      <td>${priorityBadge(d.input?.priority)}</td>
      <td>${badge(d.status)}</td>
      <td><button class="btn-sm" onclick="openExplain('${d.request_id}')">Explain</button></td>
    </tr>
  `).join('');
}

// ── Submit Ticket ──────────────────────────────────────────────────────────
$('gen-idem-btn').addEventListener('click', () => {
  $('f-idem').value = 'idem_' + Math.random().toString(36).slice(2, 14);
});

$('ticket-form').addEventListener('submit', async e => {
  e.preventDefault();
  const btn = $('submit-btn');
  btn.disabled = true;
  btn.innerHTML = `<span class="spinner"></span> Submitting...`;

  const idem = $('f-idem').value.trim();
  const headers = { 'Content-Type': 'application/json' };
  if (idem) headers['idempotency-key'] = idem;

  const body = {
    subject: $('f-subject').value.trim(),
    description: $('f-description').value.trim(),
    customer_id: $('f-customer').value.trim() || null,
    priority: $('f-priority').value
  };

  try {
    const r = await fetch(`${API}/requests`, { method: 'POST', headers, body: JSON.stringify(body) });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || 'Submission failed');

    // Store ID for dashboard
    if (!recentIds.includes(data.request_id)) recentIds.unshift(data.request_id);
    fetchDashboardData();

    $('submit-result').style.display = '';
    $('result-body').innerHTML = `
      <div class="result-box">
        <div class="result-row"><span class="result-key">Request ID</span><span class="result-val">${data.request_id}</span></div>
        <div class="result-row"><span class="result-key">Status</span><span class="result-val">${badge(data.status)}</span></div>
        <div class="result-row"><span class="result-key">Message</span><span class="result-val">${data.message}</span></div>
        <div style="margin-top:16px;display:flex;gap:10px;">
          <button class="btn-primary" style="font-size:12px;padding:9px 16px" onclick="pollAndExplain('${data.request_id}')">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none"><circle cx="11" cy="11" r="8" stroke="currentColor" stroke-width="2"/><line x1="21" y1="21" x2="16.65" y2="16.65" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
            Track & Explain
          </button>
        </div>
      </div>`;
    toast('Request submitted!', 'success');
  } catch (err) {
    toast(err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none"><line x1="22" y1="2" x2="11" y2="13" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><polygon points="22 2 15 22 11 13 2 9 22 2" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg> Submit Request`;
  }
});

// ── Polling until done ─────────────────────────────────────────────────────
async function pollAndExplain(id) {
  toast('Polling for result…', 'info');
  navigate('lookup');
  $('lookup-id').value = id;
  let attempts = 0;
  const interval = setInterval(async () => {
    attempts++;
    try {
      const r = await fetch(`${API}/requests/${id}`);
      const d = await r.json();
      const done = ['success', 'failed', 'manual_review'].includes((d.status || '').toLowerCase());
      if (done || attempts > 15) {
        clearInterval(interval);
        doExplain(id);
      }
    } catch { clearInterval(interval); }
  }, 1500);
}

// ── Lookup ─────────────────────────────────────────────────────────────────
$('lookup-btn').addEventListener('click', () => {
  const id = $('lookup-id').value.trim();
  if (!id) { toast('Enter a Request ID', 'error'); return; }
  doExplain(id);
});

$('lookup-id').addEventListener('keydown', e => {
  if (e.key === 'Enter') $('lookup-btn').click();
});

async function doExplain(id) {
  const el = $('explain-result');
  el.innerHTML = `<div style="padding:30px;text-align:center"><span class="spinner"></span> Fetching explanation…</div>`;
  try {
    const r = await fetch(`${API}/requests/${id}/explain`);
    if (!r.ok) { const d = await r.json(); throw new Error(d.detail || 'Not found'); }
    const d = await r.json();
    renderExplain(d, el);
  } catch (err) {
    el.innerHTML = `<div style="padding:20px;color:var(--red)">${err.message}</div>`;
  }
}

function renderExplain(d, container) {
  const conf = d.confidence_score != null ? Math.round(d.confidence_score * 100) : null;
  const decisionColor = {
    approve: 'var(--green)', reject: 'var(--red)',
    escalate: 'var(--amber)', manual_review: 'var(--cyan)'
  }[d.final_decision] || 'var(--text-dim)';

  container.innerHTML = `
    <div class="explain-grid">
      <!-- State + Decision -->
      <div class="explain-card">
        <div class="explain-card-title">Decision Summary</div>
        <div class="decision-block">
          <div class="decision-badge" style="background:${decisionColor}22;color:${decisionColor};border:1px solid ${decisionColor}44">
            ${d.final_decision ? d.final_decision.toUpperCase() : '⏳ PENDING'}
          </div>
          <div class="confidence-bar-wrap">
            <div class="confidence-label">Confidence ${conf != null ? conf + '%' : '—'}</div>
            <div class="confidence-bar"><div class="confidence-fill" style="width:${conf || 0}%"></div></div>
            <div style="font-size:11px;color:var(--text-muted);margin-top:4px">Workflow: ${badge(d.current_state)}</div>
          </div>
        </div>
        ${d.failure_reasons ? `<div style="margin-top:10px;font-size:12px;color:var(--red);padding:8px 12px;background:rgba(239,68,68,0.08);border-radius:6px">⚠ ${d.failure_reasons}</div>` : ''}
      </div>

      <!-- Input -->
      <div class="explain-card">
        <div class="explain-card-title">Input Data</div>
        <div class="json-block">${JSON.stringify(d.input_data, null, 2)}</div>
      </div>

      <!-- AI Output -->
      <div class="explain-card">
        <div class="explain-card-title">Raw AI Output</div>
        ${d.ai_output
          ? `<div class="json-block">${JSON.stringify(d.ai_output, null, 2)}</div>`
          : `<span class="no-data">No AI output yet</span>`}
      </div>

      <!-- Rules Triggered -->
      <div class="explain-card">
        <div class="explain-card-title">Rules Triggered</div>
        ${d.rules_triggered && d.rules_triggered.length
          ? `<div class="rules-list">${d.rules_triggered.map(r => `<div class="rule-chip">⚡ ${r}</div>`).join('')}</div>`
          : `<span class="no-data">No rules triggered</span>`}
      </div>

      <!-- Retrieved Context -->
      <div class="explain-card">
        <div class="explain-card-title">RAG Context (${d.retrieved_context?.length || 0} chunks)</div>
        ${d.retrieved_context && d.retrieved_context.length
          ? `<ul class="context-list">${d.retrieved_context.map(c => `<li>${c}</li>`).join('')}</ul>`
          : `<span class="no-data">No context retrieved</span>`}
      </div>
    </div>`;
}

// ── Open explain modal from dashboard ─────────────────────────────────────
function openExplain(id) {
  navigate('lookup');
  $('lookup-id').value = id;
  doExplain(id);
}

// ── Rules ──────────────────────────────────────────────────────────────────
$('rule-form').addEventListener('submit', async e => {
  e.preventDefault();
  const btn = $('rule-submit-btn');
  btn.disabled = true;

  let condition = {};
  try {
    const raw = $('r-condition').value.trim();
    if (raw) condition = JSON.parse(raw);
  } catch {
    toast('Invalid JSON in condition', 'error');
    btn.disabled = false;
    return;
  }

  const body = { name: $('r-name').value.trim(), condition, action: $('r-action').value };
  try {
    const r = await fetch(`${API}/rules`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || 'Failed');
    $('rule-result').style.display = '';
    $('rule-result-body').innerHTML = `
      <div class="result-box">
        <div class="result-row"><span class="result-key">ID</span><span class="result-val">${data.id}</span></div>
        <div class="result-row"><span class="result-key">Name</span><span class="result-val">${data.name}</span></div>
        <div class="result-row"><span class="result-key">Action</span><span class="result-val">${badge(data.action)}</span></div>
        <div class="result-row"><span class="result-key">Active</span><span class="result-val">${data.is_active ? '✅ Yes' : '❌ No'}</span></div>
        <div class="result-row"><span class="result-key">Condition</span><span class="result-val">${JSON.stringify(data.condition)}</span></div>
      </div>`;
    toast('Rule created!', 'success');
    $('rule-form').reset();
  } catch (err) { toast(err.message, 'error'); }
  finally { btn.disabled = false; }
});

// ── Refresh ────────────────────────────────────────────────────────────────
$('refresh-btn').addEventListener('click', () => {
  $('refresh-btn').classList.add('spinning');
  checkHealth();
  fetchDashboardData();
  setTimeout(() => $('refresh-btn').classList.remove('spinning'), 1000);
});

// ── Init ───────────────────────────────────────────────────────────────────
startClock();
checkHealth();
setInterval(checkHealth, 15000);
navigate('dashboard');
