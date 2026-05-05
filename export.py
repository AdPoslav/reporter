import os
import io
from datetime import datetime, date as date_type

import msoffcrypto
import xlrd
from xlutils.copy import copy as xl_copy
import xlwt

TEMPLATE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'export_template', 'Vorlage_XLS-Upload.xls'
)
EXPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'exports')

_USED_COLS  = {0, 1, 3, 4, 6, 22}
_TOTAL_COLS = 42

# Custom palette slots (safe range, won't clash with standard black=8 / white=9)
_PEACH_IDX    = 55   # #FFCC99  — columns A, D
_LAVENDER_IDX = 56   # #CCCCFF  — column  G
_HEADER_IDX   = 57   # #C65911  — header background
_WHITE_IDX    = 9    # standard Excel white — header text (do NOT override)


def _open_template():
    with open(TEMPLATE_PATH, 'rb') as f:
        office = msoffcrypto.OfficeFile(f)
        office.load_key(password='VelvetSweatshop')
        buf = io.BytesIO()
        office.decrypt(buf)
    buf.seek(0)
    return xlrd.open_workbook(file_contents=buf.read(), formatting_info=True)


def _format_ltxa1(ticket, description):
    ticket      = (ticket or '').strip()
    description = (description or '').strip()
    if ticket and description:
        return f"[{ticket}] - {description}"
    if ticket:
        return f"[{ticket}]"
    return description


def _make_style(fore_colour_idx=None, num_format_str=None):
    """Thin border on all sides + optional fill colour + optional number format."""
    style = xlwt.XFStyle()

    b = xlwt.Borders()
    b.left = b.right = b.top = b.bottom = xlwt.Borders.THIN
    style.borders = b

    if fore_colour_idx is not None:
        p = xlwt.Pattern()
        p.pattern = xlwt.Pattern.SOLID_PATTERN
        p.pattern_fore_colour = fore_colour_idx
        style.pattern = p

    if num_format_str:
        style.num_format_str = num_format_str

    return style


def _excel_date_serial(iso_date_str):
    """Convert YYYY-MM-DD to Excel date serial (compatible with DD-MM-YYYY cell format)."""
    d = datetime.strptime(iso_date_str, '%Y-%m-%d').date()
    return (d - date_type(1899, 12, 30)).days


def generate_export(entries, project_name, project_code, work_id,
                    first_name, last_name, year, month):
    exportable = [
        e for e in entries
        if not e.get('is_absence') and e.get('include_in_export', 1)
    ]
    if not exportable:
        return None

    exportable.sort(key=lambda e: e['entry_date'])
    os.makedirs(EXPORTS_DIR, exist_ok=True)

    rb = _open_template()
    wb = xl_copy(rb)
    ws = wb.get_sheet(0)

    # ── Palette ────────────────────────────────────────────────────────────
    wb.set_colour_RGB(_PEACH_IDX,    0xFF, 0xCC, 0x99)
    wb.set_colour_RGB(_LAVENDER_IDX, 0xCC, 0xCC, 0xFF)
    wb.set_colour_RGB(_HEADER_IDX,   0xC6, 0x59, 0x11)

    # ── Header row ─────────────────────────────────────────────────────────
    # Build a header style and discover its registered xf_index via a temp cell
    hdr_font = xlwt.Font()
    hdr_font.colour_index = _WHITE_IDX
    hdr_font.bold = True
    hdr_align = xlwt.Alignment()
    hdr_align.wrap = xlwt.Alignment.WRAP_AT_RIGHT
    hdr_align.vert = xlwt.Alignment.VERT_CENTER

    hdr_style = xlwt.XFStyle()
    hdr_style.font = hdr_font
    hdr_style.alignment = hdr_align
    hp = xlwt.Pattern()
    hp.pattern = xlwt.Pattern.SOLID_PATTERN
    hp.pattern_fore_colour = _HEADER_IDX
    hdr_style.pattern = hp

    # Write to a scratch cell to register the style and read back the xf_index
    _SCRATCH = 60000
    ws.write(_SCRATCH, 0, '', hdr_style)
    scratch_row = ws._Worksheet__rows.get(_SCRATCH)
    hdr_xf = 0
    if scratch_row:
        scratch_cell = scratch_row._Row__cells.get(0)
        if scratch_cell and hasattr(scratch_cell, 'xf_index'):
            hdr_xf = scratch_cell.xf_index
    del ws._Worksheet__rows[_SCRATCH]

    # Set row 0 height (82 points = 82 × 20 twips) and apply header style to all cells
    ws.row(0).height = 82 * 20
    ws.row(0).height_mismatch = True
    row0 = ws._Worksheet__rows.get(0)
    if row0 and hdr_xf:
        for cell in row0._Row__cells.values():
            cell.xf_index = hdr_xf

    # ── Data styles (col → XFStyle) ────────────────────────────────────────
    col_style = {
        0:  _make_style(_PEACH_IDX,    '0'),           # A  Work-ID     Number
        1:  _make_style(None,          'DD-MM-YYYY'),  # B  WORKDATE    Date
        3:  _make_style(_PEACH_IDX,    '0'),           # D  /PPA/LSTNR  Number
        4:  _make_style(None,          '0.00'),        # E  /PPA/MENGE  Number
        6:  _make_style(_LAVENDER_IDX, '@'),           # G  RPROJ       General
        22: _make_style(None,          '@'),           # W  LTXA1       General
    }

    # ── Hide unused columns ────────────────────────────────────────────────
    for col_idx in range(_TOTAL_COLS):
        if col_idx not in _USED_COLS:
            ws.col(col_idx).hidden = True

    ws.set_panes_frozen(True)
    ws.set_horz_split_pos(1)
    ws.set_remove_splits(True)

    # ── Data rows ──────────────────────────────────────────────────────────
    for row_idx, entry in enumerate(exportable, start=1):
        date_serial = _excel_date_serial(entry['entry_date'])
        hours_val   = round(float(entry['hours']), 2)
        ltxa1       = _format_ltxa1(entry.get('ticket', ''), entry.get('description', ''))
        code        = entry.get('entry_code') or entry.get('project_main_code', '')

        try:
            work_id_val = int(work_id)
        except (ValueError, TypeError):
            work_id_val = str(work_id)

        ws.write(row_idx,  0, work_id_val,  col_style[0])
        ws.write(row_idx,  1, date_serial,  col_style[1])
        ws.write(row_idx,  3, 81001,        col_style[3])
        ws.write(row_idx,  4, hours_val,    col_style[4])
        ws.write(row_idx,  6, str(code),    col_style[6])
        ws.write(row_idx, 22, ltxa1,        col_style[22])

    # ── Remove template rows below our data ────────────────────────────────
    n = len(exportable)
    rows_dict = ws._Worksheet__rows
    for k in [k for k in rows_dict if k > n]:
        del rows_dict[k]

    full_name = f"{first_name} {last_name}".strip()
    filename  = f"{full_name}_{project_code}_{month:02d}_{year}.xls"
    filepath  = os.path.join(EXPORTS_DIR, filename)
    wb.save(filepath)
    return filepath, filename
