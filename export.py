import os
import xlwt
from datetime import datetime

EXPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'exports')

# All 41 column headers matching Vorlage_XLS-Upload.xls (Tabelle1)
_HEADERS = [
    'Work-ID', 'WORKDATE', 'SKOSTL', '/PPA/LSTNR', '/PPA/MENGE',
    'RKOSTL', 'RPROJ', 'RAUFNR', 'RAUFPL', 'RAPLZL',
    'RKDAUF', 'RKDPOS', 'EXTSYSTEM', 'EXTAPPLICATION', 'EXTDOCUMENTNO',
    'AWART', 'WAERS', 'BEGUZ', 'ENDUZ', '/PPA/ACTVY',
    '/PPA/PLOSP', '/PPA/TICNR', 'LTXA1', '/PPA/TAXKM', '/PPA/NFAKT1',
    '/PPA/MAFAZ1', '/PPA/MAKTX1', '/PPA/MENGE1', '/PPA/PREIS1', '/PPA/WERT1',
    '/PPA/WAERS1', '/PPA/MAFAZ2', '/PPA/MAKTX2', '/PPA/PREIS2', '/PPA/WERT2',
    '/PPA/WAERS2', '/PPA/ANSNR', 'RNPLNR', 'SBELN', 'SBELP', 'LSTNR',
]


def _format_ltxa1(ticket, description):
    ticket = (ticket or '').strip()
    description = (description or '').strip()
    if ticket:
        return f"[{ticket}] {description}".strip()
    return description


def generate_export(entries, project_name, work_id, last_name, year, month):
    """
    Generate an .xls export file for one project from a list of entries.
    Returns (filepath, filename) or None if no exportable entries.
    """
    exportable = [
        e for e in entries
        if not e.get('is_absence') and e.get('include_in_export', 1)
    ]
    if not exportable:
        return None

    os.makedirs(EXPORTS_DIR, exist_ok=True)

    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet('Tabelle1')

    # Header style
    hdr_style = xlwt.XFStyle()
    hdr_font = xlwt.Font()
    hdr_font.bold = True
    hdr_style.font = hdr_font

    # Number style for hours
    num_style = xlwt.XFStyle()
    num_style.num_format_str = '0.00'

    # Write headers in row 0
    for col, header in enumerate(_HEADERS):
        ws.write(0, col, header, hdr_style)

    # Write data rows starting at row 1
    for row_idx, entry in enumerate(exportable, start=1):
        date_obj = datetime.strptime(entry['entry_date'], '%Y-%m-%d')
        date_str = date_obj.strftime('%d-%m-%Y')
        hours_val = round(float(entry['hours']), 2)
        ltxa1 = _format_ltxa1(entry.get('ticket', ''), entry.get('description', ''))
        entry_code = entry.get('entry_code') or entry.get('project_main_code', '')

        ws.write(row_idx, 0, work_id)               # A  Work-ID
        ws.write(row_idx, 1, date_str)               # B  WORKDATE  DD-MM-YYYY
        # C  SKOSTL  — empty
        ws.write(row_idx, 3, 81001)                  # D  /PPA/LSTNR  static 81001
        ws.write(row_idx, 4, hours_val, num_style)   # E  /PPA/MENGE
        # F  RKOSTL  — empty
        ws.write(row_idx, 6, entry_code)             # G  RPROJ
        # H–V  — empty
        ws.write(row_idx, 22, ltxa1)                 # W  LTXA1
        # X–Y  — empty
        ws.write(row_idx, 25, 'X')                   # Z  /PPA/MAFAZ1  always X for external

    safe_name = (
        project_name
        .replace(' ', '_')
        .replace('/', '_')
        .replace('\\', '_')
        .replace(':', '_')
    )
    filename = f"{last_name}_{month:02d}_{year}_{safe_name}.xls"
    filepath = os.path.join(EXPORTS_DIR, filename)
    wb.save(filepath)
    return filepath, filename
