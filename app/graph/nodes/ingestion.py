import re
from pathlib import Path

from app.db.duckdb_manager import DuckDBManager
from app.graph.state import AgentState


def sanitize_table_name(csv_path: str, existing: set[str]) -> str:
    stem = Path(csv_path).stem
    name = re.sub(r"[^a-zA-Z0-9_]", "_", stem).lower()
    if not name or name[0].isdigit():
        name = f"t_{name}"
    base = name
    i = 1
    while name in existing:
        name = f"{base}_{i}"
        i += 1
    return name


def ingestion_node(state: AgentState, db: DuckDBManager) -> AgentState:
    tables = []
    existing_names: set[str] = set(db.registry.names())

    path_to_table = {path: name for name, path in db.registry.tables.items()}

    for csv_path in state["csv_paths"]:
        if csv_path in path_to_table:
            tables.append(path_to_table[csv_path])
            continue

        table_name = sanitize_table_name(csv_path, existing_names)
        db.load_csv(csv_path, table_name)
        existing_names.add(table_name)
        tables.append(table_name)

    return {**state, "tables": tables}