import streamlit as st
from engine.column_mapper import extract_table_rows, detect_header_row_index
from engine.row_matcher import match_rows
from engine.diff_detector import detect_differences


def render():
    st.header("步骤 3/5: 确认行匹配")
    st.caption("系统已自动匹配各行，低置信度匹配请手动确认。")

    files = st.session_state.get("files", [])
    mappings = st.session_state.get("column_mappings", [])
    if not files or not mappings:
        st.warning("请先完成列映射")
        return

    data_rows_cache = st.session_state.get("data_rows_cache", [])
    baseline_idx = 0

    # Prepare baseline data
    baseline = files[baseline_idx]
    baseline_header, baseline_data = extract_table_rows(baseline["primary_table"])
    baseline_mapping = mappings[baseline_idx]["mapping"] if mappings[baseline_idx] else {}

    if "match_results" not in st.session_state:
        st.session_state.match_results = [None] * len(files)

    if st.button("开始自动匹配", type="primary", use_container_width=True):
        with st.spinner("正在匹配行..."):
            for fi, f in enumerate(files):
                if fi == baseline_idx:
                    continue
                if not f.get("primary_table"):
                    continue
                target_header, target_data = extract_table_rows(f["primary_table"])
                target_mapping = mappings[fi]["mapping"] if mappings[fi] else {}

                result = match_rows(baseline_data, target_data, baseline_mapping, target_mapping)
                st.session_state.match_results[fi] = result

                st.success(
                    f"{f['file_name']}: "
                    f"精确匹配 {len(result['matches'])} 行, "
                    f"低置信度 {len(result['low_confidence'])} 行, "
                    f"基准独有 {len(result['baseline_unmatched'])} 行, "
                    f"目标独有 {len(result['target_unmatched'])} 行"
                )

    # Show low confidence matches for manual review
    has_low_confidence = False
    for fi, mr in enumerate(st.session_state.match_results):
        if mr and mr.get("low_confidence"):
            has_low_confidence = True
            break

    if has_low_confidence:
        st.warning("以下匹配置信度较低，请确认:")
        for fi, f in enumerate(files):
            if fi == baseline_idx:
                continue
            mr = st.session_state.match_results[fi]
            if not mr or not mr.get("low_confidence"):
                continue

            target_header, target_data = extract_table_rows(f["primary_table"])

            for lc in mr["low_confidence"]:
                b_idx, t_idx, conf = lc
                c1, c2, c3 = st.columns([3, 3, 1])
                with c1:
                    b_name = _safe_get(baseline_data[b_idx], _find_col(baseline_mapping, "name"))
                    b_brand = _safe_get(baseline_data[b_idx], _find_col(baseline_mapping, "brand"))
                    b_spec = _safe_get(baseline_data[b_idx], _find_col(baseline_mapping, "spec"))
                    st.write(f"**基准:** {b_name} | {b_brand} | {b_spec}")
                with c2:
                    t_name = _safe_get(target_data[t_idx], _find_col(mappings[fi]["mapping"] if mappings[fi] else {}, "name"))
                    t_brand = _safe_get(target_data[t_idx], _find_col(mappings[fi]["mapping"] if mappings[fi] else {}, "brand"))
                    t_spec = _safe_get(target_data[t_idx], _find_col(mappings[fi]["mapping"] if mappings[fi] else {}, "spec"))
                    st.write(f"**{f['file_name']}:** {t_name} | {t_brand} | {t_spec}")
                with c3:
                    st.write(f"置信度: **{conf}%**")
                    if st.button("确认匹配", key=f"lc_ok_{fi}_{b_idx}_{t_idx}"):
                        mr["matches"].append((b_idx, t_idx, conf))
                        mr["low_confidence"].remove(lc)
                        st.rerun()
                    if st.button("不是同项", key=f"lc_no_{fi}_{b_idx}_{t_idx}"):
                        mr["baseline_unmatched"].append(b_idx)
                        mr["target_unmatched"].append(t_idx)
                        mr["low_confidence"].remove(lc)
                        st.rerun()

    # Navigation
    st.divider()
    c1, c2 = st.columns([1, 1])
    with c2:
        if st.button("下一步 → 差异确认", type="primary", use_container_width=True):
            # Run diff detection
            if "all_diffs" not in st.session_state:
                st.session_state.all_diffs = [None] * len(files)

            for fi, f in enumerate(files):
                if fi == baseline_idx:
                    continue
                if not f.get("primary_table"):
                    continue
                mr = st.session_state.match_results[fi]
                if not mr:
                    continue

                target_header, target_data = extract_table_rows(f["primary_table"])
                target_mapping = mappings[fi]["mapping"] if mappings[fi] else {}

                diffs = detect_differences(
                    baseline_data, target_data, mr,
                    baseline_mapping, target_mapping
                )
                st.session_state.all_diffs[fi] = diffs

            st.session_state.step = 4
            st.rerun()

    with c1:
        if st.button("← 返回列映射"):
            st.session_state.step = 2
            st.rerun()


def _find_col(mapping: dict, field_key: str) -> int | None:
    for col_idx, fk in mapping.items():
        if fk == field_key:
            return col_idx
    return None


def _safe_get(row: list, col_idx: int | None) -> str:
    if col_idx is None or col_idx >= len(row):
        return ""
    return str(row[col_idx]).strip() if row[col_idx] is not None else ""
