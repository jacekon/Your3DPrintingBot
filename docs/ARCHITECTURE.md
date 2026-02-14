# Architecture: Your3DPrintingBot

## Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  Telegram API   │────▶│  Your3DPrinting   │────▶│  Elegoo Centauri    │
│  (user msgs)    │◀────│  Bot (this app)   │◀────│  Carbon (SDCP/WS)   │
└─────────────────┘     └────────┬─────────┘     └─────────────────────┘
                                 │
                                 │  LLM + tools
                                 ▼
                        ┌──────────────────┐
                        │  LLM provider    │
                        │  (OpenAI/Ollama) │
                        └──────────────────┘
                                 │
                                 │  link metadata
                                 ▼
                        ┌──────────────────┐
                        │  Printables /    │
                        │  Thingiverse etc │
                        └──────────────────┘
```

## Components

### 1. Telegram layer

- Long polling or webhook to receive updates.
- Parse messages: text, entities (e.g. URLs).
- Send replies (text, optional inline keyboards).
- Single entrypoint: “incoming update” → hand off to core handler.

### 2. Message pipeline

- **Input:** Raw message text + list of URLs.
- **Link extraction:** From message text or Telegram entities.
- **Link handler:** Fetch metadata (title, author) for known domains (Printables, Thingiverse, …). Cache optional.
- **Context builder:** User message + link summaries → context for LLM.
- **LLM call:** With system prompt + context; support tool calls (e.g. `get_printer_status`, `pause_print`).
- **Tool execution:** Map tool names to printer (SDCP) or internal actions.
- **Output:** Send LLM reply (and optional follow-up) back to Telegram.

### 3. Printer client (SDCP)

- **Discovery:** Optional UDP broadcast to get printer IP (or use configured IP).
- **Connection:** WebSocket to `ws://{ip}:3030/websocket`, JSON.
- **Heartbeat:** Send periodic ping so connection is not closed (~60 s timeout).
- **Commands:** Status request, pause, resume, etc., according to SDCP/OpenCentauri docs.
- **Thread safety:** One connection (or connection pool) shared by tool calls; queue or lock if needed.

### 4. LLM integration

- **Abstraction:** One interface (e.g. “chat with tools”) so backend can be swapped.
- **System prompt:** Role (3D printing assistant), printer model (Centauri Carbon), and list of tools.
- **Tools:** e.g. `get_printer_status`, `pause_print`, `resume_print`; return structured result to LLM.
- **Streaming:** Optional; if supported, stream reply to Telegram for better UX.

### 5. Link handler

- **Detect:** Match URLs to known domains (printables.com, thingiverse.com, thangs.com, etc.).
- **Fetch:** HTTP GET (respect robots.txt and rate limits); use APIs if available (e.g. Printables).
- **Parse:** Title, author, optional image/description; return a small struct for the LLM context.
- **Errors:** Timeout or parse failure → “Couldn’t fetch link” in context, no crash.

## Data flow (per message)

1. Telegram → Update with `message.text` and `message.entities` (urls).
2. Extract URLs; for each known domain, fetch metadata (async).
3. Build context: `user_message` + `link_summaries[]`.
4. Call LLM with tools; if LLM requests a tool, run it (e.g. SDCP status), inject result, continue.
5. Final answer → send to user via Telegram.

## Configuration

- **Env vars:** `TELEGRAM_BOT_TOKEN`, `PRINTER_IP` (or rely on discovery), `LLM_*` (API key, model, base URL), optional `ALLOWED_TELEGRAM_IDS`.
- **Secrets:** No tokens in repo; use `.env` (and `.gitignore`).

## Project layout (target)

```
Your3DPrintingBot/
├── README.md
├── PROJECT_SCOPE.md
├── requirements.txt
├── .env.example
├── .gitignore
├── docs/
│   ├── ARCHITECTURE.md   (this file)
│   └── PRINTER_SDCP.md   (optional)
├── src/
│   ├── __init__.py
│   ├── bot.py            # Telegram entrypoint
│   ├── pipeline.py       # message → link handling → LLM → reply
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── base.py       # interface
│   │   └── openai.py     # or ollama.py
│   ├── printer/
│   │   ├── __init__.py
│   │   └── sdcp.py       # WebSocket + SDCP
│   └── links/
│       ├── __init__.py
│       └── fetcher.py    # metadata from Printables, etc.
└── tests/
    └── ...
```

## Security notes

- Validate and restrict which Telegram user(s) can trigger printer actions (e.g. `ALLOWED_TELEGRAM_IDS`).
- Don’t expose bot token or LLM keys; keep printer on a trusted network.
- Rate-limit or cap LLM/link requests per user to avoid abuse.
