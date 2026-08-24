"""
Safe deletion: everything goes to the Windows Recycle Bin (send2trash), never
a permanent delete, so every action here is restorable through Explorer's
own Recycle Bin. Every check is re-verified here, server-side, regardless of
what the caller (browser UI) claims about a file's category - deny-by-default.

Restoration: this app does not reimplement undo - the OS Recycle Bin already
does it. The audit log records what was sent there and when, so a user can
match an entry here to what they see in the Recycle Bin.
"""

import os
import time

from send2trash import send2trash

import audit_log
import exclusions as exclusions_mod
from scanner_core import CLEARABLE_LABELS, is_cache_zone_path, is_protected_path, junk_location_candidates

# Windows COPYENGINE HRESULTs (and the classic WinError 32 text) that all mean
# the same thing in practice: another running program has the file open, so
# the Recycle Bin move was refused. Shown to the user as one plain sentence
# instead of a raw error code - the underlying code is still kept in the
# audit log for anyone who needs to debug it.
_SHARING_VIOLATION_MARKERS = (
    "0x80270027", "0x80270028", "0x80270020", "0x80270021",
    "being used by another process", "cannot access the file",
)


def _is_file_locked(path):
    """Best-effort pre-check for 'another program has this open'. Renaming a
    file to its own name is a no-op if Windows grants exclusive-ish access,
    and fails with a sharing violation if some other process is holding it -
    a well-known trick for probing file locks without touching content.
    """
    try:
        os.rename(path, path)
        return False
    except OSError:
        return True


def _friendly_send2trash_error(exc):
    msg = str(exc)
    if any(marker in msg for marker in _SHARING_VIOLATION_MARKERS):
        return "File is currently in use by another program and couldn't be removed.", True
    return msg, False


def delete_file(path, category="personal", reason="", risk_level="medium",
                 confidence=0, duplicate_keeper=None, override=False):
    """Attempt to send one file to the Recycle Bin. Returns a result dict.
    Every attempt - success or refusal - is written to the audit log.
    """
    entry = {
        "type": "deletion",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "path": path,
        "category": category,
        "risk_level": risk_level,
        "confidence": confidence,
        "reason": reason,
    }

    if not os.path.isfile(path):
        entry.update(result="refused", detail="Path does not exist or is not a file.")
        audit_log.add_entry(entry)
        return {"success": False, "reason": entry["detail"], "already_gone": True}

    size = os.path.getsize(path)
    entry["size"] = size

    if is_protected_path(path):
        entry.update(result="refused", detail="Blocked: path is protected (system/application-owned).")
        audit_log.add_entry(entry)
        return {"success": False, "reason": entry["detail"]}

    if exclusions_mod.is_excluded(path):
        entry.update(result="refused", detail="Blocked: path is on your exclusion list.")
        audit_log.add_entry(entry)
        return {"success": False, "reason": entry["detail"]}

    if category == "duplicate":
        if not duplicate_keeper or not os.path.isfile(duplicate_keeper):
            entry.update(result="refused",
                         detail="Blocked: could not verify a kept copy still exists.")
            audit_log.add_entry(entry)
            return {"success": False, "reason": entry["detail"]}
        if os.path.normcase(os.path.normpath(duplicate_keeper)) == os.path.normcase(os.path.normpath(path)):
            entry.update(result="refused", detail="Blocked: this is the last/kept copy.")
            audit_log.add_entry(entry)
            return {"success": False, "reason": entry["detail"]}

    if category == "unknown" and not override:
        entry.update(result="refused",
                      detail="Blocked: unrecognized file type requires manual review confirmation.")
        audit_log.add_entry(entry)
        return {"success": False, "reason": entry["detail"]}

    if _is_file_locked(path):
        entry.update(result="refused", detail="Skipped: file is currently open in another program.")
        audit_log.add_entry(entry)
        return {"success": False, "reason": entry["detail"], "locked": True}

    try:
        send2trash(path)
    except Exception as e:
        friendly, locked = _friendly_send2trash_error(e)
        entry.update(result="error", detail=str(e))
        audit_log.add_entry(entry)
        return {"success": False, "reason": friendly, "locked": locked}

    entry.update(result="deleted", detail="Sent to Recycle Bin.")
    audit_log.add_entry(entry)
    return {"success": True, "size": size}


def clear_known_location(label):
    """One-click 'clear' for a known-safe cache/temp folder. `label` must be
    one of CLEARABLE_LABELS - never a path from the client - so the only
    folders this can ever touch are the fixed, well-known cache locations.
    Trashes each top-level item individually (tolerating locked files) and
    writes a single aggregate audit entry.
    """
    entry = {
        "type": "clear_folder",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "category": "temp_cache",
        "risk_level": "low",
        "confidence": 90,
        "reason": f'One-click clear of known cache location "{label}".',
    }

    if label not in CLEARABLE_LABELS:
        entry.update(path=label, result="refused", detail="Not an allowed clearable location.")
        audit_log.add_entry(entry)
        return {"success": False, "reason": entry["detail"]}

    folder = junk_location_candidates()[label]
    entry["path"] = str(folder)

    if not folder.exists():
        entry.update(result="refused", detail="Folder does not exist.")
        audit_log.add_entry(entry)
        return {"success": False, "reason": entry["detail"]}

    if not is_cache_zone_path(str(folder)) or is_protected_path(str(folder)):
        # Defense in depth: should be unreachable given CLEARABLE_LABELS, but
        # never trust a single layer of checks for a bulk-delete action.
        entry.update(result="refused", detail="Blocked: failed independent safety re-check.")
        audit_log.add_entry(entry)
        return {"success": False, "reason": entry["detail"]}

    if exclusions_mod.is_excluded(str(folder)):
        entry.update(result="refused", detail="Blocked: folder is on your exclusion list.")
        audit_log.add_entry(entry)
        return {"success": False, "reason": entry["detail"]}

    cleared, freed, errors = 0, 0, 0
    try:
        children = list(folder.iterdir())
    except OSError as e:
        entry.update(result="error", detail=str(e))
        audit_log.add_entry(entry)
        return {"success": False, "reason": str(e)}

    for child in children:
        try:
            if exclusions_mod.is_excluded(str(child)):
                continue
            size = child.stat().st_size if child.is_file() else _dir_size(child)
            send2trash(str(child))
            cleared += 1
            freed += size
        except Exception:
            errors += 1  # e.g. file locked by a running app - skip and continue

    entry.update(
        result="deleted" if cleared else ("error" if errors else "refused"),
        detail=f"Cleared {cleared} item(s), freed {freed} bytes, {errors} skipped/locked.",
        size=freed,
    )
    audit_log.add_entry(entry)
    return {"success": cleared > 0, "cleared": cleared, "freed_bytes": freed, "errors": errors}


def _dir_size(path):
    total = 0
    for dirpath, _dirnames, filenames in os.walk(path):
        for name in filenames:
            try:
                total += os.path.getsize(os.path.join(dirpath, name))
            except OSError:
                pass
    return total


def delete_many(items):
    """items: list of dicts matching delete_file's kwargs (must include 'path')."""
    results = []
    for item in items:
        r = delete_file(**item)
        r["path"] = item["path"]
        results.append(r)
    return results
