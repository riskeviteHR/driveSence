"""Exclusions management page: paths the scanner should never walk and the
cleanup engine should never recommend touching."""

from flask import url_for

from theme import esc, icon, render_page

EXTRA_CSS = """
  .excl-row { display:flex; align-items:center; gap:10px; padding: 10px 4px; border-bottom: 1px solid var(--border); font-size: 12.5px; }
  .excl-row:last-child { border-bottom: none; }
  .excl-row .excl-icon { color: var(--text-muted); flex-shrink:0; display:flex; }
  .excl-path { font-family: ui-monospace, Consolas, monospace; color: var(--text-secondary); flex: 1 1 auto; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }

  .path-input-row { display:flex; gap: 10px; align-items:stretch; }
  .path-input-row input[type=text] { flex: 1 1 auto; }

  .drop-zone { margin-top: 14px; border: 2px dashed var(--border); border-radius: 12px; padding: 22px;
               text-align:center; color: var(--text-muted); font-size: 12.5px; transition: all .15s ease; }
  .drop-zone.drag-over { border-color: var(--accent-text); background: var(--tile-bg); color: var(--text-primary); }
  .drop-zone .dz-icon { margin-bottom: 8px; opacity: .6; }
"""


def exclusions_page(items, error=None):
    err = f'<div class="alert error">{icon("alert", 16)}{esc(error)}</div>' if error else ""

    rows = "".join(f"""
        <div class="excl-row">
          <span class="excl-icon">{icon('folder-open', 16)}</span>
          <span class="excl-path" title="{esc(p)}">{esc(p)}</span>
          <form method="post" action="{url_for('exclusions_remove')}" style="margin:0">
            <input type="hidden" name="path" value="{esc(p)}">
            <button class="btn secondary btn-sm" type="submit">Remove</button>
          </form>
        </div>""" for p in items) or (
        f'<div class="empty-state"><div class="icon">{icon("exclusions", 30)}</div>'
        '<div class="t">No exclusions yet</div><div class="d">Add a folder above to keep it out of every scan.</div></div>'
    )

    body = f"""
  <h1>Exclusions</h1>
  <div class="subtitle">Paths here are never walked during a scan and never suggested for cleanup - a hard boundary the deletion engine also enforces.</div>
  <div class="card">
    {err}
    <form method="post" action="{url_for('exclusions_add')}" id="excl-form">
      <div class="field">
        <label>Folder or file path to exclude</label>
        <div class="path-input-row">
          <input type="text" name="path" id="excl-path-input" placeholder="C:\\Users\\you\\Documents\\Work" required>
          <button class="btn secondary" type="button" onclick="browseFolder()">{icon('folder-open', 15)} Browse&hellip;</button>
        </div>
      </div>
      <button class="btn" type="submit">Add exclusion</button>
    </form>
    <div class="drop-zone" id="drop-zone">
      <div class="dz-icon">{icon('drag', 24)}</div>
      <div>Drag a folder here from File Explorer, or use <b>Browse&hellip;</b> above for a reliable folder picker.</div>
    </div>
  </div>
  <div class="card">
    <h2>Current exclusions ({len(items)})</h2>
    {rows}
  </div>
  <script>
    async function browseFolder() {{
      const btn = event.target.closest('button');
      const original = btn.innerHTML;
      btn.disabled = true;
      try {{
        const res = await fetch({url_for('exclusions_browse')!r}, {{ method: 'POST' }});
        const data = await res.json();
        if (data.success) {{
          document.getElementById('excl-path-input').value = data.path;
        }} else if (data.reason && data.reason !== 'No folder selected.') {{
          window.dsToast('Could not open folder picker: ' + data.reason, {{ type: 'error', duration: 9000 }});
        }}
      }} catch (e) {{
        window.dsToast('Request failed: ' + e, {{ type: 'error', duration: 9000 }});
      }} finally {{
        btn.disabled = false;
        btn.innerHTML = original;
      }}
    }}

    const dz = document.getElementById('drop-zone');
    ['dragenter', 'dragover'].forEach((evt) => dz.addEventListener(evt, (e) => {{
      e.preventDefault(); dz.classList.add('drag-over');
    }}));
    ['dragleave', 'drop'].forEach((evt) => dz.addEventListener(evt, (e) => {{
      e.preventDefault(); dz.classList.remove('drag-over');
    }}));
    dz.addEventListener('drop', (e) => {{
      const file = e.dataTransfer.files && e.dataTransfer.files[0];
      // Browsers deliberately don't expose the real filesystem path for
      // security reasons in most cases - `.path` only exists in a few
      // embedded/legacy contexts. When it's there, use it; otherwise point
      // the user at the reliable native picker instead of failing silently.
      if (file && file.path) {{
        document.getElementById('excl-path-input').value = file.path;
      }} else {{
        window.dsToast("Your browser doesn't expose the full folder path for drag-and-drop. Use \\"Browse...\\" above instead, or paste the path manually.", {{ duration: 9000 }});
      }}
    }});
  </script>"""
    return render_page("Exclusions", body, extra_css=EXTRA_CSS, active="exclusions")
