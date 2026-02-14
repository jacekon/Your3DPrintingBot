# Elegoo Centauri Carbon – SDCP notes

Quick reference for controlling the printer from the bot. Full details: [OpenCentauri API](https://docs.opencentauri.cc/software/api/) and [SDCP Centauri Carbon](https://github.com/WalkerFrederick/sdcp-centauri-carbon).

## Connection

- **Discovery:** UDP broadcast to port `3000`, message `"M99999"`.
- **WebSocket:** `ws://{PrinterIP}:3030/websocket`
- **Format:** JSON over WebSocket. No authentication by default.
- **Keepalive:** Connection closes after ~60 s inactivity; send periodic ping/heartbeat.

## Protocol quirks

Some SDCP field names have typos and must be used exactly, e.g.:

- `MaximumCloudSDCPSercicesAllowed`
- `RelaseFilmState`
- `CurrenCoord`

Always refer to the official docs or the printer’s response schema when implementing.

## Commands to implement (for bot)

- Get printer status (temperatures, job progress, state).
- Pause / resume / stop print (exact command codes depend on firmware; check OpenCentauri/SDCP repo).

## Implementation

- Use an async WebSocket client (e.g. `websockets`).
- Implement a small SDCP client in `src/printer/sdcp.py` that:
  - Connects to `ws://{ip}:3030/websocket`
  - Sends JSON messages as per SDCP spec
  - Handles heartbeat and reconnection
