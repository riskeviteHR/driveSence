"""Shared visual design system for every page in the app: a persistent left
sidebar (fixed navy chrome, consistent on every screen, active item
highlighted) plus a light-canvas content area of compact white/glass cards -
replacing the old design where every card was itself a large dark-navy block
regardless of light/dark mode. Text/track/border tokens are defined once on
:root for each theme (light default, dark override) and both the page canvas
and card surfaces now read the *same* tokens, since card backgrounds are
theme-aware too - no more per-component light/dark branching needed anywhere
else in the app.
"""

import base64
import html
from pathlib import Path

from flask import request, url_for

BRAND_NAME = "DriveSense"
BRAND_TAGLINE = "Smarter Storage. Safer Cleanup."


def _load_favicon_base64():
    favicon_path = Path(__file__).resolve().parent / "static" / "favicon.png"
    try:
        return base64.b64encode(favicon_path.read_bytes()).decode("ascii")
    except OSError:
        return ""


FAVICON_B64 = _load_favicon_base64()

# ---- fixed palette --------------------------------------------------------
PAGE_BG = "#F5F7FA"
NAVBAR_BG = "#0B1F33"
CARD_BG = "#102A43"          # dark-mode card surface (kept for reference/back-compat)
CARD_INNER_BG = "#243B53"
TEXT_ON_DARK = "#F8FAFC"
BORDER = "#D9E2EC"

ACCENT = "#00B8D9"
ACCENT_HOVER = "#00A3BF"
ACCENT_TEXT_ON_LIGHT = "#007A8C"   # readable accent for text/links sitting on the light page
NAVY_ON_ACCENT = "#0B2540"         # button text color on accent-colored backgrounds (passes AA; near-navbar shade)

SUCCESS = "#22C55E"
WARNING = "#F59E0B"
CRITICAL = "#EF4444"
SUCCESS_TEXT_ON_LIGHT = "#15803D"
WARNING_TEXT_ON_LIGHT = "#B45309"
CRITICAL_TEXT_ON_LIGHT = "#DC2626"

# Chart/badge colors - always rendered against a theme-aware card surface now,
# so these stay vivid enough to read on either a white or dark-navy card.
CAT_COLORS = [ACCENT, WARNING, SUCCESS, "#818CF8", "#F472B6", "#38BDF8", "#FB923C"]
OTHER_COLOR = "#829AB1"
SEQ_BLUE = ACCENT  # kept as an alias so any stray reference still resolves sensibly
STATUS = {"critical": CRITICAL, "warning": WARNING, "good": SUCCESS, "neutral": "#829AB1"}


def esc(s):
    return html.escape(str(s))


def human_size(n):
    n = float(n)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if n < 1024 or unit == "TB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


# ---- icon set --------------------------------------------------------------
# Minimal hand-authored line icons (stroke=currentColor) so every icon tints
# correctly wherever it's dropped - sidebar nav, KPI cards, file-type badges -
# with zero external font/icon-library dependency.
_ICON_PATHS = {
    "dashboard": '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/>'
                 '<rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    "scan": '<circle cx="9.5" cy="9.5" r="6"/><line x1="14" y1="14" x2="20" y2="20"/>',
    "results": '<line x1="4" y1="20" x2="20" y2="20"/><rect x="5" y="12" width="3.4" height="8"/>'
               '<rect x="10.3" y="7" width="3.4" height="13"/><rect x="15.6" y="3" width="3.4" height="17"/>',
    "cleanup": '<line x1="3" y1="6" x2="17" y2="6"/><path d="M6 6l1 12a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1l1-12"/>'
               '<line x1="8.5" y1="3" x2="11.5" y2="3"/><line x1="8.5" y1="3" x2="8.5" y2="6"/><line x1="11.5" y1="3" x2="11.5" y2="6"/>'
               '<line x1="8.5" y1="10" x2="8.5" y2="15"/><line x1="11.5" y1="10" x2="11.5" y2="15"/>',
    "audit": '<rect x="5" y="3" width="10" height="15" rx="1.5"/><line x1="8" y1="8" x2="12" y2="8"/>'
             '<line x1="8" y1="11.5" x2="12" y2="11.5"/><line x1="8" y1="15" x2="10.5" y2="15"/>'
             '<rect x="7.5" y="1.5" width="5" height="2.5" rx="0.6"/>',
    "exclusions": '<path d="M10 2.5l6.5 2.6v4.7c0 4.5-2.7 7.3-6.5 8.2-3.8-.9-6.5-3.7-6.5-8.2V5.1z"/>'
                  '<path d="M7.3 10.2l1.9 1.9 3.5-4"/>',
    "logout": '<path d="M9 3H4.6a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1H9"/><polyline points="13 15 17 10 13 5"/><line x1="17" y1="10" x2="7" y2="10"/>',
    "menu": '<line x1="3" y1="6" x2="17" y2="6"/><line x1="3" y1="10" x2="17" y2="10"/><line x1="3" y1="14" x2="17" y2="14"/>',
    "close": '<line x1="5" y1="5" x2="15" y2="15"/><line x1="15" y1="5" x2="5" y2="15"/>',
    "chevron-right": '<polyline points="7 4 13 10 7 16"/>',
    "folder-open": '<path d="M3 6a1 1 0 0 1 1-1h4l1.5 2H16a1 1 0 0 1 1 1v1H5.5a1 1 0 0 0-1 .8L3 15V6z"/>'
                   '<path d="M3.6 15l1.5-6.2a1 1 0 0 1 1-.8H17a1 1 0 0 1 1 1.2l-1.5 5a1 1 0 0 1-1 .8H4.6a1 1 0 0 1-1-1z"/>',
    "search": '<circle cx="9" cy="9" r="6.5"/><line x1="13.8" y1="13.8" x2="18.5" y2="18.5"/>',
    "trash": '<line x1="3" y1="6" x2="17" y2="6"/><path d="M6 6l1 12a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1l1-12"/>'
             '<line x1="8.5" y1="3" x2="11.5" y2="3"/><line x1="8.5" y1="3" x2="8.5" y2="6"/><line x1="11.5" y1="3" x2="11.5" y2="6"/>',
    "undo": '<polyline points="6 4 2 8 6 12"/><path d="M2 8h10a5 5 0 0 1 5 5v3"/>',
    "check-circle": '<circle cx="10" cy="10" r="7.5"/><polyline points="6.5 10.2 9 12.5 13.7 7.5"/>',
    "alert": '<path d="M10 2.5l8.5 15h-17z"/><line x1="10" y1="8" x2="10" y2="12"/><circle cx="10" cy="14.7" r="0.9" fill="currentColor" stroke="none"/>',
    "info": '<circle cx="10" cy="10" r="7.5"/><line x1="10" y1="9" x2="10" y2="14"/><circle cx="10" cy="6.3" r="0.9" fill="currentColor" stroke="none"/>',
    "file-doc": '<path d="M5 2.5h6l4 4v11a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1v-14a1 1 0 0 1 1-1z"/><path d="M11 2.5v4h4"/>'
                '<line x1="6.5" y1="11" x2="13.5" y2="11"/><line x1="6.5" y1="14" x2="13.5" y2="14"/>',
    "file-image": '<rect x="3" y="4" width="14" height="12" rx="1.2"/><circle cx="7" cy="8" r="1.3"/><path d="M4 14.5l3.5-3.8 2.5 2.5 3.5-4.2 3.5 5"/>',
    "file-video": '<rect x="3" y="4" width="14" height="12" rx="1.2"/><polygon points="8,7.8 8,12.2 12,10"/>',
    "file-audio": '<circle cx="6.5" cy="15" r="2"/><circle cx="14.5" cy="13" r="2"/><path d="M8.5 15V4.5l8-1.5v9"/>',
    "file-archive": '<rect x="4" y="3" width="12" height="14" rx="1.2"/><line x1="10" y1="3" x2="10" y2="17" stroke-dasharray="1.6 1.6"/>',
    "file-code": '<polyline points="7 6 2.5 10 7 14"/><polyline points="13 6 17.5 10 13 14"/>',
    "file-exe": '<rect x="3" y="5" width="14" height="10" rx="2"/><circle cx="10" cy="10" r="2.4"/>',
    "file-question": '<path d="M5 2.5h6l4 4v11a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1v-14a1 1 0 0 1 1-1z"/><path d="M11 2.5v4h4"/>'
                      '<text x="10" y="15.5" text-anchor="middle" font-size="7" font-weight="700" fill="currentColor" stroke="none">?</text>',
    "copy": '<rect x="7" y="7" width="10" height="10" rx="1.3"/><path d="M13 7V4a1 1 0 0 0-1-1H4a1 1 0 0 0-1 1v8a1 1 0 0 0 1 1h3"/>',
    "drag": '<circle cx="7" cy="5" r="1" fill="currentColor" stroke="none"/><circle cx="13" cy="5" r="1" fill="currentColor" stroke="none"/>'
            '<circle cx="7" cy="10" r="1" fill="currentColor" stroke="none"/><circle cx="13" cy="10" r="1" fill="currentColor" stroke="none"/>'
            '<circle cx="7" cy="15" r="1" fill="currentColor" stroke="none"/><circle cx="13" cy="15" r="1" fill="currentColor" stroke="none"/>',
}

EXT_ICON_MAP = {
    "doc": {".txt", ".pdf", ".doc", ".docx", ".rtf", ".odt", ".md", ".csv", ".xls", ".xlsx", ".ppt", ".pptx"},
    "image": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".heic", ".ico", ".tiff"},
    "video": {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v"},
    "audio": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma"},
    "archive": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".iso"},
    "code": {".py", ".js", ".ts", ".java", ".c", ".cpp", ".cs", ".html", ".css", ".json", ".xml", ".sh", ".go", ".rs"},
    "exe": {".exe", ".msi", ".bat", ".cmd", ".dll", ".sys"},
}
_EXT_TO_ICON = {ext: kind for kind, exts in EXT_ICON_MAP.items() for ext in exts}


def icon(name, size=18, cls=""):
    body = _ICON_PATHS.get(name, _ICON_PATHS["file-question"])
    cls_attr = f' class="{esc(cls)}"' if cls else ""
    return (f'<svg{cls_attr} width="{size}" height="{size}" viewBox="0 0 20 20" fill="none" '
            f'stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" '
            f'aria-hidden="true">{body}</svg>')


def file_icon(ext, size=16, cls=""):
    kind = _EXT_TO_ICON.get((ext or "").lower())
    name = f"file-{kind}" if kind else "file-question"
    return icon(name, size=size, cls=cls)


def progress_ring(pct, size=64, stroke=7, color=None, track_color="var(--track)"):
    """A single-value progress ring (0-100), for compact KPI cards - distinct
    from generate_report.py's multi-segment donut_chart, which is for
    part-to-whole breakdowns rather than a single percentage."""
    import math
    color = color or ACCENT
    pct = max(0, min(100, pct))
    radius = (size - stroke) / 2
    circumference = 2 * math.pi * radius
    dash = circumference * pct / 100
    cx = cy = size / 2
    return f"""<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" class="progress-ring" role="img" aria-label="{pct:.0f}%">
      <circle cx="{cx}" cy="{cy}" r="{radius:.2f}" fill="none" stroke="{track_color}" stroke-width="{stroke}"/>
      <circle cx="{cx}" cy="{cy}" r="{radius:.2f}" fill="none" stroke="{color}" stroke-width="{stroke}"
              stroke-dasharray="{dash:.2f} {circumference:.2f}" stroke-linecap="round"
              transform="rotate(-90 {cx} {cy})"/>
      <text x="{cx}" y="{cy + 5}" text-anchor="middle" class="ring-label">{pct:.0f}%</text>
    </svg>"""


# ---- sidebar --------------------------------------------------------------
SIDEBAR_ITEMS = [
    ("dashboard", "Dashboard", "dashboard", "home"),
    ("scan", "Scan", "scan", "scan"),
    ("results", "Results", "results", "results"),
    ("cleanup", "Cleanup Center", "cleanup", "cleanup"),
    ("audit", "Audit Logs", "audit", "audit"),
    ("exclusions", "Exclusions", "exclusions", "exclusions_page"),
]


def _sidebar_html(active):
    logo_img = f'<img src="data:image/png;base64,{FAVICON_B64}" alt="">' if FAVICON_B64 else ""
    items = []
    for key, label, icon_name, endpoint in SIDEBAR_ITEMS:
        is_active = key == active
        items.append(
            f'<a class="side-link{" active" if is_active else ""}" href="{url_for(endpoint)}"'
            f'{" aria-current=\"page\"" if is_active else ""}>'
            f'<span class="side-icon">{icon(icon_name, 19)}</span><span class="side-label">{esc(label)}</span></a>'
        )
    return f"""
    <nav class="sidebar" id="sidebar">
      <div class="side-brand">{logo_img}<span>{esc(BRAND_NAME)}</span></div>
      <div class="side-links">{''.join(items)}</div>
      <div class="side-bottom">
        <a class="side-link logout" href="{url_for('logout')}">
          <span class="side-icon">{icon('logout', 19)}</span><span class="side-label">Logout</span>
        </a>
      </div>
    </nav>
    <div class="side-overlay" id="side-overlay" onclick="closeSidebar()"></div>"""


BASE_CSS = f"""
  :root {{
    --page: {PAGE_BG};
    --text-primary: #102A43;
    --text-secondary: #486581;
    --text-muted: #627D98;
    --border: {BORDER};
    --track: #E4E9F0;
    --track-hover: #DCE4EC;
    --shadow: 0 1px 2px rgba(16,42,67,0.05), 0 4px 14px rgba(16,42,67,0.07);
    --focus-ring: rgba(0,184,217,0.35);
    --accent-text: {ACCENT_TEXT_ON_LIGHT};
    --tile-bg: {ACCENT}0d;
    --panel-bg: #ffffff;
    --card-bg: #ffffff;
    --card-border: {BORDER};
    --sidebar-w: 232px;
  }}
  /* Dark mode: toggled via the header button, persisted in localStorage, applied
     on :root itself so every surface inherits correctly. Card/panel backgrounds
     are theme-aware tokens (not hardcoded navy) so the *same* text tokens work
     for both the page canvas and any card sitting on it in either theme. */
  :root[data-theme="dark"] {{
    --page: #0A1420;
    --text-primary: #F1F5F9;
    --text-secondary: #94A8C0;
    --text-muted: #6B84A0;
    --border: rgba(255,255,255,0.12);
    --track: #16212F;
    --track-hover: #1E2C3D;
    --shadow: 0 1px 2px rgba(0,0,0,0.3), 0 4px 14px rgba(0,0,0,0.35);
    --focus-ring: rgba(0,184,217,0.4);
    --accent-text: {ACCENT};
    --tile-bg: rgba(0,184,217,0.12);
    --panel-bg: #102A43;
    --card-bg: #102A43;
    --card-border: rgba(255,255,255,0.10);
  }}
  * {{ box-sizing: border-box; overflow-wrap: break-word; }}
  body {{ margin:0; font-family: system-ui, -apple-system, "Segoe UI", sans-serif; background: var(--page); color: var(--text-primary); -webkit-font-smoothing: antialiased; }}

  /* ---- sidebar shell ---- */
  .sidebar {{ position: fixed; top:0; left:0; bottom:0; width: var(--sidebar-w); background: {NAVBAR_BG};
              display:flex; flex-direction:column; z-index: 60; transition: left .2s ease; }}
  .side-brand {{ display:flex; align-items:center; gap:9px; font-weight:800; font-size:15px; color:{TEXT_ON_DARK};
                 padding: 20px 20px 16px; }}
  .side-brand img {{ height:24px; width:24px; }}
  .side-links {{ display:flex; flex-direction:column; gap:2px; padding: 6px 12px; flex: 1 1 auto; overflow-y:auto; }}
  .side-link {{ display:flex; align-items:center; gap:11px; color:#B8C7D9; text-decoration:none; font-size:13.5px;
                font-weight:600; padding:10px 12px; border-radius:9px; transition: background-color .15s ease, color .15s ease; }}
  .side-icon {{ display:inline-flex; flex-shrink:0; opacity:.9; }}
  .side-link:hover {{ color:{TEXT_ON_DARK}; background: rgba(255,255,255,0.08); }}
  .side-link.active {{ color:{TEXT_ON_DARK}; background: rgba(0,184,217,0.16); box-shadow: inset 3px 0 0 {ACCENT}; }}
  .side-link.active .side-icon {{ color: {ACCENT}; opacity:1; }}
  .side-bottom {{ padding: 12px; border-top: 1px solid rgba(255,255,255,0.08); }}
  .side-link.logout:hover {{ color:#FCA5A5; background: rgba(239,68,68,0.16); }}
  .side-overlay {{ display:none; position: fixed; inset:0; background: rgba(4,10,20,0.5); z-index: 55; }}

  .main-shell {{ margin-left: var(--sidebar-w); min-height: 100vh; display:flex; flex-direction:column; }}
  .topbar {{ position: sticky; top:0; z-index: 40; display:flex; align-items:center; gap:12px;
             padding: 14px 32px; background: var(--page); backdrop-filter: blur(8px);
             border-bottom: 1px solid var(--border); }}
  .topbar .page-title {{ font-size:15px; font-weight:700; margin-right:auto; }}
  .menu-btn {{ display:none; background:none; border:none; color:var(--text-primary); cursor:pointer; padding:6px; border-radius:8px; }}
  .menu-btn:hover {{ background: var(--track); }}
  .theme-toggle {{ display:inline-flex; align-items:center; justify-content:center; width: 34px; height: 34px;
                    border-radius: 9px; border: 1px solid var(--border); background: var(--card-bg); color: var(--text-primary);
                    font-size: 15px; cursor: pointer; transition: background-color .15s ease; }}
  .theme-toggle:hover {{ background: var(--track); }}

  .advanced-switch {{ display:inline-flex; align-items:center; gap: 8px; cursor:pointer; padding: 6px 10px 6px 6px;
                       border-radius: 9px; border: 1px solid var(--border); background: var(--card-bg); user-select:none; }}
  .advanced-switch:hover {{ background: var(--track); }}
  .advanced-switch .lbl {{ font-size: 12px; font-weight: 600; color: var(--text-secondary); white-space:nowrap; }}
  .switch-track {{ position:relative; width: 34px; height: 19px; border-radius: 999px; background: var(--track); flex-shrink:0; transition: background-color .15s ease; }}
  .switch-track .knob {{ position:absolute; top: 2px; left: 2px; width: 15px; height: 15px; border-radius: 50%;
                          background: {TEXT_ON_DARK}; box-shadow: 0 1px 3px rgba(0,0,0,0.3); transition: transform .15s ease; }}
  :root[data-advanced="true"] .switch-track {{ background: {ACCENT}; }}
  :root[data-advanced="true"] .switch-track .knob {{ transform: translateX(15px); }}

  /* Advanced-mode gating: simple by default (matches the initial data-advanced
     value the anti-flash script sets before first paint), advanced-only
     elements revealed once the switch is on. Every page that doesn't care
     about this distinction just never uses these classes. */
  :root[data-advanced="true"] .simple-only {{ display:none !important; }}
  :root:not([data-advanced="true"]) .advanced-only {{ display:none !important; }}

  .viz-root {{ max-width: 1320px; width:100%; margin: 0 auto; padding: 24px 32px 60px; flex: 1 1 auto; }}
  @media (max-width: 980px) {{
    .sidebar {{ left: calc(-1 * var(--sidebar-w)); }}
    body.sidebar-open .sidebar {{ left: 0; box-shadow: 8px 0 30px rgba(0,0,0,0.3); }}
    body.sidebar-open .side-overlay {{ display:block; }}
    .main-shell {{ margin-left: 0; }}
    .menu-btn {{ display:inline-flex; }}
    .viz-root {{ padding: 18px 16px 48px; }}
    .topbar {{ padding: 12px 16px; }}
  }}

  h1 {{ font-size: 21px; margin: 0 0 2px; letter-spacing: -0.01em; font-weight: 800; }}
  h2 {{ font-size: 14.5px; margin: 0 0 4px; font-weight: 700; }}
  .subtitle {{ color: var(--text-secondary); font-size: 13px; margin-bottom: 22px; }}

  .card {{
    background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 14px; padding: 20px 22px;
    margin-bottom: 18px; overflow-x: auto; box-shadow: var(--shadow);
    color: var(--text-primary);
  }}
  .card .desc {{ color: var(--text-muted); font-size: 12.5px; margin: 0 0 16px; }}

  a {{ color: var(--accent-text); }}

  a:focus-visible, button:focus-visible, input:focus-visible, .tile:focus-visible, .side-link:focus-visible {{
    outline: 2px solid {ACCENT}; outline-offset: 2px; border-radius: 4px;
  }}

  .btn {{ display:inline-flex; align-items:center; justify-content:center; gap:7px; background: {ACCENT};
          color: {NAVY_ON_ACCENT} !important; text-decoration:none; font-size: 13px; font-weight: 700; padding: 10px 18px;
          border-radius: 9px; white-space:nowrap; border: none; cursor: pointer; font-family: inherit;
          transition: background-color .15s ease, transform .1s ease, box-shadow .15s ease; }}
  .btn:hover {{ background: {ACCENT_HOVER}; box-shadow: 0 2px 10px rgba(0,184,217,0.35); transform: translateY(-1px); }}
  .btn:active {{ background: #008FA3; transform: translateY(0); box-shadow: none; }}
  .btn.secondary {{ background: var(--track); color: var(--text-primary) !important; }}
  .btn.secondary:hover {{ background: var(--track-hover); box-shadow: none; }}
  .btn:disabled {{ opacity: 0.5; cursor: default; transform: none; box-shadow: none; }}

  table {{ border-collapse: collapse; width: 100%; font-size: 12.5px; }}
  th {{ text-align:left; color: var(--text-muted); font-weight: 600; font-size: 11.5px; text-transform: uppercase; letter-spacing: .03em; padding: 6px 10px; border-bottom: 1px solid var(--border); white-space: nowrap; }}
  td {{ padding: 8px 10px; border-bottom: 1px solid var(--border); vertical-align: top; }}
  tr:last-child td {{ border-bottom: none; }}
  tbody tr {{ transition: background-color .1s ease; }}
  tbody tr:hover td {{ background: var(--track); }}
  .mono {{ font-family: ui-monospace, Consolas, monospace; font-variant-numeric: tabular-nums; white-space:nowrap; }}

  label {{ display:block; font-size: 12.5px; color: var(--text-secondary); margin-bottom: 6px; font-weight: 600; }}
  input[type=text], input[type=password] {{
    width: 100%; padding: 10px 12px; border-radius: 9px; border: 1px solid var(--border);
    background: var(--track); color: var(--text-primary); font-size: 14px; font-family: inherit;
    transition: border-color .15s ease, box-shadow .15s ease;
  }}
  input[type=text]::placeholder, input[type=password]::placeholder {{ color: var(--text-muted); }}
  input[type=text]:hover, input[type=password]:hover {{ border-color: var(--text-muted); }}
  input[type=text]:focus, input[type=password]:focus {{
    outline: none; border-color: {ACCENT}; box-shadow: 0 0 0 3px var(--focus-ring);
  }}
  .field {{ margin-bottom: 16px; }}
  .form-card {{ max-width: 380px; margin: 60px auto 0; }}

  .alert {{ display:flex; align-items:center; gap:9px; border-radius: 9px; padding: 10px 14px; font-size: 12.5px; margin-bottom: 16px; }}
  .alert.error {{ background: rgba(239,68,68,0.12); color: {CRITICAL_TEXT_ON_LIGHT}; }}
  :root[data-theme="dark"] .alert.error {{ color: #FCA5A5; }}
  .alert.info {{ background: var(--track); color: var(--text-secondary); }}

  .note {{ font-size: 11.5px; color: var(--text-muted); margin-top: 10px; }}

  .ring-label {{ font-size: 15px; font-weight: 800; fill: var(--text-primary); font-family: system-ui, sans-serif; text-anchor:middle; }}

  .status-pill {{ display:inline-flex; align-items:center; gap:6px; font-size: 11px; font-weight: 700;
                   padding: 3px 10px; border-radius: 999px; white-space:nowrap; }}
  .status-pill.good {{ background: rgba(34,197,94,0.14); color: {SUCCESS_TEXT_ON_LIGHT}; }}
  .status-pill.warn {{ background: rgba(245,158,11,0.14); color: {WARNING_TEXT_ON_LIGHT}; }}
  .status-pill.bad {{ background: rgba(239,68,68,0.14); color: {CRITICAL_TEXT_ON_LIGHT}; }}
  .status-pill.neutral {{ background: var(--track); color: var(--text-secondary); }}
  :root[data-theme="dark"] .status-pill.good {{ color: {SUCCESS}; }}
  :root[data-theme="dark"] .status-pill.warn {{ color: {WARNING}; }}
  :root[data-theme="dark"] .status-pill.bad {{ color: {CRITICAL}; }}

  .empty-state {{ text-align:center; padding: 36px 20px; color: var(--text-muted); }}
  .empty-state .icon {{ opacity:.5; margin-bottom:10px; }}
  .empty-state .t {{ font-size: 13.5px; font-weight:600; color: var(--text-secondary); margin-bottom:4px; }}
  .empty-state .d {{ font-size: 12px; }}

  [data-tooltip] {{ position: relative; cursor: help; }}
  [data-tooltip]:hover::after {{
    content: attr(data-tooltip); position: absolute; left: 0; bottom: calc(100% + 6px); z-index: 80;
    background: {NAVBAR_BG}; color: {TEXT_ON_DARK}; font-size: 11px; font-family: ui-monospace, Consolas, monospace;
    padding: 6px 10px; border-radius: 6px; white-space: nowrap; max-width: 480px; overflow:hidden; text-overflow:ellipsis;
    box-shadow: 0 4px 14px rgba(0,0,0,0.3);
  }}

  /* ---- shared confirm/prompt dialog + toast (dsConfirm/dsPrompt/dsToast in
     SHELL_SCRIPT) - the one dialog style used everywhere instead of the
     browser's native alert()/confirm()/prompt(), which look like OS chrome
     ("127.0.0.1:5000 says...") and can't be skipped for an already-reviewed
     bulk action. ---- */
  .ds-dialog-overlay {{ position: fixed; inset: 0; background: rgba(4,10,20,0.55); display:none;
                         align-items: center; justify-content: center; z-index: 500; padding: 20px; box-sizing: border-box; }}
  .ds-dialog-overlay.open {{ display: flex; }}
  .ds-dialog-box {{ background: var(--panel-bg); color: var(--text-primary); border-radius: 14px; padding: 22px 24px;
                     width: 100%; max-width: 440px; box-shadow: 0 12px 40px rgba(0,0,0,0.35); }}
  .ds-dialog-title {{ font-size: 15px; font-weight: 700; margin: 0 0 8px; display:flex; align-items:center; gap:8px; }}
  .ds-dialog-msg {{ font-size: 13px; color: var(--text-secondary); line-height:1.5; margin-bottom: 14px; white-space: pre-wrap; }}
  .ds-dialog-input {{ margin-bottom: 14px; }}
  .ds-dialog-actions {{ display:flex; justify-content:flex-end; gap: 10px; }}

  .ds-toast {{ position: fixed; left: 50%; bottom: 26px; transform: translate(-50%, 20px); z-index: 510;
               display:flex; align-items:center; gap: 14px; font-size: 13px; font-weight: 600; padding: 12px 16px;
               border-radius: 11px; box-shadow: 0 10px 30px rgba(0,0,0,0.25); opacity:0; pointer-events:none;
               transition: all .2s ease; max-width: min(520px, calc(100vw - 40px)); }}
  .ds-toast.show {{ opacity:1; transform: translate(-50%, 0); pointer-events:auto; }}
  .ds-toast.info {{ background: {ACCENT}; color: {NAVY_ON_ACCENT}; }}
  .ds-toast.error {{ background: {CRITICAL}; color: #fff; }}
  .ds-toast button {{ background: rgba(0,0,0,0.14); border:none; font-weight:700; font-size:12.5px;
                       padding:6px 12px; border-radius:7px; cursor:pointer; white-space:nowrap; color: inherit; flex-shrink:0; }}
  .ds-toast button:hover {{ background: rgba(0,0,0,0.24); }}
"""


THEME_INIT_SCRIPT = """<script>
(function() {
  try {
    var t = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', t);
    var a = localStorage.getItem('advancedMode') === 'true';
    document.documentElement.setAttribute('data-advanced', a ? 'true' : 'false');
  } catch (e) {}
})();
</script>"""

SHELL_SCRIPT = """<script>
function toggleTheme() {
  var html = document.documentElement;
  var next = html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
  html.setAttribute('data-theme', next);
  try { localStorage.setItem('theme', next); } catch (e) {}
  var btn = document.getElementById('theme-toggle-btn');
  if (btn) btn.textContent = next === 'dark' ? String.fromCodePoint(9728) : String.fromCodePoint(127769);
}
function openSidebar() { document.body.classList.add('sidebar-open'); }
function closeSidebar() { document.body.classList.remove('sidebar-open'); }
function toggleAdvancedMode() {
  var html = document.documentElement;
  var next = html.getAttribute('data-advanced') !== 'true';
  html.setAttribute('data-advanced', next ? 'true' : 'false');
  try { localStorage.setItem('advancedMode', next ? 'true' : 'false'); } catch (e) {}
  if (typeof window.onAdvancedModeChange === 'function') window.onAdvancedModeChange(next);
}

/* ---- shared confirm/prompt/toast: the one dialog style for the whole app,
   replacing native alert()/confirm()/prompt() everywhere. Built lazily on
   first use so pages that never need it pay nothing for it. ---- */
function _dsRoot() {
  var root = document.getElementById('ds-dialog-root');
  if (root) return root;
  root = document.createElement('div');
  root.id = 'ds-dialog-root';
  root.innerHTML =
    '<div class="ds-dialog-overlay" id="ds-dialog-overlay">' +
      '<div class="ds-dialog-box">' +
        '<div class="ds-dialog-title" id="ds-dialog-title"></div>' +
        '<div class="ds-dialog-msg" id="ds-dialog-msg"></div>' +
        '<input type="text" class="ds-dialog-input" id="ds-dialog-input" style="display:none">' +
        '<div class="ds-dialog-actions">' +
          '<button class="btn secondary" id="ds-dialog-cancel">Cancel</button>' +
          '<button class="btn" id="ds-dialog-ok">OK</button>' +
        '</div>' +
      '</div>' +
    '</div>' +
    '<div class="ds-toast" id="ds-toast"><span id="ds-toast-msg"></span><button id="ds-toast-action" style="display:none"></button></div>';
  document.body.appendChild(root);
  return root;
}
window.dsConfirm = function (message, opts) {
  opts = opts || {};
  _dsRoot();
  return new Promise(function (resolve) {
    document.getElementById('ds-dialog-title').textContent = opts.title || 'Confirm';
    document.getElementById('ds-dialog-msg').textContent = message;
    var input = document.getElementById('ds-dialog-input');
    input.style.display = 'none';
    var okBtn = document.getElementById('ds-dialog-ok');
    okBtn.textContent = opts.okLabel || 'Confirm';
    okBtn.className = opts.danger ? 'btn-del' : 'btn';
    okBtn.disabled = false;
    var cancelBtn = document.getElementById('ds-dialog-cancel');
    var overlay = document.getElementById('ds-dialog-overlay');
    function done(result) { overlay.classList.remove('open'); okBtn.onclick = null; cancelBtn.onclick = null; resolve(result); }
    okBtn.onclick = function () { done(true); };
    cancelBtn.onclick = function () { done(false); };
    overlay.classList.add('open');
  });
};
window.dsPrompt = function (message, expected, opts) {
  opts = opts || {};
  _dsRoot();
  return new Promise(function (resolve) {
    document.getElementById('ds-dialog-title').textContent = opts.title || 'Type to confirm';
    document.getElementById('ds-dialog-msg').textContent = message;
    var input = document.getElementById('ds-dialog-input');
    input.style.display = '';
    input.value = '';
    input.placeholder = expected;
    var okBtn = document.getElementById('ds-dialog-ok');
    okBtn.textContent = opts.okLabel || 'Confirm';
    okBtn.className = 'btn-del';
    okBtn.disabled = true;
    input.oninput = function () { okBtn.disabled = input.value !== expected; };
    var cancelBtn = document.getElementById('ds-dialog-cancel');
    var overlay = document.getElementById('ds-dialog-overlay');
    function done(result) { overlay.classList.remove('open'); okBtn.onclick = null; cancelBtn.onclick = null; input.oninput = null; resolve(result); }
    okBtn.onclick = function () { if (input.value === expected) done(true); };
    cancelBtn.onclick = function () { done(false); };
    overlay.classList.add('open');
    setTimeout(function () { input.focus(); }, 50);
  });
};
var _dsToastTimer = null;
window.dsToast = function (message, opts) {
  opts = opts || {};
  _dsRoot();
  var toast = document.getElementById('ds-toast');
  toast.className = 'ds-toast show ' + (opts.type || 'info');
  document.getElementById('ds-toast-msg').textContent = message;
  var actionBtn = document.getElementById('ds-toast-action');
  if (opts.actionLabel && opts.onAction) {
    actionBtn.style.display = '';
    actionBtn.textContent = opts.actionLabel;
    actionBtn.onclick = function () { toast.classList.remove('show'); opts.onAction(); };
  } else {
    actionBtn.style.display = 'none';
    actionBtn.onclick = null;
  }
  clearTimeout(_dsToastTimer);
  _dsToastTimer = setTimeout(function () { toast.classList.remove('show'); }, opts.duration || 6000);
};

document.addEventListener('DOMContentLoaded', function() {
  var btn = document.getElementById('theme-toggle-btn');
  if (btn) btn.textContent = document.documentElement.getAttribute('data-theme') === 'dark'
    ? String.fromCodePoint(9728) : String.fromCodePoint(127769);
});
</script>"""


def render_page(title, body_html, extra_css="", active=None, page_title=None):
    """active: one of SIDEBAR_ITEMS' keys to show the sidebar with that item
    highlighted, or None for chrome-less auth screens (setup/login)."""
    favicon_tag = f'<link rel="icon" type="image/png" href="data:image/png;base64,{FAVICON_B64}">' if FAVICON_B64 else ""

    if active is None:
        content = f'<div class="viz-root">{body_html}</div>'
    else:
        toggle_btn = ('<button type="button" class="theme-toggle" id="theme-toggle-btn" '
                      'onclick="toggleTheme()" title="Toggle light/dark mode" aria-label="Toggle light/dark mode">'
                      '&#127769;</button>')
        menu_btn = ('<button type="button" class="menu-btn" onclick="openSidebar()" aria-label="Open menu">'
                    f'{icon("menu", 20)}</button>')
        advanced_switch = (
            '<label class="advanced-switch" title="Show technical details (paths, risk scores, filters) for every screen">'
            '<span class="lbl">Advanced Mode</span>'
            '<span class="switch-track" onclick="toggleAdvancedMode()"><span class="knob"></span></span>'
            '</label>'
        )
        topbar = (f'<header class="topbar">{menu_btn}'
                  f'<span class="page-title">{esc(page_title or title)}</span>{advanced_switch}{toggle_btn}</header>')
        content = f'{_sidebar_html(active)}<div class="main-shell">{topbar}<div class="viz-root">{body_html}</div></div>'

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{THEME_INIT_SCRIPT}
<title>{esc(title)}</title>
{favicon_tag}
<style>
{BASE_CSS}
{extra_css}
</style>
</head>
<body>
{content}
{SHELL_SCRIPT}
</body>
</html>"""
