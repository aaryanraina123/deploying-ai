"""LangGraph chat agent for Assignment 2.

Three services exposed as tools:
1. get_random_trivia  - public API call 
2. search_wisdom - semantic search 
3. calculate - function calling

Chat ineterface is referenced from https://www.gradio.app/guides/creating-a-chatbot-fast
"""

import json
import os

import requests
from chromadb import PersistentClient
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain.tools import tool
from langchain_core.messages import SystemMessage
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt.tool_node import ToolNode, tools_condition

from assignment_chat.prompts import return_instructions
from assignment_chat.wisdom_data import WISDOM_PHRASES
from utils.logger import get_logger

_logs = get_logger(__name__)

load_dotenv(".env")
load_dotenv(".secrets")
_SECRETS_FALLBACK = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "05_src", ".secrets")
)
if os.path.exists(_SECRETS_FALLBACK):
    load_dotenv(_SECRETS_FALLBACK)

API_GATEWAY_URL = "https://k7uffyg03f.execute-api.us-east-1.amazonaws.com/prod/openai/v1"
CHROMA_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")
COLLECTION_NAME = "wisdom_phrases"


def _get_embedding_function() -> OpenAIEmbeddingFunction:
    return OpenAIEmbeddingFunction(
        api_key="any value",
        model_name="text-embedding-3-small",
        api_base=API_GATEWAY_URL,
        default_headers={"x-api-key": os.getenv("API_GATEWAY_KEY")},
    )


def _get_collection():
    """Return the persistent Chroma collection, seeding it on first run."""
    client = PersistentClient(path=CHROMA_DIR)
    embedding_fn = _get_embedding_function()
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn,
    )
    if collection.count() == 0:
        _logs.info("Seeding wisdom collection with %d phrases", len(WISDOM_PHRASES))
        collection.add(
            documents=WISDOM_PHRASES,
            ids=[f"wisdom-{i}" for i in range(len(WISDOM_PHRASES))],
        )
    return collection


# ---------- Service 1: API call ----------
@tool
def get_random_trivia() -> str:
    """Fetch a random piece of trivia from the public Useless Facts API.

    Returns a single random fact. The caller must rewrite or rephrase the
    fact in their own voice; do not pass the raw text to the user.
    """
    url = "https://uselessfacts.jsph.pl/api/v2/facts/random?language=en"
    response = requests.get(url, timeout=10)
    data = response.json()
    return data.get("text", "No trivia available.")


# ---------- Service 2: Semantic search ----------
@tool
def search_wisdom(query: str, top_n: int = 3) -> str:
    """Search a small library of aphorisms about food, friendship, and community."""
    collection = _get_collection()
    results = collection.query(query_texts=[query], n_results=top_n)
    docs = results.get("documents", [[]])[0]
    if not docs:
        return "No matching wisdom found."
    return "\n".join(f"- {doc}" for doc in docs)


@tool
def calculate(expression: str) -> str:
    """Evaluate mathematical expressions"""
    import numexpr

    try:
        result = numexpr.evaluate(expression).item()
    except Exception as exc:
        return f"Could not evaluate expression: {exc}"
    return f"{expression} = {result}"


TOOLS = [get_random_trivia, search_wisdom, calculate]


def _get_chat_model():
    return init_chat_model(
        "openai:gpt-4o-mini",
        temperature=0.7,
        base_url=API_GATEWAY_URL,
        api_key="any value",
        default_headers={"x-api-key": os.getenv("API_GATEWAY_KEY")},
    )


def _call_model(state: MessagesState):
    model = _get_chat_model().bind_tools(TOOLS)
    response = model.invoke(
        [SystemMessage(content=return_instructions())] + state["messages"]
    )
    return {"messages": [response]}


def get_graph():
    builder = StateGraph(MessagesState)
    builder.add_node("call_model", _call_model)
    builder.add_node("tools", ToolNode(TOOLS))
    builder.add_edge(START, "call_model")
    builder.add_conditional_edges("call_model", tools_condition)
    builder.add_edge("tools", "call_model")
    return builder.compile()
