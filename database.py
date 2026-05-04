import sqlite3
import os
import calendar
import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'timelog.db')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS project_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            code TEXT NOT NULL,
            label TEXT NOT NULL,
            sort_order INTEGER DEFAULT 0,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS time_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_date TEXT NOT NULL,
            project_id INTEGER,
            project_code_id INTEGER,
            hours REAL NOT NULL,
            ticket TEXT DEFAULT '',
            description TEXT DEFAULT '',
            is_absence INTEGER DEFAULT 0,
            absence_type TEXT DEFAULT '',
            include_in_export INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL,
            FOREIGN KEY (project_code_id) REFERENCES project_codes(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS holidays (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day INTEGER NOT NULL,
            month INTEGER NOT NULL,
            year INTEGER,
            description TEXT NOT NULL DEFAULT '',
            is_recurring INTEGER DEFAULT 1
        );

        INSERT OR IGNORE INTO settings (key, value) VALUES ('work_id', '');
        INSERT OR IGNORE INTO settings (key, value) VALUES ('first_name', '');
        INSERT OR IGNORE INTO settings (key, value) VALUES ('last_name', '');
    ''')
    conn.commit()
    conn.close()


def get_setting(key):
    conn = get_db()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row['value'] if row else ''


def set_setting(key, value):
    conn = get_db()
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()


def get_all_projects():
    conn = get_db()
    projects = conn.execute("SELECT * FROM projects ORDER BY name").fetchall()
    result = []
    for p in projects:
        codes = conn.execute(
            "SELECT * FROM project_codes WHERE project_id = ? ORDER BY sort_order, label",
            (p['id'],)
        ).fetchall()
        result.append({
            'id': p['id'],
            'name': p['name'],
            'code': p['code'],
            'created_at': p['created_at'],
            'codes': [dict(c) for c in codes]
        })
    conn.close()
    return result


def get_project(project_id):
    conn = get_db()
    p = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    conn.close()
    return dict(p) if p else None


def create_project(name, code):
    conn = get_db()
    cursor = conn.execute("INSERT INTO projects (name, code) VALUES (?, ?)", (name, code))
    project_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return project_id


def update_project(project_id, name, code):
    conn = get_db()
    conn.execute("UPDATE projects SET name = ?, code = ? WHERE id = ?", (name, code, project_id))
    conn.commit()
    conn.close()


def delete_project(project_id):
    conn = get_db()
    conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()


def create_project_code(project_id, code, label, sort_order=0):
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO project_codes (project_id, code, label, sort_order) VALUES (?, ?, ?, ?)",
        (project_id, code, label, sort_order)
    )
    code_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return code_id


def update_project_code(code_id, code, label):
    conn = get_db()
    conn.execute("UPDATE project_codes SET code = ?, label = ? WHERE id = ?", (code, label, code_id))
    conn.commit()
    conn.close()


def delete_project_code(code_id):
    conn = get_db()
    conn.execute("DELETE FROM project_codes WHERE id = ?", (code_id,))
    conn.commit()
    conn.close()


def get_entries(filters=None):
    conn = get_db()
    query = '''
        SELECT te.*, p.name AS project_name, p.code AS project_main_code,
               pc.code AS entry_code, pc.label AS entry_label
        FROM time_entries te
        LEFT JOIN projects p ON te.project_id = p.id
        LEFT JOIN project_codes pc ON te.project_code_id = pc.id
        WHERE 1=1
    '''
    params = []
    if filters:
        if filters.get('date_from'):
            query += " AND te.entry_date >= ?"
            params.append(filters['date_from'])
        if filters.get('date_to'):
            query += " AND te.entry_date <= ?"
            params.append(filters['date_to'])
        if filters.get('project_id'):
            query += " AND te.project_id = ?"
            params.append(filters['project_id'])
        if filters.get('code_id'):
            query += " AND te.project_code_id = ?"
            params.append(filters['code_id'])
        if filters.get('ticket'):
            query += " AND te.ticket LIKE ?"
            params.append(f"%{filters['ticket']}%")
        if filters.get('description'):
            query += " AND te.description LIKE ?"
            params.append(f"%{filters['description']}%")
        if filters.get('is_absence') is not None:
            query += " AND te.is_absence = ?"
            params.append(filters['is_absence'])
    query += " ORDER BY te.entry_date DESC, te.created_at DESC"
    entries = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(e) for e in entries]


def get_entry(entry_id):
    conn = get_db()
    entry = conn.execute('''
        SELECT te.*, p.name AS project_name, pc.code AS entry_code, pc.label AS entry_label
        FROM time_entries te
        LEFT JOIN projects p ON te.project_id = p.id
        LEFT JOIN project_codes pc ON te.project_code_id = pc.id
        WHERE te.id = ?
    ''', (entry_id,)).fetchone()
    conn.close()
    return dict(entry) if entry else None


def create_entry(entry_date, project_id, project_code_id, hours, ticket='',
                 description='', is_absence=0, absence_type='', include_in_export=1):
    conn = get_db()
    cursor = conn.execute('''
        INSERT INTO time_entries
        (entry_date, project_id, project_code_id, hours, ticket, description,
         is_absence, absence_type, include_in_export)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (entry_date, project_id, project_code_id, hours, ticket, description,
          is_absence, absence_type, include_in_export))
    entry_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return entry_id


def update_entry(entry_id, entry_date, project_id, project_code_id, hours, ticket='',
                 description='', is_absence=0, absence_type='', include_in_export=1):
    conn = get_db()
    conn.execute('''
        UPDATE time_entries SET
        entry_date=?, project_id=?, project_code_id=?, hours=?,
        ticket=?, description=?, is_absence=?, absence_type=?, include_in_export=?
        WHERE id=?
    ''', (entry_date, project_id, project_code_id, hours, ticket, description,
          is_absence, absence_type, include_in_export, entry_id))
    conn.commit()
    conn.close()


def delete_entry(entry_id):
    conn = get_db()
    conn.execute("DELETE FROM time_entries WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()


def toggle_export_flag(entry_ids, value):
    if not entry_ids:
        return
    conn = get_db()
    placeholders = ','.join(['?' for _ in entry_ids])
    conn.execute(
        f"UPDATE time_entries SET include_in_export = ? WHERE id IN ({placeholders})",
        [value] + list(entry_ids)
    )
    conn.commit()
    conn.close()


# ── Holidays ──────────────────────────────────────────────────────────────────

def get_all_holidays():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM holidays ORDER BY month, day, year NULLS FIRST"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_holiday(day, month, year, description, is_recurring):
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO holidays (day, month, year, description, is_recurring) VALUES (?,?,?,?,?)",
        (day, month, year if not is_recurring else None, description, 1 if is_recurring else 0)
    )
    hid = cursor.lastrowid
    conn.commit()
    conn.close()
    return hid


def update_holiday(hid, day, month, year, description, is_recurring):
    conn = get_db()
    conn.execute(
        "UPDATE holidays SET day=?, month=?, year=?, description=?, is_recurring=? WHERE id=?",
        (day, month, year if not is_recurring else None, description, 1 if is_recurring else 0, hid)
    )
    conn.commit()
    conn.close()


def delete_holiday(hid):
    conn = get_db()
    conn.execute("DELETE FROM holidays WHERE id=?", (hid,))
    conn.commit()
    conn.close()


def _holiday_days_in_range(date_from: datetime.date, date_to: datetime.date) -> int:
    """Count how many holidays fall on working days within [date_from, date_to]."""
    conn = get_db()
    holidays = conn.execute("SELECT day, month, year, is_recurring FROM holidays").fetchall()
    conn.close()

    count = 0
    current = date_from
    while current <= date_to:
        if current.weekday() < 5:  # working day
            for h in holidays:
                if h['month'] == current.month and h['day'] == current.day:
                    if h['is_recurring'] or h['year'] == current.year:
                        count += 1
                        break
        current += datetime.timedelta(days=1)
    return count


# ── Stats ──────────────────────────────────────────────────────────────────────

def get_month_stats(year, month):
    month_str = f"{year:04d}-{month:02d}"
    conn = get_db()

    row = conn.execute('''
        SELECT
            COALESCE(SUM(CASE WHEN is_absence=0 AND include_in_export=1 THEN hours ELSE 0 END),0) AS export_h,
            COALESCE(SUM(CASE WHEN is_absence=0 AND include_in_export=0 THEN hours ELSE 0 END),0) AS no_export_h,
            COALESCE(SUM(CASE WHEN is_absence=1                          THEN hours ELSE 0 END),0) AS absence_h
        FROM time_entries WHERE entry_date LIKE ?
    ''', (f"{month_str}%",)).fetchone()

    export_hours   = row['export_h']
    no_export_hours = row['no_export_h']
    month_hours    = export_hours + no_export_hours
    absence_hours  = row['absence_h']

    num_days = calendar.monthrange(year, month)[1]
    working_days = sum(
        1 for d in range(1, num_days + 1)
        if datetime.date(year, month, d).weekday() < 5
    )

    date_from = datetime.date(year, month, 1)
    date_to   = datetime.date(year, month, num_days)
    holiday_days = _holiday_days_in_range(date_from, date_to)
    effective_working_days = max(working_days - holiday_days, 0)
    total_fund = effective_working_days * 8

    project_stats = conn.execute('''
        SELECT p.id, p.name, COALESCE(SUM(te.hours),0) AS total_hours
        FROM projects p
        LEFT JOIN time_entries te ON te.project_id = p.id
            AND te.entry_date LIKE ? AND te.is_absence = 0
        GROUP BY p.id, p.name
        HAVING total_hours > 0
        ORDER BY total_hours DESC
    ''', (f"{month_str}%",)).fetchall()

    conn.close()
    return {
        'month_hours':    round(month_hours, 2),
        'export_hours':   round(export_hours, 2),
        'no_export_hours': round(no_export_hours, 2),
        'absence_hours':  round(absence_hours, 2),
        'total_fund':     total_fund,
        'remaining':      round(total_fund - month_hours - absence_hours, 2),
        'working_days':   effective_working_days,
        'holiday_days':   holiday_days,
        'project_stats':  [dict(p) for p in project_stats]
    }


def get_week_stats(year, week):
    jan4 = datetime.date(year, 1, 4)
    week_start = jan4 + datetime.timedelta(weeks=week - 1, days=-jan4.weekday())
    week_end = week_start + datetime.timedelta(days=6)
    date_from = week_start.strftime('%Y-%m-%d')
    date_to   = week_end.strftime('%Y-%m-%d')

    working_days = sum(
        1 for d in range(7)
        if (week_start + datetime.timedelta(days=d)).weekday() < 5
    )
    holiday_days = _holiday_days_in_range(week_start, week_end)
    effective_working_days = max(working_days - holiday_days, 0)
    total_fund = effective_working_days * 8

    conn = get_db()
    row = conn.execute('''
        SELECT
            COALESCE(SUM(CASE WHEN is_absence=0 AND include_in_export=1 THEN hours ELSE 0 END),0) AS export_h,
            COALESCE(SUM(CASE WHEN is_absence=0 AND include_in_export=0 THEN hours ELSE 0 END),0) AS no_export_h,
            COALESCE(SUM(CASE WHEN is_absence=1                          THEN hours ELSE 0 END),0) AS absence_h
        FROM time_entries WHERE entry_date>=? AND entry_date<=?
    ''', (date_from, date_to)).fetchone()
    conn.close()

    export_hours    = row['export_h']
    no_export_hours = row['no_export_h']
    week_hours      = export_hours + no_export_hours
    absence_hours   = row['absence_h']

    return {
        'week_hours':     round(week_hours, 2),
        'export_hours':   round(export_hours, 2),
        'no_export_hours': round(no_export_hours, 2),
        'absence_hours':  round(absence_hours, 2),
        'total_fund':     total_fund,
        'remaining':      round(total_fund - week_hours - absence_hours, 2),
        'working_days':   effective_working_days,
        'holiday_days':   holiday_days,
        'week_start':     date_from,
        'week_end':       date_to
    }
