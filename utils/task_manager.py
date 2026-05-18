import json
import os
import time
import streamlit as st
from config import TASK_DIR, AUTOSAVE_DIR


def save_task(task_name: str, state: dict) -> str:
    """Save current task state to JSON file."""
    os.makedirs(TASK_DIR, exist_ok=True)
    filename = f"{task_name}_{int(time.time())}.json"
    filepath = os.path.join(TASK_DIR, filename)
    state["_saved_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    state["_task_name"] = task_name
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2, default=str)
    return filepath


def load_task(filepath: str) -> dict:
    """Load task state from JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def list_tasks() -> list:
    """List all saved tasks."""
    os.makedirs(TASK_DIR, exist_ok=True)
    tasks = []
    for f in sorted(os.listdir(TASK_DIR), reverse=True):
        if f.endswith(".json"):
            path = os.path.join(TASK_DIR, f)
            try:
                state = load_task(path)
                tasks.append({
                    "name": state.get("_task_name", f.replace(".json", "")),
                    "saved_at": state.get("_saved_at", "unknown"),
                    "file_count": len(state.get("files", [])),
                    "path": path,
                })
            except Exception:
                pass
    return tasks


def autosave(state: dict):
    """Auto-save state to prevent data loss."""
    os.makedirs(AUTOSAVE_DIR, exist_ok=True)
    filepath = os.path.join(AUTOSAVE_DIR, "autosave.json")
    state["_autosaved_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2, default=str)


def load_autosave() -> dict | None:
    """Load auto-saved state if it exists."""
    filepath = os.path.join(AUTOSAVE_DIR, "autosave.json")
    if os.path.exists(filepath):
        try:
            return load_task(filepath)
        except Exception:
            pass
    return None


def delete_autosave():
    """Clear auto-save file."""
    filepath = os.path.join(AUTOSAVE_DIR, "autosave.json")
    if os.path.exists(filepath):
        os.remove(filepath)


def delete_task(filepath: str):
    """Delete a saved task."""
    if os.path.exists(filepath):
        os.remove(filepath)
