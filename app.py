"""
DriveSense - local web app
---------------------------------
A login-protected local dashboard: scan a folder, review results, find
duplicates/temp files/old downloads/large files/unknown files with
explainable risk scores, delete safely to the Recycle Bin, manage
exclusions, and check the full audit history.

Run:
    python app.py

Then open http://127.0.0.1:5000 (it also opens automatically). On first run
you'll be asked to create a local username/password.
"""

import gzip
import json
import os
import threading
import time
from functools import wraps

from flask import Flask, abort, jsonify, redirect, request, send_file, session, url_for

import audit_log
import auth
import cleanup_engine
import duplicates
import exclusions as exclusions_mod
import scanner_core
from app_paths import DATA_DIR
from cleanup_ui import cleanup_page
from deletion_engine import clear_known_location, delete_file
from excel_report import build_cleanup_excel, build_excel, build_folder_excel
from exclusions_ui import exclusions_page as render_exclusions_page
from generate_report import build_html
from pages import audit_page, home_page, login_page, scan_form_page, scan_progress_page, setup_page
from pdf_report import build_pdf_summary
from restore_engine import restore_file

DATA_JSON = DATA_DIR / "storage_data.json"
XLSX_PATH = DATA_DIR / "storage_report.xlsx"
CLEANUP_JSON = DATA_DIR / "cleanup_report.json"
FILE_INDEX_JSON = DATA_DIR / "file_index.json"

app = Flask(__name__)
app.secret_key = auth.get_secret_key()

SCAN_LOCK = threading.Lock()
SCAN_STATE = {"running": False, "message": "", "error": None, "root": None}
SCAN_CONTROL = scanner_core.ScanControl()
LAST_DATA = {"data": None, "cleanup": None, "dup_stats": None, "file_index": None}


def load_last_data():
    if LAST_DATA["data"] is None and DATA_JSON.exists():
        LAST_DATA["data"] = json.loads(DATA_JSON.read_text(encoding="utf-8"))
    return LAST_DATA["data"]


def load_last_cleanup():
    if LAST_DATA["cleanup"] is None and CLEANUP_JSON.exists():
        cached = json.loads(CLEANUP_JSON.read_text(encoding="utf-8"))
        LAST_DATA["cleanup"] = cached.get("report")
        LAST_DATA["dup_stats"] = cached.get("dup_stats")
    return LAST_DATA["cleanup"], LAST_DATA["dup_stats"]


def load_file_index():
    """Every file (>= 256 KB, same granularity Cleanup Center uses) from the
    last scan - kept around so folder-scoped exports can filter it on demand
    instead of needing a rescan. Excel/PDF-report generation only, never used
    for anything safety-critical (deletion re-validates independently)."""
    if LAST_DATA["file_index"] is None and FILE_INDEX_JSON.exists():
        LAST_DATA["file_index"] = json.loads(FILE_INDEX_JSON.read_text(encoding="utf-8"))
    return LAST_DATA["file_index"] or []


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not auth.is_configured():
            return redirect(url_for("setup"))
        if not session.get("user"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


@app.route("/setup", methods=["GET", "POST"])
def setup():
    if auth.is_configured():
        return redirect(url_for("login"))
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        if not username or not password:
            error = "Username and password are required."
        elif password != confirm:
            error = "Passwords don't match."
        elif len(password) < 4:
            error = "Password must be at least 4 characters."
        else:
            auth.set_credentials(username, password)
            return redirect(url_for("login"))
    return setup_page(error)


@app.route("/login", methods=["GET", "POST"])
def login():
    if not auth.is_configured():
        return redirect(url_for("setup"))
    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if auth.verify(username, password):
            session["user"] = username
            return redirect(url_for("home"))
        error = "Incorrect username or password."
    return login_page(error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def home():
    return home_page(session["user"], load_last_data())


def run_scan_job(root):
    def progress(msg):
        SCAN_STATE["message"] = msg

    try:
        data, safe_files, file_index = scanner_core.run_scan(root, progress=progress, control=SCAN_CONTROL)
        DATA_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
        build_excel(data, safe_files, XLSX_PATH)
        LAST_DATA["data"] = data
        FILE_INDEX_JSON.write_text(json.dumps(file_index), encoding="utf-8")
        LAST_DATA["file_index"] = file_index

        progress("Detecting duplicates (hashing candidate files)...")
        dup_groups, dup_stats = duplicates.find_duplicates(file_index, progress=progress, control=SCAN_CONTROL)

        progress("Scoring cleanup recommendations...")
        report = cleanup_engine.build_cleanup_report(file_index, dup_groups, root=root)
        CLEANUP_JSON.write_text(json.dumps({"report": report, "dup_stats": dup_stats}, indent=2), encoding="utf-8")
        LAST_DATA["cleanup"] = report
        LAST_DATA["dup_stats"] = dup_stats

        audit_log.add_entry({
            "timestamp": data["scanned_at"],
            "root": data["root"],
            "file_count": data["file_count"],
            "dir_count": data["dir_count"],
            "elapsed_seconds": data["elapsed_seconds"],
            "scanned_total": data["scanned_total"],
            "safe_total": data["safe_total"],
            "critical_total": data["critical_total"],
            "duplicate_groups": report["duplicates"]["total_groups"],
            "recoverable_estimate": report["recoverable_estimate_bytes"],
            "status": "success",
        })
    except Exception as e:
        SCAN_STATE["error"] = str(e)
        audit_log.add_entry({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "root": root,
            "status": "error",
            "error": str(e),
        })
    finally:
        SCAN_STATE["running"] = False
        SCAN_CONTROL.resume()  # reset for next scan


@app.route("/scan", methods=["GET", "POST"])
@login_required
def scan():
    if request.method == "POST":
        root = request.form.get("root", "C:\\").strip() or "C:\\"
        if not os.path.isdir(root):
            return scan_form_page(root, error=f'"{root}" is not a folder that exists / is accessible.')
        with SCAN_LOCK:
            if SCAN_STATE["running"]:
                return redirect(url_for("scan_progress"))
            SCAN_STATE.update({"running": True, "message": "Starting...", "error": None, "root": root})
        SCAN_CONTROL.resume()
        threading.Thread(target=run_scan_job, args=(root,), daemon=True).start()
        return redirect(url_for("scan_progress"))
    return scan_form_page("C:\\")


@app.route("/scan/progress")
@login_required
def scan_progress():
    return scan_progress_page()


@app.route("/scan/status")
@login_required
def scan_status():
    return jsonify({
        "running": SCAN_STATE["running"],
        "message": SCAN_STATE["message"],
        "error": SCAN_STATE["error"],
        "paused": SCAN_CONTROL.paused,
    })


@app.route("/scan/pause", methods=["POST"])
@login_required
def scan_pause():
    SCAN_CONTROL.pause()
    return jsonify({"paused": True})


@app.route("/scan/resume", methods=["POST"])
@login_required
def scan_resume():
    SCAN_CONTROL.resume()
    return jsonify({"paused": False})


@app.route("/results")
@login_required
def results():
    data = load_last_data()
    if not data:
        return redirect(url_for("scan"))
    return build_html(data, excel_href=url_for("download_excel"),
                       interactive=True, clear_folder_url=url_for("clear_folder"),
                       pdf_href=url_for("download_pdf"),
                       folder_export_url=url_for("download_excel_folder"),
                       browse_url=url_for("exclusions_browse"),
                       open_path_url=url_for("open_path"))


@app.route("/clear-folder", methods=["POST"])
@login_required
def clear_folder():
    payload = request.get_json(silent=True) or {}
    label = payload.get("label")
    if not label or not payload.get("confirm"):
        return jsonify({"success": False, "reason": "Missing label or confirmation."}), 400
    return jsonify(clear_known_location(label))


@app.route("/open-path", methods=["POST"])
@login_required
def open_path():
    # Read-only: opens the path in File Explorer, same as double-clicking it
    # there. Any existing file/folder is fair game - this doesn't grant
    # access beyond what the logged-in user already has via Explorer.
    payload = request.get_json(silent=True) or {}
    path = payload.get("path", "")
    if not path or not os.path.exists(path):
        return jsonify({"success": False, "reason": "Path does not exist."}), 404
    try:
        os.startfile(path)
    except OSError as e:
        return jsonify({"success": False, "reason": str(e)}), 500
    return jsonify({"success": True})


@app.route("/download/excel")
@login_required
def download_excel():
    if not XLSX_PATH.exists():
        abort(404)
    return send_file(XLSX_PATH, as_attachment=True, download_name="storage_report.xlsx")


@app.route("/download/excel/folder", methods=["POST"])
@login_required
def download_excel_folder():
    payload = request.get_json(silent=True) or {}
    folder = (payload.get("folder") or "").strip()
    if not folder:
        return jsonify({"success": False, "reason": "Missing folder path."}), 400

    prefix = os.path.normcase(os.path.normpath(folder))
    matches = [
        f for f in load_file_index()
        if os.path.normcase(os.path.normpath(f["path"])).startswith(prefix)
    ]
    if not matches:
        return jsonify({"success": False,
                         "reason": "No indexed files (>= 256 KB) found under that folder. "
                                   "Check the path, or rescan if it's changed since the last scan."}), 404

    out_path = DATA_DIR / "folder_export.xlsx"
    build_folder_excel(folder, matches, out_path)
    return send_file(out_path, as_attachment=True, download_name="folder_export.xlsx")


@app.route("/download/excel/cleanup")
@login_required
def download_excel_cleanup():
    report, _ = load_last_cleanup()
    if not report:
        abort(404)
    out_path = DATA_DIR / "cleanup_export.xlsx"
    build_cleanup_excel(report, out_path)
    return send_file(out_path, as_attachment=True, download_name="cleanup_export.xlsx")


@app.route("/download/pdf")
@login_required
def download_pdf():
    data = load_last_data()
    if not data:
        abort(404)
    report, dup_stats = load_last_cleanup()
    out_path = DATA_DIR / "summary_report.pdf"
    build_pdf_summary(data, report, dup_stats, out_path)
    return send_file(out_path, as_attachment=True, download_name="drivesense_summary.pdf")


@app.route("/cleanup")
@login_required
def cleanup():
    report, dup_stats = load_last_cleanup()
    if not report:
        return redirect(url_for("scan"))
    return cleanup_page(report, dup_stats, exclusions_mod.load())


def _backfill_legacy_items(payload):
    # Cached cleanup_report.json files written before the virtualized Cleanup
    # Center existed have no top-level "items" list, no id/filename/category on
    # individual entries, and no group_id/id/filename on duplicate groups.
    # Reconstruct all of it so old scans still render instead of appearing
    # empty (or breaking selection/delete) until the user rescans.
    groups = (payload.get("duplicates") or {}).get("groups", [])
    if groups and "group_id" not in groups[0]:
        for g in groups:
            group_id = g["hash"]
            g["group_id"] = group_id
            g["keeper"]["filename"] = os.path.basename(g["keeper"]["path"])
            for e in g["extras"]:
                e.setdefault("id", e["path"])
                e.setdefault("filename", os.path.basename(e["path"]))
                e.setdefault("group_id", group_id)
                e.setdefault("hash", group_id)
                e.setdefault("category", "duplicate")

    if "items" in payload:
        return
    categorized = (
        ("temp_cache", payload.get("temp_cache_files", [])),
        ("old_download", payload.get("old_downloads", [])),
        ("large_file", payload.get("large_files", [])),
        ("unknown", payload.get("unknown_files", [])),
    )
    items = []
    for category, lst in categorized:
        for item in lst:
            item.setdefault("id", item["path"])
            item.setdefault("filename", os.path.basename(item["path"]))
            item.setdefault("category", category)
            items.append(item)
    payload["items"] = items


@app.route("/cleanup/data")
@login_required
def cleanup_data():
    report, dup_stats = load_last_cleanup()
    if not report:
        return jsonify({"error": "no_scan"}), 404
    payload = dict(report)
    payload["dup_stats"] = dup_stats
    payload["exclusions"] = exclusions_mod.load()
    _backfill_legacy_items(payload)

    body = json.dumps(payload).encode("utf-8")
    accepts_gzip = "gzip" in request.headers.get("Accept-Encoding", "")
    # Large scans can produce tens of MB of JSON; the dev server (used both here
    # and in the packaged exe) has been observed to drop very large plain
    # responses mid-transfer, and gzip also just makes this much faster to load.
    if accepts_gzip and len(body) > 64 * 1024:
        body = gzip.compress(body, compresslevel=6)
        resp = app.response_class(body, mimetype="application/json")
        resp.headers["Content-Encoding"] = "gzip"
        resp.headers["Content-Length"] = str(len(body))
        return resp
    return app.response_class(body, mimetype="application/json")


@app.route("/delete", methods=["POST"])
@login_required
def delete_item():
    payload = request.get_json(silent=True) or {}
    path = payload.get("path")
    if not path or not payload.get("confirm"):
        return jsonify({"success": False, "reason": "Missing path or confirmation."}), 400
    result = delete_file(
        path,
        category=payload.get("category", "personal"),
        reason=payload.get("reason", ""),
        risk_level=payload.get("risk_level", "medium"),
        confidence=payload.get("confidence", 0),
        duplicate_keeper=payload.get("duplicate_keeper"),
        override=bool(payload.get("override")),
    )
    return jsonify(result)


@app.route("/restore", methods=["POST"])
@login_required
def restore_item():
    payload = request.get_json(silent=True) or {}
    path = payload.get("path")
    if not path:
        return jsonify({"success": False, "reason": "Missing path."}), 400
    return jsonify(restore_file(path))


@app.route("/exclusions")
@login_required
def exclusions_page():
    return render_exclusions_page(exclusions_mod.load())


@app.route("/exclusions/browse", methods=["POST"])
@login_required
def exclusions_browse():
    # This is a local desktop app - the Flask process runs on the same PC as
    # the browser, so a native OS folder dialog here returns a real, accurate
    # absolute path. A browser-side <input type=file> picker can't do this:
    # browsers deliberately withhold the real filesystem path for security.
    try:
        import tkinter
        from tkinter import filedialog
        root = tkinter.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        chosen = filedialog.askdirectory(title="Choose a folder to exclude")
        root.destroy()
    except Exception as e:
        return jsonify({"success": False, "reason": str(e)}), 500
    if not chosen:
        return jsonify({"success": False, "reason": "No folder selected."})
    return jsonify({"success": True, "path": os.path.normpath(chosen)})


@app.route("/exclusions/add", methods=["POST"])
@login_required
def exclusions_add():
    path = request.form.get("path", "").strip()
    if path:
        exclusions_mod.add(path)
    return redirect(url_for("exclusions_page"))


@app.route("/exclusions/remove", methods=["POST"])
@login_required
def exclusions_remove():
    path = request.form.get("path", "").strip()
    if path:
        exclusions_mod.remove(path)
    return redirect(url_for("exclusions_page"))


@app.route("/audit")
@login_required
def audit():
    return audit_page(audit_log.list_entries(), restore_url=url_for("restore_item"))


if __name__ == "__main__":
    if not os.environ.get("STORAGE_CLEANER_NO_BROWSER"):
        import webbrowser
        threading.Timer(1.0, lambda: webbrowser.open("http://127.0.0.1:5000/")).start()
    # Flask's built-in dev server (app.run) was observed to drop very large
    # responses (the /cleanup/data payload on big scans) mid-transfer - waitress
    # is a proper WSGI server and the fix, not just the "recommended for prod" swap.
    import waitress
    waitress.serve(app, host="127.0.0.1", port=5000, threads=8)
