import os
import sys
import json
from pathlib import Path

# Add project root to sys.path if needed
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from agents_memory_db import (
    init_db,
    query_memory as db_query_memory,
    store_memory as db_store_memory,
    assert_constraint as db_assert_constraint,
    DEFAULT_DB_PATH
)
from fastmcp import FastMCP

# Ensure DB directory and tables exist
DB_PATH = str(Path(__file__).resolve().parent / "core_state.db")
init_db(DB_PATH)

mcp = FastMCP("Local-Agent-Memory-Server")

@mcp.tool(
    name="query_memory",
    description="Retrieve relevant memories and active constraints for context."
)
def query_memory(query: str, max_results: int = 5) -> str:
    """Search memories and return active constraints."""
    return db_query_memory(query=query, max_results=max_results, db_path=DB_PATH)

@mcp.tool(
    name="store_memory",
    description="Compute SHA-256 hash, check deduplication, write memory to SQLite engine."
)
def store_memory(category: str, content: str, source_ide: str) -> str:
    """Compute SHA-256 hash, check deduplication, write memory to SQLite engine."""
    res = db_store_memory(category=category, content=content, source_ide=source_ide, db_path=DB_PATH)
    return json.dumps(res, indent=2)

@mcp.tool(
    name="assert_constraint",
    description="Insert new negative/positive architectural guardrails into memory."
)
def assert_constraint(constraint_type: str, description: str, severity: str) -> str:
    """Insert new negative/positive guardrails."""
    res = db_assert_constraint(constraint_type=constraint_type, description=description, severity=severity, db_path=DB_PATH)
    return json.dumps(res, indent=2)

if __name__ == "__main__":
    mcp.run(transport="stdio")
