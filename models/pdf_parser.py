import pdfplumber


def parse_pdf(file_path: str) -> dict:
    """Extract tables from a PDF file using pdfplumber."""
    all_tables = []

    with pdfplumber.open(file_path) as pdf:
        for pi, page in enumerate(pdf.pages):
            tables = page.extract_tables()
            for ti, table in enumerate(tables):
                if table:
                    rows = []
                    for row in table:
                        cells = [str(c).strip() if c else "" for c in row]
                        rows.append(cells)
                    if rows:
                        all_tables.append({"page": pi + 1, "table_index": ti, "rows": rows})

    if not all_tables:
        return {"tables": [], "primary_table": None}

    # Pick the largest table
    primary = max(all_tables, key=lambda t: len(t["rows"]))
    return {"tables": all_tables, "primary_table": primary["rows"], "primary_page": primary["page"]}
