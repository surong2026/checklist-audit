import os
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from config import COLOR_RED, COLOR_YELLOW, COLOR_GREEN, COLOR_GRAY, COLOR_BLUE, COLOR_WHITE


def generate_report(all_files: list, baseline_idx: int, mappings: list, match_results: list,
                    all_diffs: list, confirmed_map: dict, output_path: str = None) -> str:
    """Generate a multi-sheet Excel report.

    Args:
        all_files: list of {"file_name", "primary_table", ...}
        baseline_idx: index of baseline file in all_files
        mappings: list of column mapping dicts per file
        match_results: list of match_result dicts per file (None for baseline)
        all_diffs: list of diff lists per file (None for baseline)
        confirmed_map: {(file_idx, diff_idx): True/False} for user confirmations
        output_path: optional output path

    Returns:
        Path to generated .xlsx file.
    """
    if output_path is None:
        output_path = os.path.join(os.path.expanduser("~"), "清单核对系统", f"核对报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")

    wb = openpyxl.Workbook()

    # Styles
    header_font = Font(name="微软雅黑", bold=True, size=11)
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font_white = Font(name="微软雅黑", bold=True, size=11, color="FFFFFF")
    red_fill = PatternFill(start_color=COLOR_RED, end_color=COLOR_RED, fill_type="solid")
    yellow_fill = PatternFill(start_color=COLOR_YELLOW, end_color=COLOR_YELLOW, fill_type="solid")
    green_fill = PatternFill(start_color=COLOR_GREEN, end_color=COLOR_GREEN, fill_type="solid")
    gray_fill = PatternFill(start_color=COLOR_GRAY, end_color=COLOR_GRAY, fill_type="solid")
    blue_fill = PatternFill(start_color=COLOR_BLUE, end_color=COLOR_BLUE, fill_type="solid")
    thin_border = Border(
        left=Side(style="thin"), right=Side(style="thin"),
        top=Side(style="thin"), bottom=Side(style="thin")
    )
    wrap_align = Alignment(wrap_text=True, vertical="center")

    # Normalize mappings: accept either plain dict or {"mapping": ..., "confidence": ...} wrapper
    mappings = [_unwrap_mapping(m) for m in mappings]

    baseline_file = all_files[baseline_idx]["file_name"]
    target_files = [f["file_name"] for i, f in enumerate(all_files) if i != baseline_idx]
    stats = _compute_stats(all_files, baseline_idx, all_diffs, confirmed_map)

    # ============================================================
    # Sheet 1: 差异汇总
    # ============================================================
    ws1 = wb.active
    ws1.title = "差异汇总"

    # Title block
    ws1.merge_cells("A1:J1")
    ws1["A1"] = "清单核对报告"
    ws1["A1"].font = Font(name="微软雅黑", bold=True, size=16)
    ws1["A1"].alignment = Alignment(horizontal="center")

    ws1.merge_cells("A2:J2")
    ws1["A2"] = f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    ws1["A2"].font = Font(name="微软雅黑", size=10)

    ws1.merge_cells("A3:J3")
    ws1["A3"] = f"基准文件: {baseline_file}"
    ws1["A3"].font = Font(name="微软雅黑", size=10)

    ws1.merge_cells("A4:J4")
    ws1["A4"] = f"比对文件: {', '.join(target_files)}"
    ws1["A4"].font = Font(name="微软雅黑", size=10)

    # Statistics
    row = 6
    ws1.merge_cells(f"A{row}:J{row}")
    ws1[f"A{row}"] = "统计概览"
    ws1[f"A{row}"].font = Font(name="微软雅黑", bold=True, size=12)
    row = 7

    stat_items = [
        ("基准总项数 (扣除汇总行)", stats["baseline_count"]),
        ("匹配成功", stats["matched"]),
        ("严重问题 (缺失)", stats["critical"]),
        ("差异项 (数量/价格)", stats["warnings"]),
        ("注意项 (品牌/规格)", stats["info"]),
        ("多余项", stats["extra"]),
        ("已确认合理", stats["confirmed_ok"]),
        ("确认异常", stats["confirmed_abnormal"]),
    ]
    for label, val in stat_items:
        ws1[f"A{row}"] = label
        ws1[f"B{row}"] = val
        ws1[f"A{row}"].font = Font(name="微软雅黑", size=10)
        ws1[f"B{row}"].font = Font(name="微软雅黑", bold=True, size=10)
        row += 1

    # ---- Section A: 严重问题 (缺失项) ----
    missing_diffs = _collect_diffs_by_type(all_diffs, "missing")
    row = _write_diff_section(
        ws1, row, "严重问题 — 缺失项",
        ["序号", "品名", "品牌", "规格型号", "比对文件", "问题描述", "确认状态"],
        PatternFill(start_color="CC0000", end_color="CC0000", fill_type="solid"),
        red_fill, missing_diffs, all_files, baseline_file, target_files, confirmed_map,
        missing_desc=True
    )

    # ---- Section B: 数量/价格差异 ----
    qty_price_diffs = _collect_diffs_by_severity(all_diffs, "warning")
    row = _write_diff_section(
        ws1, row, "数量/价格差异",
        ["序号", "品名", "品牌", "规格型号", "比对文件", "差异明细", "确认状态"],
        PatternFill(start_color="E68A00", end_color="E68A00", fill_type="solid"),
        yellow_fill, qty_price_diffs, all_files, baseline_file, target_files, confirmed_map
    )

    # ---- Section C: 品牌/规格不一致 ----
    brand_spec_diffs = _collect_diffs_by_severity(all_diffs, "info")
    row = _write_diff_section(
        ws1, row, "品牌/规格不一致",
        ["序号", "品名", "品牌", "规格型号", "比对文件", "差异明细", "确认状态"],
        PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid"),
        blue_fill, brand_spec_diffs, all_files, baseline_file, target_files, confirmed_map
    )

    # ---- Section D: 多余项 ----
    extra_diffs = _collect_diffs_by_type(all_diffs, "extra")
    row = _write_diff_section(
        ws1, row, "多余项 (基准中不存在)",
        ["序号", "品名", "品牌", "规格型号", "所在文件", "问题描述", "确认状态"],
        PatternFill(start_color="808080", end_color="808080", fill_type="solid"),
        gray_fill, extra_diffs, all_files, baseline_file, target_files, confirmed_map,
        extra_desc=True
    )

    # Signature area
    row += 2
    ws1.merge_cells(f"A{row}:J{row}")
    ws1[f"A{row}"] = "签字确认"
    ws1[f"A{row}"].font = Font(name="微软雅黑", bold=True, size=11)
    row += 1
    ws1[f"A{row}"] = "核对人: ____________    日期: ____________"
    row += 1
    ws1[f"A{row}"] = "复核人: ____________    日期: ____________"
    row += 1
    ws1[f"A{row}"] = "备注:"
    row += 1
    ws1.merge_cells(f"A{row}:J{row + 2}")
    ws1[f"A{row}"] = ""

    # Column widths
    ws1.column_dimensions["A"].width = 6
    ws1.column_dimensions["B"].width = 22
    ws1.column_dimensions["C"].width = 12
    ws1.column_dimensions["D"].width = 30
    ws1.column_dimensions["E"].width = 18
    ws1.column_dimensions["F"].width = 42
    ws1.column_dimensions["G"].width = 12

    # ============================================================
    # Sheet 2: 逐项明细
    # ============================================================
    ws2 = wb.create_sheet("逐项明细")

    base_name = baseline_file
    detail_headers = ["序号", "品名", "品牌", "规格型号"]
    for fi, f in enumerate(all_files):
        if fi == baseline_idx:
            detail_headers.extend([f"{base_name}-数量", f"{base_name}-单价", f"{base_name}-总价"])
        else:
            fn = f["file_name"]
            detail_headers.extend([f"{fn}-数量", f"{fn}-单价", f"{fn}-总价"])
    detail_headers.extend(["差异状态", "差异明细", "确认状态"])

    for ci, h in enumerate(detail_headers, 1):
        cell = ws2.cell(row=1, column=ci, value=h)
        cell.font = header_font_white
        cell.fill = header_fill
        cell.border = thin_border
        cell.alignment = wrap_align

    from engine.column_mapper import detect_header_row_index
    from engine.diff_detector import describe_diff

    baseline_table = all_files[baseline_idx]["primary_table"]
    b_mapping = mappings[baseline_idx]
    b_header_idx = detect_header_row_index(baseline_table)
    baseline_data = baseline_table[b_header_idx + 1:]

    b_name_col = _find_col_in_mapping(b_mapping, "name")
    b_brand_col = _find_col_in_mapping(b_mapping, "brand")
    b_spec_col = _find_col_in_mapping(b_mapping, "spec")
    b_qty_col = _find_col_in_mapping(b_mapping, "quantity")
    b_up_col = _find_col_in_mapping(b_mapping, "unit_price")
    b_tp_col = _find_col_in_mapping(b_mapping, "total_price")

    row = 2
    for bi, b_data_row in enumerate(baseline_data):
        vals = [row - 1,
                _safe_get(b_data_row, b_name_col),
                _safe_get(b_data_row, b_brand_col),
                _safe_get(b_data_row, b_spec_col),
                _safe_get(b_data_row, b_qty_col),
                _safe_get(b_data_row, b_up_col),
                _safe_get(b_data_row, b_tp_col)]

        all_matched = True
        combined_diff_type = None
        combined_diff_desc = []

        for fi, f in enumerate(all_files):
            if fi == baseline_idx:
                continue
            target_table = f.get("primary_table")
            if target_table is None:
                vals.extend(["-", "-", "-"])
                all_matched = False
                continue
            t_header_idx = detect_header_row_index(target_table)
            target_data = target_table[t_header_idx + 1:]
            t_mapping = mappings[fi]
            if t_mapping is None:
                vals.extend(["-", "-", "-"])
                all_matched = False
                continue
            t_qty_col = _find_col_in_mapping(t_mapping, "quantity")
            t_up_col = _find_col_in_mapping(t_mapping, "unit_price")
            t_tp_col = _find_col_in_mapping(t_mapping, "total_price")

            t_row = None
            matched_diff = None
            if all_diffs[fi]:
                for diff in all_diffs[fi]:
                    if diff.get("baseline_idx") == bi and diff["type"] != "missing":
                        matched_ti = diff.get("target_idx")
                        if matched_ti is not None and matched_ti < len(target_data):
                            t_row = target_data[matched_ti]
                            matched_diff = diff
                        break

            if t_row:
                vals.extend([_safe_get(t_row, t_qty_col), _safe_get(t_row, t_up_col), _safe_get(t_row, t_tp_col)])
            else:
                vals.extend(["-", "-", "-"])
                all_matched = False

            if matched_diff:
                diff_label = _diff_status_label(matched_diff)
                if diff_label:
                    combined_diff_type = diff_label
                desc = describe_diff(matched_diff, baseline_file, all_files[fi]["file_name"])
                combined_diff_desc.append(f"[{all_files[fi]['file_name']}] {desc}")

        # Difference status
        if not all_matched:
            vals.append("缺失")
        elif combined_diff_type:
            vals.append(combined_diff_type)
        else:
            vals.append("✓ 一致")

        # Difference detail
        vals.append("；".join(combined_diff_desc) if combined_diff_desc else "")

        # Confirmation status
        conf_status = ""
        for fi, diffs in enumerate(all_diffs):
            if diffs is None:
                continue
            for di, diff in enumerate(diffs):
                if diff.get("baseline_idx") == bi:
                    c = confirmed_map.get((fi, di))
                    if c is True:
                        conf_status = "已确认合理"
                    elif c is False:
                        conf_status = "已确认异常"
                    break
        vals.append(conf_status)

        # Write row
        for ci, v in enumerate(vals, 1):
            cell = ws2.cell(row=row, column=ci, value=v)
            cell.border = thin_border
            cell.alignment = wrap_align
            status_str = str(vals[-3])  # diff status column
            if "缺失" in status_str:
                cell.fill = red_fill
            elif any(kw in status_str for kw in ("数量差异", "总价差异", "单价差异")):
                cell.fill = yellow_fill
            elif "品牌" in status_str or "规格" in status_str:
                cell.fill = blue_fill
            elif "一致" in status_str:
                cell.fill = green_fill

        row += 1

    # Column widths
    ws2.column_dimensions["A"].width = 6
    ws2.column_dimensions["B"].width = 22
    ws2.column_dimensions["C"].width = 12
    ws2.column_dimensions["D"].width = 30
    for c in "EFGHIJKLMNOPQRSTUVWXYZ":
        ws2.column_dimensions[c].width = 14

    # ============================================================
    # Sheet 3: 匹配统计
    # ============================================================
    ws3 = wb.create_sheet("匹配统计")

    stat_headers = ["文件名", "上传时间", "总行数", "有效行数", "匹配行数", "未匹配行数", "多余行数"]
    for ci, h in enumerate(stat_headers, 1):
        cell = ws3.cell(row=1, column=ci, value=h)
        cell.font = header_font_white
        cell.fill = header_fill
        cell.border = thin_border

    for fi, f in enumerate(all_files):
        table = f["primary_table"]
        h_idx = detect_header_row_index(table)
        total = len(table)
        effective = len(table) - h_idx - 1

        if fi == baseline_idx:
            matched = effective
            unmatched = 0
            extra = 0
        else:
            mr = match_results[fi] if match_results and fi < len(match_results) and match_results[fi] else {}
            matched = len(mr.get("matches", [])) + len(mr.get("low_confidence", []))
            unmatched = len(mr.get("baseline_unmatched", []))
            extra = len(mr.get("target_unmatched", []))

        vals = [f["file_name"], datetime.now().strftime("%Y-%m-%d %H:%M"), total, effective, matched, unmatched, extra]
        for ci, v in enumerate(vals, 1):
            cell = ws3.cell(row=fi + 2, column=ci, value=v)
            cell.border = thin_border

    ws3.column_dimensions["A"].width = 30
    for c in "BCDEFG":
        ws3.column_dimensions[c].width = 14

    wb.save(output_path)
    return output_path


# ================================================================
# Helper: Write a diff section on Sheet 1
# ================================================================
def _write_diff_section(ws, start_row: int, title: str, headers: list,
                        header_fill: PatternFill, row_fill: PatternFill,
                        diffs: list, all_files: list, baseline_file: str,
                        target_files: list, confirmed_map: dict,
                        missing_desc: bool = False, extra_desc: bool = False) -> int:
    """Write a titled section of diffs. Returns next available row."""
    from engine.diff_detector import describe_diff

    row = start_row + 1
    ws.merge_cells(f"A{row}:J{row}")
    ws[f"A{row}"] = title
    ws[f"A{row}"].font = Font(name="微软雅黑", bold=True, size=12)
    row += 1

    if not diffs:
        ws.merge_cells(f"A{row}:J{row}")
        ws[f"A{row}"] = "（无）"
        ws[f"A{row}"].font = Font(name="微软雅黑", size=10, italic=True)
        return row + 1

    for ci, h in enumerate(headers, 1):
        cell = ws.cell(row=row, column=ci, value=h)
        cell.font = Font(name="微软雅黑", bold=True, size=10, color="FFFFFF")
        cell.fill = header_fill
        cell.border = Border(
            left=Side(style="thin"), right=Side(style="thin"),
            top=Side(style="thin"), bottom=Side(style="thin")
        )
    row += 1

    for di, (fi, diff_idx, diff) in enumerate(diffs, 1):
        # Determine which file this diff belongs to
        fn = all_files[fi]["file_name"] if fi < len(all_files) else ""

        if missing_desc:
            desc = f"基准«{baseline_file}»中存在，但«{fn}»中完全缺失"
        elif extra_desc:
            desc = f"«{fn}»中多出此项，基准文件中不存在"
        else:
            desc = describe_diff(diff, baseline_file, fn)

        conf = confirmed_map.get((fi, diff_idx))
        status = "已确认异常" if conf is False else ("已确认合理" if conf is True else "待确认")

        row_data = [
            di,
            diff.get("name", ""),
            diff.get("brand", ""),
            diff.get("spec", ""),
            fn,
            desc,
            status,
        ]
        for ci, v in enumerate(row_data, 1):
            cell = ws.cell(row=row, column=ci, value=v)
            cell.fill = row_fill
            cell.border = Border(
                left=Side(style="thin"), right=Side(style="thin"),
                top=Side(style="thin"), bottom=Side(style="thin")
            )
            cell.alignment = Alignment(wrap_text=True, vertical="center")
        row += 1

    return row


# ================================================================
# Helpers
# ================================================================
def _collect_diffs_by_type(all_diffs: list, diff_type: str) -> list:
    """Collect all diffs of a given type across all files. Returns [(file_idx, diff_idx, diff), ...]."""
    result = []
    for fi, diffs in enumerate(all_diffs):
        if diffs is None:
            continue
        for di, diff in enumerate(diffs):
            if diff["type"] == diff_type:
                result.append((fi, di, diff))
    return result


def _collect_diffs_by_severity(all_diffs: list, severity: str) -> list:
    """Collect all diffs of a given severity across all files."""
    result = []
    for fi, diffs in enumerate(all_diffs):
        if diffs is None:
            continue
        for di, diff in enumerate(diffs):
            if diff.get("severity") == severity and diff["type"] not in ("missing", "extra"):
                result.append((fi, di, diff))
    return result


def _diff_status_label(diff: dict) -> str:
    """Return a concise Chinese label for the diff type."""
    type_map = {
        "quantity": "数量差异",
        "unit_price": "单价差异",
        "total_price": "总价差异",
        "brand_spec": "品牌/规格不一致",
        "missing": "缺失",
        "extra": "多余项",
    }
    return type_map.get(diff["type"], "差异")


def _compute_stats(all_files: list, baseline_idx: int, all_diffs: list, confirmed_map: dict) -> dict:
    """Compute summary statistics."""
    stats = {"baseline_count": 0, "matched": 0, "critical": 0, "warnings": 0,
             "info": 0, "extra": 0, "confirmed_ok": 0, "confirmed_abnormal": 0}

    baseline_table = all_files[baseline_idx]["primary_table"]
    from engine.column_mapper import detect_header_row_index
    h_idx = detect_header_row_index(baseline_table)
    stats["baseline_count"] = len(baseline_table) - h_idx - 1

    for fi, diffs in enumerate(all_diffs):
        if diffs is None:
            continue
        for di, diff in enumerate(diffs):
            if diff["type"] == "missing":
                stats["critical"] += 1
            elif diff["type"] == "extra":
                stats["extra"] += 1
            elif diff["severity"] == "warning":
                stats["warnings"] += 1
            elif diff["severity"] == "info":
                stats["info"] += 1

            conf = confirmed_map.get((fi, di))
            if conf is True:
                stats["confirmed_ok"] += 1
            elif conf is False:
                stats["confirmed_abnormal"] += 1

    all_matched_items = set()
    for fi, f in enumerate(all_files):
        if fi == baseline_idx:
            continue
        if all_diffs[fi]:
            for diff in all_diffs[fi]:
                if diff["type"] not in ("missing", "extra"):
                    all_matched_items.add(diff.get("baseline_idx"))
    stats["matched"] = len(all_matched_items)

    return stats


def _find_col_in_mapping(mapping: dict, field_key: str) -> int | None:
    for col_idx, fk in mapping.items():
        if fk == field_key:
            return col_idx
    return None


def _unwrap_mapping(mapping) -> dict:
    """Normalize mapping: accept either plain {col: field} dict or wrapped {"mapping": ..., ...} dict."""
    if mapping is None:
        return {}
    if "mapping" in mapping:
        return mapping["mapping"]
    return mapping


def _safe_get(row: list, col_idx: int | None) -> str:
    if col_idx is None or col_idx >= len(row):
        return ""
    return str(row[col_idx]).strip() if row[col_idx] is not None else ""
