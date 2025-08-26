# app/services/tracker.py
from __future__ import annotations
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, cast

from openpyxl import load_workbook
from openpyxl.workbook import Workbook as XLWorkbook
from openpyxl.worksheet.worksheet import Worksheet

HEADERS = [
    "company", "role", "date_applied", "job_url", "source", "ats_type",
    "confirmation_number", "status", "resume_version", "notes"
]
SHEET_NAME = "Applications"


def _ensure_workbook(path: Path) -> None:
    """Create workbook + sheet + headers if missing."""
    if not path.exists():
        wb = XLWorkbook()
        ws = cast(Worksheet, wb.active)   # <-- removes the editor warning
        ws.title = SHEET_NAME
        ws.append(HEADERS)
        wb.save(str(path))
        return

    wb = load_workbook(str(path))
    if SHEET_NAME not in wb.sheetnames:
        ws = wb.create_sheet(SHEET_NAME)
        ws.append(HEADERS)
        wb.save(str(path))
    else:
        ws = wb[SHEET_NAME]
        if ws.max_row == 1 and [c.value for c in ws[1]] != HEADERS:
            ws.delete_rows(1, ws.max_row)
            ws.append(HEADERS)
            wb.save(str(path))


def log_to_excel(xlsx_path: str | Path, row: Dict[str, Any]) -> str:
    """Append an application entry and return the XLSX absolute path."""
    p = Path(xlsx_path).resolve()
    p.parent.mkdir(parents=True, exist_ok=True)

    _ensure_workbook(p)

    wb = load_workbook(str(p))
    ws: Worksheet = wb[SHEET_NAME]
    ws.append([
        row.get("company", ""),
        row.get("role", ""),
        row.get("date_applied", datetime.utcnow().isoformat(timespec="seconds")),
        row.get("job_url", ""),
        row.get("source", ""),
        row.get("ats_type", ""),
        row.get("confirmation_number", ""),
        row.get("status", ""),
        row.get("resume_version", ""),
        row.get("notes", "")
    ])
    wb.save(str(p))
    return str(p)
