"""Renders scan results into the HTML storage dashboard."""

import os

from theme import ACCENT, BRAND_NAME, CAT_COLORS, OTHER_COLOR, STATUS, esc, file_icon, human_size, icon, render_page

CHART_CSS = f"""
  .top-row {{ display:flex; justify-content: space-between; align-items:flex-start; gap: 16px; flex-wrap: wrap; margin-bottom: 20px; }}

  .stat-tiles {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin-bottom: 20px; }}
  .stat-tile {{ background: var(--tile-bg); border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px; }}
  .stat-tile .v {{ font-size: 20px; font-weight: 700; }}
  .stat-tile .l {{ font-size: 11.5px; color: var(--text-muted); margin-top: 2px; }}

  .dashboard-grid {{ display:grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 20px; align-items: stretch; }}
  .dashboard-grid > .card {{ margin-bottom: 0; display:flex; flex-direction:column; }}
  @media (max-width: 760px) {{ .dashboard-grid {{ grid-template-columns: 1fr; }} }}

  .hero-row {{ display:flex; gap: 28px; flex-wrap: wrap; align-items: flex-end; margin-bottom: 14px; }}
  .hero-figure {{ font-size: 40px; font-weight: 600; line-height:1; }}
  .hero-figure .unit {{ font-size: 18px; font-weight: 500; color: var(--text-secondary); }}
  .hero-caption {{ font-size: 12.5px; color: var(--text-secondary); margin-top: 4px; }}
  .stat-mini {{ font-size: 13px; color: var(--text-secondary); }}
  .stat-mini b {{ color: var(--text-primary); font-variant-numeric: tabular-nums; }}

  .meter {{ position: relative; height: 22px; border-radius: 4px; background: var(--track); overflow: hidden; }}
  .meter-fill {{ position:absolute; left:0; top:0; bottom:0; background: {ACCENT}; border-radius: 4px; }}
  .meter-labels {{ display:flex; justify-content: space-between; font-size: 11.5px; color: var(--text-muted); margin-top: 6px; }}

  .donut-layout {{ display:flex; align-items:center; gap: 24px; flex-wrap: wrap; }}
  .donut {{ flex-shrink: 0; }}
  .donut-center-label {{ font-size: 26px; font-weight: 800; fill: var(--text-primary); font-family: system-ui, sans-serif; }}
  .donut-center-sub {{ font-size: 10.5px; fill: var(--text-muted); font-family: system-ui, sans-serif; text-transform: uppercase; letter-spacing: .04em; }}
  .donut-legend {{ display:flex; flex-direction: column; gap: 10px; flex: 1 1 160px; min-width: 160px; }}

  .stacked-bar {{ display:block; margin-bottom: 14px; }}
  .track {{ fill: var(--track); }}
  .seg {{ fill: var(--seg-color); }}

  .legend {{ display:flex; flex-wrap: wrap; gap: 8px 22px; }}
  .legend-row {{ display:flex; align-items:center; gap:7px; font-size: 12.5px; min-width: 190px; }}
  .swatch {{ width:10px; height:10px; border-radius:2px; background: var(--seg-color); flex-shrink:0; }}
  .legend-label {{ color: var(--text-primary); }}
  .legend-value {{ color: var(--text-secondary); font-variant-numeric: tabular-nums; margin-left: auto; }}
  .legend-pct {{ color: var(--text-muted); width: 42px; text-align:right; font-variant-numeric: tabular-nums; }}

  .export-row {{ display:flex; gap: 10px; flex-wrap: wrap; margin-bottom: 14px; }}
  .export-folder-row {{ display:flex; gap: 10px; flex-wrap: wrap; align-items: stretch; }}
  .export-folder-row input[type=text] {{ flex: 1 1 260px; }}

  .compact-table th {{ white-space: nowrap; }}
  .compact-table .icon-cell {{ width: 26px; color: var(--text-muted); }}
  .compact-table .name-cell {{ font-weight: 600; color: var(--text-primary); }}
  .compact-table .size-cell {{ text-align:right; font-variant-numeric: tabular-nums; white-space:nowrap; }}
  .sort-th {{ background:none; border:none; color: var(--text-muted); font: inherit; font-weight:600; font-size: 11.5px;
              text-transform: uppercase; letter-spacing: .03em; cursor:pointer; padding:0; display:inline-flex; align-items:center; gap:4px; }}
  .sort-th:hover {{ color: var(--text-primary); }}
  .sort-th .arrow {{ opacity: 0; font-size: 9px; transition: opacity .1s ease; }}
  .sort-th.active .arrow {{ opacity: 1; color: {ACCENT}; }}
  .table-toolbar {{ display:flex; justify-content:flex-end; margin-bottom: 8px; }}

  .path-cell {{ color: var(--text-secondary); word-break: break-all; }}
  .tip-cell {{ color: var(--text-secondary); min-width: 220px; }}
  .badge-cell {{ white-space: nowrap; font-weight: 500; }}
  .status-dot {{ display:inline-block; width:8px; height:8px; border-radius:50%; background: var(--dot-color); margin-right:8px; }}

  .junk-legend {{ display:flex; flex-wrap:wrap; gap: 16px; font-size: 11.5px; color: var(--text-secondary); margin: 2px 0 16px; }}
  .junk-legend span {{ display:inline-flex; align-items:center; }}
  .clear-actions {{ margin-bottom: 14px; }}
  .row-actions {{ display:flex; gap: 6px; flex-wrap: wrap; }}
  .btn-clear, .btn-open {{ display:inline-flex; align-items:center; gap:5px; background: transparent; border: 1px solid var(--border); color: var(--text-primary);
                font-size: 12px; font-weight: 600; padding: 6px 12px; border-radius: 6px; cursor:pointer;
                font-family:inherit; white-space:nowrap; transition: all .15s ease; }}
  .btn-clear:hover {{ border-color: {ACCENT}; color: {ACCENT}; background: rgba(0,184,217,0.12); }}
  .btn-open:hover {{ border-color: var(--text-secondary); color: var(--text-primary); background: var(--track); }}
  .btn-clear[disabled] {{ opacity: 0.5; cursor: default; background: var(--track) !important; color: var(--text-muted) !important; border-color: var(--border) !important; }}
  .clear-note {{ color: var(--text-muted); font-size: 11.5px; }}
  tr.gone td {{ opacity: 0.4; text-decoration: line-through; }}

  .callout {{ background: var(--track); border-radius: 8px; padding: 12px 16px; font-size: 12.5px; color: var(--text-secondary); margin-top: 6px; }}
  .callout b {{ color: var(--text-primary); }}
  ul.tips {{ margin: 8px 0 0; padding-left: 18px; font-size: 13px; color: var(--text-secondary); line-height: 1.7; }}
  ul.tips li b {{ color: var(--text-primary); }}

  .safe-split {{ display:flex; height: 10px; border-radius: 4px; overflow:hidden; margin-top: 10px; background: var(--track); }}
  .safe-split .safe {{ background: {CAT_COLORS[2]}; }}
  .safe-split .critical {{ background: var(--text-muted); }}
  .safe-legend {{ display:flex; gap:20px; margin-top:8px; font-size: 12px; color: var(--text-secondary); }}
  .dot-safe {{ display:inline-block; width:9px; height:9px; border-radius:2px; background:{CAT_COLORS[2]}; margin-right:6px; }}
  .dot-critical {{ display:inline-block; width:9px; height:9px; border-radius:2px; background: var(--text-muted); margin-right:6px; }}
"""


def _js_str(s):
    import json
    return json.dumps(s or "")


def short_path(p, keep=72):
    p = str(p)
    if len(p) <= keep:
        return p
    head = p[: keep // 2 - 2]
    tail = p[-(keep // 2 - 1):]
    return f"{head}...{tail}"


def fold_to_top_n(items, n=7):
    """items: list of (label, size). Returns top-n by size + one 'Other' bucket."""
    items = sorted(items, key=lambda x: -x[1])
    top = items[:n]
    rest = items[n:]
    other_total = sum(s for _, s in rest)
    if other_total > 0:
        top.append(("Other", other_total))
    return top


def stacked_bar(segments, total, bar_id, width=760, height=28):
    """segments: list of (label, size, hex_color). Returns (svg, legend_html)."""
    if total <= 0:
        total = 1
    gap = 2
    n = len(segments)
    usable = width - gap * (n - 1) if n > 1 else width
    x = 0
    rects = []
    for i, (label, size, color) in enumerate(segments):
        w = max(1, (size / total) * usable)
        rects.append(
            f'<rect x="{x:.2f}" y="0" width="{w:.2f}" height="{height}" '
            f'class="seg seg-{i}" style="--seg-color:{color}">'
            f'<title>{esc(label)}: {human_size(size)} ({size/total*100:.1f}%)</title></rect>'
        )
        x += w + gap

    svg = f"""
    <svg viewBox="0 0 {width} {height}" width="100%" height="{height}" class="stacked-bar" role="img"
         aria-label="Storage breakdown">
      <clipPath id="{bar_id}-clip"><rect x="0" y="0" width="{width}" height="{height}" rx="4" ry="4"/></clipPath>
      <g clip-path="url(#{bar_id}-clip)">
        <rect x="0" y="0" width="{width}" height="{height}" class="track"/>
        {''.join(rects)}
      </g>
    </svg>"""

    legend_rows = []
    for i, (label, size, color) in enumerate(segments):
        pct = size / total * 100
        legend_rows.append(f"""
        <div class="legend-row">
          <span class="swatch" style="--seg-color:{color}"></span>
          <span class="legend-label">{esc(label)}</span>
          <span class="legend-value">{human_size(size)}</span>
          <span class="legend-pct">{pct:.1f}%</span>
        </div>""")
    return svg, "".join(legend_rows)


def donut_chart(segments, total, size=150, stroke=20, center_label="", center_sub=""):
    """segments: list of (label, size, color). Renders an SVG ring chart with
    an optional number in the center - the right form for a 2-3 slice
    part-to-whole ratio (disk used/free, safe/critical), unlike a stacked bar
    which reads better for many categories."""
    import math
    if total <= 0:
        total = 1
    radius = (size - stroke) / 2
    circumference = 2 * math.pi * radius
    cx = cy = size / 2
    gap = 3
    offset = 0
    arcs = []
    for label, value, color in segments:
        frac = max(0, value) / total
        length = frac * circumference
        dash = max(0, length - gap) if length > gap else length
        arcs.append(
            f'<circle cx="{cx}" cy="{cy}" r="{radius:.2f}" fill="none" stroke="{color}" stroke-width="{stroke}" '
            f'stroke-dasharray="{dash:.2f} {max(0, circumference - dash):.2f}" stroke-dashoffset="{-offset:.2f}" '
            f'transform="rotate(-90 {cx} {cy})" stroke-linecap="round">'
            f'<title>{esc(label)}: {human_size(value)} ({frac * 100:.1f}%)</title></circle>'
        )
        offset += length

    center = ""
    if center_label:
        center = f'<text x="{cx}" y="{cy - 3}" text-anchor="middle" class="donut-center-label">{esc(center_label)}</text>'
        if center_sub:
            center += f'<text x="{cx}" y="{cy + 16}" text-anchor="middle" class="donut-center-sub">{esc(center_sub)}</text>'

    return f"""
    <svg viewBox="0 0 {size} {size}" width="{size}" height="{size}" class="donut" role="img" aria-label="chart">
      <circle cx="{cx}" cy="{cy}" r="{radius:.2f}" fill="none" stroke="var(--track)" stroke-width="{stroke}"/>
      {''.join(arcs)}
      {center}
    </svg>"""


def donut_legend(segments, total):
    if total <= 0:
        total = 1
    rows = []
    for label, value, color in segments:
        pct = value / total * 100
        rows.append(f"""
        <div class="legend-row">
          <span class="swatch" style="--seg-color:{color}"></span>
          <span class="legend-label">{esc(label)}</span>
          <span class="legend-value">{human_size(value)}</span>
          <span class="legend-pct">{pct:.1f}%</span>
        </div>""")
    return "".join(rows)


def compact_file_table(rows, table_id, is_folder=False):
    """rows: list of (path, size). A compact sortable table (name/size sort via
    a small shared client-side script) with a file-type icon and a shortened
    path that reveals the full path on hover/tap - replaces the old repetitive
    horizontal-bar list for these top-N sections."""
    body_rows = []
    for path, size in rows:
        name = os.path.basename(path.rstrip("\\")) or path
        ext = os.path.splitext(name)[1]
        row_icon = icon("folder-open", 16) if is_folder else file_icon(ext, 16)
        body_rows.append(f"""
        <tr data-name="{esc(name.lower())}" data-size="{size}">
          <td class="icon-cell">{row_icon}</td>
          <td class="name-cell">{esc(name)}</td>
          <td class="path-cell mono" data-tooltip="{esc(path)}">{esc(short_path(path, 56))}</td>
          <td class="mono size-cell">{human_size(size)}</td>
        </tr>""")

    return f"""
    <div class="table-toolbar">
      <button class="sort-th active" id="{table_id}-size-th" onclick="sortCompactTable('{table_id}','size',this)">Size <span class="arrow">&#9660;</span></button>
      &nbsp;&nbsp;
      <button class="sort-th" id="{table_id}-name-th" onclick="sortCompactTable('{table_id}','name',this)">Name <span class="arrow">&#9660;</span></button>
    </div>
    <table class="compact-table">
      <tbody id="{table_id}">{''.join(body_rows)}</tbody>
    </table>"""


SORT_SCRIPT = """
<script>
  const _sortState = {};
  function sortCompactTable(tbodyId, key, btn) {
    const tbody = document.getElementById(tbodyId);
    if (!tbody) return;
    const state = _sortState[tbodyId] || {};
    const dir = (state.key === key && state.dir === 'desc') ? 'asc' : 'desc';
    _sortState[tbodyId] = { key, dir };
    const rows = Array.from(tbody.children);
    rows.sort((a, b) => {
      const av = key === 'size' ? Number(a.dataset.size) : a.dataset.name;
      const bv = key === 'size' ? Number(b.dataset.size) : b.dataset.name;
      const cmp = av < bv ? -1 : av > bv ? 1 : 0;
      return dir === 'desc' ? -cmp : cmp;
    });
    rows.forEach((r) => tbody.appendChild(r));
    const toolbar = btn.closest('.table-toolbar');
    toolbar.querySelectorAll('.sort-th').forEach((b) => {
      b.classList.remove('active');
      b.querySelector('.arrow').innerHTML = '&#9660;';
    });
    btn.classList.add('active');
    btn.querySelector('.arrow').innerHTML = dir === 'desc' ? '&#9660;' : '&#9650;';
  }
</script>"""


def junk_status(size):
    gb = size / (1024 ** 3)
    if gb >= 5:
        return "critical"
    if gb >= 1:
        return "warning"
    if size > 0:
        return "good"
    return "neutral"


JUNK_TIPS = {
    "User Temp (%TEMP%)": "Safe to clear. These are leftover temp files from apps/installers. Close running apps first, then delete contents (not the folder itself).",
    "Windows Temp": "Safe to clear via Disk Cleanup (run as administrator) or Settings > System > Storage > Temporary files.",
    "Windows Update cache": "Safe to clear via Disk Cleanup > 'Windows Update Cleanup', or the built-in Storage Sense. It rebuilds automatically as needed.",
    "Windows.old (old OS backup)": "This is your previous Windows install, kept for ~10 days after an upgrade for rollback. If your PC is stable, remove it via Disk Cleanup > 'Previous Windows installation(s)'.",
    "Downloads folder": "Not automatically safe to delete — review manually. Old installers and duplicate downloads are usually the biggest offenders.",
    "Recycle Bin": "Safe to empty once you're sure you don't need anything in it.",
    "Explorer thumbnail cache": "Safe to clear via Disk Cleanup > 'Thumbnails'. It regenerates automatically.",
    "Chrome cache": "Safe to clear via Chrome Settings > Privacy > Clear browsing data > Cached images and files.",
    "Edge cache": "Safe to clear via Edge Settings > Privacy > Clear browsing data > Cached images and files.",
    "Windows Prefetch": "Leave this alone — Windows manages it automatically and clearing it can briefly slow app launches.",
}


def build_html(data, excel_href="storage_report.xlsx", interactive=False, clear_folder_url=None,
                pdf_href=None, folder_export_url=None, browse_url=None, open_path_url=None):
    disk = data["disk"]
    total, used, free = disk["total"], disk["used"], disk["free"]
    used_pct = used / total * 100 if total else 0
    safe_total = data.get("safe_total", 0)
    critical_total = data.get("critical_total", 0)
    scanned_total = data["scanned_total"] or 1
    safe_pct = safe_total / scanned_total * 100
    critical_pct = critical_total / scanned_total * 100
    root = data.get("root", "C:\\")

    # --- disk usage donut (used vs free) ---
    disk_donut = donut_chart(
        [("Used", used, ACCENT), ("Free", free, "var(--track)")], total,
        center_label=f"{used_pct:.0f}%", center_sub="full",
    )
    disk_legend = donut_legend([("Used", used, ACCENT), ("Free", free, "#829AB1")], total)

    # --- safe vs critical donut ---
    safe_donut = donut_chart(
        [("Your files", safe_total, CAT_COLORS[2]), ("System / app-critical", critical_total, "#829AB1")],
        scanned_total, center_label=f"{safe_pct:.0f}%", center_sub="reviewable",
    )
    safe_legend = donut_legend(
        [("Your files (reviewed)", safe_total, CAT_COLORS[2]), ("System / app-critical (excluded)", critical_total, "#829AB1")],
        scanned_total,
    )

    # --- category (file type) breakdown ---
    cat_items = list(data["category_sizes"].items())
    cat_folded = fold_to_top_n(cat_items, n=7)
    cat_segments = []
    for i, (label, size) in enumerate(cat_folded):
        color = OTHER_COLOR if label == "Other" else CAT_COLORS[i % len(CAT_COLORS)]
        cat_segments.append((label, size, color))
    cat_svg, cat_legend = stacked_bar(cat_segments, data["scanned_total"], "cattypes")

    # --- top-level folder breakdown ---
    folder_items = [(os.path.basename(p.rstrip("\\")) or p, s) for p, s in
                     ((x["path"], x["size"]) for x in data["top_level_folders"])]
    folder_folded = fold_to_top_n(folder_items, n=7)
    folder_segments = []
    for i, (label, size) in enumerate(folder_folded):
        color = OTHER_COLOR if label == "Other" else CAT_COLORS[i % len(CAT_COLORS)]
        folder_segments.append((label, size, color))
    folder_svg, folder_legend = stacked_bar(folder_segments, data["scanned_total"], "topfolders")

    # --- largest folders / files ---
    top_folders = [(x["path"], x["size"]) for x in data["top_folders"]]
    top_files = [(x["path"], x["size"]) for x in data["top_files"]]
    folders_html = compact_file_table(top_folders, "folders-body", is_folder=True)
    files_html = compact_file_table(top_files, "files-body", is_folder=False)

    # --- junk / cleanup guide ---
    junk_rows = []
    junk_sorted = sorted(data["junk"].items(), key=lambda kv: -kv[1]["size"])
    recoverable_estimate = 0
    clearable_labels_present = []
    for label, info in junk_sorted:
        if not info["exists"]:
            continue
        status = junk_status(info["size"])
        clearable = interactive and info.get("clearable") and clear_folder_url
        if label not in ("Downloads folder", "Windows Prefetch") and status in ("critical", "warning"):
            recoverable_estimate += info["size"]
        dot_color = STATUS[status]

        if clearable:
            clearable_labels_present.append(label)
            action_cell = (f'<button class="btn-clear" data-clear-label="{esc(label)}" '
                            f'onclick="clearLocation(this, this.dataset.clearLabel)">{icon("trash", 13)} Clear</button>')
        elif label == "Recycle Bin":
            action_cell = '<span class="clear-note">Empty via the Recycle Bin icon on your desktop</span>'
        elif label == "Downloads folder":
            action_cell = '<span class="clear-note">Review manually</span>'
        else:
            action_cell = '<span class="clear-note">Leave alone</span>'

        open_cell = ""
        if interactive and open_path_url:
            open_cell = (f'<button class="btn-open" onclick="openLocation(this)" '
                         f'data-open-path="{esc(info["path"])}">{icon("folder-open", 13)} Open</button>')

        junk_rows.append(f"""
        <tr data-label="{esc(label)}">
          <td class="badge-cell"><span class="status-dot" style="--dot-color:{dot_color}"></span>{esc(label)}</td>
          <td class="mono">{human_size(info['size'])}</td>
          <td class="path-cell mono">{esc(info['path'])}</td>
          <td class="tip-cell">{esc(JUNK_TIPS.get(label, ''))}</td>
          <td class="row-actions">{open_cell}{action_cell}</td>
        </tr>""")

    junk_section = ""
    if junk_rows:
        legend = f"""
    <div class="junk-legend">
      <span><span class="status-dot" style="--dot-color:{STATUS['critical']}"></span>5+ GB, worth clearing soon</span>
      <span><span class="status-dot" style="--dot-color:{STATUS['warning']}"></span>1&ndash;5 GB</span>
      <span><span class="status-dot" style="--dot-color:{STATUS['good']}"></span>Under 1 GB</span>
      <span><span class="status-dot" style="--dot-color:{STATUS['neutral']}"></span>Empty</span>
    </div>"""

        bulk_button = ""
        if interactive and clearable_labels_present and clear_folder_url:
            bulk_button = f"""
    <div class="clear-actions">
      <button class="btn-clear" id="clear-all-btn" onclick="clearAll()">Clear all safe caches ({len(clearable_labels_present)})</button>
    </div>"""

        junk_script = ""
        if interactive and (clear_folder_url or open_path_url):
            labels_json = "[" + ",".join(_js_str(l) for l in clearable_labels_present) + "]"
            junk_script = f"""
  <script>
    async function openLocation(btn) {{
      const path = btn.dataset.openPath;
      btn.disabled = true;
      try {{
        const res = await fetch({_js_str(open_path_url)}, {{
          method: 'POST', headers: {{'Content-Type': 'application/json'}},
          body: JSON.stringify({{path}}),
        }});
        const data = await res.json();
        if (!data.success) window.dsToast('Could not open: ' + data.reason, {{ type: 'error', duration: 9000 }});
      }} catch (e) {{
        window.dsToast('Request failed: ' + e, {{ type: 'error', duration: 9000 }});
      }} finally {{
        btn.disabled = false;
      }}
    }}
    async function clearOne(label) {{
      const res = await fetch({_js_str(clear_folder_url)}, {{
        method: 'POST', headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{label: label, confirm: true}})
      }});
      return res.json();
    }}
    async function clearLocation(btn, label) {{
      const ok = await window.dsConfirm(label, {{ title: 'Send the contents of this location to the Recycle Bin?', okLabel: 'Clear', danger: true }});
      if (!ok) return;
      btn.disabled = true;
      btn.textContent = 'Clearing...';
      try {{
        const data = await clearOne(label);
        const row = btn.closest('tr');
        if (data.success) {{
          row.classList.add('gone');
          btn.textContent = 'Cleared';
        }} else {{
          btn.disabled = false;
          btn.textContent = 'Clear';
          window.dsToast('Not cleared: ' + data.reason, {{ type: 'error', duration: 9000 }});
        }}
      }} catch (e) {{
        btn.disabled = false;
        btn.textContent = 'Clear';
        window.dsToast('Request failed: ' + e, {{ type: 'error', duration: 9000 }});
      }}
    }}
    async function clearAll() {{
      const labels = {labels_json};
      const ok = await window.dsConfirm(
        'Everything goes to the Recycle Bin, not a permanent delete.',
        {{ title: 'Clear all ' + labels.length + ' safe cache locations?', okLabel: 'Clear All', danger: true }}
      );
      if (!ok) return;
      const btn = document.getElementById('clear-all-btn');
      btn.disabled = true;
      for (const label of labels) {{
        btn.textContent = 'Clearing ' + label + '...';
        try {{
          const data = await clearOne(label);
          const row = document.querySelector('tr[data-label="' + label + '"]');
          if (row) {{
            row.classList.add('gone');
            const b = row.querySelector('.btn-clear');
            if (b) {{ b.disabled = true; b.textContent = data.success ? 'Cleared' : 'Failed'; }}
          }}
        }} catch (e) {{}}
      }}
      btn.textContent = 'Done';
    }}
  </script>"""

        junk_section = f"""
  <div class="card">
    <h2>How to free up space</h2>
    <div class="desc">Common junk/cache locations found on this machine. One click sends the contents to the Recycle Bin &mdash; nothing is permanently deleted.</div>
    {legend}
    {bulk_button}
    <table>
      <thead><tr><th>Location</th><th>Size</th><th>Path</th><th>What to do</th><th>Action</th></tr></thead>
      <tbody>{''.join(junk_rows)}</tbody>
    </table>
    <div class="callout">
      <b>Estimated easy wins: ~{human_size(recoverable_estimate)}</b> from temp files, caches, and update leftovers alone (excludes Downloads, which needs a manual review).
    </div>
    <ul class="tips">
      <li><b>Run Disk Cleanup as administrator</b> (search "Disk Cleanup" &rarr; "Clean up system files") to safely remove temp files, old Windows installs, and update leftovers in one pass.</li>
      <li><b>Turn on Storage Sense</b> (Settings &rarr; System &rarr; Storage) to auto-clear temp files and old Recycle Bin/Downloads items on a schedule.</li>
      <li><b>Review large installed programs</b> (Settings &rarr; Apps) &mdash; anything under "Program Files" in the folder breakdown above that you no longer use.</li>
      <li><b>Check the "Largest individual files" table above</b> for forgotten downloads, old ISOs/installers, or duplicate media &mdash; these are often multi-GB single items.</li>
      <li><b>Move rarely-used large files</b> (old videos, project archives) to an external drive or cloud storage instead of deleting.</li>
    </ul>
  </div>
  {junk_script}"""

    scan_note = ""
    if data["inaccessible"] > 0:
        scan_note = (f"{data['inaccessible']:,} folders/files were skipped (no permission to read — "
                     f"mostly protected system areas and other user profiles), so totals are a "
                     f"best-effort lower bound.")

    export_card = ""
    if interactive:
        export_card = f"""
  <div class="card" id="export-card">
    <h2>Export</h2>
    <div class="desc">Get the data out in the format you need &mdash; the full report, just one folder, or a printable PDF snapshot.</div>
    <div class="export-row">
      <a class="btn" href="{esc(excel_href)}" download>{icon('file-doc', 15)} Full Excel Report</a>
      {f'<a class="btn secondary" href="{esc(pdf_href)}" download>{icon("file-doc", 15)} PDF Summary</a>' if pdf_href else ''}
    </div>
    {f'''
    <div class="export-folder-row">
      <input type="text" id="export-folder-input" placeholder="C:\\Users\\you\\Documents">
      <button class="btn secondary" type="button" onclick="browseExportFolder()">{icon('folder-open', 15)} Browse&hellip;</button>
      <button class="btn" type="button" onclick="exportFolder()">{icon('file-doc', 15)} Export This Folder</button>
    </div>
    <div class="note">Exports every indexed file (&ge; 256&nbsp;KB) under the chosen folder, from the last scan.</div>
    <script>
      async function browseExportFolder() {{
        const btn = event.target.closest('button');
        const original = btn.innerHTML;
        btn.disabled = true;
        try {{
          const res = await fetch({browse_url!r}, {{ method: 'POST' }});
          const data = await res.json();
          if (data.success) document.getElementById('export-folder-input').value = data.path;
          else if (data.reason && data.reason !== 'No folder selected.') window.dsToast('Could not open folder picker: ' + data.reason, {{ type: 'error', duration: 9000 }});
        }} catch (e) {{ window.dsToast('Request failed: ' + e, {{ type: 'error', duration: 9000 }}); }}
        finally {{ btn.disabled = false; btn.innerHTML = original; }}
      }}
      async function exportFolder() {{
        const folder = document.getElementById('export-folder-input').value.trim();
        if (!folder) {{ window.dsToast('Enter or browse to a folder first.', {{ type: 'error' }}); return; }}
        const btn = event.target.closest('button');
        const original = btn.innerHTML;
        btn.disabled = true;
        btn.textContent = 'Exporting...';
        try {{
          const res = await fetch({folder_export_url!r}, {{
            method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify({{folder}}),
          }});
          if (res.ok) {{
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url; a.download = 'folder_export.xlsx';
            document.body.appendChild(a); a.click(); a.remove();
            URL.revokeObjectURL(url);
          }} else {{
            const data = await res.json();
            window.dsToast('Not exported: ' + data.reason, {{ type: 'error', duration: 9000 }});
          }}
        }} catch (e) {{ window.dsToast('Request failed: ' + e, {{ type: 'error', duration: 9000 }}); }}
        finally {{ btn.disabled = false; btn.innerHTML = original; }}
      }}
    </script>''' if folder_export_url and browse_url else ''}
  </div>"""

    body = f"""
  <div class="top-row">
    <div>
      <h1>{esc(BRAND_NAME)} &mdash; {esc(root)}</h1>
      <div class="subtitle">Scanned {esc(data['scanned_at'])} &middot; {data['file_count']:,} files across {data['dir_count']:,} folders in {data['elapsed_seconds']}s</div>
    </div>
  </div>
  {export_card}

  <div class="stat-tiles">
    <div class="stat-tile"><div class="v">{human_size(total)}</div><div class="l">Total capacity</div></div>
    <div class="stat-tile"><div class="v">{human_size(used)}</div><div class="l">Used ({used_pct:.0f}%)</div></div>
    <div class="stat-tile"><div class="v">{human_size(free)}</div><div class="l">Free space</div></div>
    <div class="stat-tile"><div class="v">{data['file_count']:,}</div><div class="l">Files scanned</div></div>
    <div class="stat-tile"><div class="v">{data['dir_count']:,}</div><div class="l">Folders scanned</div></div>
  </div>
  {f'<div class="note" style="margin:-10px 0 20px">{esc(scan_note)}</div>' if scan_note else ''}

  <div class="dashboard-grid" style="margin-bottom:20px">
    <div class="card">
      <h2>Disk usage</h2>
      <div class="desc">How full the {esc(os.path.splitdrive(root)[0] or root)} drive is right now.</div>
      <div class="donut-layout">
        {disk_donut}
        <div class="donut-legend">{disk_legend}</div>
      </div>
    </div>

    <div class="card">
      <h2>Safe-to-review vs. critical data</h2>
      <div class="desc">Windows, installed programs, and app configs are excluded from cleanup entirely.</div>
      <div class="donut-layout">
        {safe_donut}
        <div class="donut-legend">{safe_legend}</div>
      </div>
    </div>

    <div class="card">
      <h2>Where your data lives (by folder)</h2>
      <div class="desc">Top-level folders under {esc(root)}, by size.</div>
      {folder_svg}
      <div class="legend">{folder_legend}</div>
    </div>

    <div class="card">
      <h2>What your data is (by file type)</h2>
      <div class="desc">All scanned files grouped by category, out of {human_size(data['scanned_total'])} scanned.</div>
      {cat_svg}
      <div class="legend">{cat_legend}</div>
    </div>
  </div>

  <div class="card">
    <h2>Largest folders</h2>
    <div class="desc">The biggest space users, any depth.</div>
    {folders_html}
  </div>

  <div class="card">
    <h2>Largest individual files</h2>
    <div class="desc">Top {len(top_files)} <b>safe-to-delete</b> files by size — system and application-critical files are already filtered out. Full list ({data.get('safe_files_count', 0):,} files &ge; 1&nbsp;MB) is in the Excel download above.</div>
    {files_html}
  </div>
{junk_section}
{SORT_SCRIPT}"""

    return render_page(f"{BRAND_NAME} Dashboard", body, extra_css=CHART_CSS, active="results", page_title="Results")
