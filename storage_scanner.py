"""
Storage Scanner & Cleanup Dashboard (CLI)
------------------------------------------
Scans a folder (default: C:\\), aggregates storage usage by folder and file
type, finds the largest safe-to-delete files/folders, checks common "junk"
locations, and renders a self-contained HTML dashboard + Excel file-wise
analysis.

Run:
    python storage_scanner.py [folder]

No admin rights required. Folders you don't have permission to read are
skipped and counted, so totals are a best-effort lower bound on protected
system areas (e.g. System Volume Information).

For the login-protected web app with scan history, use `python app.py` instead.
"""

import json
import sys
import webbrowser

from app_paths import DATA_DIR
from scanner_core import run_scan


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "C:\\"

    data, safe_files, file_index = run_scan(root, progress=print)
    print(f"Files: {data['file_count']:,}  Dirs: {data['dir_count']:,}  "
          f"Skipped (no access): {data['inaccessible']:,}")

    out_dir = DATA_DIR
    json_path = out_dir / "storage_data.json"
    json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Raw data written to {json_path}")

    from excel_report import build_excel
    xlsx_path = out_dir / "storage_report.xlsx"
    build_excel(data, safe_files, xlsx_path)
    print(f"Excel file-wise analysis written to {xlsx_path}")

    from generate_report import build_html
    html = build_html(data)
    html_path = out_dir / "storage_report.html"
    html_path.write_text(html, encoding="utf-8")
    print(f"Dashboard written to {html_path}")

    webbrowser.open(html_path.resolve().as_uri())


if __name__ == "__main__":
    main()
