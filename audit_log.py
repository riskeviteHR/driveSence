"""Append-only scan history log, shown on the Audit Logs page."""

import json

from app_paths import DATA_DIR

LOG_PATH = DATA_DIR / "audit_log.jsonl"


def add_entry(entry):
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def list_entries():
    if not LOG_PATH.exists():
        return []
    entries = []
    with LOG_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    entries.reverse()  # newest first
    return entries
