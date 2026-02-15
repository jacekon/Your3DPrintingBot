"""Example script to test the Intent Parser."""
import asyncio
import json
import logging

from src.intent.parser import IntentParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_intent_parser():
    """Test the intent parser with various messages."""
    parser = IntentParser()

    test_cases = [
        "Can you print this? https://www.printables.com/model/12345",
        "Save this for later: https://www.thingiverse.com/thing:67890",
        "What is this model? https://www.printables.com/model/11111",
        "Print this model please",
        "https://www.printables.com/model/22222",
        "I want to print this thingiverse model: https://www.thingiverse.com/thing:33333",
        "This is a cool model: https://example.com/model",  # Unsupported site
        "Just asking a question without any link",
    ]

    print("Testing Intent Parser\n" + "=" * 60)

    for i, message in enumerate(test_cases, 1):
        print(f"\n[{i}] Message: {message}")
        print("-" * 60)
        try:
            intent = await parser.parse(message)
            print(json.dumps(intent, indent=2))
        except Exception as e:
            print(f"ERROR: {e}")

    # Close LLM connection if needed
    if hasattr(parser.llm, "close"):
        await parser.llm.close()


if __name__ == "__main__":
    asyncio.run(test_intent_parser())
