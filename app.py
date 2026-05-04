import os
import threading
import webbrowser
import datetime

from flask import Flask, render_template, request, jsonify, send_file

import database as db
import export as exp

app = Flask(__name__)
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
    )


# ── Settings API ──────────────────────────────────────────────────────────────

@app.route('/api/settings', methods=['GET'])
def api_get_settings():
    return jsonify({
        'work_id':    db.get_setting('work_id'),
        'first_name': db.get_setting('first_name'),
        'last_name':  db.get_setting('last_name'),
    })


@app.route('/api/settings', methods=['POST'])
def api_save_settings():
    data = request.get_json()
    db.set_setting('work_id',    data.get('work_id', ''))
    db.set_setting('first_name', data.get('first_name', ''))
    db.set_setting('last_name',  data.get('last_name', ''))
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


@app.route('/api/projects/<int:pid>/codes', methods=['POST'])
def api_create_code(pid):
    data = request.get_json()
    cid = db.create_project_code(pid, data['code'].strip(), data['label'].strip())
    return jsonify({'id': cid, 'success': True})


@app.route('/api/projects/<int:pid>/codes/<int:cid>', methods=['PUT'])
def api_update_code(pid, cid):
    data = request.get_json()
    db.update_project_code(cid, data['code'].strip(), data['label'].strip())
    return jsonify({'success': True})


@app.route('/api/projects/<int:pid>/codes/<int:cid>', methods=['DELETE'])
def api_delete_code(pid, cid):
    db.delete_project_code(cid)
    return jsonify({'success': True})


# ── Entries API ───────────────────────────────────────────────────────────────

@app.route('/api/entries', methods=['GET'])
def api_entries():
    filters = {k: v for k, v in {
        'date_from':   request.args.get('date_from'),
        'date_to':     request.args.get('date_to'),
        'project_id':  request.args.get('project_id'),
        'code_id':     request.args.get('code_id'),
        'ticket':      request.args.get('ticket'),
        'description': request.args.get('description'),
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


# ── Export API ────────────────────────────────────────────────────────────────

@app.route('/api/export', methods=['POST'])
def api_export():
    d     = request.get_json()
    year  = int(d['year'])
    month = int(d['month'])

    work_id   = db.get_setting('work_id')
    last_name = db.get_setting('last_name')
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
            work_id=work_id,
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


# ── Boot ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    db.init_db()

    def _open_browser():
        import time
        time.sleep(1.2)
        webbrowser.open('http://localhost:5000')

    threading.Thread(target=_open_browser, daemon=True).start()
    app.run(host='127.0.0.1', port=5000, debug=False)
