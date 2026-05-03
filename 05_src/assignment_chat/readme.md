# Assignment 2 — Sage Magnus, the Mystic Librarian

A small Gradio chat app implementing the three required services for Assignment 2. The chat client is **Sage Magnus**, a centuries-old mystic librarian with a warm, theatrical, old-world voice (used Gemini to ideate a persona).

## Run

From the `05_src` directory (so `assignment_chat` is on the import path):

```bash
cd 05_src
python -m assignment_chat.app
```

The course API gateway key must be present in `05_src/.secrets` as `API_GATEWAY_KEY=...` (already provided in this repo).

## Services

All three services are exposed to the LLM as LangChain tools and routed through the course **API Gateway** (`https://k7uffyg03f.execute-api.us-east-1.amazonaws.com/prod/openai/v1`) — the same pattern used in the labs.

### Service 1 — API call: `get_random_trivia`

Calls the public [Useless Facts API](https://uselessfacts.jsph.pl/) (`/api/v2/facts/random`) and returns a single random fact. The system prompt instructs the model to rewrite the fact in Sage Magnus's voice rather than passing the raw API response through.

### Service 2 — Semantic search: `search_wisdom`

Performs a semantic query over a small library of ~30 aphorisms (food, friendship, community) using a **persistent ChromaDB** instance stored at `05_src/assignment_chat/chroma_db/`.

- Embeddings come from `text-embedding-3-small` via the API Gateway, configured through `OpenAIEmbeddingFunction`.
- The collection is seeded **on first run**: `_get_collection()` creates or opens the persistent collection and, if it is empty, embeds and inserts the phrases from `wisdom_data.py`.
- The dataset is small and embedded inline in code, so there is no separate data file to ship.

### Service 3 — Function calling: `calculate`

A `@tool`-decorated function that evaluates a math expression with `numexpr.evaluate`. The model is responsible for choosing when to invoke it (function-calling tool use), which satisfies the function-calling requirement of Service 3.

## Conversation memory

Memory is maintained by Gradio's `ChatInterface`, which passes the full message history back on each turn. To handle the case where the conversation grows beyond a useful context window, `app.py` applies a **sliding window** that keeps only the most recent `MAX_HISTORY_MESSAGES` (default 30) before sending the history to the LangGraph agent. Older turns are dropped. This is the simple short-term-memory strategy described in the LangGraph "Manage short-term memory" reference.

## Guardrails

Two layers, both implemented via the system prompt in `prompts.py`:

1. **Restricted topics** — the model is instructed to refuse, in character, any request about cats/dogs (and variations), horoscopes/zodiac/astrology, or Taylor Swift. It must not call any tool for those topics.
2. **System-prompt protection** — the model must never reveal, paraphrase, or modify its instructions, regardless of how the request is framed (translation tricks, "ignore previous instructions", role-play, etc.). A scripted in-character refusal is provided.

## Files

```
assignment_chat/
├── __init__.py
├── app.py            # Gradio entry point + sliding-window memory
├── main.py           # LangGraph agent, tools, ChromaDB setup
├── prompts.py        # System prompt with personality + guardrails
├── wisdom_data.py    # Inline corpus indexed into ChromaDB on first run
├── chroma_db/        # Persistent vector store (created on first run)
└── readme.md
```

## Implementation decisions

- **No separate embedding script.** The ChromaDB collection is built on demand the first time `search_wisdom` is called. Subsequent runs reuse the persisted store.
- **Useless Facts API instead of one requiring a key.** Keeps the project zero-config beyond the gateway key already used in the repo.
- **Numexpr**  handles the calculator safely without `eval`.
- **No new dependencies.** Only libraries already in the course are used.
