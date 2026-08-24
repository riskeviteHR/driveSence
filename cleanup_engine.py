"""
Deny-by-default classification + risk/confidence scoring for cleanup
recommendations.

Every recommendation carries an explainable reason, a risk level, and a
confidence score - nothing is presented as "just delete this" without saying
why. Rules:
  - protected (critical/system) files never appear here at all - scanner_core
    excludes them from the file index before this module ever sees them.
  - duplicates: content-hash verified: the oldest copy in each group is
    always kept; only the extra copies are ever recommended for removal.
  - unknown file types: always "manual_review" - never a one-click delete.
  - everything else gets a risk level + confidence + reason, but deletion
    still always goes through the deny-by-default checks in deletion_engine.
"""

import os
import time
from pathlib import Path

from scanner_core import EXT_TO_CATEGORY

LARGE_FILE_THRESHOLD = 500 * 1024 * 1024  # 500 MB
OLD_DOWNLOAD_DAYS = 90

HOME = Path.home()
DOWNLOADS_DIR = os.path.normcase(os.path.normpath(str(HOME / "Downloads")))


def age_days(mtime, now=None):
    now = now or time.time()
    return max(0, int((now - mtime) / 86400))


def age_label(days):
    if days < 30:
        return "Last 30 days"
    if days < 90:
        return "30-90 days"
    if days < 365:
        return "90-365 days"
    return "Over a year"


def _in_downloads(path):
    p = os.path.normcase(os.path.normpath(path))
    return p == DOWNLOADS_DIR or p.startswith(DOWNLOADS_DIR + os.sep)


def _is_unknown_ext(ext):
    return ext not in EXT_TO_CATEGORY


# One-line, jargon-free explanation per category, for the beginner-friendly
# view - the full technical `reason` (hash verification, exact day count,
# etc.) stays available in Advanced Mode.
SIMPLE_LABELS = {
    "duplicate": "Duplicate copy — identical to a file we're keeping.",
    "temp_cache": "Temporary file — made automatically by an app or Windows; it'll just be recreated if needed.",
    "old_download": "Old download — sitting untouched for a while, probably already used.",
    "large_file": "Large file — worth a quick look before deciding.",
    "unknown": "Unrecognized file type — needs your review before we'd suggest removing it.",
}

# A simplified 2-tier view for beginners: everything Cleanup Center lists is
# already deny-by-default safe to show (protected files never reach here) -
# "safe" vs "review" just distinguishes routine one-click items (duplicates,
# temp/cache) from ones worth a human glance first (old downloads, large
# files, unknown types), mirroring the existing risk_level low/medium/high.


def _base_item(f, now):
    days = age_days(f["mtime"], now)
    path = f["path"]
    return {
        "id": path,
        "path": path,
        "filename": os.path.basename(path),
        "size": f["size"],
        "mtime": f["mtime"],
        "age_days": days,
        "age_label": age_label(days),
        "ext": f.get("ext", os.path.splitext(path)[1].lower()),
    }


def build_cleanup_report(file_index, duplicate_groups, root=None):
    now = time.time()
    dup_extra_paths = set()  # non-keeper duplicate paths, excluded from other buckets

    duplicate_items = []
    total_dup_waste = 0
    for group in duplicate_groups:
        keeper = group["files"][0]  # oldest = keeper, per duplicates.find_duplicates
        extras = group["files"][1:]
        for extra in extras:
            dup_extra_paths.add(extra["path"])
        total_dup_waste += group["waste_bytes"]
        group_id = group["hash"]
        duplicate_items.append({
            "group_id": group_id,
            "hash": group["hash"],
            "size": group["size"],
            "count": group["count"],
            "waste_bytes": group["waste_bytes"],
            "keeper": {"path": keeper["path"], "mtime": keeper["mtime"], "filename": os.path.basename(keeper["path"])},
            "extras": [
                {
                    "id": e["path"], "path": e["path"], "filename": os.path.basename(e["path"]),
                    "mtime": e["mtime"], "size": group["size"], "group_id": group_id, "hash": group["hash"],
                    "risk_level": "low", "confidence": 95, "category": "duplicate",
                    "tier": "safe", "simple_label": SIMPLE_LABELS["duplicate"],
                    "reason": f'Identical content (verified by SHA-256) to the copy kept at "{keeper["path"]}".',
                    "action": "delete_to_recyclebin",
                }
                for e in extras
            ],
        })
    duplicate_items.sort(key=lambda g: -g["waste_bytes"])

    temp_cache_files = []
    old_downloads = []
    large_files = []
    unknown_files = []

    for f in file_index:
        if f["path"] in dup_extra_paths:
            continue  # already covered as a duplicate recommendation

        item = _base_item(f, now)

        if f.get("cache_zone"):
            item.update({
                "category": "temp_cache",
                "risk_level": "low", "confidence": 90,
                "tier": "safe", "simple_label": SIMPLE_LABELS["temp_cache"],
                "reason": "Located in a known cache/temp folder; regenerated automatically by the app or OS.",
                "action": "delete_to_recyclebin",
            })
            temp_cache_files.append(item)
            continue

        if _in_downloads(f["path"]) and item["age_days"] > OLD_DOWNLOAD_DAYS:
            confidence = min(90, 55 + item["age_days"] // 30 * 5)
            item.update({
                "category": "old_download",
                "risk_level": "medium", "confidence": confidence,
                "tier": "review", "simple_label": SIMPLE_LABELS["old_download"],
                "reason": f'In Downloads and untouched for {item["age_days"]} days - likely an installer or '
                          f"file you already used, but review before deleting.",
                "action": "delete_to_recyclebin",
            })
            old_downloads.append(item)
            continue

        if _is_unknown_ext(item["ext"]):
            item.update({
                "category": "unknown",
                "risk_level": "high", "confidence": 20,
                "tier": "review", "simple_label": SIMPLE_LABELS["unknown"],
                "reason": f'Unrecognized file type ("{item["ext"] or "no extension"}") - cannot automatically '
                          f"verify what this is or whether it's safe to remove.",
                "action": "manual_review",
            })
            unknown_files.append(item)
            continue

        if f["size"] >= LARGE_FILE_THRESHOLD:
            item.update({
                "category": "large_file",
                "risk_level": "medium", "confidence": 45,
                "tier": "review", "simple_label": SIMPLE_LABELS["large_file"],
                "reason": f'Large file ({f["category"]}) not otherwise flagged - worth a manual look, '
                          f"not automatically known to be safe.",
                "action": "delete_to_recyclebin",
            })
            large_files.append(item)
            continue

    for lst in (temp_cache_files, old_downloads, large_files, unknown_files):
        lst.sort(key=lambda x: -x["size"])

    recoverable_estimate = (
        total_dup_waste
        + sum(i["size"] for i in temp_cache_files)
        + sum(i["size"] for i in old_downloads if i["confidence"] >= 70)
    )

    dup_extra_count = sum(g["count"] - 1 for g in duplicate_items)
    safe_count = dup_extra_count + len(temp_cache_files)
    safe_bytes = total_dup_waste + sum(i["size"] for i in temp_cache_files)
    review_items = old_downloads + large_files + unknown_files
    review_count = len(review_items)
    review_bytes = sum(i["size"] for i in review_items)

    return {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "duplicates": {
            "groups": duplicate_items,
            "total_groups": len(duplicate_items),
            "total_waste_bytes": total_dup_waste,
        },
        "temp_cache_files": temp_cache_files,
        "old_downloads": old_downloads,
        "large_files": large_files,
        "unknown_files": unknown_files,
        "items": temp_cache_files + old_downloads + large_files + unknown_files,
        "recoverable_estimate_bytes": recoverable_estimate,
        "counts": {
            "duplicates": dup_extra_count,
            "temp_cache": len(temp_cache_files),
            "old_downloads": len(old_downloads),
            "large_files": len(large_files),
            "unknown": len(unknown_files),
        },
        # Beginner-facing 2-tier summary (see SIMPLE_LABELS / the "safe" vs
        # "review" tier above) - lets the simplified UI show "N items safe to
        # remove in one click" without re-deriving it client-side.
        "tiers": {
            "safe": {"count": safe_count, "bytes": safe_bytes},
            "review": {"count": review_count, "bytes": review_bytes},
        },
    }
