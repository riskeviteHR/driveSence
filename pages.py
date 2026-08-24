"""HTML page builders for the web app's non-dashboard screens: setup, login,
home, scan form/progress, and audit logs."""

from flask import url_for

from theme import (ACCENT, BRAND_NAME, BRAND_TAGLINE, NAVY_ON_ACCENT, SUCCESS,
                    esc, human_size, icon, progress_ring, render_page)

EXTRA_CSS = f"""
  .auth-logo {{ display:block; width: 96px; height: 96px; margin: 0 auto 12px; object-fit: contain; }}
  .auth-brand {{ text-align:center; font-size: 22px; font-weight: 800; margin-bottom: 2px; }}
  .auth-tagline {{ text-align:center; font-size: 12px; color: var(--text-muted); margin-bottom: 22px; }}

  .spinner {{ width: 28px; height: 28px; border-radius: 50%; border: 3px solid var(--track);
             border-top-color: {ACCENT}; animation: spin 0.8s linear infinite; margin: 20px auto; }}
  @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
  .progress-msg {{ text-align:center; color: var(--text-secondary); font-size: 13px; }}

  .filter-bar {{ display:flex; gap: 10px; flex-wrap: wrap; align-items:center; margin: 0 0 16px; }}
  .filter-bar input[type=text] {{ max-width: 320px; flex: 1 1 220px; }}
  .filter-bar select {{ padding: 9px 10px; border-radius: 8px; border: 1px solid var(--border); background: var(--track); color: var(--text-primary); font-size: 13px; }}
  .filter-bar .result-count {{ color: var(--text-muted); font-size: 12px; margin-left: auto; white-space: nowrap; }}
  .path-cell {{ color: var(--text-secondary); }}
  .btn-sm {{ padding: 5px 12px !important; font-size: 12px !important; }}

  /* ---- dashboard KPI + quick-action cards ---- */
  .kpi-grid {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 14px; margin-bottom: 20px; }}
  .kpi-card {{ display:flex; align-items:center; gap: 14px; }}
  .kpi-ring {{ flex-shrink:0; }}
  .kpi-figure {{ font-size: 21px; font-weight: 800; line-height:1.15; }}
  .kpi-label {{ font-size: 11.5px; color: var(--text-muted); margin-top: 3px; }}
  .kpi-icon {{ display:inline-flex; align-items:center; justify-content:center; width:40px; height:40px;
               border-radius: 10px; background: var(--tile-bg); color: {ACCENT}; flex-shrink:0; }}

  .quick-grid {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px; margin: 20px 0; }}
  .quick-card {{ display:flex; flex-direction:column; gap: 10px; text-decoration:none !important; padding: 18px 18px;
                 transition: transform .15s ease, box-shadow .15s ease; }}
  .quick-card:hover {{ transform: translateY(-2px); box-shadow: 0 10px 26px rgba(16,42,67,0.12); }}
  :root[data-theme="dark"] .quick-card:hover {{ box-shadow: 0 10px 26px rgba(0,0,0,0.4); }}
  .quick-card .qc-icon {{ display:inline-flex; align-items:center; justify-content:center; width:38px; height:38px;
                           border-radius: 10px; background: var(--tile-bg); color: {ACCENT}; }}
  .quick-card .qc-title {{ font-size: 14px; font-weight: 700; color: var(--text-primary); }}
  .quick-card .qc-desc {{ font-size: 12px; color: var(--text-muted); line-height:1.5; }}

  /* ---- hero scan CTA ---- */
  .hero-card {{ text-align:center; padding: 36px 28px 30px; }}
  .hero-card h1 {{ font-size: 24px; margin: 4px 0 6px; }}
  .hero-icon {{ display:inline-flex; align-items:center; justify-content:center; width:64px; height:64px;
                border-radius: 50%; background: var(--tile-bg); color: {ACCENT}; margin-bottom: 10px; }}
  .btn-hero {{ font-size: 15px; padding: 14px 30px; border-radius: 11px; }}
  .hero-secondary {{ margin-top: 12px; font-size: 12.5px; }}
  .hero-secondary a {{ text-decoration: none; }}
  .hero-secondary a:hover {{ text-decoration: underline; }}

  /* ---- journey stepper ---- */
  .journey-stepper {{ display:flex; align-items:flex-start; justify-content:center; gap: 0; margin: 32px 0 8px;
                       max-width: 640px; margin-left:auto; margin-right:auto; }}
  .step {{ display:flex; flex-direction:column; align-items:center; gap: 6px; flex: 0 1 130px; text-align:center; }}
  .step-num {{ display:flex; align-items:center; justify-content:center; width:30px; height:30px; border-radius:50%;
               background: var(--track); color: var(--text-muted); font-size:13px; font-weight:700; flex-shrink:0; }}
  .step.current .step-num {{ background: {ACCENT}; color: {NAVY_ON_ACCENT}; }}
  .step.done .step-num {{ background: {SUCCESS}; color: #fff; }}
  .step-label {{ font-size: 12.5px; font-weight:700; color: var(--text-secondary); }}
  .step.current .step-label {{ color: var(--text-primary); }}
  .step-desc {{ font-size: 10.5px; color: var(--text-muted); line-height:1.4; }}
  .step-line {{ flex: 1 1 auto; height: 2px; background: var(--border); margin-top: 15px; min-width: 16px; }}

  /* ---- safety trust panel ---- */
  .safety-panel {{ display:flex; flex-wrap:wrap; justify-content:center; gap: 10px; margin-top: 28px; }}
  .safety-item {{ display:flex; align-items:center; gap: 8px; background: var(--tile-bg); color: var(--text-secondary);
                   font-size: 12px; font-weight: 600; padding: 9px 14px; border-radius: 999px; }}
  .safety-item svg {{ color: {SUCCESS}; flex-shrink:0; }}
"""


def _auth_header():
    return f"""
    <img class="auth-logo" src="/static/logo.png" alt="{esc(BRAND_NAME)}">
    <div class="auth-brand">{esc(BRAND_NAME)}</div>
    <div class="auth-tagline">{esc(BRAND_TAGLINE)}</div>"""


def setup_page(error=None):
    err = f'<div class="alert error">{icon("alert", 16)}{esc(error)}</div>' if error else ""
    body = f"""
  <div class="card form-card">
    {_auth_header()}
    <div class="desc">This protects the dashboard with a local username and password. Only stored on this PC.</div>
    {err}
    <form method="post">
      <div class="field"><label>Username</label><input type="text" name="username" autofocus required></div>
      <div class="field"><label>Password</label><input type="password" name="password" required></div>
      <div class="field"><label>Confirm password</label><input type="password" name="confirm" required></div>
      <button class="btn" type="submit" style="width:100%">Create login</button>
    </form>
  </div>"""
    return render_page(f"Set up login - {BRAND_NAME}", body, extra_css=EXTRA_CSS)


def login_page(error=None):
    err = f'<div class="alert error">{icon("alert", 16)}{esc(error)}</div>' if error else ""
    body = f"""
  <div class="card form-card">
    {_auth_header()}
    {err}
    <form method="post">
      <div class="field"><label>Username</label><input type="text" name="username" autofocus required></div>
      <div class="field"><label>Password</label><input type="password" name="password" required></div>
      <button class="btn" type="submit" style="width:100%">Log in</button>
    </form>
  </div>"""
    return render_page(f"Log in - {BRAND_NAME}", body, extra_css=EXTRA_CSS)


def _journey_stepper(scanned):
    steps = [
        ("scan", "Scan", "Look at what's on your computer"),
        ("review", "Review", "See what's taking up space"),
        ("clean", "Clean", "Remove what you approve"),
        ("restore", "Restore", "Undo anytime, nothing is final"),
    ]
    # Nothing here is destructive to compute this way: "done"/"current" are
    # purely illustrative signposting (has a scan run yet or not), not a
    # tracked workflow state - simple and honest about what it's showing.
    cells = []
    for i, (key, label, desc) in enumerate(steps):
        state = "done" if (scanned and i == 0) else ("current" if (i == 1 and scanned) or (i == 0 and not scanned) else "")
        cells.append(f"""
        <div class="step {state}">
          <div class="step-num">{icon('check-circle', 15) if state == 'done' else i + 1}</div>
          <div class="step-label">{esc(label)}</div>
          <div class="step-desc">{esc(desc)}</div>
        </div>""")
        if i < len(steps) - 1:
            cells.append('<div class="step-line"></div>')
    return f'<div class="journey-stepper">{"".join(cells)}</div>'


def _safety_panel():
    items = [
        ("check-circle", "Nothing is deleted without your approval"),
        ("exclusions", "System files are always protected"),
        ("undo", "Deleted files can be restored from the Recycle Bin"),
    ]
    cells = "".join(
        f'<div class="safety-item">{icon(i, 17)}<span>{esc(t)}</span></div>' for i, t in items
    )
    return f'<div class="safety-panel">{cells}</div>'


def home_page(username, data):
    kpis = ""
    if data:
        safe_pct = (data.get("safe_total", 0) / data["scanned_total"] * 100) if data["scanned_total"] else 0
        disk = data.get("disk") or {}
        used_pct = (disk["used"] / disk["total"] * 100) if disk.get("total") else 0
        kpis = f"""
  <div class="kpi-grid">
    <div class="card kpi-card">
      {progress_ring(safe_pct, size=58, stroke=6)}
      <div><div class="kpi-figure">{human_size(data.get('safe_total', 0))}</div><div class="kpi-label">Space you could reclaim</div></div>
    </div>
    <div class="card kpi-card">
      {progress_ring(used_pct, size=58, stroke=6, color="var(--text-muted)")}
      <div><div class="kpi-figure">{used_pct:.0f}% full</div><div class="kpi-label">{esc(data.get('root', 'C:\\\\'))} drive</div></div>
    </div>
    <div class="card kpi-card advanced-only">
      <div class="kpi-icon">{icon('scan', 20)}</div>
      <div><div class="kpi-figure">{data['file_count']:,}</div><div class="kpi-label">Files scanned</div></div>
    </div>
    <div class="card kpi-card">
      <div class="kpi-icon">{icon('audit', 20)}</div>
      <div><div class="kpi-figure">{esc(data['scanned_at'].split(' ')[0])}</div><div class="kpi-label">Last scan date</div></div>
    </div>
  </div>"""
    else:
        kpis = f'<div class="card"><div class="empty-state"><div class="icon">{icon("dashboard", 32)}</div>' \
               '<div class="t">No scan yet</div><div class="d">Scan your computer below to see what\'s using space.</div></div></div>'

    hero = f"""
  <div class="card hero-card">
    <div class="hero-icon">{icon('scan', 30)}</div>
    <h1>Find and safely clean up wasted space</h1>
    <div class="subtitle" style="margin-bottom:20px">One click looks at your whole computer. Nothing is touched until you say so.</div>
    <form method="post" action="{url_for('scan')}">
      <input type="hidden" name="root" value="C:\\">
      <button class="btn btn-hero" type="submit">{icon('scan', 18)} Scan My Computer</button>
    </form>
    <div class="hero-secondary advanced-only"><a href="{url_for('scan')}">Scan a specific folder instead &rarr;</a></div>
    {_journey_stepper(bool(data))}
    {_safety_panel()}
  </div>"""

    body = f"""
  <h1>Welcome, {esc(username)}</h1>
  <div class="subtitle">Your computer's storage, made simple.</div>
  {hero}
  {kpis}
  <div class="quick-grid">
    <a class="card quick-card" href="{url_for('cleanup')}">
      <div class="qc-icon">{icon('cleanup', 19)}</div>
      <div class="qc-title">Review &amp; Clean Up</div>
      <div class="qc-desc">See what's safe to remove and what needs a quick look first.</div>
    </a>
    <a class="card quick-card" href="{url_for('results')}">
      <div class="qc-icon">{icon('results', 19)}</div>
      <div class="qc-title">See What's Using Space</div>
      <div class="qc-desc">A full breakdown of your storage, in plain language.</div>
    </a>
    <a class="card quick-card" href="{url_for('audit')}">
      <div class="qc-icon">{icon('undo', 19)}</div>
      <div class="qc-title">Restore Deleted Files</div>
      <div class="qc-desc">Changed your mind? Bring anything back in one click.</div>
    </a>
    <a class="card quick-card advanced-only" href="{url_for('exclusions_page')}">
      <div class="qc-icon">{icon('exclusions', 19)}</div>
      <div class="qc-title">Exclusions</div>
      <div class="qc-desc">Manage paths the scanner should always skip.</div>
    </a>
  </div>"""
    return render_page(BRAND_NAME, body, extra_css=EXTRA_CSS, active="dashboard", page_title="Dashboard")


def scan_form_page(default_root, error=None):
    err = f'<div class="alert error">{icon("alert", 16)}{esc(error)}</div>' if error else ""
    body = f"""
  <h1>Scan Your Folder</h1>
  <div class="subtitle">Enter a folder path to analyze. Use a drive root (e.g. C:\\) for the fullest picture, including junk/cache detection.</div>
  <div class="card">
    {err}
    <form method="post">
      <div class="field">
        <label>Folder to scan</label>
        <input type="text" name="root" value="{esc(default_root)}" autofocus required>
      </div>
      <button class="btn" type="submit">Start Scan</button>
    </form>
    <div class="note">Scanning a full drive can take 1&ndash;3 minutes depending on how many files you have, plus extra time to hash files for duplicate detection. You can pause and resume from the progress screen, and leave the tab open &mdash; it'll move to the results automatically.</div>
  </div>"""
    return render_page("Scan Your Folder", body, extra_css=EXTRA_CSS, active="scan")


def scan_progress_page():
    body = f"""
  <h1>Scanning&hellip;</h1>
  <div class="card">
    <div class="spinner" id="spinner"></div>
    <div class="progress-msg" id="msg">Starting...</div>
    <div style="text-align:center;margin-top:16px">
      <button class="btn secondary" id="pause-btn" onclick="togglePause()">Pause</button>
    </div>
  </div>
  <script>
    let paused = false;
    async function togglePause() {{
      const url = paused ? "{url_for('scan_resume')}" : "{url_for('scan_pause')}";
      await fetch(url, {{method: 'POST'}});
      paused = !paused;
      document.getElementById('pause-btn').textContent = paused ? 'Resume' : 'Pause';
      document.getElementById('spinner').style.animationPlayState = paused ? 'paused' : 'running';
    }}
    async function poll() {{
      try {{
        const res = await fetch("{url_for('scan_status')}");
        const s = await res.json();
        document.getElementById('msg').textContent = (s.paused ? '(paused) ' : '') + (s.message || 'Working...');
        if (s.error) {{
          document.getElementById('msg').textContent = 'Scan failed: ' + s.error;
          return;
        }}
        if (!s.running) {{
          window.location.href = "{url_for('results')}";
          return;
        }}
      }} catch (e) {{}}
      setTimeout(poll, 1200);
    }}
    poll();
  </script>"""
    return render_page("Scanning...", body, extra_css=EXTRA_CSS, active="scan")


def audit_page(entries, restore_url=None):
    scan_entries = [e for e in entries if "type" not in e]
    action_entries = [e for e in entries if e.get("type") in ("deletion", "clear_folder", "restore")]

    # A path counts as "already restored" if a later successful restore entry
    # exists for it - keeps the Restore button state correct even after a
    # page reload, without needing separate storage for restore status.
    latest_restore_ts = {}
    for e in action_entries:
        if e.get("type") == "restore" and e.get("result") == "restored":
            p = e.get("path", "")
            if p not in latest_restore_ts or e["timestamp"] > latest_restore_ts[p]:
                latest_restore_ts[p] = e["timestamp"]

    scan_rows = []
    for e in scan_entries:
        folder = e.get("root", "")
        if e.get("status") == "error":
            scan_rows.append(f"""
            <tr data-folder="{esc(folder)}" data-status="error">
              <td class="mono">{esc(e.get('timestamp', ''))}</td>
              <td>{esc(folder)}</td>
              <td colspan="5"><span class="status-pill bad">Failed</span> {esc(e.get('error', 'unknown error'))}</td>
            </tr>""")
            continue
        safe_pct = (e.get("safe_total", 0) / e["scanned_total"] * 100) if e.get("scanned_total") else 0
        dup_note = ""
        if e.get("duplicate_groups") is not None:
            dup_note = f" &middot; {e['duplicate_groups']} dup groups"
        scan_rows.append(f"""
        <tr data-folder="{esc(folder)}" data-status="success">
          <td class="mono">{esc(e.get('timestamp', ''))}</td>
          <td>{esc(folder)}</td>
          <td class="mono">{e.get('file_count', 0):,}</td>
          <td class="mono">{e.get('dir_count', 0):,}</td>
          <td class="mono">{e.get('elapsed_seconds', 0)}s</td>
          <td class="mono">{human_size(e.get('scanned_total', 0))}</td>
          <td class="mono">{human_size(e.get('safe_total', 0))} ({safe_pct:.0f}%){dup_note}</td>
        </tr>""")

    scan_filter = ""
    scan_table = f'<div class="empty-state"><div class="icon">{icon("audit", 30)}</div><div class="t">No scans yet</div><div class="d">Run a scan to see history here.</div></div>'
    if scan_rows:
        scan_filter = """
    <div class="filter-bar">
      <input type="text" id="s-search" placeholder="Search by folder..." oninput="filterScans()">
      <select id="s-status" onchange="filterScans()">
        <option value="all">All results</option>
        <option value="success">Succeeded</option>
        <option value="error">Failed</option>
      </select>
      <button class="btn secondary btn-sm" onclick="clearScanFilters()">Clear Filters</button>
      <span class="result-count" id="s-count"></span>
    </div>"""
        scan_table = f"""
    <table>
      <thead><tr><th>When</th><th>Folder</th><th>Files</th><th>Dirs</th><th>Duration</th><th>Scanned</th><th>Safe to review</th></tr></thead>
      <tbody>{''.join(scan_rows)}</tbody>
    </table>"""

    del_rows = []
    del_categories = set()
    for e in action_entries:
        etype = e.get("type")
        result = e.get("result", "")
        category = "restore" if etype == "restore" else e.get("category", "")
        del_categories.add(category)
        pill_cls = "neutral"
        if result in ("deleted", "restored"):
            pill_cls = "good"
        elif result in ("refused", "error"):
            pill_cls = "bad"
        size_cell = "&mdash;" if etype == "restore" else human_size(e.get("size", 0))

        action_cell = "&mdash;"
        if etype == "deletion" and result == "deleted":
            path = e.get("path", "")
            if latest_restore_ts.get(path, "") > e.get("timestamp", ""):
                action_cell = '<span class="status-pill good">Restored</span>'
            else:
                action_cell = (
                    f'<button class="btn secondary btn-sm" data-path="{esc(path)}" '
                    f'onclick="restoreItem(this)">{icon("undo", 13)} Restore</button>'
                )

        del_rows.append(f"""
        <tr data-path="{esc(e.get('path', ''))}" data-cat="{esc(category)}" data-result="{esc(result)}">
          <td class="mono">{esc(e.get('timestamp', ''))}</td>
          <td class="path-cell mono" style="max-width:300px;overflow:hidden;text-overflow:ellipsis" data-tooltip="{esc(e.get('path', ''))}">{esc(e.get('path', ''))}</td>
          <td>{esc(category)}</td>
          <td class="mono">{size_cell}</td>
          <td><span class="status-pill {pill_cls}">{esc(result)}</span></td>
          <td style="color:var(--text-secondary)">{esc(e.get('detail', ''))}</td>
          <td>{action_cell}</td>
        </tr>""")

    del_filter = ""
    del_table = f'<div class="empty-state"><div class="icon">{icon("cleanup", 30)}</div><div class="t">No cleanup actions yet</div><div class="d">Deletions and restores will show up here.</div></div>'
    if del_rows:
        cat_options = "".join(f'<option value="{esc(c)}">{esc(c)}</option>' for c in sorted(del_categories))
        del_filter = f"""
    <div class="filter-bar">
      <input type="text" id="d-search" placeholder="Search by path..." oninput="filterActions()">
      <select id="d-category" onchange="filterActions()">
        <option value="all">All categories</option>
        {cat_options}
      </select>
      <select id="d-result" onchange="filterActions()">
        <option value="all">All results</option>
        <option value="deleted">Deleted</option>
        <option value="restored">Restored</option>
        <option value="refused">Refused</option>
        <option value="error">Error</option>
      </select>
      <button class="btn secondary btn-sm" onclick="clearActionFilters()">Clear Filters</button>
      <span class="result-count" id="d-count"></span>
    </div>"""
        del_table = f"""
    <table>
      <thead><tr><th>When</th><th>Path</th><th>Category</th><th>Size</th><th>Result</th><th>Detail</th><th>Action</th></tr></thead>
      <tbody>{''.join(del_rows)}</tbody>
    </table>"""

    body = f"""
  <h1>Audit Logs</h1>
  <div class="subtitle">Full history: every scan and every cleanup action (including refused ones), so nothing happens silently.</div>
  <div class="card">
    <h2>Scan history</h2>
    {scan_filter}
    {scan_table}
  </div>
  <div class="card">
    <h2>Cleanup activity</h2>
    {del_filter}
    {del_table}
  </div>
  <script>
    function filterScans() {{
      const q = (document.getElementById('s-search') || {{value:''}}).value.toLowerCase();
      const status = (document.getElementById('s-status') || {{value:'all'}}).value;
      let shown = 0, total = 0;
      document.querySelectorAll('tr[data-folder]').forEach(row => {{
        total++;
        const folder = row.getAttribute('data-folder').toLowerCase();
        const rowStatus = row.getAttribute('data-status');
        const matches = folder.includes(q) && (status === 'all' || status === rowStatus);
        row.style.display = matches ? '' : 'none';
        if (matches) shown++;
      }});
      const el = document.getElementById('s-count');
      if (el) el.textContent = (q || status !== 'all') ? shown + ' of ' + total + ' shown' : '';
    }}
    function clearScanFilters() {{
      const s = document.getElementById('s-search'); if (s) s.value = '';
      const st = document.getElementById('s-status'); if (st) st.value = 'all';
      filterScans();
    }}
    function filterActions() {{
      const q = (document.getElementById('d-search') || {{value:''}}).value.toLowerCase();
      const cat = (document.getElementById('d-category') || {{value:'all'}}).value;
      const result = (document.getElementById('d-result') || {{value:'all'}}).value;
      let shown = 0, total = 0;
      document.querySelectorAll('tr[data-path]').forEach(row => {{
        total++;
        const path = row.getAttribute('data-path').toLowerCase();
        const rowCat = row.getAttribute('data-cat');
        const rowResult = row.getAttribute('data-result');
        const matches = path.includes(q) && (cat === 'all' || cat === rowCat) && (result === 'all' || result === rowResult);
        row.style.display = matches ? '' : 'none';
        if (matches) shown++;
      }});
      const el = document.getElementById('d-count');
      if (el) el.textContent = (q || cat !== 'all' || result !== 'all') ? shown + ' of ' + total + ' shown' : '';
    }}
    function clearActionFilters() {{
      const s = document.getElementById('d-search'); if (s) s.value = '';
      const c = document.getElementById('d-category'); if (c) c.value = 'all';
      const r = document.getElementById('d-result'); if (r) r.value = 'all';
      filterActions();
    }}
    async function restoreItem(btn) {{
      const path = btn.getAttribute('data-path');
      const ok = await window.dsConfirm(path, {{ title: 'Restore this file to its original location?', okLabel: 'Restore' }});
      if (!ok) return;
      btn.disabled = true;
      btn.textContent = 'Restoring...';
      try {{
        const res = await fetch({restore_url!r}, {{
          method: 'POST', headers: {{'Content-Type': 'application/json'}},
          body: JSON.stringify({{path}}),
        }});
        const data = await res.json();
        if (data.success) {{
          btn.outerHTML = '<span class="status-pill good">Restored</span>';
        }} else {{
          btn.disabled = false;
          btn.textContent = 'Restore';
          window.dsToast('Not restored: ' + data.reason, {{ type: 'error', duration: 9000 }});
        }}
      }} catch (e) {{
        btn.disabled = false;
        btn.textContent = 'Restore';
        window.dsToast('Request failed: ' + e, {{ type: 'error', duration: 9000 }});
      }}
    }}
  </script>"""
    return render_page("Audit Logs", body, extra_css=EXTRA_CSS, active="audit")
