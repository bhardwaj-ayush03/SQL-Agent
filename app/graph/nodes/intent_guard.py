import re

WRITE_KEYWORDS = [
    "delete", "remove", "drop", "update", "insert",
    "modify", "edit", "alter", "truncate", "overwrite",
]


def contains_write_intent(question):
    q = question.lower()
    return any(re.search(rf"\b{word}\b", q) for word in WRITE_KEYWORDS)


def intent_guard_node(state):
    if contains_write_intent(state["user_question"]):
        message = "I can only answer questions about your data — I'm not able to delete, update, or otherwise modify it."
        return {**state, "is_write_request": True, "final_answer": message, "chart_spec": None}

    return {**state, "is_write_request": False}