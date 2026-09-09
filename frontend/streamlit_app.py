import os
import sys
import tempfile
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import plotly.graph_objects as go
from langgraph.types import Command

from app.db.duckdb_manager import DuckDBManager
from app.embeddings.column_store import ColumnStore
from app.llm.client import get_llm_client
from app.graph.build_graph import build_graph

st.set_page_config(page_title="SQL Agent", layout="centered")
st.title("Ask your data")


def init_session():
    if "graph" in st.session_state:
        return

    db = DuckDBManager()
    store = ColumnStore()
    llm = get_llm_client()

    st.session_state.db = db
    st.session_state.store = store
    st.session_state.graph = build_graph(db, llm, store)
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.temp_dir = tempfile.mkdtemp()
    st.session_state.csv_paths = []
    st.session_state.pending_clarification = None
    st.session_state.history = []


init_session()

uploaded_files = st.file_uploader("Upload one or more CSV files", type="csv", accept_multiple_files=True)

if uploaded_files:
    csv_paths = []
    for f in uploaded_files:
        path = os.path.join(st.session_state.temp_dir, f.name)
        with open(path, "wb") as out:
            out.write(f.getbuffer())
        csv_paths.append(path)
    st.session_state.csv_paths = csv_paths
    st.success(f"Loaded {len(csv_paths)} file(s)")


def display_assistant_turn(result):
    with st.chat_message("assistant"):
        with st.expander("SQL used"):
            st.code(result.get("generated_sql", ""), language="sql")

        st.write(result.get("final_answer", ""))

        columns = result.get("result_columns")
        rows = result.get("result_rows")
        if columns and rows:
            st.dataframe([dict(zip(columns, row)) for row in rows], use_container_width=True)

        chart_spec = result.get("chart_spec")
        if chart_spec:
            fig = go.Figure(data=go.Bar(x=chart_spec["x"], y=chart_spec["y"]))
            fig.update_layout(xaxis_title=chart_spec["x_label"], yaxis_title=chart_spec["y_label"])
            st.plotly_chart(fig, use_container_width=True)


for entry in st.session_state.history:
    if entry["role"] == "user":
        st.chat_message("user").write(entry["content"])
    else:
        display_assistant_turn(entry["result"])

config = {"configurable": {"thread_id": st.session_state.thread_id}}


def render_result(result):
    display_assistant_turn(result)
    st.session_state.history.append({"role": "assistant", "result": result})


if st.session_state.pending_clarification:
    st.info(st.session_state.pending_clarification)
    clarification = st.chat_input("Your clarification")
    if clarification:
        st.session_state.history.append({"role": "user", "content": clarification})
        st.chat_message("user").write(clarification)

        result = st.session_state.graph.invoke(Command(resume=clarification), config=config)
        st.session_state.pending_clarification = None

        if "__interrupt__" in result:
            st.session_state.pending_clarification = result["__interrupt__"][0].value
            st.rerun()
        else:
            render_result(result)

else:
    question = st.chat_input("Ask a question about your data")
    if question:
        if not st.session_state.csv_paths:
            st.warning("Upload a CSV first.")
        else:
            st.session_state.history.append({"role": "user", "content": question})
            st.chat_message("user").write(question)

            initial_state = {
                "user_question": question,
                "csv_paths": st.session_state.csv_paths,
                "sql_attempt_count": 0,
            }
            result = st.session_state.graph.invoke(initial_state, config=config)

            if "__interrupt__" in result:
                st.session_state.pending_clarification = result["__interrupt__"][0].value
                st.rerun()
            else:
                render_result(result)