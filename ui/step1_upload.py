import streamlit as st
import os
import tempfile
import shutil
from config import SUPPORTED_EXTENSIONS, MAX_FILES, MIN_FILES
from models.file_parser import parse_file


def render():
    st.header("步骤 1/5: 上传清单文件")
    st.caption("支持格式: .xls / .xlsx / .pdf / .docx / .et | 至少 2 份，最多 10 份")

    if "uploaded_files_info" not in st.session_state:
        st.session_state.uploaded_files_info = []
    if "temp_dir" not in st.session_state:
        st.session_state.temp_dir = tempfile.mkdtemp(prefix="checklist_")

    uploaded = st.file_uploader(
        "拖拽或点击上传清单文件",
        type=["xls", "xlsx", "pdf", "docx", "et"],
        accept_multiple_files=True,
        key="file_uploader",
    )

    if uploaded:
        # Save to temp dir
        for uf in uploaded:
            if uf.name not in [info["name"] for info in st.session_state.uploaded_files_info]:
                if len(st.session_state.uploaded_files_info) >= MAX_FILES:
                    st.warning(f"最多支持 {MAX_FILES} 份文件")
                    break
                # Save file
                file_path = os.path.join(st.session_state.temp_dir, uf.name)
                with open(file_path, "wb") as f:
                    f.write(uf.getbuffer())
                st.session_state.uploaded_files_info.append({
                    "name": uf.name,
                    "path": file_path,
                    "size": uf.size,
                    "parsed": False,
                })

    # Show uploaded files
    if st.session_state.uploaded_files_info:
        st.subheader("已上传文件")
        files_to_remove = []

        for fi, info in enumerate(st.session_state.uploaded_files_info):
            c1, c2, c3 = st.columns([0.06, 0.7, 0.24])
            with c1:
                if fi == 0:
                    st.markdown("⭐")
                else:
                    st.write(f"#{fi + 1}")
            with c2:
                ext = os.path.splitext(info["name"])[1].lower()
                label = "基准文件" if fi == 0 else f"比对文件 {fi + 1}"
                st.write(f"**{info['name']}** ({ext}) — {label}")
            with c3:
                if st.button("删除", key=f"del_{fi}"):
                    files_to_remove.append(fi)

        for fi in sorted(files_to_remove, reverse=True):
            removed = st.session_state.uploaded_files_info.pop(fi)
            if os.path.exists(removed["path"]):
                os.remove(removed["path"])

    # Parse all files
    if st.session_state.uploaded_files_info and not all(info.get("parsed") for info in st.session_state.uploaded_files_info):
        if st.button("解析所有文件", type="primary", use_container_width=True):
            with st.spinner("正在解析文件..."):
                for info in st.session_state.uploaded_files_info:
                    if not info.get("parsed"):
                        result = parse_file(info["path"])
                        info["parsed"] = True
                        info["parse_result"] = result
                        if result.get("error"):
                            st.error(f"解析 {info['name']} 失败: {result['error']}")
                        elif result.get("primary_table"):
                            table = result["primary_table"]
                            st.success(f"{info['name']}: 解析成功，提取到 {len(table)} 行数据")
                        else:
                            st.warning(f"{info['name']}: 未检测到表格数据")

    # Navigation
    c1, c2 = st.columns([1, 1])
    with c2:
        parsed_count = sum(1 for info in st.session_state.uploaded_files_info if info.get("parsed") and not info.get("parse_result", {}).get("error"))
        can_proceed = parsed_count >= MIN_FILES
        if not can_proceed:
            st.info(f"至少需要 {MIN_FILES} 份文件解析成功才能继续 (当前: {parsed_count})")

        if st.button("下一步 → 列映射", type="primary", disabled=not can_proceed, use_container_width=True):
            save_parsed_data_to_session()
            st.session_state.step = 2
            st.rerun()


def save_parsed_data_to_session():
    """Save parsed file data into session state for downstream steps."""
    st.session_state.files = []
    for info in st.session_state.uploaded_files_info:
        parsed = info.get("parse_result", {})
        st.session_state.files.append({
            "file_name": info["name"],
            "file_path": info["path"],
            "extension": os.path.splitext(info["name"])[1].lower(),
            "primary_table": parsed.get("primary_table"),
            "error": parsed.get("error"),
            "meta": parsed.get("meta", {}),
        })
