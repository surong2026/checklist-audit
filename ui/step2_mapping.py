import streamlit as st
from engine.column_mapper import map_columns, detect_header_row_index, extract_table_rows
from config import STANDARD_FIELDS


def render():
    st.header("步骤 2/5: 确认列映射")
    st.caption("系统已自动匹配各文件的列到标准字段，请检查并调整低置信度匹配。")

    files = st.session_state.get("files", [])
    if not files:
        st.warning("请先上传文件")
        return

    if "column_mappings" not in st.session_state:
        st.session_state.column_mappings = [None] * len(files)

    if "data_rows_cache" not in st.session_state:
        st.session_state.data_rows_cache = [None] * len(files)

    # Render mapping for each file
    for fi, f in enumerate(files):
        label = "⭐ 基准文件" if fi == 0 else f"比对文件 #{fi + 1}"
        with st.expander(f"{label}: {f['file_name']}", expanded=(fi == 0 or st.session_state.column_mappings[fi] is None)):
            if f.get("error") or not f.get("primary_table"):
                st.error(f"文件解析失败: {f.get('error', '未知错误')}")
                continue

            # Extract header and data rows
            header, data_rows = extract_table_rows(f["primary_table"])
            st.session_state.data_rows_cache[fi] = data_rows

            # Auto-map
            auto_result = map_columns(header)
            current_mapping = st.session_state.column_mappings[fi]

            # If already confirmed by user, show current
            if current_mapping and current_mapping.get("_confirmed"):
                show_confirmed_mapping(fi, f, header, current_mapping)
            else:
                show_editable_mapping(fi, f, header, auto_result)

    # Navigation
    c1, c2 = st.columns([1, 1])
    with c2:
        all_mapped = all(
            m is not None and m.get("_confirmed")
            for i, m in enumerate(st.session_state.column_mappings)
            if files[i].get("primary_table")
        )
        if st.button("下一步 → 行匹配", type="primary", disabled=not all_mapped, use_container_width=True):
            # Save defaults for any unmapped but valid files
            for fi, f in enumerate(files):
                if f.get("primary_table") and not st.session_state.column_mappings[fi]:
                    header, _ = extract_table_rows(f["primary_table"])
                    auto = map_columns(header)
                    auto["_confirmed"] = True
                    st.session_state.column_mappings[fi] = auto
            st.session_state.step = 3
            st.rerun()

    with c1:
        if st.button("← 返回上传"):
            st.session_state.step = 1
            st.rerun()


def show_editable_mapping(fi: int, f: dict, header: list, auto_result: dict):
    """Show editable mapping interface."""
    mapping = auto_result["mapping"]
    confidence = auto_result["confidence"]
    unmapped = auto_result["unmapped"]

    st.write(f"**表头:** {' | '.join(str(h) for h in header if h)}")
    st.write("---")

    updated_mapping = dict(mapping)

    for ri, raw_col in enumerate(header):
        if not str(raw_col).strip():
            continue

        c1, c2, c3 = st.columns([0.35, 0.4, 0.25])

        with c1:
            st.write(f"**{raw_col}**")
        with c2:
            current_field = mapping.get(ri, "")
            field_options = ["— 忽略此列 —"] + [f"{info['cn']}" for info in STANDARD_FIELDS.values()]
            default_idx = 0
            if current_field:
                cn = STANDARD_FIELDS.get(current_field, {}).get("cn", "")
                if cn:
                    try:
                        default_idx = field_options.index(cn)
                    except ValueError:
                        pass

            selected = st.selectbox(
                f"映射到",
                                field_options,
                                index=default_idx,
                                key=f"map_{fi}_{ri}",
                                label_visibility="collapsed",
                            )
            if selected == "— 忽略此列 —":
                if ri in updated_mapping:
                    del updated_mapping[ri]
            else:
                for fk, finfo in STANDARD_FIELDS.items():
                    if finfo["cn"] == selected:
                        updated_mapping[ri] = fk
                        break

        with c3:
            if ri in confidence:
                score = confidence[ri]
                if score >= 90:
                    st.success(f"✓ {score}%")
                else:
                    st.warning(f"⚠ {score}%")
            else:
                st.write("")

    if st.button("确认此文件的列映射", key=f"confirm_map_{fi}", type="primary"):
        auto_result["mapping"] = updated_mapping
        auto_result["_confirmed"] = True
        st.session_state.column_mappings[fi] = auto_result
        st.rerun()


def show_confirmed_mapping(fi: int, f: dict, header: list, mapping: dict):
    """Show already-confirmed mapping."""
    st.success("列映射已确认 ✓")
    for ri, raw_col in enumerate(header):
        if not str(raw_col).strip():
            continue
        field_key = mapping["mapping"].get(ri, "")
        cn = STANDARD_FIELDS.get(field_key, {}).get("cn", "忽略") if field_key else "忽略"
        score = mapping.get("confidence", {}).get(ri, "-")
        st.write(f"  {raw_col} → **{cn}** (置信度: {score}%)")

    if st.button("重新映射", key=f"remap_{fi}"):
        st.session_state.column_mappings[fi] = None
        st.rerun()
