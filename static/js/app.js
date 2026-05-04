/* ── Utilities ───────────────────────────────────────────────────────── */

function escHtml(str) {
  return String(str ?? '')
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}

function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

function getISOWeek(date) {
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  d.setUTCDate(d.getUTCDate() + 4 - (d.getUTCDay() || 7));
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  const week = Math.ceil((((d - yearStart) / 86400000) + 1) / 7);
  return { year: d.getUTCFullYear(), week };
}

function fmtDate(iso) {
  if (!iso) return '';
  const [y, m, d] = iso.split('-');
  const days = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
  const dow = days[new Date(iso).getDay()];
  return `${dow} ${d}.${m}.${y}`;
}

function hoursToDisplay(h) {
  const hrs  = Math.floor(h);
  const mins = Math.round((h - hrs) * 60);
  const md   = (h / 8).toFixed(2);
  if (mins === 0) return `${hrs}h (${md} MD)`;
  return `${hrs}h ${mins}m (${md} MD)`;
}

/* ── API helper ──────────────────────────────────────────────────────── */

async function apiFetch(url, opts = {}) {
  try {
    const defaults = { headers: { 'Content-Type': 'application/json' } };
    const res = await fetch(url, { ...defaults, ...opts,
      headers: { ...defaults.headers, ...(opts.headers || {}) } });
    const data = await res.json();
    if (!res.ok) {
      showToast(data.error || `Error ${res.status}`, 'error');
      return null;
    }
    return data;
  } catch (err) {
    showToast('Network error', 'error');
    return null;
  }
}

/* ── Toast ───────────────────────────────────────────────────────────── */

function showToast(msg, type = 'info') {
  const c = document.getElementById('toast-container');
  if (!c) return;
  const t = document.createElement('div');
  t.className = 'toast' + (type === 'error' ? ' toast-error' : '');
  t.textContent = msg;
  c.appendChild(t);
  setTimeout(() => t.remove(), 3500);
}

/* ── Modal ───────────────────────────────────────────────────────────── */

function openModal(title, bodyHtml) {
  document.getElementById('modal-title').textContent = title;
  document.getElementById('modal-body').innerHTML = bodyHtml;
  document.getElementById('modal-overlay').classList.remove('hidden');
  const first = document.querySelector('#modal-body input, #modal-body select, #modal-body textarea');
  if (first) setTimeout(() => first.focus(), 50);
}

function closeModal(event) {
  if (event && event.target !== document.getElementById('modal-overlay')) return;
  document.getElementById('modal-overlay').classList.add('hidden');
  document.getElementById('modal-body').innerHTML = '';
}

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') document.getElementById('modal-overlay').classList.add('hidden');
});

/* ── Entry form ──────────────────────────────────────────────────────── */

let _allProjects = [];

async function ensureProjects() {
  if (!_allProjects.length) {
    _allProjects = await apiFetch('/api/projects') || [];
  }
  return _allProjects;
}

function buildEntryForm(entry) {
  const today = new Date().toISOString().slice(0, 10);
  const isAbsence = entry?.is_absence ? 1 : 0;

  const projectsHtml = _allProjects.map(p =>
    `<option value="${p.id}" ${entry?.project_id == p.id ? 'selected' : ''}>${escHtml(p.name)}</option>`
  ).join('');

  const codesHtml = entry?.project_id
    ? buildCodesOptions(entry.project_id, entry.project_code_id)
    : '<option value="">— select project first —</option>';

  return `
<form id="entry-form" onsubmit="saveEntry(event)">
  <input type="hidden" id="ef-id" value="${entry?.id || ''}"/>

  <div class="form-group">
    <label>Date *</label>
    <input type="date" id="ef-date" required value="${entry?.entry_date || today}"/>
  </div>

  <div class="form-group">
    <div class="toggle-row" style="margin-bottom:8px">
      <input type="checkbox" id="ef-absence" onchange="toggleAbsenceMode(this.checked)" ${isAbsence ? 'checked' : ''}/>
      <label for="ef-absence" style="margin:0;font-weight:500">This is an absence entry (vacation, sick day, etc.)</label>
    </div>
  </div>

  <div id="ef-absence-section" class="${isAbsence ? '' : 'hidden'}">
    <div class="absence-section">
      <div class="form-group" style="margin-bottom:0">
        <label>Absence Type</label>
        <input type="text" id="ef-absence-type" placeholder="e.g. Vacation, Doctor, Sick day"
               value="${escHtml(entry?.absence_type || '')}"/>
      </div>
    </div>
  </div>

  <div id="ef-work-section" class="${isAbsence ? 'hidden' : ''}">
    <div class="form-group">
      <label>Project *</label>
      <select id="ef-project" onchange="onProjectChange(this.value)" ${isAbsence ? '' : 'required'}>
        <option value="">— select project —</option>
        ${projectsHtml}
      </select>
    </div>

    <div class="form-group">
      <label>Billing Code *</label>
      <select id="ef-code" ${isAbsence ? '' : 'required'}>
        ${codesHtml}
      </select>
    </div>

    <div class="form-group">
      <label>Ticket <span class="label-hint">(optional)</span></label>
      <input type="text" id="ef-ticket" placeholder="e.g. PROJ-1234" value="${escHtml(entry?.ticket || '')}"/>
    </div>

    <div class="form-group">
      <label>Description *</label>
      <textarea id="ef-description" ${isAbsence ? '' : 'required'} placeholder="What did you work on?">${escHtml(entry?.description || '')}</textarea>
    </div>

    <div class="form-group">
      <div class="toggle-row">
        <input type="checkbox" id="ef-export" ${entry && !entry.include_in_export ? '' : 'checked'}/>
        <label for="ef-export" style="margin:0">Include in export</label>
      </div>
    </div>
  </div>

  <div class="form-group">
    <label>Time *</label>
    <div class="hours-input-row">
      <input type="number" id="ef-hours-val" min="0" step="0.25" placeholder="0" style="width:80px"
             value="${entry ? getDisplayHoursValue(entry.hours, 'h') : ''}" oninput="updateTimeDisplay()"/>
      <select class="hours-unit-select" id="ef-hours-unit" onchange="updateTimeDisplay()">
        <option value="h">Hours (h)</option>
        <option value="m">Minutes (m)</option>
        <option value="md">Man-days (MD)</option>
      </select>
    </div>
    <div class="time-display" id="ef-time-display">${entry ? hoursToDisplay(entry.hours) : ''}</div>
  </div>

  <div class="form-actions">
    <button type="button" class="btn btn-outline" onclick="closeModal()">Cancel</button>
    <button type="submit" class="btn btn-primary">${entry ? 'Save Changes' : 'Add Entry'}</button>
  </div>
</form>`;
}

function getDisplayHoursValue(hours, unit) {
  if (unit === 'h')  return hours;
  if (unit === 'm')  return Math.round(hours * 60);
  if (unit === 'md') return (hours / 8).toFixed(2);
  return hours;
}

function getHoursFromInput() {
  const val  = parseFloat(document.getElementById('ef-hours-val').value) || 0;
  const unit = document.getElementById('ef-hours-unit').value;
  if (unit === 'h')  return val;
  if (unit === 'm')  return val / 60;
  if (unit === 'md') return val * 8;
  return val;
}

function updateTimeDisplay() {
  const h = getHoursFromInput();
  const el = document.getElementById('ef-time-display');
  if (el) el.textContent = h > 0 ? hoursToDisplay(h) : '';
}

function buildCodesOptions(projectId, selectedCodeId) {
  const proj = _allProjects.find(p => p.id == projectId);
  if (!proj || !proj.codes.length) return '<option value="">— no codes —</option>';
  return proj.codes.map(c =>
    `<option value="${c.id}" ${c.id == selectedCodeId ? 'selected' : ''}>${escHtml(c.code)} — ${escHtml(c.label)}</option>`
  ).join('');
}

function onProjectChange(projectId) {
  const sel = document.getElementById('ef-code');
  if (sel) sel.innerHTML = buildCodesOptions(projectId, null);
}

function toggleAbsenceMode(isAbsence) {
  document.getElementById('ef-absence-section').classList.toggle('hidden', !isAbsence);
  document.getElementById('ef-work-section').classList.toggle('hidden', isAbsence);
  const proj = document.getElementById('ef-project');
  const code = document.getElementById('ef-code');
  const desc = document.getElementById('ef-description');
  if (proj) proj.required = !isAbsence;
  if (code) code.required = !isAbsence;
  if (desc) desc.required = !isAbsence;
}

async function openAddEntry(prefillDate) {
  await ensureProjects();
  openModal('Log Time', buildEntryForm(prefillDate ? { entry_date: prefillDate } : null));
}

async function openEditEntry(id) {
  await ensureProjects();
  const entry = await apiFetch(`/api/entries/${id}`);
  if (!entry) return;
  openModal('Edit Entry', buildEntryForm(entry));
}

async function saveEntry(e) {
  e.preventDefault();
  const id       = document.getElementById('ef-id').value;
  const isAbsence = document.getElementById('ef-absence').checked;
  const hours    = getHoursFromInput();

  if (hours <= 0) { showToast('Please enter a valid time', 'error'); return; }

  const data = {
    entry_date:      document.getElementById('ef-date').value,
    hours,
    is_absence:      isAbsence ? 1 : 0,
    absence_type:    isAbsence ? (document.getElementById('ef-absence-type').value || '') : '',
    project_id:      isAbsence ? null : (document.getElementById('ef-project').value || null),
    project_code_id: isAbsence ? null : (document.getElementById('ef-code').value || null),
    ticket:          isAbsence ? '' : (document.getElementById('ef-ticket')?.value || ''),
    description:     isAbsence ? document.getElementById('ef-absence-type').value : (document.getElementById('ef-description')?.value || ''),
    include_in_export: isAbsence ? 0 : (document.getElementById('ef-export')?.checked ? 1 : 0),
  };

  const url    = id ? `/api/entries/${id}` : '/api/entries';
  const method = id ? 'PUT' : 'POST';
  const res    = await apiFetch(url, { method, body: JSON.stringify(data) });
  if (res) {
    closeModal();
    _allProjects = []; // reset cache
    showToast(id ? 'Entry updated' : 'Entry added');
    // Refresh whichever page is active
    if (typeof applyFiltersAndLoad === 'function') applyFiltersAndLoad();
    if (typeof loadDashboardStats  === 'function') { loadDashboardStats(); loadWeekStats(); loadRecentEntries(); }
  }
}

async function deleteEntry(id) {
  if (!confirm('Delete this entry?')) return;
  const res = await apiFetch(`/api/entries/${id}`, { method: 'DELETE' });
  if (res) {
    showToast('Entry deleted');
    if (typeof applyFiltersAndLoad === 'function') applyFiltersAndLoad();
    if (typeof loadDashboardStats  === 'function') { loadDashboardStats(); loadWeekStats(); loadRecentEntries(); }
  }
}

/* ── Entries table renderer (shared) ────────────────────────────────── */

function renderEntriesTable(entries, compact) {
  if (!entries.length) return '<div class="empty-state"><p>No entries.</p></div>';

  return `
<table class="data-table">
  <thead>
    <tr>
      ${!compact ? '<th style="width:32px"><input type="checkbox" onchange="selectAllInTable(this)"/></th>' : ''}
      <th>Date</th>
      <th>Project / Type</th>
      <th>Code</th>
      <th>Time</th>
      <th>Ticket</th>
      <th>Description</th>
      ${!compact ? '<th>Export</th>' : ''}
      <th></th>
    </tr>
  </thead>
  <tbody>
    ${entries.map(e => {
      const absence = e.is_absence;
      return `
      <tr class="${absence ? 'row-absence' : ''}">
        ${!compact ? `<td><input type="checkbox" class="entry-checkbox" data-id="${e.id}"
             ${typeof selectedIds !== 'undefined' && selectedIds.has(e.id) ? 'checked' : ''}
             onchange="toggleSelect(${e.id}, this.checked)"/></td>` : ''}
        <td style="white-space:nowrap">${fmtDate(e.entry_date)}</td>
        <td>
          ${absence
            ? `<span class="badge-absence-row">Absence</span> ${escHtml(e.absence_type || '')}`
            : escHtml(e.project_name || '—')}
        </td>
        <td>
          ${!absence && e.entry_code
            ? `<code class="code-chip-sm">${escHtml(e.entry_code)}</code>`
            : '<span style="color:#94a3b8">—</span>'}
        </td>
        <td style="white-space:nowrap">
          <span class="hours-chip">${e.hours.toFixed(2)}h</span>
          <span class="md-chip">${(e.hours/8).toFixed(2)}MD</span>
        </td>
        <td>${escHtml(e.ticket || '')}</td>
        <td class="td-desc" title="${escHtml(e.description || '')}">${escHtml(e.description || '')}</td>
        ${!compact ? `<td>${e.include_in_export && !absence
            ? '<span class="badge-yes">Yes</span>'
            : '<span class="badge-no">No</span>'}</td>` : ''}
        <td>
          <div class="td-actions">
            <button class="btn-icon" title="Edit" onclick="openEditEntry(${e.id})">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
              </svg>
            </button>
            <button class="btn-icon btn-icon-danger" title="Delete" onclick="deleteEntry(${e.id})">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="3 6 5 6 21 6"/>
                <path d="M19 6l-1 14H6L5 6"/>
                <path d="M10 11v6"/><path d="M14 11v6"/>
                <path d="M9 6V4h6v2"/>
              </svg>
            </button>
          </div>
        </td>
      </tr>`;
    }).join('')}
  </tbody>
</table>`;
}

function selectAllInTable(masterCb) {
  document.querySelectorAll('.entry-checkbox').forEach(cb => {
    cb.checked = masterCb.checked;
    if (typeof toggleSelect === 'function') toggleSelect(parseInt(cb.dataset.id), masterCb.checked);
  });
  if (typeof updateBulkBar === 'function') updateBulkBar();
}

/* ── Sidebar user ────────────────────────────────────────────────────── */

function updateSidebarUser(firstName, lastName) {
  const el = document.getElementById('sidebar-username');
  if (el) el.textContent = [firstName, lastName].filter(Boolean).join(' ') || '—';
}

async function loadSidebarUser() {
  const s = await apiFetch('/api/settings');
  if (s) updateSidebarUser(s.first_name, s.last_name);
}

/* ── Boot ────────────────────────────────────────────────────────────── */

document.addEventListener('DOMContentLoaded', loadSidebarUser);
