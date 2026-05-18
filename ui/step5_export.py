import streamlit as st
import os
from engine.report_generator import generate_report
from utils.task_manager import save_task, list_tasks, load_task, delete_task, autosave


def render():
    st.header("步骤 5/5: 导出报告 & 保存任务")

    files = st.session_state.get("files", [])
    mappings = st.session_state.get("column_mappings", [])
    match_results = st.session_state.get("match_results", [])
    all_diffs = st.session_state.get("all_diffs", [])
    confirmed_map = st.session_state.get("confirmed_map", {})

    baseline_idx = 0

    # Generate report
    if "report_path" not in st.session_state:
        with st.spinner("正在生成报告..."):
            path = generate_report(files, baseline_idx, mappings, match_results, all_diffs, confirmed_map)
            st.session_state.report_path = path

    report_path = st.session_state.report_path

    # Summary
    st.subheader("报告概览")
    from engine.report_generator import _compute_stats
    stats = _compute_stats(files, baseline_idx, all_diffs, confirmed_map)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("基准项数", stats["baseline_count"])
    with c2:
        st.metric("严重问题", stats["critical"], delta=None if stats["critical"] == 0 else str(stats["critical"]))
    with c3:
        st.metric("已确认异常", stats["confirmed_abnormal"])
    with c4:
        st.metric("已确认合理", stats["confirmed_ok"])

    # Export
    st.subheader("导出报告")
    with open(report_path, "rb") as f:
        st.download_button(
            label="下载 Excel 报告 (.xlsx)",
            data=f,
            file_name=os.path.basename(report_path),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="primary",
        )

    # Save task
    st.subheader("保存核对任务")
    task_name = st.text_input("任务名称", value=f"核对_{files[baseline_idx]['file_name']}" if files else "")
    if st.button("保存当前任务", use_container_width=True):
        state = {
            "files": files,
            "mappings": mappings,
            "match_results": match_results,
            "all_diffs": all_diffs,
            "confirmed_map": {str(k): v for k, v in confirmed_map.items()},
            "report_path": report_path,
        }
        saved_path = save_task(task_name, state)
        st.success(f"任务已保存: {os.path.basename(saved_path)}")

        # Also autosave
        autosave(state)
        st.info("已自动备份")

    # Load task
    with st.expander("加载历史任务"):
        tasks = list_tasks()
        if tasks:
            for t in tasks[:10]:
                c1, c2, c3 = st.columns([5, 2, 1])
                with c1:
                    st.write(f"**{t['name']}** — {t['file_count']} 文件")
                with c2:
                    st.write(t["saved_at"])
                with c3:
                    if st.button("加载", key=f"load_{t['path']}"):
                        state = load_task(t["path"])
                        st.session_state.files = state.get("files", [])
                        st.session_state.column_mappings = state.get("mappings", [])
                        st.session_state.match_results = state.get("match_results", [])
                        st.session_state.all_diffs = state.get("all_diffs", [])
                        st.session_state.confirmed_map = {eval(k): v for k, v in state.get("confirmed_map", {}).items()}
                        st.session_state.step = 1
                        st.rerun()
                # Trash button
                with st.expander("", expanded=False):
                    if st.button("删除", key=f"del_task_{t['path']}"):
                        delete_task(t["path"])
                        st.rerun()
        else:
            st.write("暂无保存的任务")

    # New task
    st.divider()
    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("← 返回差异确认"):
            st.session_state.step = 4
            st.rerun()
    with c2:
        if st.button("开始新任务", type="secondary", use_container_width=True):
            _clear_session()
            st.rerun()


def _clear_session():
    """Clear all session state for a new task."""
    keys_to_keep = []
    for key in list(st.session_state.keys()):
        if key not in keys_to_keep:
            del st.session_state[key]
    st.session_state.step = 1
