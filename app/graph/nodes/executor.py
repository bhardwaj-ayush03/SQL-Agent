from app.db.duckdb_manager import DuckDBManager


def executor_node(state, db: DuckDBManager):
    sql = state["generated_sql"]

    try:
        columns, rows = db.execute_readonly(sql)
        return {
            **state,
            "result_columns": columns,
            "result_rows": rows,
            "execution_error": None,
        }
    except Exception as e:
        return {
            **state,
            "result_columns": [],
            "result_rows": [],
            "execution_error": str(e),
        }