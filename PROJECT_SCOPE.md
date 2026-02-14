# Project scope: Your3DPrintingBot

## Goal

A single Telegram bot that:

1. Talks to the user in a **human-like way** (LLM behind the scenes).
2. Understands **links** to Printables, Thingiverse, and similar model sites.
3. Can **query and control** the Elegoo Centauri Carbon 3D printer.

## Out of scope (for now)

- Multiple printers or multi-user access control
- Web dashboard (Telegram only)
- Slicing (e.g. Cura) — focus on printer control and link handling; slicing can be added later

---

## 1. Telegram interface

- **Bot:** [@Your3DPrintingBot](https://t.me/Your3DPrintingBot) (token from BotFather, stored in env).
- Handle:
  - Text messages (conversation + commands).
  - Links in messages (detect and pass to link handler).
- Optional: inline buttons for status, pause, resume, etc.
- Optional: simple auth (e.g. single allowed Telegram user ID) so only you can control the printer.

---

## 2. LLM (human-like responses)

- All user text (except maybe explicit “/status” style commands) goes through an LLM so replies feel natural.
- **Possible backends:** OpenAI API, local (Ollama, llama.cpp), or other provider (e.g. Anthropic, open-source APIs).
- System prompt should include:
  - Role: helpful assistant for 3D printing and this specific printer (Elegoo Centauri Carbon).
  - Capabilities: answer questions, explain prints, and that the bot can check printer status / control it.
- Bot should be able to call “tools” (e.g. get printer status, start/pause) and weave results into the answer.

---

## 3. Link handling (Printables, Thingiverse, etc.)

- **Detect** links in incoming messages (e.g. `printables.com`, `thingiverse.com`, `thangs.com`, etc.).
- **Parse** page to get:
  - Model name
  - Author
  - Optional: image URL, description, file list (if easily available).
- **Use in conversation:** e.g. “I see you shared a Printables model: **X** by **Y**. Do you want to print it or just save it for later?”
- Optional: download model files (STL/3MF) and later send to printer or slicer (future phase).

---

## 4. Printer: Elegoo Centauri Carbon

- **Protocol:** SDCP (Smart Device Control Protocol) over **WebSocket**.
- **Discovery:** UDP broadcast (e.g. port 3000, message `"M99999"`) to find printer IP.
- **Connection:** `ws://{PrinterIP}:3030/websocket`, JSON messages, no auth by default.
- **Details:** [OpenCentauri API docs](https://docs.opencentauri.cc/software/api/), [SDCP Centauri Carbon](https://github.com/WalkerFrederick/sdcp-centauri-carbon).
- **Implement:**
  - Connect/disconnect and basic heartbeat (connection closes after ~60 s inactivity).
  - Get status (temperature, progress, state, etc.).
  - Send commands (e.g. pause, resume, stop) as needed.
- **Note:** Some SDCP field names have typos (e.g. `CurrenCoord`, `RelaseFilmState`); use exact names from the docs/spec.

---

## 5. High-level flow

1. User sends a message (with or without links).
2. Extract links → link handler returns model info (name, author, etc.).
3. User message + link context (if any) → LLM with tools (e.g. “get printer status”, “pause”).
4. LLM may request tool calls; bot runs them (e.g. SDCP status) and continues the conversation.
5. Bot sends the final (or streaming) reply back to the user on Telegram.

---

## 6. Docs to create / refine

- **README.md** — Setup, run, link to repo and bot.
- **PROJECT_SCOPE.md** (this file) — Scope, features, printer/LLM/link handling.
- **docs/ARCHITECTURE.md** — Components, data flow, tech choices.
- **docs/PRINTER_SDCP.md** (optional) — SDCP commands and fields used for this bot.
- **CONTRIBUTING.md** (optional) — If you open-source and want contributions.

---

## 7. Tech stack (suggested)

- **Language:** Python 3.11+
- **Telegram:** `python-telegram-bot` (v20+).
- **LLM:** TBD (e.g. `openai`, `ollama`, or a small abstraction so you can swap).
- **Printer:** Async WebSocket client (e.g. `websockets`) + JSON for SDCP.
- **Link parsing:** HTTP client (e.g. `httpx`) + HTML parsing (e.g. `beautifulsoup4`) or official APIs if available (Printables has an API).
- **Config:** Environment variables (`.env`), optional `pydantic-settings`.

---

## 8. Repository

- **GitHub:** [github.com/jacekon/Your3DPrintingBot](https://github.com/jacekon/Your3DPrintingBot)
- **Branch strategy:** `main` as default; feature branches as needed.
- Add `.gitignore` (Python, `.env`, IDE, OS files) and a minimal `requirements.txt` from the start.
