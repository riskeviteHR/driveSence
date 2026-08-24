"""Content-hash duplicate detection. Two files only count as duplicates when
their SHA-256 digests match exactly - same size alone is never enough."""

import hashlib
import os

import manifest as manifest_mod

HASH_CHUNK = 4 * 1024 * 1024


def hash_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(HASH_CHUNK)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def find_duplicates(file_index, progress=None, use_manifest=True, control=None):
    """file_index: list of {path, size, mtime, ext, category}.

    Returns (groups, stats) where groups is a list of:
      {hash, size, count, waste_bytes, files: [{path, mtime}, ...]}
    sorted by waste_bytes descending. Only sizes shared by 2+ files are ever
    hashed - a unique size can never have a content duplicate.
    """
    by_size = {}
    for f in file_index:
        by_size.setdefault(f["size"], []).append(f)
    candidates = [group for group in by_size.values() if len(group) >= 2]
    total_to_hash = sum(len(g) for g in candidates)

    conn = manifest_mod.get_conn() if use_manifest else None
    hashed = 0
    cache_hits = 0
    by_hash = {}
    errors = 0

    for group in candidates:
        for f in group:
            if control is not None:
                control.wait_if_paused()
            sha = None
            if conn is not None:
                sha = manifest_mod.get_cached_hash(conn, f["path"], f["size"], f["mtime"])
                if sha:
                    cache_hits += 1
            if sha is None:
                try:
                    sha = hash_file(f["path"])
                except (OSError, PermissionError):
                    errors += 1
                    continue
                if conn is not None:
                    manifest_mod.store_hash(conn, f["path"], f["size"], f["mtime"], sha)
            hashed += 1
            if progress and hashed % 200 == 0:
                progress(f"Hashing for duplicates... {hashed}/{total_to_hash} "
                         f"({cache_hits} from cache)")
            by_hash.setdefault((sha, f["size"]), []).append(f)

    if conn is not None:
        manifest_mod.commit(conn)
        conn.close()

    groups = []
    for (sha, size), files in by_hash.items():
        if len(files) < 2:
            continue
        files_sorted = sorted(files, key=lambda f: f["mtime"])  # oldest first = keeper
        groups.append({
            "hash": sha,
            "size": size,
            "count": len(files_sorted),
            "waste_bytes": size * (len(files_sorted) - 1),
            "files": [{"path": f["path"], "mtime": f["mtime"]} for f in files_sorted],
        })
    groups.sort(key=lambda g: -g["waste_bytes"])

    stats = {
        "candidates_hashed": hashed,
        "cache_hits": cache_hits,
        "hash_errors": errors,
        "duplicate_groups": len(groups),
        "total_waste_bytes": sum(g["waste_bytes"] for g in groups),
    }
    return groups, stats
