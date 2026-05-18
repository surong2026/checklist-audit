import streamlit as st
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import APP_NAME, APP_VERSION
from utils.task_manager import load_autosave

st.set_page_config(
    page_title=f"{APP_NAME} v{APP_VERSION}",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def main():
    # CSS for better appearance
    st.markdown("""
    <style>
    .stApp { max-width: 1200px; margin: 0 auto; }
    .step-indicator { display: flex; justify-content: center; gap: 12px; margin-bottom: 24px; }
    .step-dot { width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; color: white; }
    .step-active { background-color: #1f77b4; }
    .step-done { background-color: #2ca02c; }
    .step-inactive { background-color: #ccc; }
    </style>
    """, unsafe_allow_html=True)

    # Initialize session state
    if "step" not in st.session_state:
        # Try to restore from autosave
        autosave = load_autosave()
        if autosave:
            st.session_state.files = autosave.get("files", [])
            st.session_state.column_mappings = autosave.get("mappings", [None] * len(autosave.get("files", [])))
            st.session_state.match_results = autosave.get("match_results", [None] * len(autosave.get("files", [])))
            st.session_state.all_diffs = autosave.get("all_diffs", [None] * len(autosave.get("files", [])))
            st.session_state.confirmed_map = {}
            for k, v in autosave.get("confirmed_map", {}).items():
                try:
                    st.session_state.confirmed_map[eval(k)] = v
                except Exception:
                    pass
            st.session_state.step = 1
        else:
            st.session_state.step = 1

    # Title
    st.title(f"📋 {APP_NAME}")
    st.caption(f"v{APP_VERSION} — 多份清单逐项核对，自动识别差异，生成核对报告")

    # Step indicator
    steps = ["① 上传文件", "② 列映射", "③ 行匹配", "④ 差异确认", "⑤ 导出报告"]
    cols = st.columns(5)
    for i, (col, label) in enumerate(zip(cols, steps)):
        with col:
            if i + 1 == st.session_state.step:
                st.markdown(f"**🔵 {label}**")
            elif i + 1 < st.session_state.step:
                st.markdown(f"✅ ~~{label}~~")
            else:
                st.markdown(f"⚪ {label}")

    st.divider()

    # Render current step
    from ui.step1_upload import render as step1
    from ui.step2_mapping import render as step2
    from ui.step3_match import render as step3
    from ui.step4_confirm import render as step4
    from ui.step5_export import render as step5

    step_funcs = {1: step1, 2: step2, 3: step3, 4: step4, 5: step5}
    render_func = step_funcs.get(st.session_state.step, step1)
    render_func()


if __name__ == "__main__":
    main()
