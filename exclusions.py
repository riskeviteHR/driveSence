"""User-managed exclusion list: paths the scanner/recommendation engine must
never touch. Applied both at scan time (skip walking) and at recommendation
time (never suggest deleting anything under an excluded path)."""

import json
import os

from app_paths import DATA_DIR

PATH = DATA_DIR / "exclusions.json"


def load():
    if not PATH.exists():
        return []
    try:
        return json.loads(PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def save(items):
    PATH.write_text(json.dumps(sorted(set(items)), indent=2), encoding="utf-8")


def add(path):
    items = load()
    norm = os.path.normpath(path)
    if norm not in items:
        items.append(norm)
        save(items)
    return items


def remove(path):
    items = [p for p in load() if p != path]
    save(items)
    return items


def is_excluded(path, exclusions=None):
    if exclusions is None:
        exclusions = load()
    if not exclusions:
        return False
    p = os.path.normpath(path).lower()
    for ex in exclusions:
        ex_norm = os.path.normpath(ex).lower()
        if p == ex_norm or p.startswith(ex_norm + os.sep):
            return True
    return False
