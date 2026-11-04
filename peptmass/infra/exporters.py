"""
exporters.py
============
Exportação de tabelas de fragmentos / resultados para CSV, XLSX, PDF e TXT,
além de importação FASTA e exportação compatível com Skyline.
"""

import csv


# ---------------------------------------------------------------------------
# FASTA
# ---------------------------------------------------------------------------
def parse_fasta(text: str):
    """Retorna lista de (header, sequence) a partir de texto FASTA."""
    entries = []
    header = None
    seq_lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(">"):
            if header is not None:
                entries.append((header, "".join(seq_lines)))
            header = line[1:].strip()
            seq_lines = []
        else:
            seq_lines.append(line)
    if header is not None:
        entries.append((header, "".join(seq_lines)))
    # caso seja sequência crua sem cabeçalho
    if not entries and text.strip():
        entries.append(("sequence", "".join(text.split())))
    return entries


# ---------------------------------------------------------------------------
# Tabelas genéricas:  headers = [..], rows = [[...], ...]
# ---------------------------------------------------------------------------
def to_csv(path, headers, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(headers)
        w.writerows(rows)


def to_txt(path, headers, rows, title=""):
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))
    with open(path, "w", encoding="utf-8") as f:
        if title:
            f.write(title + "\n" + "=" * len(title) + "\n\n")
        line = "  ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
        f.write(line + "\n")
        f.write("-" * len(line) + "\n")
        for row in rows:
            f.write("  ".join(str(c).ljust(widths[i])
                              for i, c in enumerate(row)) + "\n")


def to_xlsx(path, headers, rows, title="Resultados"):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    wb = Workbook()
    ws = wb.active
    ws.title = title[:31]
    header_fill = PatternFill("solid", fgColor="2C3E50")
    header_font = Font(bold=True, color="FFFFFF")
    for c, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=c, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")
    for r, row in enumerate(rows, 2):
        for c, val in enumerate(row, 1):
            ws.cell(row=r, column=c, value=val)
    for c, h in enumerate(headers, 1):
        maxlen = max([len(str(h))] + [len(str(row[c-1])) for row in rows] or [0])
        ws.column_dimensions[ws.cell(row=1, column=c).column_letter].width = \
            min(maxlen + 3, 40)
    ws.freeze_panes = "A2"
    wb.save(path)


def to_pdf(path, headers, rows, title="Resultados", subtitle=""):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                    Paragraph, Spacer)
    from reportlab.lib.styles import getSampleStyleSheet

    doc = SimpleDocTemplate(path, pagesize=landscape(A4),
                            leftMargin=12*mm, rightMargin=12*mm,
                            topMargin=12*mm, bottomMargin=12*mm)
    styles = getSampleStyleSheet()
    elems = [Paragraph(title, styles["Title"])]
    if subtitle:
        elems.append(Paragraph(subtitle, styles["Normal"]))
    elems.append(Spacer(1, 6*mm))

    data = [headers] + [[str(c) for c in row] for row in rows]
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#F2F4F6")]),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    elems.append(table)
    doc.build(elems)


def to_skyline_transition_list(path, peptide_sequence, fragments,
                               precursor_charge=2, precursor_mz=None):
    """
    Exporta lista de transições em CSV compatível com importação no Skyline.
    Colunas: Peptide, Precursor m/z, Precursor Charge, Product m/z,
             Product Charge, Fragment, Label
    """
    headers = ["Peptide Modified Sequence", "Precursor m/z",
               "Precursor Charge", "Product m/z", "Product Charge",
               "Fragment Name", "Label Type"]
    rows = []
    for f in fragments:
        rows.append([
            peptide_sequence,
            f"{precursor_mz:.6f}" if precursor_mz else "",
            precursor_charge,
            f"{f.mz:.6f}",
            f.charge,
            f.label,
            "light",
        ])
    to_csv(path, headers, rows)
