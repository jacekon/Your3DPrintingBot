# Project Progress Summary

This document summarizes the current state of the project and what remains to be done. It is intended for a new AI agent to pick up work quickly and continue.

## What’s Implemented

### Slicing Workflow
- OrcaSlicer CLI integration fixed and stabilized.
- G-code slicing is integrated into the bot flow after model download.
- G-code output saved into the job directory.
- SLICER_PATH environment variable is supported via .env/.env.example.

### SDCP Integration (Current Direction)
- We decided to abandon the old ElegooLink/Cassini protocol for uploads and move to SDCP V3.
- Added sdcp-printer-api as a git submodule at:
  - src/printerConnector/sdcp-printer-api
- New SDCP client wrapper created:
  - src/printerConnector/sdcp_client.py
- Implemented request_status() and added tests for real printer connectivity.

### Testing
- test_sdcp_client.py now only runs a real-printer integration test using PRINTER_IP from .env.
- Integration test shows SDCP connection works and can refresh status.

### Documentation
- Elegoo Centauri Carbon SDCP spec draft created:
  - src/printerConnector/ElegooCentauriCarbon.md
- Spec reflects verified behaviors and marks unverified areas (e.g., upload endpoint).

### Dependencies
- Added asyncio-dgram (required by sdcp-printer-api) to requirements.txt.

## What’s Still Missing / To Do

### 1) SDCP Command Implementations (Core)
- Only Cmd 0 (request_status) is implemented in SdcpClient.
- All other SDCP commands are stubbed in SdcpClient and need to be implemented one-by-one with tests.
- Commands to implement first (suggested order):
  1. request_attributes (Cmd 1)
  2. retrieve_file_list (Cmd 258)
  3. retrieve_file_details (Cmd 260)
  4. start_print (Cmd 128)
  5. pause_print / stop_print / continue_print
- Confirm command payload structures against the SDCP V3 spec and firmware behavior.

### 2) File Upload
- Upload is not working yet. HTTP endpoints are unverified.
- Implemented Cmd 256 with local HTTP server and `${ipaddr}` URL placeholder; printer accepts request but file does not appear on device.
- Must confirm exact payload fields/format and whether additional fields are required for Centauri Carbon.

### 3) Bot Refactor (Critical Note)
- The bot currently lives in src/bot.py and is imported in src/__init__.py.
- This creates side effects during tests (config/logging initialized on import).
- We need to move the bot to a subfolder and make it a module there.
- Then update src/__init__.py to remove the direct import of src.bot.

### 4) SDCP Client Integration into Bot
- The bot still references the older connector path in some places.
- After SDCP client supports file upload and start_print, integrate it into bot flow.
- Ensure errors are user-friendly and timeouts handled properly.

### 5) Update Spec as Behavior is Verified
- ElegooCentauriCarbon.md should be updated whenever a command or upload method is verified.
- Replace “unverified” sections with confirmed endpoints/payloads as they are validated.

## Known Issues / Context

- Importing from src.* triggers src/__init__.py which imports src.bot and loads config/logging.
- This is the reason tests previously had noisy output and required manual module loading.
- Once bot is moved and __init__ cleaned up, tests can import modules normally.

## Useful Files

- SDCP client wrapper: src/printerConnector/sdcp_client.py
- SDCP submodule: src/printerConnector/sdcp-printer-api
- SDCP test: tests/test_sdcp_client.py
- Printer spec: src/printerConnector/ElegooCentauriCarbon.md
- Bot entry: src/bot.py (to be moved)

## Suggested Next Steps

1) Implement request_attributes in SdcpClient and write its test (real printer).
2) Implement retrieve_file_list and test it.
3) Confirm and implement upload method (Cmd 256 or HTTP endpoint).
4) Implement start_print and test it with a known file.
5) Move bot into a subfolder module; fix src/__init__.py.
6) Integrate fully working SDCP client into bot flow.
