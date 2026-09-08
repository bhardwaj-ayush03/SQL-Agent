import json
from langgraph.types import interrupt

CHECK_PROMPT = """You are checking if a question can be answered clearly using the given columns.

Columns available:
{columns}

User question: {question}

Reply with only JSON, nothing else, in this exact format:
{{"ambiguous": true or false, "clarifying_question": "question to ask user, or empty string if not ambiguous"}}

Mark it ambiguous only if the question could reasonably mean more than one thing given these columns
(for example: which metric, which time period, which grouping). Do not mark it ambiguous just because
it's a normal question with an obvious column match.
"""


def format_columns(columns):
    lines = []
    for c in columns:
        lines.append(f"- {c['table']}.{c['column']} ({c['dtype']})")
    return "\n".join(lines)


def ambiguity_check_node(state, llm):
    columns_text = format_columns(state["relevant_columns"])
    prompt = CHECK_PROMPT.format(columns=columns_text, question=state["user_question"])

    response = llm([{"role": "user", "content": prompt}])

    try:
        result = json.loads(response)
    except json.JSONDecodeError:
        result = {"ambiguous": False, "clarifying_question": ""}

    if not result.get("ambiguous"):
        return {**state, "is_ambiguous": False, "clarification_question": None}

    clarifying_question = result.get("clarifying_question", "Could you clarify your question?")
    user_answer = interrupt(clarifying_question)
    updated_question = f"{state['user_question']} (clarification: {user_answer})"

    return {
        **state,
        "is_ambiguous": True,
        "clarification_question": clarifying_question,
        "user_clarification": user_answer,
        "user_question": updated_question,
    }