import json

ANSWER_PROMPT = """Answer the user's question using only the data below. Be direct and short.

Question: {question}

SQL used: {sql}

Result columns: {columns}
Result rows: {rows}

Give a plain, direct answer using the actual numbers from the result. Don't add any information
that isn't in the result. If there is more than one row, list each one on its own line, don't
run them together in one sentence.
"""

CHART_PROMPT = """Decide how to visualize this query result, if at all.

User question: {question}

Result columns: {columns}
Sample rows:
{rows}

Reply with only JSON, nothing else, in this exact format:
{{"chart_type": "bar", "x_column": "exact column name", "y_column": "exact column name"}}

chart_type must be one of: "bar", "scatter", "line", "none"
- "bar": comparing a category against a numeric value
- "scatter": showing the relationship between two numeric variables
- "line": only if there's a clear time/sequence column (date, year, month) for the x-axis
- "none": a chart wouldn't meaningfully help answer this question

x_column and y_column must be exact column names from the list above, or empty strings if chart_type is "none".
"""


def format_result_rows(columns, rows, max_rows=20):
    if not rows:
        return "no rows returned"
    lines = [", ".join(columns)]
    for row in rows[:max_rows]:
        lines.append(", ".join(str(v) for v in row))
    return "\n".join(lines)


def decide_chart(question, columns, rows, llm):
    if not rows or len(rows) < 2:
        return None

    prompt = CHART_PROMPT.format(
        question=question,
        columns=", ".join(columns),
        rows=format_result_rows(columns, rows, max_rows=10),
    )

    response = llm([{"role": "user", "content": prompt}])

    try:
        decision = json.loads(response)
    except json.JSONDecodeError:
        return None

    chart_type = decision.get("chart_type")
    if chart_type not in ("bar", "scatter", "line"):
        return None

    x_col = decision.get("x_column")
    y_col = decision.get("y_column")
    if x_col not in columns or y_col not in columns:
        return None

    x_idx = columns.index(x_col)
    y_idx = columns.index(y_col)

    return {
        "type": chart_type,
        "x": [row[x_idx] for row in rows],
        "y": [row[y_idx] for row in rows],
        "x_label": x_col,
        "y_label": y_col,
    }


def formatter_node(state, llm):
    columns = state["result_columns"]
    rows = state["result_rows"]

    prompt = ANSWER_PROMPT.format(
        question=state["user_question"],
        sql=state["generated_sql"],
        columns=", ".join(columns),
        rows=format_result_rows(columns, rows),
    )

    answer = llm([{"role": "user", "content": prompt}])
    chart_spec = decide_chart(state["user_question"], columns, rows, llm)

    return {**state, "final_answer": answer.strip(), "chart_spec": chart_spec}