"""Builds a one-shot PDF snapshot of the current storage + cleanup situation
- a readable, printable summary rather than a pixel copy of the dashboard's
charts (those are interactive SVGs; a PDF is a static document, so a set of
clean tables reads better than trying to rasterize the donut/bar charts)."""

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (PageBreak, Paragraph, SimpleDocTemplate, Spacer,
                                 Table, TableStyle)

from theme import ACCENT, BRAND_NAME, BRAND_TAGLINE, NAVBAR_BG, human_size

NAVY = colors.HexColor(NAVBAR_BG)
ACCENT_C = colors.HexColor(ACCENT)
LIGHT_ROW = colors.HexColor("#F5F7FA")
BORDER = colors.HexColor("#D9E2EC")

_styles = getSampleStyleSheet()
TITLE = ParagraphStyle("DSTitle", parent=_styles["Title"], textColor=NAVY, fontSize=22, spaceAfter=2)
SUBTITLE = ParagraphStyle("DSSubtitle", parent=_styles["Normal"], textColor=colors.HexColor("#627D98"), fontSize=10, spaceAfter=18)
H2 = ParagraphStyle("DSH2", parent=_styles["Heading2"], textColor=NAVY, fontSize=13, spaceBefore=16, spaceAfter=8)
BODY = ParagraphStyle("DSBody", parent=_styles["Normal"], fontSize=9.5)


def _table(rows, col_widths, header=True):
    t = Table(rows, colWidths=col_widths, repeatRows=1 if header else 0)
    style = [
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 1 if header else 0), (-1, -1), [colors.white, LIGHT_ROW]),
    ]
    if header:
        style += [
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]
    t.setStyle(TableStyle(style))
    return t


def build_pdf_summary(data, cleanup_report, dup_stats, out_path):
    doc = SimpleDocTemplate(str(out_path), pagesize=letter,
                             topMargin=0.6 * inch, bottomMargin=0.6 * inch,
                             leftMargin=0.6 * inch, rightMargin=0.6 * inch)
    story = []

    story.append(Paragraph(BRAND_NAME, TITLE))
    story.append(Paragraph(BRAND_TAGLINE, SUBTITLE))

    disk = data["disk"]
    used_pct = disk["used"] / disk["total"] * 100 if disk["total"] else 0
    story.append(Paragraph("Scan Overview", H2))
    story.append(_table([
        ["Metric", "Value"],
        ["Drive / folder scanned", data.get("root", "")],
        ["Scanned at", data.get("scanned_at", "")],
        ["Scan duration", f"{data.get('elapsed_seconds', 0)}s"],
        ["Files scanned", f"{data.get('file_count', 0):,}"],
        ["Folders scanned", f"{data.get('dir_count', 0):,}"],
        ["Total capacity", human_size(disk["total"])],
        ["Used", f"{human_size(disk['used'])} ({used_pct:.0f}%)"],
        ["Free", human_size(disk["free"])],
        ["Safe-to-review data (your files)", human_size(data.get("safe_total", 0))],
        ["System / app-critical (excluded)", human_size(data.get("critical_total", 0))],
    ], [2.6 * inch, 3.4 * inch]))

    cat_rows = [["Category", "Size"]]
    for cat, size in sorted(data.get("category_sizes", {}).items(), key=lambda kv: -kv[1])[:12]:
        cat_rows.append([cat, human_size(size)])
    if len(cat_rows) > 1:
        story.append(Paragraph("Storage by File Type", H2))
        story.append(_table(cat_rows, [4 * inch, 2 * inch]))

    folder_rows = [["Folder", "Size"]]
    for item in data.get("top_level_folders", [])[:12]:
        folder_rows.append([item["path"], human_size(item["size"])])
    if len(folder_rows) > 1:
        story.append(Paragraph("Largest Top-Level Folders", H2))
        story.append(_table(folder_rows, [4 * inch, 2 * inch]))

    file_rows = [["File", "Size"]]
    for item in data.get("top_files", [])[:15]:
        file_rows.append([item["path"], human_size(item["size"])])
    if len(file_rows) > 1:
        story.append(Paragraph("Largest Individual Files", H2))
        story.append(_table(file_rows, [4.6 * inch, 1.4 * inch]))

    junk_rows = [["Location", "Size", "Path"]]
    for label, info in sorted(data.get("junk", {}).items(), key=lambda kv: -kv[1]["size"]):
        if info.get("exists"):
            junk_rows.append([label, human_size(info["size"]), info["path"]])
    if len(junk_rows) > 1:
        story.append(Paragraph("Junk / Cache Locations", H2))
        story.append(_table(junk_rows, [1.8 * inch, 1 * inch, 3.2 * inch]))

    if cleanup_report:
        story.append(PageBreak())
        story.append(Paragraph("Cleanup Center Summary", H2))
        counts = cleanup_report["counts"]
        story.append(_table([
            ["Metric", "Value"],
            ["Estimated recoverable space", human_size(cleanup_report["recoverable_estimate_bytes"])],
            ["Duplicate waste", human_size(cleanup_report["duplicates"]["total_waste_bytes"])],
            ["Duplicate groups", f"{cleanup_report['duplicates']['total_groups']:,}"],
            ["Duplicate extra copies", f"{counts['duplicates']:,}"],
            ["Temp/cache files", f"{counts['temp_cache']:,}"],
            ["Old downloads", f"{counts['old_downloads']:,}"],
            ["Large files to review", f"{counts['large_files']:,}"],
            ["Unknown - needs review", f"{counts['unknown']:,}"],
        ], [3.2 * inch, 2.8 * inch]))

        dup_rows = [["Kept Copy", "Copies", "Size Each", "Wastes"]]
        for g in sorted(cleanup_report["duplicates"]["groups"], key=lambda g: -g["waste_bytes"])[:15]:
            dup_rows.append([g["keeper"]["path"], str(g["count"]), human_size(g["size"]), human_size(g["waste_bytes"])])
        if len(dup_rows) > 1:
            story.append(Paragraph("Largest Duplicate Groups", H2))
            story.append(_table(dup_rows, [3.4 * inch, 0.8 * inch, 1 * inch, 1 * inch]))

    story.append(Spacer(1, 20))
    story.append(Paragraph(
        f"Generated by {BRAND_NAME} on {data.get('scanned_at', '')}. This is a point-in-time snapshot of the last scan.",
        ParagraphStyle("DSFooter", parent=BODY, textColor=colors.HexColor("#829AB1"), fontSize=8),
    ))

    doc.build(story)
