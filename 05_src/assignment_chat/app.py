"""Gradio chat interface for Assignment 2."""
import gradio as gr
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage

from assignment_chat.main import get_graph
from utils.logger import get_logger

_logs = get_logger(__name__)
load_dotenv(".secrets")

MAX_HISTORY_MESSAGES = 30

graph = get_graph()


def _trim_history(messages: list) -> list:
    """Keep only the most recent MAX_HISTORY_MESSAGES messages."""
    if len(messages) <= MAX_HISTORY_MESSAGES:
        return messages
    return messages[-MAX_HISTORY_MESSAGES:]


def chat(message: str, history: list[dict]) -> str:
    langchain_messages = []
    for msg in history:
        if msg["role"] == "user":
            langchain_messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            langchain_messages.append(AIMessage(content=msg["content"]))
    langchain_messages.append(HumanMessage(content=message))
    langchain_messages = _trim_history(langchain_messages)

    response = graph.invoke({"messages": langchain_messages})
    return response["messages"][-1].content


interface = gr.ChatInterface(
    fn=chat,
    type="messages",
    title="Sage Magnus, the Mystic Librarian",
    description=(
        "Ask the Sage for a curious fact, a piece of wisdom about food, "
        "friendship, or community, or a calculation. He will not, however, "
        "speak of felines, canines, the zodiac, or a certain pop laureate."
    ),
)


if __name__ == "__main__":
    _logs.info("Starting Assignment 2 chat app...")
    interface.launch()
