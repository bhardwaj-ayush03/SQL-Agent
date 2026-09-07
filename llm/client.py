import logging
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from openai import OpenAI

from app.config import settings

logger = logging.getLogger(__name__)

groq_llm = ChatGroq(
    api_key=settings.groq_api_key,
    model=settings.groq_model,
    temperature=0.0,
)

openrouter_client = OpenAI(
    api_key=settings.openrouter_api_key,
    base_url="https://openrouter.ai/api/v1",
)

role_to_lc_message = {
    "system": SystemMessage,
    "user": HumanMessage,
    "assistant": AIMessage,
}


def to_langchain_messages(messages: list[dict]):
    """Converts OpenAI-style [{'role': ..., 'content': ...}] dicts into
    LangChain message objects, since ChatGroq expects the latter."""
    lc_messages = []
    for m in messages:
        cls = role_to_lc_message.get(m["role"], HumanMessage)
        lc_messages.append(cls(content=m["content"]))
    return lc_messages


def get_llm_client():
    """
    Returns a callable: chat(messages: list[dict], **kwargs) -> str

    messages follow the familiar OpenAI-style format:
        [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]

    Tries Groq (via LangChain) first; on any exception (rate limit,
    timeout, provider outage) falls back to OpenRouter directly.
    """

    def chat(messages: list[dict], temperature: float = 0.0, **kwargs) -> str:
        try:
            lc_messages = to_langchain_messages(messages)
            response = groq_llm.invoke(lc_messages, temperature=temperature, **kwargs)
            return response.content
        except Exception as e:
            logger.warning(f"Groq (LangChain) call failed ({e}); falling back to OpenRouter")
            resp = openrouter_client.chat.completions.create(
                model=settings.openrouter_model,
                messages=messages,
                temperature=temperature,
                **kwargs,
            )
            return resp.choices[0].message.content

    return chat