# Nuki ctoken for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![HA min version](https://img.shields.io/badge/Home%20Assistant-%3E%3D2024.8-blue)](https://www.home-assistant.io)

A custom Home Assistant integration for the local **Nuki Bridge HTTP API** that uses encrypted `ctoken` authentication — your Bridge token is never sent in plain text over the network.

## Features

- Communicates with the Nuki Bridge on your local network only
- No cloud dependency
- Token is encrypted using XSalsa20-Poly1305 (NaCl SecretBox) for every request
- No external Python dependencies — pure Python crypto, works on any HA architecture (including aarch64 / Raspberry Pi)
- Auto-discovers devices from the Bridge via `/list`
- Five service actions: `lock`, `unlock`, `open`, `lockngo`, `lockngo_open`
- Fires a `nuki_ctoken_action` event after every action for automations and logging
- Logs user, automation, and context info for every action

## How the ctoken works

For every request the integration generates:

1. A random 24-byte nonce
2. A plaintext of `{UTC timestamp},{random 16-bit number}`
3. The Bridge token is SHA-256 hashed to produce the encryption key
4. The plaintext is encrypted with XSalsa20-Poly1305

The `ctoken` (MAC + ciphertext) and `nonce` are sent as query parameters. The plain token never appears in a URL.

## Installation

### HACS (recommended)

1. Open HACS in Home Assistant
2. Go to **Integrations** → three-dot menu → **Custom repositories**
3. Add `https://github.com/leubeem/Hass-Nuki-CToken` with category **Integration**
4. Search for **Nuki ctoken** and install it
5. Restart Home Assistant

### Manual

Copy the `custom_components/nuki_ctoken/` folder into your HA config directory:

```
config/custom_components/nuki_ctoken/
```

Then restart Home Assistant.

## Setup

In Home Assistant:

```
Settings → Devices & services → Add integration → Nuki ctoken
```

Enter:

| Field | Example |
|-------|---------|
| Bridge IP address | `192.168.1.100` |
| Bridge port | `8080` |
| Local API token | (from the Nuki app: Bridge → API) |

The integration calls `/list` on the Bridge and lets you pick the detected device. `nukiId` and `deviceType` are discovered automatically — you do not enter them manually.

To find the local API token: Nuki app → Bridge → Settings → HTTP API → API token.

## Available actions

| Action | Nuki action code | Description |
|--------|-----------------|-------------|
| `nuki_ctoken.lock` | 2 | Lock |
| `nuki_ctoken.unlock` | 1 | Unlock |
| `nuki_ctoken.open` | 3 | Unlatch / opener trigger |
| `nuki_ctoken.lockngo` | 4 | Lock 'n' Go |
| `nuki_ctoken.lockngo_open` | 5 | Lock 'n' Go with unlatch |

All actions are fire-and-forget (`nowait=1`).

## Service call examples

### Lock

```yaml
action: nuki_ctoken.lock
data:
  source: "automation.front_door_lock_at_night"
```

### Unlock

```yaml
action: nuki_ctoken.unlock
```

### Open / unlatch

```yaml
action: nuki_ctoken.open
data:
  source: "button.front_door_open"
```

### Multiple devices

If you have more than one Nuki device configured, select the target device from the **Device** dropdown in the action UI, or pass `entry_id` in YAML:

```yaml
action: nuki_ctoken.lock
data:
  entry_id: "01JABCDE1234567890ABCDE123"
  source: "automation.lock_back_door"
```

The entry ID is visible in **Settings → Devices & services → Nuki ctoken → (device) → three-dot menu → System information**.

## Event: `nuki_ctoken_action`

After every successful action the integration fires an event on the HA event bus.

Example payload:

```json
{
  "timestamp": "2026-05-14T12:00:00Z",
  "action": "open",
  "device_name": "Front Door",
  "nuki_id": 123456789,
  "entry_id": "01JABCDE1234567890ABCDE123",
  "source": "automation.front_door_open",
  "user_id": "abc123",
  "user_name": "Eva",
  "automation_entity_id": "automation.front_door_open",
  "automation_name": "Front door open",
  "context_id": "...",
  "context_parent_id": "...",
  "nuki_response": {"success": true}
}
```

Use this event to build history dashboards, send notifications, or trigger follow-up automations.

> **Note:** Home Assistant does not always expose a real user for automation-triggered actions. Use the `source` field for reliable attribution when `user_id` is null.

## Logging

Every action writes an `INFO`-level log line to the Home Assistant log:

```
Nuki action executed timestamp=... action=open device=Front Door nuki_id=123456789 ...
```

To see only nuki_ctoken log entries, filter the log by `nuki_ctoken` in **Settings → System → Logs**.

## Security notes

- Keep the Nuki Bridge on a trusted local network or VLAN — do not expose it to the internet
- The Bridge token is stored in Home Assistant's internal config entry storage (`.storage/core.config_entries`)
- The token is never sent to the Bridge in plain text; only the encrypted ctoken and nonce are transmitted
- HA's config entry storage is not encrypted by default — treat your HA instance accordingly

## Requirements

- Home Assistant 2024.8.0 or newer
- Nuki Bridge with local HTTP API enabled and a valid API token
- Network access from Home Assistant to the Nuki Bridge

## Repository layout

```
custom_components/nuki_ctoken/
  __init__.py       Main integration: client, ctoken builder, service handlers
  _crypto.py        Pure-Python XSalsa20-Poly1305 (no native dependencies)
  config_flow.py    UI setup flow
  const.py          Constants
  manifest.json
  services.yaml
  strings.json
hacs.json
README.md
```

## Contributing

Bug reports and pull requests are welcome at [github.com/leubeem/Hass-Nuki-CToken](https://github.com/leubeem/Hass-Nuki-CToken).
