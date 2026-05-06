import io
import json
import os
import sys
import threading
import webbrowser
import datetime

from flask import Flask, render_template, request, jsonify, send_file

import database as db
import export as exp


def _resource(relative_path):
    """Resolve path to a bundled resource — works in dev and as PyInstaller exe."""
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, relative_path)


if getattr(sys, 'frozen', False):
    app = Flask(__name__,
                template_folder=_resource('templates'),
                static_folder=_resource('static'))
else:
    app = Flask(__name__)   # dev: use default relative folders
app.secret_key = 'timelog-internal-2024'


# ── Helpers ──────────────────────────────────────────────────────────────────

def _today():
    return datetime.date.today()


# ── Pages ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    today = _today()
    projects = db.get_all_projects()
    stats = db.get_month_stats(today.year, today.month)
    iso = today.isocalendar()
    week_stats = db.get_week_stats(iso[0], iso[1])
    settings = {
        'work_id':    db.get_setting('work_id'),
        'first_name': db.get_setting('first_name'),
        'last_name':  db.get_setting('last_name'),
    }
    return render_template(
        'index.html',
        projects=projects,
        stats=stats,
        week_stats=week_stats,
        settings=settings,
        today=today.strftime('%Y-%m-%d'),
        current_year=today.year,
        current_month=today.month,
        current_week=iso[1],
    )


@app.route('/entries')
def entries_page():
    today = _today()
    projects = db.get_all_projects()
    return render_template(
        'entries.html',
        projects=projects,
        today=today.strftime('%Y-%m-%d'),
        current_year=today.year,
        current_month=today.month,
        current_week=today.isocalendar()[1],
    )


@app.route('/projects')
def projects_page():
    projects = db.get_all_projects()
    return render_template('projects.html', projects=projects)


@app.route('/holidays')
def holidays_page():
    holidays = db.get_all_holidays()
    return render_template('holidays.html', holidays=holidays)


@app.route('/api/holidays', methods=['GET'])
def api_holidays():
    return jsonify(db.get_all_holidays())


@app.route('/api/holidays', methods=['POST'])
def api_create_holiday():
    d = request.get_json()
    is_recurring = bool(d.get('is_recurring', True))
    hid = db.create_holiday(
        day=int(d['day']),
        month=int(d['month']),
        year=int(d['year']) if d.get('year') and not is_recurring else None,
        description=d['description'].strip(),
        is_recurring=is_recurring,
    )
    return jsonify({'id': hid, 'success': True})


@app.route('/api/holidays/<int:hid>', methods=['PUT'])
def api_update_holiday(hid):
    d = request.get_json()
    is_recurring = bool(d.get('is_recurring', True))
    db.update_holiday(
        hid=hid,
        day=int(d['day']),
        month=int(d['month']),
        year=int(d['year']) if d.get('year') and not is_recurring else None,
        description=d['description'].strip(),
        is_recurring=is_recurring,
    )
    return jsonify({'success': True})


@app.route('/api/holidays/<int:hid>', methods=['DELETE'])
def api_delete_holiday(hid):
    db.delete_holiday(hid)
    return jsonify({'success': True})


@app.route('/export')
def export_page():
    today = _today()
    projects = db.get_all_projects()
    return render_template(
        'export.html',
        projects=projects,
        current_year=today.year,
        current_month=today.month,
    )


@app.route('/settings')
def settings_page():
    return render_template(
        'settings.html',
        work_id=db.get_setting('work_id'),
        first_name=db.get_setting('first_name'),
        last_name=db.get_setting('last_name'),
        jira_prefix=db.get_setting('jira_prefix') or '',
    )


# ── Settings API ──────────────────────────────────────────────────────────────

@app.route('/api/settings', methods=['GET'])
def api_get_settings():
    return jsonify({
        'work_id':     db.get_setting('work_id'),
        'first_name':  db.get_setting('first_name'),
        'last_name':   db.get_setting('last_name'),
        'jira_prefix': db.get_setting('jira_prefix') or '',
    })


@app.route('/api/settings', methods=['POST'])
def api_save_settings():
    data = request.get_json()
    db.set_setting('work_id',     data.get('work_id', ''))
    db.set_setting('first_name',  data.get('first_name', ''))
    db.set_setting('last_name',   data.get('last_name', ''))
    db.set_setting('jira_prefix', data.get('jira_prefix', ''))
    return jsonify({'success': True})


# ── Projects API ──────────────────────────────────────────────────────────────

@app.route('/api/projects', methods=['GET'])
def api_projects():
    return jsonify(db.get_all_projects())


@app.route('/api/projects', methods=['POST'])
def api_create_project():
    data = request.get_json()
    pid = db.create_project(data['name'].strip(), data['code'].strip())
    return jsonify({'id': pid, 'success': True})


@app.route('/api/projects/<int:pid>', methods=['PUT'])
def api_update_project(pid):
    data = request.get_json()
    db.update_project(pid, data['name'].strip(), data['code'].strip())
    return jsonify({'success': True})


@app.route('/api/projects/<int:pid>', methods=['DELETE'])
def api_delete_project(pid):
    db.delete_project(pid)
    return jsonify({'success': True})


@app.route('/api/projects/<int:pid>/archive', methods=['POST'])
def api_archive_project(pid):
    db.archive_project(pid)
    return jsonify({'success': True})

@app.route('/api/projects/<int:pid>/restore', methods=['POST'])
def api_restore_project(pid):
    db.restore_project(pid)
    return jsonify({'success': True})


@app.route('/api/projects/<int:pid>/codes', methods=['POST'])
def api_create_code(pid):
    data = request.get_json()
    cid = db.create_project_code(
        pid, data['code'].strip(), data['label'].strip(),
        deprecated=bool(data.get('deprecated', False))
    )
    return jsonify({'id': cid, 'success': True})


@app.route('/api/projects/<int:pid>/codes/<int:cid>', methods=['PUT'])
def api_update_code(pid, cid):
    data = request.get_json()
    db.update_project_code(
        cid, data['code'].strip(), data['label'].strip(),
        deprecated=bool(data.get('deprecated', False))
    )
    return jsonify({'success': True})


@app.route('/api/projects/<int:pid>/codes/<int:cid>', methods=['DELETE'])
def api_delete_code(pid, cid):
    db.delete_project_code(cid)
    return jsonify({'success': True})


# ── Entries API ───────────────────────────────────────────────────────────────

@app.route('/api/entries', methods=['GET'])
def api_entries():
    filters = {k: v for k, v in {
        'date_from':    request.args.get('date_from'),
        'date_to':      request.args.get('date_to'),
        'project_id':   request.args.get('project_id'),
        'code_id':      request.args.get('code_id'),
        'ticket':       request.args.get('ticket'),
        'ticket_exact': request.args.get('ticket_exact'),
        'description':  request.args.get('description'),
    }.items() if v}
    return jsonify(db.get_entries(filters))


@app.route('/api/entries', methods=['POST'])
def api_create_entry():
    d = request.get_json()
    eid = db.create_entry(
        entry_date=d['entry_date'],
        project_id=d.get('project_id') or None,
        project_code_id=d.get('project_code_id') or None,
        hours=float(d['hours']),
        ticket=d.get('ticket', ''),
        description=d.get('description', ''),
        is_absence=int(d.get('is_absence', 0)),
        absence_type=d.get('absence_type', ''),
        include_in_export=int(d.get('include_in_export', 1)),
    )
    return jsonify({'id': eid, 'success': True})


@app.route('/api/entries/<int:eid>', methods=['GET'])
def api_get_entry(eid):
    entry = db.get_entry(eid)
    if not entry:
        return jsonify({'error': 'Not found'}), 404
    return jsonify(entry)


@app.route('/api/entries/<int:eid>', methods=['PUT'])
def api_update_entry(eid):
    d = request.get_json()
    db.update_entry(
        entry_id=eid,
        entry_date=d['entry_date'],
        project_id=d.get('project_id') or None,
        project_code_id=d.get('project_code_id') or None,
        hours=float(d['hours']),
        ticket=d.get('ticket', ''),
        description=d.get('description', ''),
        is_absence=int(d.get('is_absence', 0)),
        absence_type=d.get('absence_type', ''),
        include_in_export=int(d.get('include_in_export', 1)),
    )
    return jsonify({'success': True})


@app.route('/api/entries/<int:eid>', methods=['DELETE'])
def api_delete_entry(eid):
    db.delete_entry(eid)
    return jsonify({'success': True})


@app.route('/api/entries/bulk-toggle-export', methods=['POST'])
def api_bulk_toggle():
    d = request.get_json()
    db.toggle_export_flag(d['ids'], d['value'])
    return jsonify({'success': True})


# ── Stats API ─────────────────────────────────────────────────────────────────

@app.route('/api/stats/month')
def api_month_stats():
    today = _today()
    year  = int(request.args.get('year',  today.year))
    month = int(request.args.get('month', today.month))
    return jsonify(db.get_month_stats(year, month))


@app.route('/api/stats/week')
def api_week_stats():
    today = _today()
    iso   = today.isocalendar()
    year  = int(request.args.get('year',  iso[0]))
    week  = int(request.args.get('week',  iso[1]))
    return jsonify(db.get_week_stats(year, week))


@app.route('/api/stats/today')
def api_today_stats():
    date_str = request.args.get('date')
    return jsonify(db.get_day_stats(date_str))


# ── Export API ────────────────────────────────────────────────────────────────

@app.route('/api/export', methods=['POST'])
def api_export():
    d     = request.get_json()
    year  = int(d['year'])
    month = int(d['month'])

    work_id    = db.get_setting('work_id')
    first_name = db.get_setting('first_name')
    last_name  = db.get_setting('last_name')
    if not work_id:
        return jsonify({'error': 'Please set your Work-ID in Settings first.'}), 400
    if not last_name:
        return jsonify({'error': 'Please set your last name in Settings first.'}), 400

    month_str = f"{year:04d}-{month:02d}"
    filters = {
        'date_from': f"{month_str}-01",
        'date_to':   f"{month_str}-31",
    }
    if d.get('project_id'):
        filters['project_id'] = d['project_id']

    # If specific entry IDs were provided, use only those
    selected_ids = set(d.get('entry_ids', []))

    all_entries = db.get_entries(filters)

    if selected_ids:
        all_entries = [e for e in all_entries if e['id'] in selected_ids]
        # Mark all selected as include_in_export for this run
        for e in all_entries:
            e['include_in_export'] = 1

    # Group by project_id
    projects_map: dict = {}
    for entry in all_entries:
        if entry.get('is_absence'):
            continue
        if not entry.get('include_in_export', 1):
            continue
        pid = entry.get('project_id')
        if pid is None:
            continue
        if pid not in projects_map:
            projects_map[pid] = {
                'project_name': entry['project_name'],
                'project_code': entry['project_main_code'],
                'entries': [],
            }
        projects_map[pid]['entries'].append(entry)

    if not projects_map:
        return jsonify({'error': 'No exportable entries found for the selected period.'}), 400

    generated = []
    for pid, pdata in projects_map.items():
        result = exp.generate_export(
            entries=pdata['entries'],
            project_name=pdata['project_name'],
            project_code=pdata['project_code'],
            work_id=work_id,
            first_name=first_name,
            last_name=last_name,
            year=year,
            month=month,
        )
        if result:
            filepath, filename = result
            generated.append(filename)

    return jsonify({'success': True, 'files': generated, 'count': len(generated)})


@app.route('/api/export/download/<path:filename>')
def api_download(filename):
    filepath = os.path.join(exp.EXPORTS_DIR, filename)
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    return send_file(filepath, as_attachment=True, download_name=filename)


# ── Data export / import ──────────────────────────────────────────────────────

@app.route('/api/stats/missing-days')
def api_missing_days():
    year  = int(request.args.get('year',  _today().year))
    month = int(request.args.get('month', _today().month))
    today = _today()

    num_days = __import__('calendar').monthrange(year, month)[1]

    conn = db.get_db()
    holidays = conn.execute('SELECT day, month, year, is_recurring FROM holidays').fetchall()
    # hours logged per day (non-absence only)
    # work hours per day (for display in tooltip)
    work_rows = conn.execute('''
        SELECT entry_date, COALESCE(SUM(hours),0) AS h
        FROM time_entries
        WHERE entry_date LIKE ? AND is_absence = 0
        GROUP BY entry_date
    ''', (f'{year:04d}-{month:02d}%',)).fetchall()
    # total hours per day incl. absence (for deficit calculation)
    total_rows = conn.execute('''
        SELECT entry_date, COALESCE(SUM(hours),0) AS h
        FROM time_entries
        WHERE entry_date LIKE ?
        GROUP BY entry_date
    ''', (f'{year:04d}-{month:02d}%',)).fetchall()
    conn.close()

    work_hours        = {r['entry_date']: round(r['h'], 2) for r in work_rows}
    total_hours       = {r['entry_date']: round(r['h'], 2) for r in total_rows}
    days_with_entries = set(total_hours.keys())

    def is_holiday(d):
        return any(
            h['month'] == d.month and h['day'] == d.day and
            (h['is_recurring'] or h['year'] == d.year)
            for h in holidays
        )

    days = []
    missing_dates = []
    for day_num in range(1, num_days + 1):
        d      = datetime.date(year, month, day_num)
        ds     = d.strftime('%Y-%m-%d')
        is_we  = d.weekday() >= 5
        is_hol = is_holiday(d)
        is_fut = d > today
        hours  = work_hours.get(ds, 0.0)
        has_any = ds in days_with_entries
        is_work = not is_we and not is_hol
        missing = is_work and not is_fut and not has_any

        days.append({
            'date':       ds,
            'day':        day_num,
            'weekday':    d.weekday(),  # 0=Mon
            'is_working': is_work,
            'is_future':  is_fut,
            'is_holiday': is_hol,
            'is_weekend': is_we,
            'hours':      hours,
            'has_entries': has_any,
            'missing':    missing,
        })
        if missing:
            missing_dates.append(ds)

    # Hours deficit for past working days — use total hours (work + absence)
    past_fund    = sum(8 for d in days if d['is_working'] and not d['is_future'])
    past_logged  = sum(total_hours.get(d['date'], 0.0) for d in days if d['is_working'] and not d['is_future'])
    deficit      = round(past_fund - past_logged, 2)

    return jsonify({
        'year': year, 'month': month,
        'days': days,
        'missing_count':  len(missing_dates),
        'missing_dates':  missing_dates,
        'past_fund':      past_fund,
        'past_logged':    round(past_logged, 2),
        'deficit':        deficit,
    })


@app.route('/api/data/export', methods=['GET'])
def api_data_export():
    conn = db.get_db()
    settings = {r['key']: r['value'] for r in conn.execute('SELECT key, value FROM settings').fetchall()}
    projects = []
    for p in conn.execute('SELECT * FROM projects ORDER BY id').fetchall():
        codes = [dict(c) for c in conn.execute(
            'SELECT * FROM project_codes WHERE project_id = ? ORDER BY sort_order, id', (p['id'],)
        ).fetchall()]
        projects.append({**dict(p), 'codes': codes})
    holidays     = [dict(r) for r in conn.execute('SELECT * FROM holidays ORDER BY id').fetchall()]
    time_entries = [dict(r) for r in conn.execute('SELECT * FROM time_entries ORDER BY id').fetchall()]
    conn.close()

    bundle = {
        'version':     2,
        'exported_at': datetime.datetime.now().isoformat(timespec='seconds'),
        'settings':    settings,
        'projects':    projects,
        'holidays':    holidays,
        'time_entries': time_entries,
    }
    buf = io.BytesIO(json.dumps(bundle, indent=2, ensure_ascii=False).encode('utf-8'))
    ts  = datetime.datetime.now().strftime('%Y%m%d_%H%M')
    return send_file(buf, mimetype='application/json',
                     as_attachment=True, download_name=f'timelog_backup_{ts}.json')


@app.route('/api/data/import', methods=['POST'])
def api_data_import():
    mode = request.args.get('mode', 'merge')   # 'merge' | 'replace'

    f = request.files.get('file')
    if not f:
        return jsonify({'error': 'No file uploaded'}), 400
    try:
        bundle = json.loads(f.read().decode('utf-8'))
    except Exception:
        return jsonify({'error': 'Invalid JSON file'}), 400

    if bundle.get('version') not in (1, 2):
        return jsonify({'error': 'Unsupported backup version'}), 400

    conn = db.get_db()
    try:
        if mode == 'replace':
            conn.executescript('''
                DELETE FROM time_entries;
                DELETE FROM project_codes;
                DELETE FROM projects;
                DELETE FROM holidays;
                DELETE FROM settings;
            ''')

        # ── Settings ──────────────────────────────────────────────────────────
        for key, value in (bundle.get('settings') or {}).items():
            if mode == 'replace':
                conn.execute('INSERT INTO settings (key, value) VALUES (?, ?)', (key, value))
            else:
                conn.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', (key, value))

        # ── Projects + codes (build old_id → new_id maps) ─────────────────────
        proj_id_map = {}   # old_id → new_id
        code_id_map = {}   # old_id → new_id

        for p in (bundle.get('projects') or []):
            old_pid = p['id']
            if mode == 'replace':
                cur = conn.execute(
                    'INSERT INTO projects (name, code, created_at, archived_at) VALUES (?,?,?,?)',
                    (p['name'], p['code'], p.get('created_at'), p.get('archived_at'))
                )
                new_pid = cur.lastrowid
            else:
                existing = conn.execute(
                    'SELECT id FROM projects WHERE name = ? AND code = ?', (p['name'], p['code'])
                ).fetchone()
                if existing:
                    new_pid = existing['id']
                else:
                    cur = conn.execute(
                        'INSERT INTO projects (name, code, created_at, archived_at) VALUES (?,?,?,?)',
                        (p['name'], p['code'], p.get('created_at'), p.get('archived_at'))
                    )
                    new_pid = cur.lastrowid
            proj_id_map[old_pid] = new_pid

            for c in (p.get('codes') or []):
                old_cid = c['id']
                if mode == 'replace':
                    cur = conn.execute(
                        'INSERT INTO project_codes (project_id, code, label, sort_order, deprecated) VALUES (?,?,?,?,?)',
                        (new_pid, c['code'], c['label'], c.get('sort_order', 0), c.get('deprecated', 0))
                    )
                    new_cid = cur.lastrowid
                else:
                    existing = conn.execute(
                        'SELECT id FROM project_codes WHERE project_id = ? AND code = ?', (new_pid, c['code'])
                    ).fetchone()
                    if existing:
                        new_cid = existing['id']
                    else:
                        cur = conn.execute(
                            'INSERT INTO project_codes (project_id, code, label, sort_order, deprecated) VALUES (?,?,?,?,?)',
                            (new_pid, c['code'], c['label'], c.get('sort_order', 0), c.get('deprecated', 0))
                        )
                        new_cid = cur.lastrowid
                code_id_map[old_cid] = new_cid

        # ── Holidays ──────────────────────────────────────────────────────────
        h_inserted = 0
        for h in (bundle.get('holidays') or []):
            if mode == 'merge':
                exists = conn.execute(
                    'SELECT id FROM holidays WHERE day=? AND month=? AND is_recurring=? AND description=?',
                    (h['day'], h['month'], h.get('is_recurring', 1), h.get('description', ''))
                ).fetchone()
                if exists:
                    continue
            conn.execute(
                'INSERT INTO holidays (day, month, year, description, is_recurring) VALUES (?,?,?,?,?)',
                (h['day'], h['month'], h.get('year'), h.get('description', ''), h.get('is_recurring', 1))
            )
            h_inserted += 1

        # ── Time entries ──────────────────────────────────────────────────────
        e_inserted = 0
        for e in (bundle.get('time_entries') or []):
            new_pid = proj_id_map.get(e.get('project_id'))
            new_cid = code_id_map.get(e.get('project_code_id'))
            if mode == 'merge':
                exists = conn.execute('''
                    SELECT id FROM time_entries
                    WHERE entry_date=? AND hours=? AND ticket=? AND description=?
                    AND project_id IS ? AND is_absence=?
                ''', (e['entry_date'], e['hours'], e.get('ticket',''),
                      e.get('description',''), new_pid, e.get('is_absence', 0))
                ).fetchone()
                if exists:
                    continue
            conn.execute('''
                INSERT INTO time_entries
                (entry_date, project_id, project_code_id, hours, ticket, description,
                 is_absence, absence_type, include_in_export, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            ''', (e['entry_date'], new_pid, new_cid, e['hours'],
                  e.get('ticket',''), e.get('description',''),
                  e.get('is_absence', 0), e.get('absence_type',''),
                  e.get('include_in_export', 1), e.get('created_at')))
            e_inserted += 1

        conn.commit()
    except Exception as ex:
        conn.rollback()
        conn.close()
        return jsonify({'error': str(ex)}), 500

    conn.close()
    return jsonify({
        'success': True,
        'mode': mode,
        'projects_mapped': len(proj_id_map),
        'holidays_inserted': h_inserted,
        'entries_inserted': e_inserted,
    })


@app.route('/api/data/download-db', methods=['GET'])
def api_download_db():
    return send_file(db.DB_PATH, as_attachment=True,
                     download_name='timelog_backup.db',
                     mimetype='application/octet-stream')


# ── Boot ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    db.init_db()

    # dev uses 5001, exe uses 5000 — prevents port clash if both run simultaneously
    PORT = 5001 if not getattr(sys, 'frozen', False) else 5000

    def _open_browser():
        import time
        time.sleep(1.2)
        webbrowser.open(f'http://localhost:{PORT}')

    threading.Thread(target=_open_browser, daemon=True).start()
    app.run(host='127.0.0.1', port=PORT, debug=False)
