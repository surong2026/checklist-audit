import streamlit as st
from engine.column_mapper import extract_table_rows
from engine.diff_detector import describe_diff


def render():
    st.header("步骤 4/5: 人工确认差异")
    st.caption("所有差异已标出，请逐项确认为「合理」或「异常」。")

    files = st.session_state.get("files", [])
    all_diffs = st.session_state.get("all_diffs", [])
    mappings = st.session_state.get("column_mappings", [])

    if not all_diffs or all(d is None for d in all_diffs):
        st.warning("请先完成行匹配")
        return

    if "confirmed_map" not in st.session_state:
        st.session_state.confirmed_map = {}  # {(file_idx, diff_idx): True/False/None}

    baseline_idx = 0
    baseline = files[baseline_idx]
    baseline_header, baseline_data = extract_table_rows(baseline["primary_table"])

    # Count diffs
    total_diffs = 0
    confirmed_count = 0
    for fi, diffs in enumerate(all_diffs):
        if diffs:
            total_diffs += len(diffs)
            for di in range(len(diffs)):
                if (fi, di) in st.session_state.confirmed_map:
                    confirmed_count += 1

    # Summary bar
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("总差异数", total_diffs)
    with c2:
        st.metric("已确认", confirmed_count)
    with c3:
        critical = sum(1 for diffs in all_diffs if diffs for d in diffs if d["type"] == "missing")
        st.metric("严重(缺失)", critical)
    with c4:
        unconfirmed = total_diffs - confirmed_count
        st.metric("待确认", unconfirmed)

    if total_diffs == 0:
        st.success("未发现差异！可以直接导出报告。")
    else:
        # Filter tabs
        tab1, tab2, tab3, tab4 = st.tabs(["🔴 严重", "🟡 差异", "🔵 多余", "✅ 已处理"])

        for fi, f in enumerate(files):
            if fi == baseline_idx or not all_diffs[fi]:
                continue

            target_header, target_data = extract_table_rows(f["primary_table"])

            for di, diff in enumerate(all_diffs[fi]):
                conf = st.session_state.confirmed_map.get((fi, di))

                # Determine which tab to show in
                if diff["type"] == "missing":
                    container = tab1
                elif diff["type"] == "extra":
                    container = tab3
                elif conf is not None:
                    container = tab4
                else:
                    container = tab2

                with container:
                    render_diff_card(fi, di, diff, conf, f["file_name"], baseline_data, target_data, mappings[fi]["mapping"] if mappings[fi] else {})

    # Batch operations
    st.divider()
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        if st.button("全部标记为合理", use_container_width=True):
            for fi, diffs in enumerate(all_diffs):
                if diffs:
                    for di in range(len(diffs)):
                        if (fi, di) not in st.session_state.confirmed_map:
                            st.session_state.confirmed_map[(fi, di)] = True
            st.rerun()
    with c2:
        if st.button("全部标记为异常", use_container_width=True):
            for fi, diffs in enumerate(all_diffs):
                if diffs:
                    for di in range(len(diffs)):
                        if (fi, di) not in st.session_state.confirmed_map:
                            st.session_state.confirmed_map[(fi, di)] = False
            st.rerun()
    with c3:
        if st.button("清空确认", use_container_width=True):
            st.session_state.confirmed_map = {}
            st.rerun()

    # Navigation
    st.divider()
    c1, c2 = st.columns([1, 1])
    with c2:
        if unconfirmed > 0:
            st.info(f"仍有 {unconfirmed} 项差异未确认，是否继续导出？")
        if st.button("下一步 → 导出报告", type="primary", use_container_width=True):
            st.session_state.step = 5
            st.rerun()
    with c1:
        if st.button("← 返回行匹配"):
            st.session_state.step = 3
            st.rerun()


def render_diff_card(fi: int, di: int, diff: dict, conf, target_filename: str,
                     baseline_data: list, target_data: list, target_mapping: dict):
    """Render a single diff item card."""
    severity_icon = {"critical": "🔴", "warning": "🟡", "info": "🔵"}.get(diff["severity"], "⚪")
    status_badge = ""
    if conf is True:
        status_badge = "✅ 已确认合理"
    elif conf is False:
        status_badge = "❌ 已确认异常"

    baseline_file = st.session_state.get("files", [{}])[0].get("file_name", "基准文件")

    with st.container(border=True):
        c1, c2, c3 = st.columns([6, 2, 2])
        with c1:
            st.write(f"{severity_icon} **{diff.get('name', '?')}** | {diff.get('brand', '?')} | {diff.get('spec', '?')}")
            # Summary line using describe_diff
            desc = describe_diff(diff, baseline_file, target_filename)
            if diff["type"] == "missing":
                st.error(desc)
            elif diff["type"] == "extra":
                st.info(desc)
            else:
                st.warning(desc)
                # Detailed field breakdown
                for fk, fd in diff.get("fields", {}).items():
                    if not fd.get("match"):
                        field_cn = {"name": "品名", "brand": "品牌", "spec": "规格", "quantity": "数量", "unit_price": "单价", "total_price": "总价"}.get(fk, fk)
                        st.write(f"  {field_cn}: **{fd.get('baseline', '-')}** → **{fd.get('target', '-')}**")
        with c2:
            st.write(status_badge)
        with c3:
            if conf is None:
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("合理 ✓", key=f"ok_{fi}_{di}", use_container_width=True):
                        st.session_state.confirmed_map[(fi, di)] = True
                        st.rerun()
                with col_b:
                    if st.button("异常 ✗", key=f"ab_{fi}_{di}", use_container_width=True):
                        st.session_state.confirmed_map[(fi, di)] = False
                        st.rerun()
            else:
                if st.button("重置", key=f"reset_{fi}_{di}"):
                    del st.session_state.confirmed_map[(fi, di)]
                    st.rerun()
