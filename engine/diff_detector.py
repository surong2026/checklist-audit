from models.data_normalizer import extract_number, normalize_text
from engine.row_matcher import _find_col_idx, _get_val


def detect_differences(baseline_rows: list, target_rows: list, match_result: dict,
                       baseline_mapping: dict, target_mapping: dict) -> list:
    """Detect all differences between matched and unmatched rows.

    Returns a list of diff dicts:
        {
            "type": "missing" | "extra" | "quantity" | "unit_price" | "total_price" | "brand_spec" | "unparseable",
            "severity": "critical" | "warning" | "info",
            "baseline_idx": int or None,
            "target_idx": int or None,
            "name": str,
            "brand": str,
            "spec": str,
            "fields": {field_key: {"baseline": val, "target": val, "match": bool}},
            "confirmed": None  # None=unconfirmed, True=confirmed_ok, False=confirmed_abnormal
        }
    """
    diffs = []

    b_name = _find_col_idx(baseline_mapping, "name")
    b_brand = _find_col_idx(baseline_mapping, "brand")
    b_spec = _find_col_idx(baseline_mapping, "spec")
    t_name = _find_col_idx(target_mapping, "name")
    t_brand = _find_col_idx(target_mapping, "brand")
    t_spec = _find_col_idx(target_mapping, "spec")

    # Missing items in target (in baseline but not matched)
    for b_idx in match_result["baseline_unmatched"]:
        diffs.append({
            "type": "missing",
            "severity": "critical",
            "baseline_idx": b_idx,
            "target_idx": None,
            "name": _get_val(baseline_rows[b_idx], b_name),
            "brand": _get_val(baseline_rows[b_idx], b_brand),
            "spec": _get_val(baseline_rows[b_idx], b_spec),
            "fields": _compare_fields(baseline_rows[b_idx], None, baseline_mapping, target_mapping),
            "confirmed": None,
        })

    # Extra items in target (not in baseline)
    for t_idx in match_result["target_unmatched"]:
        diffs.append({
            "type": "extra",
            "severity": "info",
            "baseline_idx": None,
            "target_idx": t_idx,
            "name": _get_val(target_rows[t_idx], t_name),
            "brand": _get_val(target_rows[t_idx], t_brand),
            "spec": _get_val(target_rows[t_idx], t_spec),
            "fields": _compare_fields(None, target_rows[t_idx], baseline_mapping, target_mapping),
            "confirmed": None,
        })

    # Matched rows: compare fields
    compare_fields = ["quantity", "unit_price", "total_price"]

    for b_idx, t_idx, confidence in match_result["matches"] + match_result["low_confidence"]:
        b_row = baseline_rows[b_idx]
        t_row = target_rows[t_idx]

        field_diffs = {}

        # Check each comparable numeric field
        for fk in compare_fields:
            b_col = _find_col_idx(baseline_mapping, fk)
            t_col = _find_col_idx(target_mapping, fk)

            b_raw = _get_val(b_row, b_col) if b_col is not None else ""
            t_raw = _get_val(t_row, t_col) if t_col is not None else ""

            b_num, _ = extract_number(b_raw)
            t_num, _ = extract_number(t_raw)

            if b_num is None and t_num is None:
                # Both unparseable, not a diff
                continue
            if b_num is None and t_num is not None:
                field_diffs[fk] = {"baseline": b_raw, "target": t_raw, "baseline_num": None, "target_num": t_num, "match": False, "issue": "baseline_unparseable"}
            elif b_num is not None and t_num is None:
                field_diffs[fk] = {"baseline": b_raw, "target": t_raw, "baseline_num": b_num, "target_num": None, "match": False, "issue": "target_unparseable"}
            elif abs(b_num - t_num) > 0.001:
                field_diffs[fk] = {"baseline": b_raw, "target": t_raw, "baseline_num": b_num, "target_num": t_num, "match": False, "issue": None}

        # Check brand/spec match for auto-matched rows
        # Only flag differences when BOTH sides have the column
        b_brand_val = _get_val(b_row, b_brand) if b_brand is not None else ""
        t_brand_val = _get_val(t_row, t_brand) if t_brand is not None else ""
        b_spec_val = _get_val(b_row, b_spec) if b_spec is not None else ""
        t_spec_val = _get_val(t_row, t_spec) if t_spec is not None else ""

        # Only compare brand if target file actually has a brand column
        if t_brand is not None and normalize_text(b_brand_val) != normalize_text(t_brand_val):
            field_diffs["brand"] = {"baseline": b_brand_val, "target": t_brand_val, "baseline_num": None, "target_num": None, "match": False, "issue": None}
        # Only compare spec if target file actually has a spec column
        if t_spec is not None and normalize_text(b_spec_val) != normalize_text(t_spec_val):
            field_diffs["spec"] = {"baseline": b_spec_val, "target": t_spec_val, "baseline_num": None, "target_num": None, "match": False, "issue": None}

        if field_diffs:
            # Classify severity
            has_quantity_diff = "quantity" in field_diffs
            has_price_diff = "unit_price" in field_diffs or "total_price" in field_diffs
            has_brand_spec_diff = "brand" in field_diffs or "spec" in field_diffs

            if has_quantity_diff or has_price_diff:
                sev = "warning"
                dtype = "quantity" if has_quantity_diff else "total_price"
            elif has_brand_spec_diff and not has_quantity_diff and not has_price_diff:
                sev = "info"
                dtype = "brand_spec"
            else:
                sev = "warning"
                dtype = "quantity"

            diffs.append({
                "type": dtype,
                "severity": sev,
                "baseline_idx": b_idx,
                "target_idx": t_idx,
                "name": _get_val(b_row, b_name),
                "brand": _get_val(b_row, b_brand),
                "spec": _get_val(b_row, b_spec),
                "fields": _merge_field_comparisons(b_row, t_row, baseline_mapping, target_mapping, field_diffs),
                "match_confidence": confidence,
                "confirmed": None,
            })

    return diffs


def describe_diff(diff: dict, baseline_file: str, target_file: str) -> str:
    """Generate human-readable Chinese description of a difference."""
    field_labels = {
        "name": "品名", "brand": "品牌", "spec": "规格型号",
        "quantity": "数量", "unit_price": "单价", "total_price": "总价",
    }

    if diff["type"] == "missing":
        name = diff.get("name", "未知")
        return f"«{baseline_file}» 中存在「{name}」，但 «{target_file}» 中完全缺失"

    if diff["type"] == "extra":
        name = diff.get("name", "未知")
        return f"«{target_file}» 中多出「{name}」，基准文件中不存在此项"

    # Matched row with field differences
    parts = []
    for fk, fd in diff.get("fields", {}).items():
        if fd.get("match"):
            continue
        label = field_labels.get(fk, fk)
        b_val = fd.get("baseline", "")
        t_val = fd.get("target", "")
        b_num = fd.get("baseline_num")
        t_num = fd.get("target_num")
        if b_num is not None and t_num is not None:
            delta = t_num - b_num
            sign = "+" if delta > 0 else ""
            parts.append(f"{label}: {b_val} → {t_val} ({sign}{delta})")
        else:
            parts.append(f"{label}: {b_val} → {t_val}")

    return "；".join(parts)


def _compare_fields(baseline_row: list | None, target_row: list | None,
                    baseline_mapping: dict, target_mapping: dict) -> dict:
    """Compare all mapped fields between two rows (one may be None for missing/extra)."""
    fields = {}
    all_keys = set(baseline_mapping.values()) | set(target_mapping.values())
    for fk in all_keys:
        b_val = ""
        t_val = ""
        if baseline_row is not None:
            b_col = _find_col_idx(baseline_mapping, fk)
            b_val = _get_val(baseline_row, b_col) if b_col is not None else ""
        if target_row is not None:
            t_col = _find_col_idx(target_mapping, fk)
            t_val = _get_val(target_row, t_col) if t_col is not None else ""
        fields[fk] = {"baseline": b_val, "target": t_val, "baseline_num": None, "target_num": None, "match": b_val == t_val, "issue": None}
    return fields


def _merge_field_comparisons(baseline_row: list, target_row: list,
                             baseline_mapping: dict, target_mapping: dict,
                             field_diffs: dict) -> dict:
    """Build full field comparison with diff fields merged in."""
    full = _compare_fields(baseline_row, target_row, baseline_mapping, target_mapping)
    full.update(field_diffs)
    return full
