from typing import TypedDict, Optional, Any


class ColumnCard(TypedDict):
    table: str
    column: str
    dtype: str
    sample_values: list
    null_fraction: float
    cardinality: int


class AgentState(TypedDict, total=False):
    
    user_question: str
    csv_paths: list[str]          
    # ingestion
    tables: list[str] #table names registered in DuckDB

    # profiling 
    column_cards: list[ColumnCard]

    # retrieval
    relevant_columns: list[ColumnCard]

    #  ambiguity check
    is_ambiguous: bool
    clarification_question: Optional[str]
    user_clarification: Optional[str]

    #   sql generation  
    generated_sql: str
    sql_attempt_count: int

    #   validation  
    is_valid_sql: bool
    validation_error: Optional[str]

    #   execution  
    execution_error: Optional[str]
    result_columns: list[str]
    result_rows: list[tuple]

    #   formatting  
    final_answer: str
    chart_spec: Optional[dict[str, Any]]