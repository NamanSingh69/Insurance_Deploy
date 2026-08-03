import sqlite3
from datetime import datetime
from pathlib import Path

def sync_markdown_dashboard(db_path, md_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    constraints = cur.execute(
        "SELECT constraint_type, description, severity FROM constraints WHERE active_status = 1 ORDER BY id DESC"
    ).fetchall()
    
    memories = cur.execute(
        "SELECT category, content, source_ide, decay_factor FROM memories ORDER BY id DESC"
    ).fetchall()
    
    conn.close()
    
    lines = [
        "# AGENT MEMORY DASHBOARD",
        f"*Last Synchronized: {datetime.utcnow().isoformat()}*",
        "",
        "## ACTIVE ARCHITECTURAL CONSTRAINTS"
    ]
    
    for c_type, desc, severity in constraints:
        lines.append(f"- **[{severity}]** ({c_type}): {desc}")
        
    lines.append("")
    lines.append("## RECENT MEMORY TRACES")
    
    for cat, content, ide, decay in memories:
        decay_val = decay if decay is not None else 1.0
        lines.append(f"- `[{cat}]` (IDE: {ide or 'antigravity'} | Weight: {decay_val:.2f}): {content}")
        
    lines.append("")
    
    md_file = Path(md_path)
    md_file.parent.mkdir(parents=True, exist_ok=True)
    md_file.write_text("\n".join(lines), encoding="utf-8")
