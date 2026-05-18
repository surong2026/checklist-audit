import re
from config import STANDARD_FIELDS
from models.data_normalizer import normalize_text


def detect_header_row_index(rows: list) -> int:
    """Auto-detect the header row index in a table.

    Returns the index of the best header row, or 0 if undetectable.
    """
    if not rows:
        return 0
    if len(rows) <= 1:
        return 0

    keywords = ["品名", "名称", "品牌", "规格", "型号", "数量", "单价", "金额", "序号"]
    best_score = 0
    best_idx = 0

    for i, row in enumerate(rows[:10]):  # Only look at first 10 rows
        row_text = " ".join(str(c) for c in row if c)
        score = sum(1 for kw in keywords if kw in row_text)
        if score > best_score:
            best_score = score
            best_idx = i

    return best_idx if best_score >= 2 else 0


def extract_table_rows(primary_table: list) -> tuple:
    """Extract header and data rows from a primary table.

    Returns (header_row, data_rows).
    """
    if not primary_table:
        return [], []

    header_idx = detect_header_row_index(primary_table)
    header = primary_table[header_idx]
    data_rows = primary_table[header_idx + 1 :]
    return header, data_rows


def map_columns(header: list, standard_fields: dict = None) -> dict:
    """Map raw column headers to standard field keys using semantic matching.

    Returns:
        {
            "mapping": {raw_col_index: standard_field_key},
            "confidence": {raw_col_index: score},
            "unmapped": [raw_col_index]
        }
    """
    if standard_fields is None:
        standard_fields = STANDARD_FIELDS

    raw_mapping = []  # list of (col_idx, field_key, score)

    for ri, raw_col in enumerate(header):
        raw = normalize_text(str(raw_col)) if raw_col else ""
        if not raw:
            continue

        best_field = None
        best_score = 0

        for field_key, field_info in standard_fields.items():
            score = _column_similarity(raw, field_info["cn"])
            for alias in field_info["aliases"]:
                alias_score = _column_similarity(raw, alias)
                if alias_score > score:
                    score = alias_score

            # Content-type hints (only boost, don't create new mappings)
            if field_key == "quantity" and re.search(r"^\s*数\s*量\s*$|^\s*件数\s*$", raw):
                score = max(score, 95)
            if field_key == "total_price" and re.search(r"^\s*金\s*额|^\s*总\s*价|^\s*合.*计", raw):
                score = max(score, 90)
            if field_key == "unit_price" and re.search(r"^\s*单\s*价", raw):
                score = max(score, 95)
            if field_key == "name" and re.search(r"品\s*名|名\s*称|货物", raw):
                score = max(score, 95)
            if field_key == "brand" and re.search(r"品\s*牌|厂\s*家|商标", raw):
                score = max(score, 95)
            if field_key == "spec" and re.search(r"规格|型\s*号|参\s*数", raw):
                score = max(score, 95)

            if score > best_score:
                best_score = score
                best_field = field_key

        if best_field:
            raw_mapping.append((ri, best_field, best_score))

    # Deduplicate: for each target field, keep only the highest-confidence column
    field_best = {}  # field_key -> (col_idx, score)
    for col_idx, field_key, score in raw_mapping:
        if field_key not in field_best or score > field_best[field_key][1]:
            field_best[field_key] = (col_idx, score)

    mapping = {}
    confidence = {}
    unmapped = []
    mapped_fields = set()

    for col_idx, field_key, score in raw_mapping:
        best_col, best_score_for_field = field_best[field_key]
        if col_idx == best_col:
            mapping[col_idx] = field_key
            confidence[col_idx] = score
            mapped_fields.add(field_key)
            if score < 90:
                unmapped.append(col_idx)
        else:
            # This column lost to a higher-confidence one
            unmapped.append(col_idx)

    # Also mark columns with no field at all
    for ri in range(len(header)):
        raw = normalize_text(str(header[ri])) if ri < len(header) and header[ri] else ""
        if not raw:
            unmapped.append(ri)

    # Deduplicate unmapped
    unmapped = sorted(set(unmapped))

    return {"mapping": mapping, "confidence": confidence, "unmapped": unmapped}


def _column_similarity(raw: str, target: str) -> int:
    """Calculate similarity between a raw column name and a target field name."""
    target = normalize_text(target)

    # Exact match after normalization
    if raw == target:
        return 100

    # Contains match
    if target in raw or raw in target:
        return 95

    # Character overlap (Jaccard-like)
    raw_set = set(raw.replace(" ", ""))
    target_set = set(target.replace(" ", ""))
    if not target_set:
        return 0
    overlap = len(raw_set & target_set)
    return int(overlap / len(target_set) * 100)


def apply_mapping(row: list, mapping: dict) -> dict:
    """Apply column mapping to a data row, returning a dict of standard field -> value."""
    result = {}
    for col_idx, field_key in mapping.items():
        if col_idx < len(row):
            result[field_key] = str(row[col_idx]).strip() if row[col_idx] is not None else ""
    return result
