# app/graph/nodes/sql_generator.py

GENERATE_PROMPT = """Write a single DuckDB SQL query to answer the question below.

Only use these tables and columns, nothing else:
{columns}

Question: {question}

{retry_note}

Rules:
- Only SELECT statements, never modify data
- Use only the tables and columns listed above, do not invent columns
- Reply with only the SQL query, no explanation, no markdown formatting, no code fences
"""


def format_columns(columns):
    lines = []
    for c in columns:
        values = ", ".join(str(v) for v in c["sample_values"])
        lines.append(f"- {c['table']}.{c['column']} ({c['dtype']}), example values: {values}")
    return "\n".join(lines)


def clean_sql(raw_sql):
    sql = raw_sql.strip()
    if sql.startswith("```"):
        sql = sql.strip("`")
        sql = sql.replace("sql\n", "", 1)
    return sql.strip().rstrip(";")


def sql_generator_node(state, llm):
    columns_text = format_columns(state["relevant_columns"])

    retry_note = ""
    error = state.get("validation_error") or state.get("execution_error")
    if error:
        retry_note = f"Your previous attempt failed with this error, fix it: {error}"

    prompt = GENERATE_PROMPT.format(
        columns=columns_text,
        question=state["user_question"],
        retry_note=retry_note,
    )

    response = llm([{"role": "user", "content": prompt}])
    sql = clean_sql(response)

    attempt_count = state.get("sql_attempt_count", 0) + 1

    return {
        **state,
        "generated_sql": sql,
        "sql_attempt_count": attempt_count,
        "validation_error": None,
        "execution_error": None,
    }