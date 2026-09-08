from functools import partial
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from app.config import settings
from app.graph.state import AgentState
from app.graph.nodes.ingestion import ingestion_node
from app.graph.nodes.profiling import profiling_node
from app.graph.nodes.retrieval import retrieval_node
from app.graph.nodes.ambiguity_check import ambiguity_check_node
from app.graph.nodes.sql_generator import sql_generator_node
from app.graph.nodes.validator import validator_node
from app.graph.nodes.executor import executor_node
from app.graph.nodes.formatter import formatter_node


def give_up_node(state):
    message = "I couldn't generate a working query for this after a few attempts. Could you try rephrasing the question?"
    return {**state, "final_answer": message, "chart_spec": None}


def route_after_validator(state):
    if state["is_valid_sql"]:
        return "executor"
    if state["sql_attempt_count"] >= settings.max_sql_retries:
        return "give_up"
    return "sql_generator"


def route_after_executor(state):
    if not state["execution_error"]:
        return "formatter"
    if state["sql_attempt_count"] >= settings.max_sql_retries:
        return "give_up"
    return "sql_generator"


def build_graph(db, llm, store):
    graph = StateGraph(AgentState)

    graph.add_node("ingestion", partial(ingestion_node, db=db))
    graph.add_node("profiling", partial(profiling_node, db=db))
    graph.add_node("retrieval", partial(retrieval_node, store=store))
    graph.add_node("ambiguity_check", partial(ambiguity_check_node, llm=llm))
    graph.add_node("sql_generator", partial(sql_generator_node, llm=llm))

    def run_validator(state):
        known_columns = [(c["table"], c["column"]) for c in state["column_cards"]]
        return validator_node(state, known_columns)

    graph.add_node("validator", run_validator)
    graph.add_node("executor", partial(executor_node, db=db))
    graph.add_node("formatter", partial(formatter_node, llm=llm))
    graph.add_node("give_up", give_up_node)

    graph.add_edge(START, "ingestion")
    graph.add_edge("ingestion", "profiling")
    graph.add_edge("profiling", "retrieval")
    graph.add_edge("retrieval", "ambiguity_check")
    graph.add_edge("ambiguity_check", "sql_generator")
    graph.add_edge("sql_generator", "validator")

    graph.add_conditional_edges("validator", route_after_validator, {
        "executor": "executor",
        "sql_generator": "sql_generator",
        "give_up": "give_up",
    })

    graph.add_conditional_edges("executor", route_after_executor, {
        "formatter": "formatter",
        "sql_generator": "sql_generator",
        "give_up": "give_up",
    })

    graph.add_edge("formatter", END)
    graph.add_edge("give_up", END)

    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)