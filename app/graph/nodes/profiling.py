from app.db.duckdb_manager import DuckDBManager
from app.graph.state import AgentState, ColumnCard


def profiling_node(state: AgentState, db: DuckDBManager) -> AgentState:
    column_cards: list[ColumnCard] = []

    for table in state["tables"]:
        schema = db.get_schema(table)  
        for col_name, col_type in schema:
            column_cards.append(
                ColumnCard(
                    table=table,
                    column=col_name,
                    dtype=col_type,
                    sample_values=db.sample_values(table, col_name),
                    null_fraction=db.null_fraction(table, col_name),
                    cardinality=db.cardinality(table, col_name),
                )
            )

    return {**state, "column_cards": column_cards}