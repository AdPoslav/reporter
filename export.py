import os
import io
from datetime import datetime

import msoffcrypto
import xlrd
from xlutils.copy import copy as xl_copy
import xlwt

TEMPLATE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'export_template', 'Vorlage_XLS-Upload.xls'
)
EXPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'exports')

# Columns (0-indexed) that actually receive data — all others will be hidden
_USED_COLS = {0, 1, 3, 4, 6, 22, 25}
# Template has 42 columns (A–AP)
_TOTAL_COLS = 42


def _open_template():
    """Decrypt the XOR-protected template and return an xlrd workbook."""
    with open(TEMPLATE_PATH, 'rb') as f:
        office = msoffcrypto.OfficeFile(f)
        office.load_key(password='VelvetSweatshop')
        buf = io.BytesIO()
        office.decrypt(buf)
    buf.seek(0)
    return xlrd.open_workbook(file_contents=buf.read(), formatting_info=True)


def _format_ltxa1(ticket, description):
    ticket = (ticket or '').strip()
    description = (description or '').strip()
    if ticket:
        return f"[{ticket}] {description}".strip()
    return description


def generate_export(entries, project_name, project_code, work_id, first_name, last_name, year, month):
    """
    Copy the XLS template, fill data rows, hide empty columns.
    Returns (filepath, filename) or None if nothing to export.
    """
    exportable = [
        e for e in entries
        if not e.get('is_absence') and e.get('include_in_export', 1)
    ]
    if not exportable:
        return None

    os.makedirs(EXPORTS_DIR, exist_ok=True)

    # Open template and create a writable copy
    rb = _open_template()
    wb = xl_copy(rb)
    ws = wb.get_sheet(0)

    # Hide all columns that stay empty so the file looks clean
    for col_idx in range(_TOTAL_COLS):
        if col_idx not in _USED_COLS:
            ws.col(col_idx).hidden = True

    # Style for the hours cell (decimal, 2 places)
    num_style = xlwt.XFStyle()
    num_style.num_format_str = '0.00'

    for row_idx, entry in enumerate(exportable, start=1):
        date_str  = datetime.strptime(entry['entry_date'], '%Y-%m-%d').strftime('%d-%m-%Y')
        hours_val = round(float(entry['hours']), 2)
        ltxa1     = _format_ltxa1(entry.get('ticket', ''), entry.get('description', ''))
        code      = entry.get('entry_code') or entry.get('project_main_code', '')

        ws.write(row_idx,  0, work_id)             # A  Work-ID
        ws.write(row_idx,  1, date_str)             # B  WORKDATE  DD-MM-YYYY
        # C  SKOSTL  — empty / hidden
        ws.write(row_idx,  3, 81001)                # D  /PPA/LSTNR  81001 static
        ws.write(row_idx,  4, hours_val, num_style) # E  /PPA/MENGE  0.00
        # F  RKOSTL  — empty / hidden
        ws.write(row_idx,  6, code)                 # G  RPROJ
        # H–V  — empty / hidden
        ws.write(row_idx, 22, ltxa1)                # W  LTXA1
        # X–Y  — empty / hidden
        ws.write(row_idx, 25, 'X')                  # Z  /PPA/MAFAZ1  always X
        # AA–AP — empty / hidden

    full_name = f"{first_name} {last_name}".strip()
    filename = f"{full_name}_{project_code}_{month:02d}_{year}.xls"
    filepath = os.path.join(EXPORTS_DIR, filename)
    wb.save(filepath)
    return filepath, filename
