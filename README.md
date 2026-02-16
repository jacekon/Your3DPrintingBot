# Your3DPrintingBot

A Telegram bot that acts as a conversational interface to your **Elegoo Centauri Carbon** 3D printer. It responds in a human-like way (LLM-powered), understands links to Printables, Thingiverse, and similar sites, and can control or query the printer.

- **Telegram bot:** [@Your3DPrintingBot](https://t.me/Your3DPrintingBot)
- **GitHub:** [jacekon/Your3DPrintingBot](https://github.com/jacekon/Your3DPrintingBot)

## Features (planned)

- Natural-language chat with an LLM backend
- Parse and handle links to Printables, Thingiverse, and other model sites
- Query and control the Elegoo Centauri Carbon via SDCP (WebSocket)
- Optional: start prints, check status, pause/resume from Telegram

## Quick start

1. **Clone and enter the repo**
   ```bash
   git clone https://github.com/jacekon/Your3DPrintingBot.git
   cd Your3DPrintingBot
   ```

2. **Create a virtual environment and install dependencies**
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure**
   - Copy `.env.example` to `.env`
   - Set `TELEGRAM_BOT_TOKEN` (from [@BotFather](https://t.me/BotFather))
   - Set other optional vars (LLM API key, printer IP, etc.)

4. **Run the bot**
   ```bash
   python -m src.bot
   ```

## Project layout

- `src/` — Bot and printer logic
- `docs/` — Architecture, scope, and design notes
- `tests/` — Tests (when added)

See [PROJECT_SCOPE.md](PROJECT_SCOPE.md) for scope and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for architecture.

## License

MIT
