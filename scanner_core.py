"""
Core scanning engine, shared by the CLI script (storage_scanner.py) and the
web app (app.py). Walks a folder, aggregates storage usage by folder and file
type, builds an index of "safe" (non-critical, user-owned) files for the
cleanup engine to classify, and (when the scanned folder is a drive root)
checks common junk/cache locations.

Safety model: files under Windows/Program Files/ProgramData/AppData/recovery/
AV-sandbox folders, OS-reserved root files, and DLL/SYS/OCX/DRV/VXD component
files anywhere are treated as protected and are never added to the safe file
index, regardless of exclusions or anything else downstream.
"""

import heapq
import os
import shutil
import threading
import time
from pathlib import Path

import exclusions as exclusions_mod

MAX_DEPTH_FOR_DIR_SIZES = 4   # how deep below the scan root to record individual folder sizes
TOP_FILES_COUNT = 30
TOP_FOLDERS_COUNT = 15
SKIP_DIR_NAMES = {"System Volume Information", "$Recycle.Bin"}

# Anything under a folder with one of these names (case-insensitive) is treated as
# owned by Windows or an installed application, not something to suggest deleting.
CRITICAL_DIR_NAMES = {
    "windows", "program files", "program files (x86)", "programdata",
    "system volume information", "recovery", "perflogs", "msocache",
    "$winreagent", "$sysreset", "config.msi", "windowsapps", "appdata",
    "$recycle.bin", "boot", "efi", "drivers", "system32", "syswow64",
}
# Root-level OS files that must never be suggested for deletion.
ROOT_SYSTEM_FILES = {
    "pagefile.sys", "hiberfil.sys", "swapfile.sys", "dumpstack.log.tmp",
    "bootmgr", "bootnxt", "bootsect.bak",
}
# File types that are OS/application components wherever they're found.
CRITICAL_EXTENSIONS = {".dll", ".sys", ".ocx", ".drv", ".vxd"}

EXCEL_MIN_SIZE = 1 * 1024 * 1024  # only list safe files >= 1 MB in the Excel export
EXCEL_MAX_ROWS = 5000

# Minimum size for a file to enter the in-memory "safe file index" that powers
# duplicate detection, large-file/old-download/unknown flagging, and search.
# Below this, files are counted in totals but not indexed individually - too
# numerous and too little storage impact to be worth tracking per-file.
FILE_INDEX_MIN_SIZE = 256 * 1024  # 256 KB

EXTENSION_CATEGORIES = {
    "Documents": {".doc", ".docx", ".pdf", ".txt", ".xls", ".xlsx", ".ppt",
                  ".pptx", ".csv", ".md", ".rtf", ".odt", ".ods", ".odp", ".xps"},
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp",
               ".heic", ".tiff", ".tif", ".ico", ".raw", ".cr2", ".nef"},
    "Videos": {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm",
               ".m4v", ".mpg", ".mpeg", ".3gp"},
    "Audio": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a", ".opus"},
    "Archives": {".zip", ".rar", ".7z", ".tar", ".gz", ".iso", ".bz2", ".xz", ".cab"},
    "Programs & Installers": {".exe", ".msi", ".msix", ".appx"},
    "Code & Dev": {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp",
                   ".h", ".hpp", ".cs", ".html", ".css", ".json", ".xml", ".sql",
                   ".go", ".rb", ".php", ".ipynb", ".yml", ".yaml", ".sh", ".ps1"},
    "System & Libraries": {".dll", ".sys", ".log", ".dat", ".bak", ".tmp", ".cache"},
}
EXT_TO_CATEGORY = {ext: cat for cat, exts in EXTENSION_CATEGORIES.items() for ext in exts}

# Specific, well-known cache/temp folders that are safe-to-delete even though
# they live under otherwise-protected trees (AppData, Windows). These are an
# explicit allowlist override of the broader "appdata"/"windows" critical
# rule above - nothing else under those trees is affected.
def _cache_roots():
    home = Path.home()
    return [
        os.path.normcase(os.path.normpath(str(p))) for p in [
            home / "AppData" / "Local" / "Temp",
            home / "AppData" / "Local" / "Microsoft" / "Windows" / "Explorer",
            home / "AppData" / "Local" / "Google" / "Chrome" / "User Data" / "Default" / "Cache",
            home / "AppData" / "Local" / "Microsoft" / "Edge" / "User Data" / "Default" / "Cache",
            Path("C:/Windows/Temp"),
            Path("C:/Windows/SoftwareDistribution/Download"),
        ]
    ]


CACHE_ROOTS = _cache_roots()


def is_cache_zone_path(path):
    p = os.path.normcase(os.path.normpath(path))
    return any(p == root or p.startswith(root + os.sep) for root in CACHE_ROOTS)


def human_size(n):
    n = float(n)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if n < 1024 or unit == "TB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def classify(filename):
    ext = os.path.splitext(filename)[1].lower()
    return EXT_TO_CATEGORY.get(ext, "Other")


def is_critical_dir_name(name):
    n = name.lower()
    # "_MEI<random>" is PyInstaller's own onefile runtime extraction folder
    # under %TEMP% - it's this app's own bundled files (DLLs, the Python
    # runtime), actively in use by the running exe. It normally cleans itself
    # up on exit, but a folder can survive a forced/crashed shutdown; without
    # this check it would get scanned and offered up for deletion like any
    # other temp file, and deleting a locked file the app itself is running
    # from fails with a raw OS/OLE error instead of being screened out here.
    return n in CRITICAL_DIR_NAMES or "sandbox" in n or n.startswith("_mei")


def is_protected_path(path):
    """Standalone re-classification of a single path (no directory walk),
    used by the deletion engine to independently re-verify safety right
    before deleting anything - never trusts a category computed earlier."""
    path = os.path.abspath(path)
    if is_cache_zone_path(path):
        return False
    name = os.path.basename(path).lower()
    ext = os.path.splitext(name)[1].lower()
    if name in ROOT_SYSTEM_FILES or ext in CRITICAL_EXTENSIONS:
        return True
    drive, tail = os.path.splitdrive(path)
    for part in tail.split(os.sep):
        if part and is_critical_dir_name(part):
            return True
    return False


def is_drive_root(path):
    drive, tail = os.path.splitdrive(os.path.abspath(path))
    return tail in ("\\", "/", "")


class ScanControl:
    """Cooperative pause/resume for a running scan. Thread-safe."""

    def __init__(self):
        self._resume_event = threading.Event()
        self._resume_event.set()  # start "running"

    def pause(self):
        self._resume_event.clear()

    def resume(self):
        self._resume_event.set()

    @property
    def paused(self):
        return not self._resume_event.is_set()

    def wait_if_paused(self):
        self._resume_event.wait()


class ScanResult:
    def __init__(self):
        self.category_sizes = {}
        self.category_counts = {}
        self.file_index = []  # list of dicts: path,size,mtime,ext,category - safe files >= FILE_INDEX_MIN_SIZE
        self.dir_sizes = {}  # path -> size, depth-limited
        self.dir_critical = {}  # path -> bool, same keys as dir_sizes - Windows/Program Files/etc.
                                 # subtrees, so folder-size listings can exclude them the same way
                                 # individual files already are (nothing user-facing ever names a
                                 # specific system folder - it's just rolled into one protected total)
        self.file_count = 0
        self.dir_count = 0
        self.inaccessible = 0
        self.excluded_count = 0
        self.total_size = 0
        self.safe_total = 0
        self.critical_total = 0

    def add_file(self, path, size, mtime, critical, excluded, cache_zone=False):
        self.total_size += size
        self.file_count += 1
        cat = classify(path)

        if critical:
            self.critical_total += size
            return

        # Category breakdown only counts your own (non-critical) files - a
        # Windows/Program Files DLL contributing to "System & Libraries" would
        # make that chart look like it's reporting on your data when it's
        # actually reporting on system internals you can't and shouldn't
        # touch. Disk usage totals (used/free) are unaffected - those come
        # from shutil.disk_usage, not this per-file accounting.
        self.category_sizes[cat] = self.category_sizes.get(cat, 0) + size
        self.category_counts[cat] = self.category_counts.get(cat, 0) + 1
        self.safe_total += size

        if excluded:
            self.excluded_count += 1
            return

        if size >= FILE_INDEX_MIN_SIZE:
            self.file_index.append({
                "path": path, "size": size, "mtime": mtime,
                "ext": os.path.splitext(path)[1].lower(), "category": cat,
                "cache_zone": cache_zone,
            })


def scan_dir(path, result, depth, critical=False, exclusion_list=None, control=None, cache_zone=False):
    """Recursively compute size of `path`; records folder sizes up to MAX_DEPTH_FOR_DIR_SIZES.

    `critical` marks this whole subtree as owned by Windows/an installed application
    (inherited by every file and subfolder below it) so it's excluded from the
    "safe to delete" file lists. `cache_zone` marks it as one of the specific
    known-safe cache folders (overrides `critical` for this subtree only).
    `exclusion_list` paths are skipped entirely - not walked, not counted.
    `control`, if given, is a ScanControl for pause/resume.
    """
    if control is not None:
        control.wait_if_paused()

    if exclusion_list and exclusions_mod.is_excluded(path, exclusion_list):
        result.excluded_count += 1
        return 0

    total = 0
    try:
        with os.scandir(path) as it:
            entries = list(it)
    except (PermissionError, OSError):
        result.inaccessible += 1
        return 0

    for entry in entries:
        if control is not None:
            control.wait_if_paused()
        try:
            if entry.is_symlink():
                continue
            entry_cache_zone = cache_zone or is_cache_zone_path(entry.path)
            if entry.is_dir(follow_symlinks=False):
                if entry.name in SKIP_DIR_NAMES:
                    continue
                if exclusion_list and exclusions_mod.is_excluded(entry.path, exclusion_list):
                    result.excluded_count += 1
                    continue
                result.dir_count += 1
                child_critical = False if entry_cache_zone else (critical or is_critical_dir_name(entry.name))
                total += scan_dir(entry.path, result, depth + 1, child_critical, exclusion_list, control, entry_cache_zone)
            elif entry.is_file(follow_symlinks=False):
                try:
                    st = entry.stat(follow_symlinks=False)
                except OSError:
                    result.inaccessible += 1
                    continue
                size = st.st_size
                ext = os.path.splitext(entry.name)[1].lower()
                file_critical = False if entry_cache_zone else (
                    critical
                    or ext in CRITICAL_EXTENSIONS
                    or entry.name.lower() in ROOT_SYSTEM_FILES
                )
                file_excluded = bool(exclusion_list) and exclusions_mod.is_excluded(entry.path, exclusion_list)
                result.add_file(entry.path, size, st.st_mtime, file_critical, file_excluded, entry_cache_zone)
                total += size
        except (PermissionError, OSError):
            result.inaccessible += 1
            continue

    if depth <= MAX_DEPTH_FOR_DIR_SIZES:
        result.dir_sizes[path] = total
        result.dir_critical[path] = critical
    return total


def dir_size_quiet(path):
    """Best-effort recursive size of a specific known path, no recording."""
    total = 0
    try:
        with os.scandir(path) as it:
            for entry in it:
                try:
                    if entry.is_symlink():
                        continue
                    if entry.is_dir(follow_symlinks=False):
                        total += dir_size_quiet(entry.path)
                    elif entry.is_file(follow_symlinks=False):
                        total += entry.stat(follow_symlinks=False).st_size
                except OSError:
                    continue
    except OSError:
        return 0
    return total


def junk_location_candidates():
    """The fixed set of known junk/cache locations this app knows about,
    label -> Path. This is the single source of truth for both display
    (scan_junk_locations) and the one-click clear action (deletion_engine) -
    the clear action only ever accepts a label from this dict, never a raw
    path from the client."""
    home = Path.home()
    return {
        "User Temp (%TEMP%)": home / "AppData" / "Local" / "Temp",
        "Windows Temp": Path("C:/Windows/Temp"),
        "Windows Update cache": Path("C:/Windows/SoftwareDistribution/Download"),
        "Windows.old (old OS backup)": Path("C:/Windows.old"),
        "Downloads folder": home / "Downloads",
        "Recycle Bin": Path("C:/$Recycle.Bin"),
        "Explorer thumbnail cache": home / "AppData" / "Local" / "Microsoft" / "Windows" / "Explorer",
        "Chrome cache": home / "AppData" / "Local" / "Google" / "Chrome" / "User Data" / "Default" / "Cache",
        "Edge cache": home / "AppData" / "Local" / "Microsoft" / "Edge" / "User Data" / "Default" / "Cache",
        "Windows Prefetch": Path("C:/Windows/Prefetch"),
    }


# Locations safe for a one-click bulk clear: well-understood, regenerated
# automatically, and narrow in blast radius. Recycle Bin (needs its own
# empty semantics and holds files from outside this app's scans), Downloads
# (needs manual review), Windows.old, and Prefetch (leave alone) are excluded.
CLEARABLE_LABELS = {
    "User Temp (%TEMP%)", "Windows Temp", "Windows Update cache",
    "Explorer thumbnail cache", "Chrome cache", "Edge cache",
}


def scan_junk_locations():
    results = {}
    for label, p in junk_location_candidates().items():
        if p.exists():
            size = dir_size_quiet(str(p))
            results[label] = {"path": str(p), "size": size, "exists": True, "clearable": label in CLEARABLE_LABELS}
        else:
            results[label] = {"path": str(p), "size": 0, "exists": False, "clearable": label in CLEARABLE_LABELS}
    return results


def run_scan(root, progress=None, control=None):
    """Scan `root` and return (data_dict, safe_files_for_excel, file_index).

    `progress`, if given, is called with short status strings so a caller
    (e.g. the web app) can surface live progress. `control`, if given, is a
    ScanControl enabling pause/resume mid-scan.
    """
    def report(msg):
        if progress:
            progress(msg)

    root = os.path.abspath(root)
    if not root.endswith("\\"):
        root += "\\"

    report(f"Scanning {root} ...")
    t0 = time.time()

    drive_root = os.path.splitdrive(root)[0] + "\\"
    total, used, free = shutil.disk_usage(drive_root)

    exclusion_list = exclusions_mod.load()

    result = ScanResult()
    scan_dir(root, result, depth=0, exclusion_list=exclusion_list, control=control,
             cache_zone=is_cache_zone_path(root))
    elapsed = time.time() - t0

    report(f"Scan complete in {elapsed:.1f}s. Checking junk/cache locations...")
    junk = scan_junk_locations() if is_drive_root(root) else {}

    top_files_sorted = heapq.nlargest(TOP_FILES_COUNT, result.file_index, key=lambda f: f["size"])
    # Windows/Program Files/ProgramData/etc. subtrees are excluded from every
    # folder-size listing, the same way individual files in them already are -
    # nothing user-facing ever names a specific system folder. Their combined
    # size is still reflected in critical_total, just not broken out by path.
    top_folders_sorted = sorted(
        ((p, s) for p, s in result.dir_sizes.items() if p != root and not result.dir_critical.get(p)),
        key=lambda x: -x[1],
    )[:TOP_FOLDERS_COUNT]

    top_level = sorted(
        ((p, s) for p, s in result.dir_sizes.items()
         if (os.path.dirname(p.rstrip("\\")) == root.rstrip("\\") or p == root) and not result.dir_critical.get(p)),
        key=lambda x: -x[1],
    )

    excel_candidates = [f for f in result.file_index if f["size"] >= EXCEL_MIN_SIZE]
    excel_candidates.sort(key=lambda f: -f["size"])
    safe_files_truncated = len(excel_candidates) > EXCEL_MAX_ROWS
    safe_files = excel_candidates[:EXCEL_MAX_ROWS]

    data = {
        "scanned_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "root": root,
        "disk": {"total": total, "used": used, "free": free},
        "scanned_total": result.total_size,
        "safe_total": result.safe_total,
        "critical_total": result.critical_total,
        "file_count": result.file_count,
        "dir_count": result.dir_count,
        "inaccessible": result.inaccessible,
        "excluded_count": result.excluded_count,
        "elapsed_seconds": round(elapsed, 1),
        "category_sizes": result.category_sizes,
        "category_counts": result.category_counts,
        "top_files": [{"path": f["path"], "size": f["size"]} for f in top_files_sorted],
        "top_folders": [{"path": p, "size": s} for p, s in top_folders_sorted],
        "top_level_folders": [{"path": p, "size": s} for p, s in top_level if p != root],
        "junk": junk,
        "safe_files_count": len(excel_candidates),
        "safe_files_truncated": safe_files_truncated,
        "indexed_file_count": len(result.file_index),
    }
    safe_files_for_excel = [{"path": f["path"], "size": f["size"], "category": f["category"]} for f in safe_files]

    report("Scan finished.")
    return data, safe_files_for_excel, result.file_index
