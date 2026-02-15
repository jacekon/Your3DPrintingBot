#!/usr/bin/env python3
"""
Test that the intent parser actually calls the LLM.
Run from project root: python scripts/test_llm_intent.py   or   python -m scripts.test_llm_intent
Ensure Ollama is running (e.g. ollama serve) and a model is pulled (e.g. ollama run llama3.2).
"""
import asyncio
import json
import logging
import sys
from pathlib import Path

# Ensure project root is on path when run as script
if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

# Show INFO logs from the intent parser and LLM
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
    datefmt="%H:%M:%S",
)

from src.intent.parser import IntentParser


async def main():
    print("Testing intent parser with LLM (you should see 'Calling LLM' and 'LLM response received' above)\n")
    parser = IntentParser()
    intent = await parser.parse("hello")
    print("\nParsed intent:")
    print(json.dumps(intent, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
