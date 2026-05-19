"""Desktop launcher for Checklist Audit System.

Packaged by PyInstaller — double-click to start the server and open browser.
"""
import os
import sys
import tempfile
import time
import webbrowser


PORT = 8501
LOCK_FILE = os.path.join(tempfile.gettempdir(), "checklist_audit_streamlit.lock")


def lock_owner_alive() -> bool:
    """Check if the process that owns the lock is still running."""
    try:
        with open(LOCK_FILE) as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)  # signal 0 just checks existence
        return True
    except (FileNotFoundError, ValueError, OSError):
        return False


def main():
    # Resolve app.py path (inside _internal/ when frozen)
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))

    app_path = os.path.join(base, "main.py")
    if not os.path.exists(app_path):
        # Fallback: search in _internal
        candidates = [
            os.path.join(base, "_internal", "main.py"),
            os.path.join(os.path.dirname(__file__), "main.py"),
        ]
        for c in candidates:
            if os.path.exists(c):
                app_path = c
                break

    # Prevent duplicate launch
    if lock_owner_alive():
        webbrowser.open(f"http://127.0.0.1:{PORT}")
        return

    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))

    # Configure Streamlit args before importing
    sys.argv = [
        "streamlit", "run", app_path,
        "--server.port", str(PORT),
        "--server.address", "127.0.0.1",
        "--server.headless", "true",
        "--global.developmentMode", "false",
        "--browser.gatherUsageStats", "false",
        "--server.enableXsrfProtection", "false",
        "--server.fileWatcherType", "none",
    ]

    # Open browser after a short delay
    import threading
    threading.Timer(1.5, lambda: webbrowser.open(f"http://127.0.0.1:{PORT}")).start()

    from streamlit.web.cli import main as stcli_main
    stcli_main()


if __name__ == "__main__":
    main()
