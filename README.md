<p align="center">
  <img src="https://raw.githubusercontent.com/ADNPolymerase/ha-landroid-vision/main/logo.png" alt="Worx Landroid Vision PLUS" width="380">
</p>

# Worx Landroid Vision PLUS

[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://badgen.net/github/release/ADNPolymerase/ha-landroid-vision)](https://github.com/ADNPolymerase/ha-landroid-vision/releases)
[![Validate](https://github.com/ADNPolymerase/ha-landroid-vision/actions/workflows/validate.yml/badge.svg)](https://github.com/ADNPolymerase/ha-landroid-vision/actions/workflows/validate.yml)
[![HA Version](https://img.shields.io/badge/Home%20Assistant-2026.3%2B-blue.svg)](https://www.home-assistant.io/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/ADNPolymerase/ha-landroid-vision/blob/main/LICENSE)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-support-yellow.svg?logo=buy-me-a-coffee)](https://buymeacoffee.com/adnpolymerase)

<a href="https://buymeacoffee.com/adnpolymerase" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-orange.png" alt="Buy Me A Coffee" height="60"></a>
<a href="https://adnpolymerase.github.io/HA/" target="_blank"><img src="https://raw.githubusercontent.com/ADNPolymerase/HA/main/assets/site-button.svg" alt="Link to my github.io for my other projects" height="60"></a>

Custom Home Assistant integration for Worx Landroid Vision / Vision Cloud / RTK mowers.

This integration is built on top of the community `pyworxcloud` library and adds a cleaner Home Assistant entity layer for Vision mowers: mower controls, useful sensors, diagnostics, schedule calendar, RTK map rendering and live-ish robot position tracking.

## Features

- Native `lawn_mower` entity: start, pause, dock, one-time mowing (runtime, edge cutting, RTK zones) and on-demand edge cutting.
- Mower controls: firmware auto-update, lock, native schedule, smart edge cutting, save the hedgehogs, party mode, and (when your mower reports the matching hardware module) ACS, off limits, cutting height, torque and border distance.
- Daily area/progress tracking persisted per mower in Home Assistant storage, immune to cloud counter resets and multi-day gaps, plus a locally computed estimate that keeps moving even when Worx's own stats go stale.
- Schedule sensor and calendar, next mowing time, RTK map camera with mowed-area trail, RTK robot position and reverse-geocoded address (opt-in).
- Battery, status, error, connectivity, maintenance and mowing-readiness sensors, with Home Assistant Repairs alerts for blade/battery service and a restart button.
- Download diagnostics with automatic redaction of coordinates, addresses and identifiers.
- Translated into 11 languages (English, Polish, French, German, Dutch, Spanish, Italian, Swedish, Norwegian, Danish, Russian), including entity states, schedule and calendar.

## Installation

### Option 1: HACS (recommended)

The integration is in the HACS default store, so no custom repository is needed:

1. Open HACS and search for `Worx Landroid Vision PLUS`.
2. Download it.
3. Restart Home Assistant.
4. Go to `Settings > Devices & services > Add integration` and search for `Worx Landroid Vision PLUS`.

### Option 2: direct from this repository

Without HACS, copy this directory:

```text
custom_components/worx_vision_cloud
```

to your Home Assistant config directory:

```text
/config/custom_components/worx_vision_cloud
```

Then restart Home Assistant and add the integration from `Settings > Devices & services`. You are responsible for updates with this method. HACS handles them for you with option 1.

At setup, sign in with the same e-mail and password as in your mower app and pick your brand cloud: `worx`, `kress` or `landxcape`.

## Entities

The exact entity list depends on what your mower reports. Typical entities include:

- `lawn_mower` mower control
- `button` refresh, reset blade runtime, reset battery cycles and start edge cutting
- `calendar` mowing schedule
- `camera` RTK map
- `device_tracker` RTK robot position
- `sensor` battery, status, error, readiness, cloud connection, RSSI, schedule, next schedule, RTK map, RTK trail, daily progress, remaining progress, today and total mowed area, estimated daily area and progress, mowing time today, lawn area, runtime, efficiency, cloud statistics freshness and maintenance values (home time and charging time are included but disabled by default, see below)
- `binary_sensor` online, IoT/MQTT registration, rain, robot lifted and pause mode
- `switch` firmware auto update, mower lock, native schedule, smart edge cutting, save the hedgehogs, party mode, off limits and ACS (the last two only when your mower reports the matching module)
- `number` rain delay, schedule time extension, lawn area, lawn perimeter, cutting height and torque (the last two only when your mower reports the matching module; torque is disabled by default)
- `update` firmware version, release notes and OTA install when supported

See [docs/entities.md](docs/entities.md) for a more detailed list.

## Cards

Any standard Home Assistant card works with these entities. Two are worth knowing:

- **[landroid-card](https://github.com/Barma-lej/landroid-card)** by Barma-lej: a full mower dashboard card. Point its `camera:` option at the RTK map camera to show the map inside it.
- **`lovelace/worx-map-rtk-card.js`** in this repository: a standalone RTK map card, with a companion info card. Copy it to `config/www/`, register it as a Lovelace resource, then use `type: custom:worx-map-rtk-card` with your map camera entity.

The `lawn_mower` entity deliberately has no name of its own, so it displays exactly the device name, and it stays available through connectivity blips rather than going unavailable. Both are for cards like landroid-card, which use it as the label prefix for every other entity and blank their body when it is unavailable. Only commands are blocked while genuinely offline, with a clear error.

## RTK Map & Address

For Vision Cloud / RTK mowers, a camera entity renders the boundary, excluded areas, station and the day's mowing trail as SVG from the private Worx map endpoint. It is not a video stream: it updates when new data arrives. The trail covers the full local day like the Worx app, resets at local midnight, survives a restart, and keeps the last known map if a fetch briefly fails.

An `RTK address` sensor (disabled by default) reverse-geocodes the mower's rounded position with OpenStreetMap Nominatim, cached 24h. It is opt-in because RTK coordinates can reveal a home location. Maps and coordinates are precise, so don't publish debug dumps, storage files, tokens or screenshots showing them. See [SECURITY.md](SECURITY.md).

### Recovering the map after upgrading from an older version

*Before 1.6.3 the RTK map id was not cached, so the map camera and the lawn-area and progress sensors could go blank whenever Worx stopped sending it. It has been cached and persisted since, but that cache is empty on the first restart after upgrading. If those entities are unavailable then, open the **RTK map** sensor's history, take the last UUID it held, and pass it to the `worx_vision_cloud.set_rtk_map_id` action with your `lawn_mower` entity. Everything updates immediately and stays fresh on its own afterwards.*

## Mowed area

Mowing figures are covered area, not unique lawn area: overlapping passes mean Today and Total mowed area can legitimately exceed your lawn size, and Daily progress reaches 100% once covered area matches it. The daily baseline is stored per mower, so it survives restarts and entity renames and handles cloud counter resets and multi-day gaps.

Lawn area comes from the account's `lawn_size` when Worx provides one, otherwise from the sum of the RTK map's mowed zones. Zones the mower only drives through, such as a corridor linking two mowing areas, carry no cutting metadata and are excluded, so the figure matches the Worx app rather than the raw map total.

### A caveat on daily attribution

Today mowed area and Daily progress come from the cloud's cumulative counter, so they follow when Worx **publishes** a session, not when the mower actually mowed. Publication can lag by hours: one observed session ran from 14:02 to 17:54 and its 310 m² only appeared at 03:26 the next morning, crediting them to the following day.

Nothing is lost, Total mowed area stays correct. For a figure that tracks the current day as it happens, use the locally computed Estimated mowed area today and Estimated daily progress sensors, derived from observed mowing time rather than the cloud counter.

## Limitations

The Worx / Positec cloud API is not officially public. Some endpoints used here are reverse-engineered and can change without notice. This is a best-effort custom integration, not official Worx software.

- Off limits and ACS entities can read `unavailable` on a mower that supports them. Availability depends on pyworxcloud seeing the matching module (`DF`, `US`) in live data, and the off limits module only appears once a zone has been configured in the Worx app at least once. A limitation of the API data, shared with the community `landroid_cloud` integration.
- Worx publishes firmware release notes only while an update is pending; once installed the endpoint answers 404 and they are gone. The integration records them as they go past, but nothing can be recovered for a version installed before that existed. Use the `worx_vision_cloud.set_firmware_notes` action to paste those in from the Worx account portal.
- An update touching only the vision head is invisible here. Firmware ships as a head and mower pair, but availability is computed by comparing mower versions alone, and the head's running version is not exposed at all. Both follow from the API; the Worx app remains the reference for head firmware.
- Mower home time and charging time can read `0` permanently for some accounts, because the API does not populate them for every model. Both sensors are disabled by default; enable them if your account reports real values.

## Credits

- Uses [`pyworxcloud`](https://github.com/MTrab/pyworxcloud).
- Integration originally prepared by Smart Service.
