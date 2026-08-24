"""Restore a file this app previously sent to the Recycle Bin, back to its
original location. Only ever called with a path that the caller (the Audit
Logs page) sourced from a successful "deleted" entry in our own audit log -
this never exposes arbitrary Recycle Bin browsing, only "undo what this app
did", matching the deny-by-default spirit of the rest of the app.
"""

import time

import winshell

import audit_log


def restore_file(path):
    """Restore the most recently recycled version of `path`. Returns a
    result dict; every attempt - success or failure - is audit-logged.
    """
    entry = {
        "type": "restore",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "path": path,
    }

    try:
        restored_to = winshell.recycle_bin().undelete(path)
    except winshell.x_not_found_in_recycle_bin:
        entry.update(result="refused",
                      detail="Not found in the Recycle Bin (already restored, emptied, or permanently deleted).")
        audit_log.add_entry(entry)
        return {"success": False, "reason": entry["detail"]}
    except Exception as e:
        entry.update(result="error", detail=str(e))
        audit_log.add_entry(entry)
        return {"success": False, "reason": str(e)}

    entry.update(result="restored", detail=f"Restored to {restored_to}.", restored_to=restored_to)
    audit_log.add_entry(entry)
    return {"success": True, "restored_to": restored_to}
