from app.embeddings.column_store import ColumnStore


def retrieval_node(state, store: ColumnStore, top_k=5):
    store.build(state["column_cards"])
    relevant = store.search(state["user_question"], top_k=top_k)
    return {**state, "relevant_columns": relevant}
