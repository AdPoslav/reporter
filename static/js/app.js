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

  const projectsHtml = _allProjects
    .filter(p => !p.archived_at || entry?.project_id == p.id)
    .map(p => `<option value="${p.id}" ${entry?.project_id == p.id ? 'selected' : ''}>${escHtml(p.name)}</option>`)
    .join('');

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
      <label>Ticket <span class="label-hint">(optional, comma-separated for multiple)</span></label>
      <input type="text" id="ef-ticket" placeholder="e.g. PROJ-1234 or PROJ-1, PROJ-2, PROJ-3" value="${escHtml(entry?.ticket || '')}"/>
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
  return proj.codes.map(c => {
    const label = c.deprecated
      ? `${escHtml(c.code)} — ${escHtml(c.label)} [deprecated]`
      : `${escHtml(c.code)} — ${escHtml(c.label)}`;
    return `<option value="${c.id}" ${c.id == selectedCodeId ? 'selected' : ''}>${label}</option>`;
  }).join('');
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
    _allProjects = [];
    showToast(id ? 'Entry updated' : 'Entry added');
    if (typeof applyFiltersAndLoad === 'function') applyFiltersAndLoad();
    if (typeof loadDashboardStats  === 'function') { loadDashboardStats(); loadWeekStats(); loadWeekEntries(); }
    loadTodayStats();
  }
}

async function deleteEntry(id) {
  if (!confirm('Delete this entry?')) return;
  const res = await apiFetch(`/api/entries/${id}`, { method: 'DELETE' });
  if (res) {
    showToast('Entry deleted');
    if (typeof applyFiltersAndLoad === 'function') applyFiltersAndLoad();
    if (typeof loadDashboardStats  === 'function') { loadDashboardStats(); loadWeekStats(); loadWeekEntries(); }
    loadTodayStats();
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
        <td>${renderTickets(e.ticket)}</td>
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

/* ── Ticket helpers ──────────────────────────────────────────────────── */

const _MN = ['January','February','March','April','May','June',
             'July','August','September','October','November','December'];

function renderTickets(ticketStr) {
  if (!ticketStr || !ticketStr.trim()) return '<span style="color:#94a3b8">—</span>';
  const tickets = ticketStr.split(',').map(t => t.trim()).filter(Boolean);
  if (!tickets.length) return '<span style="color:#94a3b8">—</span>';
  return tickets.map(t =>
    `<button class="ticket-link" data-ticket="${escHtml(t)}" onclick="openTicketDetail(this,this.dataset.ticket)">${escHtml(t)}</button>`
  ).join(' ');
}

async function openTicketDetail(btn, ticket) {
  if (!ticket) return;
  const tr = btn.closest('tr');

  // Close any detail rows not belonging to this tr
  document.querySelectorAll('.ticket-detail-row').forEach(r => {
    if (r !== tr?.nextElementSibling) r.remove();
  });
  document.querySelectorAll('.ticket-link.ticket-active').forEach(b => {
    if (b !== btn) b.classList.remove('ticket-active');
  });

  // Toggle off if already open for this row
  if (tr?.nextElementSibling?.classList.contains('ticket-detail-row')) {
    tr.nextElementSibling.remove();
    btn.classList.remove('ticket-active');
    return;
  }

  btn.classList.add('ticket-active');

  const entries = await apiFetch(`/api/entries?ticket=${encodeURIComponent(ticket)}`);
  if (!entries) { btn.classList.remove('ticket-active'); return; }

  const totalH = entries.reduce((s, e) => s + e.hours, 0);
  const byMonth = {};
  entries.forEach(e => {
    const ym = e.entry_date.slice(0, 7);
    byMonth[ym] = (byMonth[ym] || 0) + e.hours;
  });
  const months = Object.keys(byMonth).sort().reverse();
  const monthRows = months.map(ym => {
    const [y, m] = ym.split('-');
    const h = byMonth[ym];
    return `<tr><td>${_MN[+m-1]} ${y}</td><td>${h.toFixed(2)} h</td><td>${(h/8).toFixed(2)} MD</td></tr>`;
  }).join('');

  const jiraLink = _jiraPrefix
    ? `<a href="${escHtml(_jiraPrefix + ticket)}" target="_blank" rel="noopener" class="ticket-jira-link">↗ Jira</a>`
    : '';

  const colCount = tr ? tr.cells.length : 8;
  const detailTr = document.createElement('tr');
  detailTr.className = 'ticket-detail-row';
  const td = document.createElement('td');
  td.colSpan = colCount;
  td.innerHTML = `
    <div class="ticket-inline-detail">
      <div class="ticket-inline-header">
        <span class="ticket-inline-name">${escHtml(ticket)}</span>
        ${jiraLink}
        <span class="ticket-inline-total">${totalH.toFixed(2)} h &nbsp;·&nbsp; ${(totalH/8).toFixed(2)} MD total</span>
        <button class="ticket-inline-close" onclick="this.closest('.ticket-detail-row').previousElementSibling
          .querySelectorAll('.ticket-link').forEach(b=>b.classList.remove('ticket-active'));
          this.closest('.ticket-detail-row').remove()">✕</button>
      </div>
      <table class="ticket-month-table">
        <thead><tr><th>Period</th><th>Hours</th><th>MD</th></tr></thead>
        <tbody>${monthRows}</tbody>
      </table>
    </div>`;
  detailTr.appendChild(td);
  if (tr) tr.after(detailTr);
}

/* ── Sidebar user & settings ─────────────────────────────────────────── */

let _jiraPrefix = '';

function updateSidebarUser(firstName, lastName) {
  const el = document.getElementById('sidebar-username');
  if (el) el.textContent = [firstName, lastName].filter(Boolean).join(' ') || '—';
}

async function loadSidebarUser() {
  const s = await apiFetch('/api/settings');
  if (s) {
    updateSidebarUser(s.first_name, s.last_name);
    _jiraPrefix = s.jira_prefix || '';
  }
  loadTodayStats();
}

/* ── Day panel (visible on all pages) ───────────────────────────────── */

let dayOffset = 0;

function _offsetToIso(offset) {
  const d = new Date();
  d.setDate(d.getDate() + offset);
  return d.toISOString().slice(0, 10);
}

function shiftDay(delta) {
  const newOffset = dayOffset + delta;
  if (newOffset > 0) return;
  const prevIso = _offsetToIso(dayOffset);
  dayOffset = newOffset;
  const newIso  = _offsetToIso(dayOffset);
  // If we crossed a month boundary, sync the calendar
  if (prevIso.slice(0, 7) !== newIso.slice(0, 7)) {
    const [y, m] = newIso.split('-');
    asideCalYear  = parseInt(y);
    asideCalMonth = parseInt(m);
    loadAsideCalendar();
  } else {
    _highlightAsideCalDay(newIso);
  }
  loadTodayStats();
}

function jumpToToday() {
  dayOffset = 0;
  const iso = _offsetToIso(0);
  const [y, m] = iso.split('-');
  asideCalYear  = parseInt(y);
  asideCalMonth = parseInt(m);
  loadAsideCalendar();
  loadTodayStats();
}

function jumpToDay(iso) {
  const todayDate = new Date();
  todayDate.setHours(0, 0, 0, 0);
  const target = new Date(iso + 'T00:00:00');
  if (target > todayDate) return;
  dayOffset = Math.round((target - todayDate) / 86400000);
  const [y, m] = iso.split('-');
  asideCalYear  = parseInt(y);
  asideCalMonth = parseInt(m);
  loadTodayStats();
  _highlightAsideCalDay(iso);
}

/* ── Aside mini calendar ─────────────────────────────────────────────── */

let asideCalYear  = new Date().getFullYear();
let asideCalMonth = new Date().getMonth() + 1;
const _ASIDE_MONTHS = ['January','February','March','April','May','June',
                       'July','August','September','October','November','December'];

function shiftAsideCal(delta) {
  asideCalMonth += delta;
  if (asideCalMonth > 12) { asideCalMonth = 1; asideCalYear++; }
  if (asideCalMonth < 1)  { asideCalMonth = 12; asideCalYear--; }
  loadAsideCalendar();
}

async function loadAsideCalendar() {
  const grid = document.getElementById('aside-cal-grid');
  if (!grid) return;

  const labelEl  = document.getElementById('aside-cal-label');
  const nextBtn  = document.getElementById('aside-cal-next-btn');
  const badgeEl  = document.getElementById('aside-cal-badge');
  const today    = new Date(); today.setHours(0,0,0,0);
  const nowYear  = today.getFullYear();
  const nowMonth = today.getMonth() + 1;

  if (labelEl) labelEl.textContent = `${_ASIDE_MONTHS[asideCalMonth-1]} ${asideCalYear}`;
  // disable next-month if already at current month
  if (nextBtn) nextBtn.disabled = (asideCalYear === nowYear && asideCalMonth === nowMonth);

  const data = await apiFetch(`/api/stats/missing-days?year=${asideCalYear}&month=${asideCalMonth}`);
  if (!data) return;

  // update badge
  if (badgeEl) {
    if (data.missing_count === 0) {
      badgeEl.innerHTML = '<span class="aside-cal-badge badge-ok">✓ all filled</span>';
    } else {
      badgeEl.innerHTML = `<span class="aside-cal-badge badge-warn">${data.missing_count} day${data.missing_count > 1 ? 's' : ''} missing</span>`;
    }
  }

  const activeIso = _offsetToIso(dayOffset);
  const headers   = Array.from(grid.children).slice(0, 7);
  grid.innerHTML  = '';
  headers.forEach(h => grid.appendChild(h));

  // leading blanks
  const firstWd = data.days[0].weekday;
  for (let i = 0; i < firstWd; i++) {
    const b = document.createElement('div');
    b.className = 'aside-cal-day day-blank';
    grid.appendChild(b);
  }

  data.days.forEach(d => {
    const cell = document.createElement('div');
    const isActive = d.date === activeIso;
    let cls = 'aside-cal-day ';
    if (isActive)                         cls += 'day-active';
    else if (d.is_weekend || d.is_holiday) cls += 'day-off';
    else if (d.is_future)                  cls += 'day-future';
    else if (d.missing)                    cls += 'day-missing';
    else                                   cls += 'day-ok';
    cell.className = cls;
    cell.textContent = d.day;

    let tip = d.date;
    if (d.is_holiday)       tip += ' · holiday';
    else if (d.is_weekend)  tip += ' · weekend';
    else if (d.is_future)   tip += ' · future';
    else if (d.missing)     tip += ' · no entries!';
    else if (d.hours > 0)   tip += ` · ${d.hours}h logged`;
    else                    tip += ' · absence logged';
    cell.title = tip;

    if (!d.is_future) cell.onclick = () => jumpToDay(d.date);
    grid.appendChild(cell);
  });
}

function _highlightAsideCalDay(iso) {
  document.querySelectorAll('#aside-cal-grid .aside-cal-day').forEach(cell => {
    if (cell.title.startsWith(iso)) {
      cell.classList.add('day-active');
      cell.classList.remove('day-ok', 'day-missing', 'day-off', 'day-future');
    } else if (cell.classList.contains('day-active')) {
      cell.classList.remove('day-active');
      // restore original class from data — simpler to just reload
      loadAsideCalendar();
    }
  });
}

async function loadTodayStats() {
  const dowEl = document.getElementById('today-dow');
  if (!dowEl) return;

  const iso = _offsetToIso(dayOffset);
  const ts  = await apiFetch(`/api/stats/today?date=${iso}`);
  if (!ts) return;

  const d    = new Date(ts.date + 'T00:00:00');
  const dows = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
  const [y, m, day] = ts.date.split('-');
  const isToday = dayOffset === 0;

  dowEl.textContent = dows[d.getDay()] + (isToday ? ' — Today' : '');
  const fullDateEl = document.getElementById('today-full-date');
  if (fullDateEl) fullDateEl.textContent = `${day}.${m}.${y}`;
  const subtitleEl = document.getElementById('dash-subtitle');
  if (subtitleEl) subtitleEl.textContent = ts.date;

  const nextBtn = document.getElementById('today-nav-next');
  const jumpBtn = document.getElementById('today-jump-btn');
  if (nextBtn) nextBtn.style.visibility = isToday ? 'hidden' : '';
  if (jumpBtn) jumpBtn.style.display    = isToday ? 'none'   : '';

  const h = ts.today_hours;
  setText('panel-today-hours', `${h.toFixed(2)} h`);
  setText('panel-today-md',    `${(h/8).toFixed(2)} MD`);

  const bar = document.getElementById('panel-today-bar');
  if (bar) bar.style.width = `${Math.min(h/8*100, 100).toFixed(1)}%`;

  const remEl  = document.getElementById('panel-today-remaining');
  const remSub = document.getElementById('panel-today-remaining-sub');

  if (!ts.is_workday) {
    if (remEl) { remEl.textContent = '—'; remEl.className = 'today-rem-val today-rem-ok'; }
    if (remSub) remSub.textContent = 'Weekend / holiday';
    if (bar) { bar.style.width = '0%'; bar.className = 'today-bar-fill'; }
  } else {
    const rem = ts.remaining;
    if (remEl) {
      remEl.textContent = `${rem.toFixed(2)} h`;
      remEl.className = 'today-rem-val ' + (rem < 0 ? 'today-rem-over' : rem === 0 ? 'today-rem-ok' : '');
    }
    if (remSub) remSub.textContent = `${(rem/8).toFixed(2)} MD`;
    if (bar) bar.className = 'today-bar-fill' + (rem < 0 ? ' today-bar-over' : rem === 0 ? ' today-bar-done' : '');
  }
}

/* ── Boot ────────────────────────────────────────────────────────────── */

document.addEventListener('DOMContentLoaded', () => {
  loadSidebarUser();
  loadAsideCalendar();
});
