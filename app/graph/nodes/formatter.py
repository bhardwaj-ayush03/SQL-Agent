ANSWER_PROMPT = """Answer the user's question using only the data below. Be direct and short.

Question: {question}

SQL used: {sql}

Result columns: {columns}
Result rows: {rows}

Give a plain, direct answer using the actual numbers from the result. Don't add any information
that isn't in the result.
"""


def format_result_rows(columns, rows, max_rows=20):
    if not rows:
        return "no rows returned"
    lines = [", ".join(columns)]
    for row in rows[:max_rows]:
        lines.append(", ".join(str(v) for v in row))
    return "\n".join(lines)


def build_chart_spec(columns, rows):
    if not rows or len(rows) < 2:
        return None

    numeric_idx = None
    label_idx = None
    for i, value in enumerate(rows[0]):
        if isinstance(value, (int, float)) and numeric_idx is None:
            numeric_idx = i
        elif not isinstance(value, (int, float)) and label_idx is None:
            label_idx = i

    if numeric_idx is None or label_idx is None:
        return None

    labels = [str(row[label_idx]) for row in rows]
    values = [row[numeric_idx] for row in rows]

    return {
        "type": "bar",
        "x": labels,
        "y": values,
        "x_label": columns[label_idx],
        "y_label": columns[numeric_idx],
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
    chart_spec = build_chart_spec(columns, rows)

    return {**state, "final_answer": answer.strip(), "chart_spec": chart_spec}