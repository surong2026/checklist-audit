from models.data_normalizer import make_match_key, fuzzy_similarity, normalize_text
from config import FUZZY_MATCH_THRESHOLD_AUTO, FUZZY_MATCH_THRESHOLD_MANUAL


def build_match_index(rows: list, name_col: int, brand_col: int, spec_col: int) -> dict:
    """Build a lookup index for rows based on the match key (name + brand + spec).

    Returns:
        {match_key: [row_index, ...]}  (may have multiple rows per key)
    """
    index = {}
    for ri, row in enumerate(rows):
        name = str(row[name_col]).strip() if name_col is not None and name_col < len(row) else ""
        brand = str(row[brand_col]).strip() if brand_col is not None and brand_col < len(row) else ""
        spec = str(row[spec_col]).strip() if spec_col is not None and spec_col < len(row) else ""
        key = make_match_key(name, brand, spec)
        if key not in index:
            index[key] = []
        index[key].append(ri)
    return index


def match_rows(baseline_rows: list, target_rows: list, baseline_mapping: dict, target_mapping: dict) -> dict:
    """Match rows between baseline and target file using name+brand+spec triple matching.

    Returns:
        {
            "matches": [(baseline_idx, target_idx, confidence)],  # matched pairs
            "baseline_unmatched": [baseline_idx],                 # in baseline but not target
            "target_unmatched": [target_idx],                     # in target but not baseline
            "low_confidence": [(baseline_idx, target_idx, confidence)],  # needs manual review
        }
    """
    # Get column indices from mappings
    b_name = _find_col_idx(baseline_mapping, "name")
    b_brand = _find_col_idx(baseline_mapping, "brand")
    b_spec = _find_col_idx(baseline_mapping, "spec")
    t_name = _find_col_idx(target_mapping, "name")
    t_brand = _find_col_idx(target_mapping, "brand")
    t_spec = _find_col_idx(target_mapping, "spec")

    # Build indices
    b_index = build_match_index(baseline_rows, b_name, b_brand, b_spec)
    t_index = build_match_index(target_rows, t_name, t_brand, t_spec)

    matches = []
    low_confidence = []
    matched_target_indices = set()

    for b_key, b_indices in b_index.items():
        for b_idx in b_indices:
            # Try exact match first
            if b_key in t_index:
                for t_idx in t_index[b_key]:
                    if t_idx not in matched_target_indices:
                        matches.append((b_idx, t_idx, 100))
                        matched_target_indices.add(t_idx)
                        break
                continue

            # Fuzzy match across all unmatched target rows
            b_name_val = _get_val(baseline_rows[b_idx], b_name)
            b_brand_val = _get_val(baseline_rows[b_idx], b_brand)
            b_spec_val = _get_val(baseline_rows[b_idx], b_spec)

            best_t_idx = None
            best_score = 0

            for t_key, t_indices in t_index.items():
                for t_idx in t_indices:
                    if t_idx in matched_target_indices:
                        continue
                    t_name_val = _get_val(target_rows[t_idx], t_name)
                    t_brand_val = _get_val(target_rows[t_idx], t_brand)
                    t_spec_val = _get_val(target_rows[t_idx], t_spec)

                    # Adaptive weighted fuzzy score
                    # Determine which dimensions are available on both sides
                    has_brand = bool(b_brand_val) and bool(t_brand_val)
                    has_spec = bool(b_spec_val) and bool(t_spec_val)

                    name_score = fuzzy_similarity(b_name_val, t_name_val)

                    if has_brand and has_spec:
                        brand_score = fuzzy_similarity(b_brand_val, t_brand_val)
                        spec_score = fuzzy_similarity(b_spec_val, t_spec_val)
                        total = int(name_score * 0.5 + brand_score * 0.25 + spec_score * 0.25)
                    elif has_brand:
                        brand_score = fuzzy_similarity(b_brand_val, t_brand_val)
                        total = int(name_score * 0.65 + brand_score * 0.35)
                    elif has_spec:
                        spec_score = fuzzy_similarity(b_spec_val, t_spec_val)
                        total = int(name_score * 0.65 + spec_score * 0.35)
                    else:
                        total = name_score

                    if total > best_score:
                        best_score = total
                        best_t_idx = t_idx

            if best_score >= FUZZY_MATCH_THRESHOLD_AUTO and best_t_idx is not None:
                matches.append((b_idx, best_t_idx, best_score))
                matched_target_indices.add(best_t_idx)
            elif best_score >= FUZZY_MATCH_THRESHOLD_MANUAL and best_t_idx is not None:
                low_confidence.append((b_idx, best_t_idx, best_score))
                matched_target_indices.add(best_t_idx)
            else:
                pass  # Falls through to baseline_unmatched

    # Collect unmatched
    all_matched_baseline = {m[0] for m in matches} | {m[0] for m in low_confidence}
    baseline_unmatched = [i for i in range(len(baseline_rows)) if i not in all_matched_baseline]

    target_unmatched = [i for i in range(len(target_rows)) if i not in matched_target_indices]

    return {
        "matches": matches,
        "baseline_unmatched": baseline_unmatched,
        "target_unmatched": target_unmatched,
        "low_confidence": low_confidence,
    }


def _find_col_idx(mapping: dict, field_key: str) -> int | None:
    """Find the raw column index for a standard field key."""
    for col_idx, fk in mapping.items():
        if fk == field_key:
            return col_idx
    return None


def _get_val(row: list, col_idx: int | None) -> str:
    if col_idx is None or col_idx >= len(row):
        return ""
    return str(row[col_idx]).strip() if row[col_idx] is not None else ""
