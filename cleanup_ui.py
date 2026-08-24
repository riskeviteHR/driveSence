"""Cleanup Center page: duplicates, temp/cache, old downloads, large files,
and the unknown/manual-review queue. Data-heavy rendering (search, filter,
sort, virtualized scrolling, side panel, bulk actions) lives client-side in
static/cleanup.js and is fed by the /cleanup/data JSON endpoint - this module
just renders the page shell, since generating HTML for tens of thousands of
rows server-side doesn't scale."""

from flask import url_for

from theme import ACCENT, CRITICAL, CRITICAL_TEXT_ON_LIGHT, SUCCESS, WARNING, human_size, icon, render_page

EXTRA_CSS = f"""
  .top-row {{ display:flex; justify-content: space-between; align-items:flex-start; gap: 16px; flex-wrap: wrap; margin-bottom: 4px; }}

  .stat-tiles {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin: 16px 0 20px; }}
  .stat-tile {{ background: var(--tile-bg); border-radius: 10px; padding: 14px 16px; }}
  .stat-tile .v {{ font-size: 20px; font-weight: 700; }}
  .stat-tile .l {{ font-size: 11.5px; color: var(--text-muted); margin-top: 2px; }}

  :root {{ --risk-low: {SUCCESS}; --risk-med: {WARNING}; --risk-high: {CRITICAL}; }}

  .filter-bar {{ display:flex; gap: 10px; flex-wrap: wrap; align-items:center; margin: 4px 0 18px;
                 background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 12px; padding: 12px 14px; }}
  .filter-bar input[type=text] {{ max-width: 240px; flex: 1 1 180px; }}
  .filter-bar select {{ padding: 9px 10px; border-radius: 8px; border: 1px solid var(--border); background: var(--track); color: var(--text-primary); font-size: 13px; }}
  .filter-bar .result-count {{ color: var(--text-muted); font-size: 12px; margin-left: auto; white-space: nowrap; }}

  .tier-tabs {{ display:flex; gap: 4px; background: var(--track); border-radius: 9px; padding: 3px; }}
  .tier-tab {{ display:inline-flex; align-items:center; gap:5px; background:none; border:none; color: var(--text-secondary);
               font-size: 12.5px; font-weight: 600; padding: 7px 12px; border-radius: 7px; cursor:pointer; font-family:inherit;
               transition: all .15s ease; white-space:nowrap; }}
  .tier-tab:hover {{ color: var(--text-primary); }}
  .tier-tab.active {{ background: var(--card-bg); color: var(--text-primary); box-shadow: var(--shadow); }}
  .clean-all-row {{ display:flex; align-items:center; gap: 14px; flex-wrap:wrap; margin-top: -2px; margin-bottom: 16px; }}
  .clean-all-hint {{ font-size: 11.5px; color: var(--text-muted); }}
  .simple-label {{ color: var(--text-secondary); font-size: 11.5px; line-height:1.4; }}

  .risk-badge {{ display:inline-flex; align-items:center; gap:6px; font-size: 11px; font-weight: 700;
                padding: 3px 10px 3px 8px; border-radius: 999px; white-space:nowrap;
                background: var(--track); color: var(--text-primary); }}
  .risk-dot {{ width:7px; height:7px; border-radius:50%; flex-shrink:0; }}
  .conf {{ color: var(--text-muted); font-size: 11px; margin-left: 4px; }}
  .section-empty {{ color: var(--text-muted); font-size: 12.5px; padding: 8px 0; }}

  .btn-del {{ background: transparent; border: 1px solid var(--border); color: var(--text-primary);
             font-size: 12px; font-weight: 600; padding: 5px 10px; border-radius: 6px; cursor:pointer;
             font-family:inherit; transition: all .15s ease; white-space: nowrap; display:inline-flex; align-items:center; gap:5px; }}
  /* Hover text is a darker red by default (readable on the light cards/panels
     these buttons normally sit on) and switches to the lighter shade only in
     dark mode - a flat light-pink hover color here previously washed out to
     near-illegible on white/light backgrounds, reading as a disabled button
     even though it was fully clickable. */
  .btn-del:hover {{ border-color: {CRITICAL}; color: {CRITICAL_TEXT_ON_LIGHT}; background: rgba(239,68,68,0.14); }}
  :root[data-theme="dark"] .btn-del:hover {{ color: #FCA5A5; }}
  .btn-del[disabled] {{ opacity: 0.5; cursor: not-allowed; background: var(--track) !important; color: var(--text-muted) !important; border-color: var(--border) !important; }}

  #cleanup-loading {{ color: var(--text-muted); font-size: 13px; padding: 20px 0; }}

  .vlist-head {{ display:flex; align-items:center; gap: 10px; padding: 6px 10px; font-size: 11px; font-weight:600;
                 text-transform: uppercase; letter-spacing: .03em; color: var(--text-muted); border-bottom: 1px solid var(--border); }}
  .vlist {{ position: relative; height: 460px; overflow-y: auto; border-radius: 8px; }}
  .vlist-spacer {{ position: relative; }}
  .vlist-range {{ font-size: 11.5px; color: var(--text-muted); margin-top: 8px; text-align: right; }}

  .vrow {{ display:flex; align-items:center; gap: 10px; padding: 0 10px; height: {40}px; box-sizing: border-box;
           border-bottom: 1px solid var(--border); cursor: pointer; transition: background-color .1s ease; }}
  .vrow:hover {{ background: var(--track); }}
  .vrow-extra {{ height: 34px; padding-left: 28px; background: var(--track); }}
  .vcell-check {{ flex: 0 0 22px; }}
  .vcell-check input {{ cursor: pointer; }}
  .vcell-icon {{ flex: 0 0 18px; color: var(--text-muted); display:flex; }}
  .vcell-path {{ flex: 1 1 auto; min-width: 0; font-family: ui-monospace, Consolas, monospace; font-size: 11.5px;
                 color: var(--text-secondary); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
  .vcell-cat {{ flex: 0 0 100px; font-size: 11.5px; color: var(--text-muted); }}
  .vcell-size {{ flex: 0 0 80px; text-align:right; font-size: 12px; }}
  .vcell-risk {{ flex: 0 0 130px; }}
  .vcell-actions {{ flex: 0 0 110px; text-align: right; display:flex; gap:6px; justify-content:flex-end; }}
  .btn-open-file {{ padding: 5px 8px !important; }}

  .dup-header {{ display:flex; justify-content:space-between; align-items:flex-start; gap: 14px; margin-bottom: 4px; flex-wrap: wrap; }}
  .dup-header-actions {{ display:flex; gap: 8px; flex-wrap: wrap; flex-shrink: 0; }}
  .dup-header .btn-del {{ flex-shrink: 0; padding: 8px 14px; }}

  .vgroup {{ position: relative; }}
  .vgroup-header {{ display:flex; align-items:center; gap: 10px; padding: 0 10px; height: 60px; box-sizing: border-box;
                     border-bottom: 1px solid var(--border); cursor: pointer; font-size: 12.5px; color: var(--text-secondary); }}
  .vgroup-header:hover {{ background: var(--track); }}
  .vgroup-caret {{ flex: 0 0 14px; color: var(--text-muted); display:flex; transition: transform .15s ease; }}
  .vgroup-caret.open {{ transform: rotate(90deg); }}
  .vgroup-title {{ flex: 0 0 auto; color: var(--text-primary); }}
  .vgroup-title b {{ color: var(--text-primary); }}
  .vgroup-keeper {{ margin-left: auto; font-family: ui-monospace, Consolas, monospace; font-size: 11px;
                     color: var(--text-muted); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width: 380px; }}

  .cleanup-layout {{ display:flex; gap: 20px; align-items: flex-start; }}
  .cleanup-main {{ flex: 1 1 auto; min-width: 0; }}

  .side-panel {{ position: fixed; top: 0; right: -420px; width: 400px; max-width: 92vw; height: 100vh; background: var(--panel-bg);
                 border-left: 1px solid var(--border); box-shadow: -8px 0 24px rgba(0,0,0,0.2); padding: 24px 22px;
                 transition: right .2s ease; overflow-y: auto; z-index: 50; color: var(--text-primary); }}
  .side-panel.open {{ right: 0; }}
  .side-panel h3 {{ margin: 0 0 4px; font-size: 15px; word-break: break-all; }}
  .side-panel .panel-close {{ position:absolute; top: 18px; right: 18px; background:none; border:none; color: var(--text-muted);
                               font-size: 20px; cursor:pointer; line-height:1; }}
  .panel-row {{ margin-top: 16px; }}
  .panel-row .k {{ font-size: 11px; text-transform: uppercase; letter-spacing: .03em; color: var(--text-muted); margin-bottom: 4px; }}
  .panel-row .v {{ font-size: 13px; color: var(--text-primary); word-break: break-word; }}
  .panel-row .v.mono {{ font-family: ui-monospace, Consolas, monospace; font-size: 11.5px; word-break: break-all; }}
  .panel-btn-row {{ display:flex; gap: 10px; }}
  .panel-btn-row .btn-del {{ flex: 1 1 0; padding: 10px; }}

  .bulk-toolbar {{ display:flex; align-items:center; gap: 10px; margin-bottom: 10px; flex-wrap: wrap; }}
  .bulk-bar {{ position: sticky; bottom: 16px; display:none; align-items:center; gap: 14px; background: var(--panel-bg);
               border: 1px solid var(--border); border-radius: 12px; padding: 12px 18px; margin-top: 16px;
               box-shadow: 0 8px 26px rgba(16,42,67,0.18); color: var(--text-primary); flex-wrap: wrap; }}
  :root[data-theme="dark"] .bulk-bar {{ box-shadow: 0 8px 26px rgba(0,0,0,0.4); }}
  .bulk-bar b {{ font-size: 13px; }}
  .bulk-reclaim {{ display:flex; flex-direction:column; line-height:1.25; margin-right:auto; }}
  .bulk-reclaim .amt {{ font-size: 15px; font-weight: 800; color: {ACCENT}; }}
  .bulk-reclaim .lbl {{ font-size: 10.5px; color: var(--text-muted); text-transform:uppercase; letter-spacing:.03em; }}

  .modal-overlay {{ position: fixed; inset: 0; background: rgba(4,10,20,0.55); display:none;
                     align-items: center; justify-content: center; z-index: 100; padding: 20px; box-sizing: border-box; }}
  .modal-overlay.open {{ display: flex; }}
  .modal-box {{ background: var(--panel-bg); color: var(--text-primary); border-radius: 14px; padding: 24px 26px;
                width: 100%; max-width: 540px; max-height: 82vh; display:flex; flex-direction: column;
                box-shadow: 0 12px 40px rgba(0,0,0,0.35); }}
  .modal-box h3 {{ margin: 0 0 4px; font-size: 17px; }}
  .modal-sub {{ font-size: 12.5px; color: var(--text-muted); margin-bottom: 14px; }}
  .modal-stats {{ display:flex; gap: 18px; flex-wrap: wrap; margin-bottom: 14px; font-size: 12.5px; }}
  .modal-stats b {{ display:block; font-size: 17px; color: {ACCENT}; }}
  .modal-note {{ font-size: 12px; color: {WARNING}; background: rgba(245,158,11,0.12);
                 border: 1px solid rgba(245,158,11,0.3); border-radius: 8px; padding: 8px 12px; margin-bottom: 12px; }}
  .modal-list {{ flex: 1 1 auto; overflow-y: auto; border: 1px solid var(--border); border-radius: 8px;
                 font-family: ui-monospace, Consolas, monospace; font-size: 11.5px; }}
  .modal-list-row {{ display:flex; justify-content: space-between; gap: 10px; padding: 6px 10px;
                      border-bottom: 1px solid var(--border); color: var(--text-secondary); }}
  .modal-list-row:last-child {{ border-bottom: none; }}
  .modal-list-row span:first-child {{ overflow:hidden; text-overflow:ellipsis; white-space:nowrap; min-width:0; }}
  .modal-list-row span:last-child {{ flex: 0 0 auto; color: var(--text-muted); }}
  .modal-more {{ padding: 8px 10px; color: var(--text-muted); font-style: italic; }}
  .modal-actions {{ display:flex; justify-content:flex-end; gap: 10px; margin-top: 18px; }}

  .toast {{ position: fixed; left: 50%; bottom: 26px; transform: translate(-50%, 20px); z-index: 200;
            display:flex; align-items:center; gap: 14px; background: {ACCENT}; color: {"#0B2540"};
            font-size: 13px; font-weight: 600; padding: 12px 16px; border-radius: 11px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.25); opacity:0; pointer-events:none; transition: all .2s ease; }}
  .toast.show {{ opacity:1; transform: translate(-50%, 0); pointer-events:auto; }}
  .toast button {{ background: rgba(11,37,64,0.14); border:none; color:{"#0B2540"}; font-weight:700; font-size:12.5px;
                    padding:6px 12px; border-radius:7px; cursor:pointer; white-space:nowrap; }}
  .toast button:hover {{ background: rgba(11,37,64,0.24); }}
"""


def cleanup_page(report, dup_stats, exclusions_list):
    counts = report["counts"]
    tiles = f"""
    <div class="stat-tiles">
      <div class="stat-tile"><div class="v">{human_size(report['recoverable_estimate_bytes'])}</div><div class="l">Estimated recoverable</div></div>
      <div class="stat-tile"><div class="v">{human_size(report['duplicates']['total_waste_bytes'])}</div><div class="l">Duplicate waste ({counts['duplicates']} files)</div></div>
      <div class="stat-tile"><div class="v">{counts['temp_cache']}</div><div class="l">Temp/cache files</div></div>
      <div class="stat-tile"><div class="v">{counts['old_downloads']}</div><div class="l">Old downloads</div></div>
      <div class="stat-tile"><div class="v">{counts['large_files']}</div><div class="l">Large files to review</div></div>
      <div class="stat-tile"><div class="v">{counts['unknown']}</div><div class="l">Unknown - needs review</div></div>
    </div>"""

    dup_hashed_note = ""
    if dup_stats:
        dup_hashed_note = (f'<div class="note">Hashed {dup_stats["candidates_hashed"]:,} candidate files '
                            f'({dup_stats["cache_hits"]:,} reused from the last scan\'s cache) to verify duplicates.</div>')

    excl_note = ""
    if exclusions_list:
        excl_note = (f'<div class="note">{len(exclusions_list)} path(s) on your exclusion list are never scanned '
                      f'or recommended. <a href="{url_for("exclusions_page")}">Manage exclusions</a>.</div>')

    filter_bar = f"""
    <div class="filter-bar">
      <input type="text" id="f-search" placeholder="Search by name..." oninput="onFilterChange()">
      <div class="tier-tabs simple-only">
        <button class="tier-tab active" data-tier="all" onclick="window.setTierFilter('all', this)">All</button>
        <button class="tier-tab" data-tier="safe" onclick="window.setTierFilter('safe', this)">{icon('check-circle', 13)} Safe to Remove</button>
        <button class="tier-tab" data-tier="review" onclick="window.setTierFilter('review', this)">{icon('alert', 13)} Review Required</button>
      </div>
      <select id="f-category" class="advanced-only" onchange="onFilterChange()">
        <option value="all">All categories</option>
        <option value="duplicate">Duplicates</option>
        <option value="temp_cache">Temp/Cache</option>
        <option value="old_download">Old Downloads</option>
        <option value="large_file">Large Files</option>
        <option value="unknown">Unknown</option>
      </select>
      <select id="f-risk" class="advanced-only" onchange="onFilterChange()">
        <option value="all">All risk levels</option>
        <option value="low">Low risk</option>
        <option value="medium">Medium risk</option>
        <option value="high">High risk</option>
      </select>
      <input type="text" id="f-minsize" class="advanced-only" placeholder="Min MB" style="max-width:90px" oninput="onFilterChange()">
      <input type="text" id="f-maxsize" class="advanced-only" placeholder="Max MB" style="max-width:90px" oninput="onFilterChange()">
      <input type="text" id="f-location" class="advanced-only" placeholder="Folder contains..." style="max-width:180px" oninput="onFilterChange()">
      <select id="f-sort" class="advanced-only" onchange="onSortChange()">
        <option value="size_desc">Largest first</option>
        <option value="size_asc">Smallest first</option>
        <option value="filename_asc">File name (A-Z)</option>
        <option value="risk_desc">Highest risk first</option>
        <option value="count_desc">Most copies first</option>
      </select>
      <button class="btn secondary btn-sm" onclick="window.clearAllFilters()">Clear Filters</button>
    </div>
    <div class="simple-only clean-all-row">
      <button class="btn" onclick="window.cleanAllSafe()">{icon('trash', 15)} Clean All Safe Items</button>
      <span class="clean-all-hint">Duplicates and temp/cache files &mdash; the routine, low-risk stuff. Everything else waits for your review.</span>
    </div>"""

    body = f"""
  <div class="top-row">
    <div>
      <h1>Cleanup Center</h1>
      <div class="subtitle simple-only">Review what's safe to remove and what's worth a quick look first. Nothing is deleted until you approve it.</div>
      <div class="subtitle advanced-only">Deny-by-default: protected system/app files never appear here. Unknown file types always require manual confirmation. Duplicates always keep at least one copy. Every delete goes to the Recycle Bin, never a permanent delete.</div>
    </div>
    <a class="btn secondary advanced-only" href="{url_for('download_excel_cleanup')}" download>{icon('file-doc', 15)} Download Excel</a>
  </div>
  <div class="card">
    <h2>Recoverable space</h2>
    {tiles}
    {dup_hashed_note}
    {excl_note}
  </div>

  <div id="cleanup-loading">Loading file data&hellip;</div>
  <div id="cleanup-content" style="display:none">
    {filter_bar}

    <div class="cleanup-layout">
      <div class="cleanup-main">
        <div class="card" id="dup-section">
          <div class="dup-header">
            <div>
              <h2>Duplicates</h2>
              <div class="desc">Verified by SHA-256 content hash, not just size/name. The oldest copy in each group is always kept. Click a group to expand it.</div>
            </div>
            <div class="dup-header-actions">
              <button class="btn secondary btn-sm" onclick="window.selectAllDuplicates()">{icon('check-circle', 14)} Select All Duplicates</button>
              <button class="btn-del" onclick="window.deleteAllDuplicates()">{icon('trash', 14)} Delete All Duplicates</button>
            </div>
          </div>
          <div class="vlist" id="dup-list"><div class="vlist-spacer" id="dup-spacer"></div></div>
          <div class="vlist-range" id="dup-range"></div>
        </div>
        <div class="section-empty" id="dup-empty" style="display:none">No verified duplicates found.</div>

        <div class="card">
          <h2>Files</h2>
          <div class="desc">Temp/cache, old downloads, large files, and unknown types - filtered and sorted above. Click a row for full details.</div>
          <div class="bulk-toolbar">
            <button class="btn secondary btn-sm" onclick="window.selectAllFiltered()">{icon('check-circle', 14)} Select All</button>
          </div>
          <div class="vlist-head">
            <span style="flex:0 0 22px"></span>
            <span style="flex:0 0 18px"></span>
            <span style="flex:1 1 auto">Path</span>
            <span style="flex:0 0 100px">Category</span>
            <span style="flex:0 0 80px;text-align:right">Size</span>
            <span style="flex:0 0 130px">Risk</span>
            <span style="flex:0 0 110px"></span>
          </div>
          <div class="vlist" id="file-list" style="height:560px"><div class="vlist-spacer" id="file-spacer"></div></div>
          <div class="section-empty" id="files-empty" style="display:none">No files match your filters.</div>
          <div class="vlist-range" id="files-range"></div>
        </div>

        <div class="bulk-bar" id="bulk-bar">
          <div class="bulk-reclaim">
            <span class="amt" id="bulk-reclaim-amt">0 B</span>
            <span class="lbl">Reclaimable space</span>
          </div>
          <b id="bulk-count"></b>
          <button class="btn secondary" onclick="window.openBulkPreview()">Review Selected</button>
          <button class="btn secondary" onclick="window.clearSelection()">Clear selection</button>
        </div>
      </div>
    </div>
  </div>

  <div class="side-panel" id="side-panel">
    <button class="panel-close" onclick="window.closePanel()" aria-label="Close">&times;</button>
    <h3 id="panel-filename"></h3>
    <div class="panel-row"><div class="k">Full path</div><div class="v mono" id="panel-path"></div></div>
    <div class="panel-row"><div class="k">Size</div><div class="v" id="panel-size"></div></div>
    <div class="panel-row"><div class="k">Category</div><div class="v" id="panel-cat"></div></div>
    <div class="panel-row"><div class="k">Risk</div><div class="v" id="panel-risk"></div></div>
    <div class="panel-row"><div class="k">Age</div><div class="v" id="panel-age"></div></div>
    <div class="panel-row"><div class="k">Why this was flagged</div><div class="v" id="panel-reason"></div></div>
    <div class="panel-row advanced-only"><div class="k">Technical details</div><div class="v" id="panel-reason-technical" style="color:var(--text-muted);font-size:12px"></div></div>
    <div class="panel-row panel-btn-row">
      <button class="btn-del" id="panel-open-btn" style="justify-content:center">{icon('folder-open', 14)} Open</button>
      <button class="btn-del" id="panel-delete-btn" style="justify-content:center">Delete</button>
    </div>
  </div>

  <div class="modal-overlay" id="preview-modal">
    <div class="modal-box">
      <h3 id="preview-title">Review selected files</h3>
      <div class="modal-sub">Confirm what will be sent to the Recycle Bin.</div>
      <div class="modal-stats">
        <div><b id="preview-count">0</b> files</div>
        <div><b id="preview-size">0 B</b> total size</div>
      </div>
      <div class="modal-note" id="preview-unknown-note" style="display:none"></div>
      <div class="modal-list" id="preview-list"></div>
      <div class="modal-actions">
        <button class="btn secondary" onclick="window.closeBulkPreview()">Cancel</button>
        <button class="btn-del" id="preview-confirm-btn" style="padding:10px 18px" onclick="window.confirmBulkPreview()">Clean Selected</button>
      </div>
    </div>
  </div>

  <div class="toast" id="toast">
    <span id="toast-msg"></span>
    <button id="toast-action" style="display:none"></button>
  </div>

  <script>
    window.CLEANUP_URLS = {{ dataUrl: {url_for('cleanup_data')!r}, deleteUrl: {url_for('delete_item')!r}, restoreUrl: {url_for('restore_item')!r}, openUrl: {url_for('open_path')!r} }};
  </script>
  <script src="/static/cleanup.js"></script>
"""
    return render_page("Cleanup Center", body, extra_css=EXTRA_CSS, active="cleanup")
