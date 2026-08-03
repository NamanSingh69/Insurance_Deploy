import os
import sys
import time
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from agents_memory_sync import sync_markdown_dashboard

DB_PATH = str(Path(__file__).resolve().parent / "core_state.db")
MD_PATH = str(Path(__file__).resolve().parent / "MEMORY_LOGS.md")

def run_sync():
    sync_markdown_dashboard(db_path=DB_PATH, md_path=MD_PATH)
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Synchronized memory logs to {MD_PATH}")

if __name__ == "__main__":
    run_sync()
