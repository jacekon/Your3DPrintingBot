# Elegoo Centauri Carbon - Printer Specifications

## Overview

The **Elegoo Centauri Carbon** is an FDM (Fused Deposition Modeling) 3D printer with WiFi connectivity, using the SDCP V3.0.0 protocol for network communication.

---

## Hardware Specifications

| Specification | Value |
|---------------|-------|
| **Brand** | ELEGOO |
| **Model** | Centauri Carbon |
| **Type** | FDM (Filament) |
| **Connectivity** | WiFi, USB |

---

## Network Protocol

| Parameter | Value |
|-----------|-------|
| **Protocol Version** | SDCP V3.0.0 |
| **UDP Discovery Port** | 3000 |
| **WebSocket Port** | 3030 |
| **WebSocket Endpoint** | `/websocket` |
| **HTTP Upload Endpoint** | _Unknown / unverified_ |

---

## Discovery Response

Sending `M99999` via UDP to port 3000 returns:

```json
{
    "Id": "979d4C788A4a78bC777A870F1A02867A",
    "Data": {
        "Name": "Centauri Carbon",
        "MachineName": "Centauri Carbon",
        "BrandName": "ELEGOO",
        "MainboardIP": "192.168.31.104",
        "MainboardID": "0c6612d10147017000002c0000000000",
        "ProtocolVersion": "V3.0.0",
        "FirmwareVersion": "V1.1.25"
    }
}
```

### Discovery Response Fields

| Field | Description |
|-------|-------------|
| `Id` | Printer UUID |
| `Data.Name` | User-configurable printer name |
| `Data.MachineName` | Model name |
| `Data.BrandName` | Manufacturer |
| `Data.MainboardIP` | Current IP address |
| `Data.MainboardID` | Unique mainboard identifier (used for WebSocket topics) |
| `Data.ProtocolVersion` | SDCP protocol version |
| `Data.FirmwareVersion` | Current firmware version |

---

## Status Message Structure

The printer broadcasts status messages via WebSocket with the following structure:

```json
{
    "Status": {
        "CurrentStatus": [0],
        "TimeLapseStatus": 0,
        "PlatFormType": 0,
        "TempOfHotbed": 25.39,
        "TempOfNozzle": 26.47,
        "TempOfBox": 23.07,
        "TempTargetHotbed": 0,
        "TempTargetNozzle": 0
    },
    "MainboardID": "0c6612d10147017000002c0000000000",
    "TimeStamp": 1771442663,
    "Topic": "sdcp/status/0c6612d10147017000002c0000000000"
}
```

### Status Fields (FDM-specific)

| Field | Type | Description |
|-------|------|-------------|
| `CurrentStatus` | int[] | Machine status codes |
| `TimeLapseStatus` | int | Time-lapse photography status (0=off, 1=on) |
| `PlatFormType` | int | Build platform type |
| `TempOfHotbed` | float | Current heated bed temperature (°C) |
| `TempOfNozzle` | float | Current nozzle/hotend temperature (°C) |
| `TempOfBox` | float | Current enclosure temperature (°C) |
| `TempTargetHotbed` | float | Target heated bed temperature (°C) |
| `TempTargetNozzle` | float | Target nozzle temperature (°C) |

---

## WebSocket Communication

### Connection URL
```
ws://{MainboardIP}:3030/websocket
```

### Topics

| Direction | Topic Pattern |
|-----------|---------------|
| Request (Client → Printer) | `sdcp/request/{MainboardID}` |
| Response (Printer → Client) | `sdcp/response/{MainboardID}` |
| Status (Printer → Client) | `sdcp/status/{MainboardID}` |
| Attributes (Printer → Client) | `sdcp/attributes/{MainboardID}` |
| Error (Printer → Client) | `sdcp/error/{MainboardID}` |
| Notice (Printer → Client) | `sdcp/notice/{MainboardID}` |

### Heartbeat

| Feature | Status |
|---------|--------|
| Ping/Pong | **Not supported** (printer ignores ping messages) |

---

## Supported Commands

Supported commends: only Cmd 0 and Cmd 1 have been verified on this firmware. All other commands below are currently stubs in the client and remain untested.

| Cmd | Description | Tested |
|-----|-------------|--------|
| 0 | Request status refresh | ✅ Working |
| 1 | Request attributes refresh | ✅ Working |
| 128 | Start printing | Not tested |
| 129 | Pause printing | Not tested |
| 130 | Stop printing | Not tested |
| 131 | Continue/Resume printing | Not tested |
| 192 | Change printer name | Not tested |
| 258 | Retrieve file list | Not tested |
| 259 | Batch delete files | Not tested |

---

## Command Request Format

```json
{
    "Id": "{MachineId}",
    "Data": {
        "Cmd": 0,
        "Data": {},
        "RequestID": "{random-32-hex}",
        "MainboardID": "{MainboardID}",
        "TimeStamp": 1771442663,
        "From": 0
    },
    "Topic": "sdcp/request/{MainboardID}"
}
```

### From Values

| Value | Source |
|-------|--------|
| 0 | Local PC (LAN) |
| 1 | PC via Web |
| 2 | Web Client |
| 3 | Mobile App |
| 4 | Server |

---

## Command Response Format

```json
{
    "Id": "{MachineId}",
    "Data": {
        "Cmd": 0,
        "Data": {
            "Ack": 0
        },
        "RequestID": "{same-as-request}",
        "MainboardID": "{MainboardID}",
        "TimeStamp": 1771442663
    },
    "Topic": "sdcp/response/{MainboardID}"
}
```

### Ack Values

| Value | Meaning |
|-------|---------|
| 0 | Success |
| 1+ | Error (command-specific) |

---

## File Upload

File upload for Centauri Carbon is **not yet verified**. Multiple HTTP endpoints tried so far have returned 404/500. We implemented SDCP Cmd 256 (printer pulls from a local HTTP server) and sent URLs using the `${ipaddr}` placeholder. The printer accepts the request (no error) but the file does **not** appear on the printer yet. Further payload field validation is needed.

---

## Firmware Information

| Version | Notes |
|---------|-------|
| V1.1.25 | Tested, working with SDCP V3.0.0 |

---

## References

- [SDCP V3.0.0 Official Specification](https://github.com/cbd-tech/SDCP-Smart-Device-Control-Protocol-V3.0.0)
