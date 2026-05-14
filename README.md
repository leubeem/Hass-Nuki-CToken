# Nuki ctoken for Home Assistant

Custom Home Assistant integration for the local Nuki Bridge HTTP API using encrypted `ctoken` authentication.

It provides native Home Assistant service actions:

- `nuki_ctoken.lock`
- `nuki_ctoken.unlock`
- `nuki_ctoken.open`
- `nuki_ctoken.lockngo`
- `nuki_ctoken.lockngo_open`

The integration does not use YAML configuration. Setup is done through the Home Assistant UI.

## What it does

For every action call, the integration generates a fresh encrypted token:

- `ctoken`: encrypted timestamp and random number
- `nonce`: random 24-byte nonce

The plain Bridge token is never sent to the Nuki Bridge in the URL.

## Installation

### Manual installation

Copy this folder into your Home Assistant config directory:

```text
custom_components/nuki_ctoken/
```

Then restart Home Assistant.

### HACS custom repository

1. Push this repository to GitHub.
2. In HACS, add it as a custom repository.
3. Category: `Integration`.
4. Install it.
5. Restart Home Assistant.

## Setup

In Home Assistant:

```text
Settings -> Devices & services -> Add integration -> Nuki ctoken
```

Enter:

- Bridge IP address, for example `192.168.13.54`
- Bridge port, usually `8080`
- Local Nuki Bridge API token

The integration then calls `/list` and lets you select the detected Nuki device. `nuki_id` and `device_type` are therefore not entered manually.

## Automation examples

### Lock

```yaml
actions:
  - action: nuki_ctoken.lock
    data:
      source: "automation.front_door_lock_at_night"
```

### Unlock

```yaml
actions:
  - action: nuki_ctoken.unlock
    data:
      source: "automation.front_door_unlock"
```

### Open / unlatch

```yaml
actions:
  - action: nuki_ctoken.open
    data:
      source: "automation.front_door_open"
```

`open` maps to Nuki action `3`.

For a Smart Lock this usually means `unlatch`, meaning it pulls the latch. For a Nuki Opener it triggers the opener action.

## Multiple locks

If you configure multiple Nuki devices, service calls must include `entry_id`.

You can find the entry ID from Home Assistant's service developer tools or logs.

Example:

```yaml
actions:
  - action: nuki_ctoken.lock
    data:
      entry_id: "01JABCDE1234567890ABCDE123"
      source: "automation.lock_back_door"
```

## Logging

Every action logs an info-level Home Assistant log line containing:

- timestamp
- action
- device name
- Nuki ID
- Home Assistant `user_id`, if available
- Home Assistant user name, if resolvable
- automation entity ID, best effort only
- automation name, best effort only
- explicit `source`, if provided
- context ID
- parent context ID
- Nuki Bridge response

It also fires an event:

```text
nuki_ctoken_action
```

Event payload example:

```json
{
  "timestamp": "2026-05-14T10:30:00Z",
  "action": "open",
  "device_name": "Front Door",
  "nuki_id": 123456789,
  "source": "automation.front_door_open",
  "user_id": null,
  "user_name": null,
  "automation_entity_id": "automation.front_door_open",
  "automation_name": "Front door open",
  "context_id": "...",
  "context_parent_id": "...",
  "nuki_response": {"success": true}
}
```

Home Assistant does not always expose a real human user for automation-triggered actions. In those cases this integration logs the context IDs and the optional `source` field so you can correlate events later.

## Security notes

- Do not expose the Nuki Bridge HTTP API to the internet.
- Keep the Bridge and Home Assistant in a trusted network or VLAN.
- The local Bridge token is stored in Home Assistant's config entry storage. It is not sent to the Bridge in action URLs, but it still exists on the Home Assistant system.
- Use `source` in automations if you want reliable attribution.

## Development

Repository layout:

```text
custom_components/nuki_ctoken/
  __init__.py
  config_flow.py
  const.py
  manifest.json
  services.yaml
  strings.json
hacs.json
README.md
```
