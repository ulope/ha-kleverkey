# KleverKey for Home Assistant

[![hacs][hacs-badge]][hacs-url]
[![Validate][validate-badge]][validate-url]
[![Tests][tests-badge]][tests-url]

A custom [Home Assistant][home-assistant] integration for [KleverKey][kleverkey]
locks and gateways.

During setup you pick one or more of the organizations your API key has access
to, and every lock and gateway in them is added to Home Assistant as a device.

## Scope

The integration deliberately uses only two areas of the [KleverKey API][api-docs]:

| API area | Endpoints used |
| --- | --- |
| Organization locks | `GET /organizations/{organizationId}/locks`, `PUT /organizations/{organizationId}/locks/{lockId}/restart` |
| Organization gateways | `GET /organizations/{organizationId}/gateways`, `PUT /organizations/{organizationId}/gateways/{gatewayId}/restart` |

Two further read-only endpoints are used during configuration to discover which
organizations you can choose from: `GET /users/me` and
`GET /organizations/{organizationId}`.

Locks are reported, not operated: remote opening lives in the
`/users/me/permissions` part of the API, which is outside this scope.

## Installation

### HACS (recommended)

1. In Home Assistant, open **HACS → ⋮ → Custom repositories**.
2. Add `https://github.com/ulope/ha-kleverkey` with category **Integration**.
3. Search for **KleverKey** in HACS, install it and restart Home Assistant.
4. Go to **Settings → Devices & services → Add integration** and pick **KleverKey**.

### Manual

Copy `custom_components/kleverkey` into your Home Assistant `config/custom_components`
directory and restart Home Assistant.

## Configuration

1. Create an API key in the [KleverKey portal][api-keys] under **Account → API keys**.
2. Add the integration and paste the API key.
3. Select the organizations you want to import. You can change the selection
   later via **Configure** on the integration entry.

The integration polls the KleverKey API once a minute.

## Entities

Each lock and each gateway becomes a device. Locks that are linked to a gateway
are shown behind that gateway in the device tree.

### Lock

| Entity | Platform | Notes |
| --- | --- | --- |
| Lock | `binary_sensor` | On when the lock is not locked |
| Door | `binary_sensor` | On when the lock reports its door as open |
| Connectivity | `binary_sensor` | Diagnostic |
| Battery | `binary_sensor` | On when the battery is low or a change is recommended |
| Emergency | `binary_sensor` | Diagnostic, on while the lock signals an emergency |
| Update | `binary_sensor` | Diagnostic, on when a firmware update is available |
| Physical state | `sensor` | `open`, `closed` or `locked` |
| Weekly openings | `sensor` | |
| Last activity | `sensor` | Diagnostic timestamp |
| Controller temperature | `sensor` | Diagnostic, whole °C — the lock's controller, not ambient |
| Signal strength | `sensor` | Diagnostic, BLE RSSI |
| Connected since, Disconnected since | `sensor` | Diagnostic timestamps |
| Battery changed | `sensor` | Diagnostic, disabled by default |
| Restart | `button` | Restarts the lock |

### Gateway

| Entity | Platform | Notes |
| --- | --- | --- |
| Connectivity | `binary_sensor` | Diagnostic |
| Update | `binary_sensor` | Diagnostic, on when a firmware update is available |
| Last activity | `sensor` | Diagnostic timestamp |
| Signal strength | `sensor` | Diagnostic, Wi-Fi RSSI |
| Connected since, Disconnected since | `sensor` | Diagnostic timestamps |
| Restart | `button` | Restarts the gateway |

The battery-changed timestamp is disabled by default and can be turned on from
the device page.

## Troubleshooting

If the API key is revoked or expires, the integration asks you to re-authenticate
with a new key. Download diagnostics from the integration entry to inspect the
data the integration receives; API keys and hardware IDs are redacted.

## Development

```bash
uv venv --python 3.13 .venv
uv pip install -r requirements_test.txt
.venv/bin/pytest
.venv/bin/ruff check .
```

## Brand assets

`custom_components/kleverkey/brand/` holds a **placeholder** key icon so that
HACS validation passes. It is a generic glyph, not KleverKey artwork — see the
README in that directory for how to replace it.

## Disclaimer

This is an unofficial integration and is not affiliated with, endorsed by, or
supported by KleverKey.

[home-assistant]: https://www.home-assistant.io/
[kleverkey]: https://www.kleverkey.com/
[api-docs]: https://portal.kleverkey.com/documentation/api
[api-keys]: https://portal.kleverkey.com/account/api-keys
[hacs-badge]: https://img.shields.io/badge/HACS-Custom-41BDF5.svg
[hacs-url]: https://hacs.xyz
[validate-badge]: https://github.com/ulope/ha-kleverkey/actions/workflows/validate.yml/badge.svg
[validate-url]: https://github.com/ulope/ha-kleverkey/actions/workflows/validate.yml
[tests-badge]: https://github.com/ulope/ha-kleverkey/actions/workflows/tests.yml/badge.svg
[tests-url]: https://github.com/ulope/ha-kleverkey/actions/workflows/tests.yml
