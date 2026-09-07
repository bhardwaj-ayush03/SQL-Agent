import duckdb
from dataclasses import dataclass, field

from app.config import settings


@dataclass
class TableRegistry:
    """Tracks table_name -> source_path and lets us list known tables."""
    tables: dict[str, str] = field(default_factory=dict)

    def register(self, table_name: str, source_path: str):
        self.tables[table_name] = source_path

    def names(self) -> list[str]:
        return list(self.tables.keys())


class DuckDBManager:
    def __init__(self, path: str | None = None):
        self.conn = duckdb.connect(path or settings.duckdb_path)
        self.registry = TableRegistry()

    def load_csv(self, csv_path: str, table_name: str) -> None:
        """
        Loads a CSV into DuckDB with automatic type inference.
        read_csv_auto handles delimiter/header/dtype detection so we don't
        write our own CSV-parsing/dtype-inference logic.
        """
        self.conn.execute(
            f"""
            CREATE OR REPLACE TABLE "{table_name}" AS
            SELECT * FROM read_csv_auto(?, header=True)
            """,
            [csv_path],
        )
        self.registry.register(table_name, csv_path)

    def get_schema(self, table_name: str) -> list[tuple]:
        """Returns [(column_name, column_type), ...] for a table."""
        result = self.conn.execute(f'DESCRIBE "{table_name}"').fetchall()
        # DESCRIBE returns: column_name, column_type, null, key, default, extra
        return [(row[0], row[1]) for row in result]

    def sample_values(self, table_name: str, column_name: str, n: int = 5) -> list:
        rows = self.conn.execute(
            f'SELECT DISTINCT "{column_name}" FROM "{table_name}" '
            f'WHERE "{column_name}" IS NOT NULL LIMIT {n}'
        ).fetchall()
        return [r[0] for r in rows]

    def row_count(self, table_name: str) -> int:
        return self.conn.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()[0]

    def null_fraction(self, table_name: str, column_name: str) -> float:
        total = self.row_count(table_name)
        if total == 0:
            return 0.0
        nulls = self.conn.execute(
            f'SELECT COUNT(*) FROM "{table_name}" WHERE "{column_name}" IS NULL'
        ).fetchone()[0]
        return nulls / total

    def cardinality(self, table_name: str, column_name: str) -> int:
        return self.conn.execute(
            f'SELECT COUNT(DISTINCT "{column_name}") FROM "{table_name}"'
        ).fetchone()[0]

    def execute_readonly(self, sql: str) -> tuple[list[str], list[tuple]]:
        """
        Executes a SELECT query and returns (column_names, rows).
        Caller (validator node) is responsible for ensuring this is
        actually a read-only statement before it reaches here.
        """
        cursor = self.conn.execute(sql)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        return columns, rows