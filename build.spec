# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for ChecklistAudit — Windows onedir build."""

import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

# SPECPATH is provided by PyInstaller — points to the directory containing the .spec file
base = Path(SPECPATH).absolute()

# Collect streamlit templates, static files, and all sub-modules
streamlit_datas, streamlit_binaries, streamlit_hiddenimports = collect_all("streamlit")

datas = [
    (str(base / "main.py"), "."),
    (str(base / "config.py"), "."),
    (str(base / "run_app.py"), "."),
]

# Add all project source directories
for sub in ["models", "engine", "ui", "utils"]:
    sub_path = base / sub
    if sub_path.is_dir():
        for f in sub_path.rglob("*.py"):
            rel = str(f.relative_to(base))
            dest = str(f.parent.relative_to(base))
            datas.append((str(f), dest))

datas.extend(streamlit_datas)

hiddenimports = [
    "streamlit",
    "streamlit.runtime",
    "streamlit.runtime.scriptrunner",
    "streamlit.runtime.scriptrunner.script_run_context",
    "streamlit.web",
    "streamlit.web.server",
    "streamlit.web.bootstrap",
    "streamlit.web.cli",
    "streamlit.commands",
    "streamlit.elements",
    "streamlit.components",
    "streamlit.components.v1",
    "openpyxl",
    "openpyxl.styles",
    "openpyxl.utils",
    "openpyxl.formatting",
    "docx",
    "docx.opc",
    "docx.oxml",
    "xml.etree.ElementTree",
    "xlrd",
    "olefile",
    "pdfplumber",
]
hiddenimports.extend(streamlit_hiddenimports)

excludes = [
    "tkinter",
    "matplotlib",
    "numpy.tests",
    "scipy",
    "PIL",
    "cv2",
    "pandas",
    "pymupdf",
    "torch",
    "torchvision",
    "easyocr",
    "onnxruntime",
    "onnx",
    "tokenizers",
    "ipython",
    "jupyter",
    "notebook",
]

a = Analysis(
    [str(base / "run_app.py")],
    pathex=[str(base)],
    binaries=streamlit_binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="ChecklistAudit",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="ChecklistAudit",
)
