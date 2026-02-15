#!/usr/bin/env python3
"""
Test that the intent parser actually calls the LLM and returns valid results.
Run from project root: python scripts/test_llm_intent.py
Ensure Ollama is running (e.g. ollama serve) and a model is pulled (e.g. ollama run llama3.2).
Exits with 0 on pass, 1 on failure.
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

VALID_INTENTS = {"print", "save", "info", "unclear"}

# Load supported websites from config (same as intent parser)
CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
SUPPORTED_DOMAINS_JSON = CONFIG_DIR / "supported_domains.json"


def _load_supported_from_config() -> tuple[list[str], set[str]]:
    """Load config/supported_domains.json; return (list of domains, set of site names)."""
    if not SUPPORTED_DOMAINS_JSON.exists():
        raise FileNotFoundError(f"Config not found: {SUPPORTED_DOMAINS_JSON}")
    domains = json.loads(SUPPORTED_DOMAINS_JSON.read_text(encoding="utf-8"))
    if not isinstance(domains, list) or not all(isinstance(d, str) for d in domains):
        raise ValueError("supported_domains.json must be a list of strings")
    domains = [d.lower().strip() for d in domains if d and not d.startswith("www.")]
    # Site name = first label (e.g. printables.com -> printables)
    sites = {d.split(".", 1)[0] for d in domains}
    return domains, sites


SUPPORTED_DOMAINS, SUPPORTED_SITES = _load_supported_from_config()


def _sample_url_for_print_test() -> str:
    """Build a sample URL from the first supported domain for the 'print <link>' test."""
    if not SUPPORTED_DOMAINS:
        return "https://www.printables.com/model/123456"
    domain = SUPPORTED_DOMAINS[0]
    return f"https://www.{domain}/model/123456"


def _check_common(intent: dict) -> list[str]:
    """Common checks for any intent result. Returns list of failure reasons."""
    errors = []
    if "intent" not in intent:
        errors.append("missing key 'intent'")
    if "confidence" not in intent:
        errors.append("missing key 'confidence'")
    if errors:
        return errors
    if intent["intent"] not in VALID_INTENTS:
        errors.append(f"invalid intent {intent['intent']!r}, must be one of {VALID_INTENTS}")
    c = intent["confidence"]
    if not isinstance(c, (int, float)) or not (0 <= c <= 1):
        errors.append(f"confidence must be 0-1, got {c!r}")
    return errors


def check_hello(intent: dict, message: str) -> list[str]:
    """Assert result for message 'hello': intent unclear, no URL."""
    errors = _check_common(intent)
    if errors:
        return errors
    if message.strip().lower() != "hello":
        return errors
    if intent["intent"] != "unclear":
        errors.append(f"for 'hello' expected intent 'unclear', got {intent['intent']!r}")
    if intent.get("url") not in (None, ""):
        errors.append(f"for 'hello' expected no url, got {intent.get('url')!r}")
    return errors


def check_print_link(intent: dict, message: str) -> list[str]:
    """Assert result for 'print <supported link>': intent print, valid URL and site."""
    errors = _check_common(intent)
    if errors:
        return errors
    if "print" not in message.lower():
        return errors
    if intent["intent"] != "print":
        errors.append(f"for 'print <link>' expected intent 'print', got {intent['intent']!r}")
    url = intent.get("url") or ""
    if not url or not isinstance(url, str):
        errors.append("expected non-empty 'url' for print link message")
    else:
        if not any(d in url for d in SUPPORTED_DOMAINS):
            errors.append(f"url must be from supported site ({SUPPORTED_DOMAINS}), got {url!r}")
    site = intent.get("site")
    if site not in SUPPORTED_SITES:
        errors.append(f"expected 'site' in {SUPPORTED_SITES}, got {site!r}")
    return errors


async def run_test(parser: IntentParser, name: str, message: str, check_fn) -> tuple[bool, dict]:
    """Run one test; return (passed, intent_result)."""
    try:
        intent = await parser.parse(message)
    except Exception as e:
        print(f"  FAILED: parser raised {e}")
        return False, {}
    failures = check_fn(intent, message)
    if failures:
        print(f"  FAILED: {'; '.join(failures)}")
        print("  Result:", json.dumps(intent, indent=2))
        return False, intent
    print("  Result:", json.dumps(intent, indent=2))
    return True, intent


async def main() -> int:
    print("Testing intent parser with LLM...\n")
    parser = IntentParser()

    # Test 1: "hello" -> unclear
    print("[1] Message: 'hello' (expect intent=unclear)")
    passed1, _ = await run_test(parser, "hello", "hello", check_hello)
    if not passed1:
        print("\nOverall: FAILED (hello test)")
        return 1
    print("  PASSED\n")

    # Test 2: "print <link>" -> print + supported URL/site (link from config)
    print("[2] Message: 'print <link to supported website>'")
    message_with_link = f"print {_sample_url_for_print_test()}"
    print(f"  Input: {message_with_link!r}")
    passed2, _ = await run_test(parser, "print_link", message_with_link, check_print_link)
    if not passed2:
        print("\nOverall: FAILED (print link test)")
        return 1
    print("  PASSED\n")

    print("Overall: PASSED (all tests)")
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
