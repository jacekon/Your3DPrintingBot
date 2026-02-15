# Intent Parser

The Intent Parser analyzes user messages to extract structured intent information, particularly when users share links to Printables or Thingiverse.

## Features

- **URL Detection**: Automatically detects URLs from Printables and Thingiverse in user messages
- **URL Validation**: Validates that URLs are from supported sites
- **LLM-based Intent Extraction**: Uses an LLM (default: Ollama) to understand user intent
- **Structured JSON Output**: Returns consistent JSON schema for downstream processing
- **Error Handling**: Gracefully handles invalid URLs, parsing errors, and unclear intent

## Config files

Intent parser behaviour is driven by config under `config/`:

- **`config/prompts/intent_parser.txt`** — LLM prompt template (placeholders: `{user_message}`, `{urls}`)
- **`config/supported_domains.json`** — JSON array of supported base domains (e.g. `["printables.com", "thingiverse.com"]`); `www.` variants are added automatically
- **`config/intent_schema.json`** — JSON Schema for the intent result (for reference / validation)

## Supported Sites

By default (from `config/supported_domains.json`):

- **printables.com** (Printables)
- **thingiverse.com** (Thingiverse)

## Intent Types

- `print`: User wants to print the model (e.g., "print this", "can you print")
- `save`: User wants to save/bookmark for later (e.g., "save this", "bookmark")
- `info`: User just wants information (e.g., "what is this", "tell me about")
- `unclear`: Cannot determine intent or no clear action requested

## JSON Schema

```json
{
  "intent": "print|save|info|unclear",
  "url": "https://...",
  "site": "printables|thingiverse|null",
  "confidence": 0.0-1.0,
  "material": "PLA",
  "color": "printer_default",
  "error": null or error message string
}
```

### Fields

- **intent** (required): One of `print`, `save`, `info`, `unclear`
- **url**: Detected URL (if any)
- **site**: Detected site name (`printables`, `thingiverse`, or `null`)
- **confidence** (required): Confidence score 0.0-1.0
- **material**: Material type (defaults to `"PLA"` for now)
- **color**: Color (defaults to `"printer_default"` - current printer color)
- **error**: Error message if parsing failed

## Usage

```python
from src.intent.parser import IntentParser
from src.llm.ollama import OllamaProvider

# Create parser (uses Ollama by default)
parser = IntentParser()

# Parse user message
intent = await parser.parse("Can you print this? https://www.printables.com/model/12345")

print(intent)
# {
#   "intent": "print",
#   "url": "https://www.printables.com/model/12345",
#   "site": "printables",
#   "confidence": 0.95,
#   "material": "PLA",
#   "color": "printer_default",
#   "error": null
# }
```

## Configuration

The Intent Parser uses the LLM provider configured via environment variables:

- `OLLAMA_BASE_URL`: Ollama API URL (default: `http://localhost:11434`)
- `OLLAMA_MODEL`: Model name (default: `llama3.2`)

## LLM Prompt

The parser uses a carefully crafted prompt that instructs the LLM to:

1. Analyze user messages for intent
2. Extract URLs and identify sites
3. Determine intent (print/save/info/unclear)
4. Return structured JSON matching the schema
5. Handle errors gracefully

The prompt emphasizes:
- Returning **only JSON** (no extra text)
- Defaulting material to "PLA"
- Defaulting color to "printer_default"
- Setting confidence scores appropriately
- Handling unclear or invalid inputs

## Error Handling

The parser handles several error scenarios:

1. **Invalid URLs**: URLs that don't match supported domains → `error` field set, `intent: "unclear"`
2. **Unsupported sites**: URLs from other sites → `error` field set, `intent: "unclear"`
3. **LLM JSON parse errors**: Malformed JSON from LLM → `error` field set, `intent: "unclear"`
4. **LLM API errors**: Network/timeout errors → `error` field set, `intent: "unclear"`
5. **Unclear intent**: LLM cannot determine intent → `intent: "unclear"`, low confidence

## Implementation Details

- Uses regex for URL detection (`src/intent/parser.py`)
- Validates URLs using `urllib.parse`
- Calls LLM via async HTTP (httpx)
- Parses JSON response, handling markdown code blocks
- Validates output against schema and enforces defaults
