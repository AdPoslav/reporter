import os
import io
import struct
from datetime import datetime, date as date_type

import msoffcrypto
import xlrd
import xlwt
from xlwt import BIFFRecords as B  # noqa: F401  (kept for callers/extension)
from xlutils.copy import copy as xl_copy

TEMPLATE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'export_template', 'Vorlage_XLS-Upload.xls'
)
EXPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'exports')

# Columns kept visible in the export; everything else is hidden.
_USED_COLS  = {0, 1, 3, 4, 6, 22}
_TOTAL_COLS = 41          # template spans A:AO (41 columns)

# Columns that need their template-defined data style reused. The actual XF
# index inside the xlwt workbook is discovered at runtime — xlutils remaps the
# template's XFs into a new index space when copying.
_DATA_STYLE_COLS = (0, 1, 3, 4, 6, 22)

# AutoFilter range: rows 0..nrows (header + data), cols 0..40 (A..AO)
_AF_FIRST_COL = 0
_AF_LAST_COL  = _TOTAL_COLS - 1


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


def _excel_date_serial(iso_date_str):
    d = datetime.strptime(iso_date_str, '%Y-%m-%d').date()
    return (d - date_type(1899, 12, 30)).days


def _write_cell(ws, row, col, value, xf_index):
    """Write a cell and force it to use one of the template's existing XF indexes,
    so the template's colour/format/border survives untouched."""
    ws.write(row, col, value)
    cell = ws._Worksheet__rows[row]._Row__cells[col]
    cell.xf_idx = xf_index


def _install_autofilter(wb, sheet_idx, last_row):
    """Inject SUPBOOK + EXTERNSHEET + NAME(_FilterDatabase) at workbook level,
    plus an AutoFilterInfo record on the sheet, so Excel shows the clickable
    filter dropdowns over A1:AO{last_row+1}.

    xlwt has no public API for AutoFilter, so we patch the two record builders
    that compose the BIFF stream.
    """
    sheet = wb.get_sheet(sheet_idx)

    # ── _FilterDatabase NAME + supporting link records ─────────────────────
    # RPN: tArea3d (0x3B) + ixti(2) + rwFirst(2) + rwLast(2) + colFirst(2) + colLast(2)
    rpn = struct.pack('<BHHHHH',
                      0x3B, 0,
                      0, last_row,
                      _AF_FIRST_COL, _AF_LAST_COL)

    # NAME record for builtin _FilterDatabase (0x0D). Built manually because
    # xlwt.BIFFRecords.NameRecord is Py2-only (passes str to struct '%ds').
    # Layout: H(opts) B(kb) B(uname_len) H(sz_rpn) H(reserved) H(sheet_1based)
    #         B(lm) B(ld) B(lh) B(ls) B(uflag) B(name_byte) + rpn
    name_payload = struct.pack(
        '<HBBHHHBBBBBB',
        0x0021,          # fBuiltin | fHidden
        0x00,            # keyboard shortcut
        0x01,            # uname_len
        len(rpn),
        0x0000,          # reserved
        sheet_idx + 1,   # 1-based local sheet index
        0, 0, 0, 0,      # lm, ld, lh, ls
        0x00,            # unicode flag (compressed)
        0x0D,            # builtin code: _FilterDatabase
    ) + rpn
    name_rec = struct.pack('<HH', 0x0018, len(name_payload)) + name_payload

    n_sheets = len(wb._Workbook__worksheets)
    supbook_rec     = B.InternalReferenceSupBookRecord(n_sheets).get()
    externsheet_rec = B.ExternSheetRecord([(0, sheet_idx, sheet_idx)]).get()

    def _patched_all_links(self):
        return supbook_rec + externsheet_rec + name_rec

    wb._Workbook__all_links_rec = _patched_all_links.__get__(wb, type(wb))

    # ── AutoFilterInfo record on the sheet ─────────────────────────────────
    # 0x009D, length 2, payload = number of dropdown columns.
    n_filter_cols = _AF_LAST_COL - _AF_FIRST_COL + 1
    auto_filter_info = struct.pack('<HHH', 0x009D, 2, n_filter_cols)

    orig_get_biff_data = sheet.get_biff_data
    eof_marker = struct.pack('<HH', 0x000A, 0)

    def _patched_sheet_biff():
        data = orig_get_biff_data()
        if data.endswith(eof_marker):
            return data[:-len(eof_marker)] + auto_filter_info + eof_marker
        return data + auto_filter_info

    sheet.get_biff_data = _patched_sheet_biff


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

    # Snapshot the xf_idx that xlutils assigned to each used column on the
    # template's first data row. Reusing these on every output row keeps the
    # template's exact colours, fonts, borders and number formats intact.
    template_row1 = ws._Worksheet__rows[1]
    data_xf = {c: template_row1._Row__cells[c].xf_idx for c in _DATA_STYLE_COLS}

    # ── Hide unused columns (header colours of active cols stay intact) ───
    for col_idx in range(_TOTAL_COLS):
        if col_idx not in _USED_COLS:
            ws.col(col_idx).hidden = True

    ws.set_panes_frozen(True)
    ws.set_horz_split_pos(1)
    ws.set_remove_splits(True)

    # ── Data rows ──────────────────────────────────────────────────────────
    try:
        work_id_val = int(work_id)
    except (ValueError, TypeError):
        work_id_val = str(work_id)

    for row_idx, entry in enumerate(exportable, start=1):
        date_serial = _excel_date_serial(entry['entry_date'])
        hours_val   = round(float(entry['hours']), 2)
        ltxa1       = _format_ltxa1(entry.get('ticket', ''), entry.get('description', ''))
        code        = entry.get('entry_code') or entry.get('project_main_code', '')

        _write_cell(ws, row_idx,  0, work_id_val, data_xf[0])
        _write_cell(ws, row_idx,  1, date_serial, data_xf[1])
        _write_cell(ws, row_idx,  3, 81001,       data_xf[3])
        _write_cell(ws, row_idx,  4, hours_val,   data_xf[4])
        _write_cell(ws, row_idx,  6, str(code),   data_xf[6])
        _write_cell(ws, row_idx, 22, ltxa1,       data_xf[22])

    # ── Drop the template's leftover blank rows below our data ─────────────
    n = len(exportable)
    rows_dict = ws._Worksheet__rows
    for k in [k for k in rows_dict if k > n]:
        del rows_dict[k]

    # ── Re-attach the AutoFilter on the new data range ─────────────────────
    _install_autofilter(wb, 0, last_row=n)

    full_name = f"{first_name} {last_name}".strip()
    filename  = f"{full_name}_{project_code}_{month:02d}_{year}.xls"
    filepath  = os.path.join(EXPORTS_DIR, filename)
    wb.save(filepath)
    return filepath, filename
