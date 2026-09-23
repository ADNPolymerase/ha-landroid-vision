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

- Native `lawn_mower` entity: start, pause, dock, one-time mowing and on-demand edge cutting.
- One-time zone mowing on RTK mowers, the way the Worx app does it: pick the zones, a fixed or automatic order and the edge routine, and the mower mows them through before coming home. Available as the `worx_vision_cloud.start_zone_mowing` action, so an automation can schedule it, and from the Start one-time mowing button.
- Each RTK zone's mowing pattern (natural, parallel, diamond, checker) and angle, read from the mower, one pair of sensors per zone named after it. Display only: the settings are changed in the Worx app.
- Mower controls: firmware auto-update, lock, native schedule, smart edge cutting, save the hedgehogs, party mode, and (when your mower reports the matching hardware module) ACS, off limits, cutting height, torque and border distance.
- Daily area/progress tracking persisted per mower in Home Assistant storage, immune to cloud counter resets and multi-day gaps, plus a locally computed estimate that keeps moving even when Worx's own stats go stale.
- Schedule sensor and calendar (one week before and after today by default, adjustable in the integration options), next mowing time, RTK map camera with mowed-area trail, RTK robot position and reverse-geocoded address (opt-in).
- On RTK mowers, each weekly slot shows the zones set for it in the Worx app, by name, and whether their order was imposed. They appear in the calendar events and in the `slots` attribute of the schedule sensor (`zones`, `zone_names`, `zone_order`), ready for a card or a template.
- Battery, status, error, connectivity, maintenance and mowing-readiness sensors, with Home Assistant Repairs alerts for blade/battery service and for a mower left stopped away from its base, and a restart button.
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

The integration ships its own card, **Worx Landroid Vision**, and registers it for you: after installing or updating, reload the browser and pick it in the card list. It shows:

- the mower's detailed state (searching a zone, crossing a border, leaving home...) with the zone it is in and the battery, where the `lawn_mower` entity alone only knows mowing, docked, paused, returning or error;
- the Wi-Fi signal next to the battery, whether the mower is ready to mow, and a red banner with the current error and since when, only when there is one;
- a light blue rain banner while the mower waits because of rain, with the time left before it can go out again and the rain delay set, rather than a red error;
- start, pause and dock, and a party mode button under the battery: while it is on, a banner says the mower will not go out, even during the schedule;
- the RTK map with the day's trail;
- one-time mowing the way the Worx app does it: tick the zones, shown side by side, keep the order you ticked them in (Special) or let the mower choose (Auto), add the edge cut or not, and start;
- the weekly schedule received from the cloud, folded under the slot running now, or the next mowing time otherwise, and unfolded day by day with each slot's zones, order and edge cut;
- the mower's current blade time, as in the Worx app, with progress toward the blade service threshold, and a reset button that asks for confirmation first.

A click on the state, the zone, the battery, the Wi-Fi, the readiness, the error, the rain banner or the map opens Home Assistant's more-info dialog, with its history.

```yaml
type: custom:worx-vision-card
entity: lawn_mower.your_mower
```

Only `entity` is needed, the card finds the other entities of the same mower by itself, so renaming them does not break it. Optional: `title`, `show_info`, `show_controls`, `show_map`, `show_zones`, `show_schedule`, `show_blades` (all `true` by default) and `refresh_interval` for the map, in seconds (30 by default, 0 to turn it off). On an older Landroid with no RTK map and no zones, the card shows the state, the controls and the schedule.

The card is developed in [ha-landroid-vision-card](https://github.com/ADNPolymerase/ha-landroid-vision-card), and this integration ships a copy of it. If you installed that card through HACS, uninstall it there: the integration now registers its own copy and removes the HACS resource on start, but HACS may add it back on its next update, and both files would compete for the same card name.

The card replaces `worx-map-rtk-card.js`, which is no longer in this repository. A Lovelace resource pointing at it is removed automatically, and dashboards still using `custom:worx-map-rtk-card` keep showing the map, now drawn by the new card.

*If your Lovelace resources are managed in YAML, the integration never writes to them: add `/worx_vision_cloud_frontend/worx-vision-card.js` as a `module` resource yourself.*

**[landroid-card](https://github.com/Barma-lej/landroid-card)** by Barma-lej also works with these entities, if you prefer a card shared across mower and vacuum brands. Point its `camera:` option at the RTK map camera to show the map inside it.

The `lawn_mower` entity deliberately has no name of its own, so it displays exactly the device name, and it stays available through connectivity blips rather than going unavailable. Both are for cards like landroid-card, which use it as the label prefix for every other entity and blank their body when it is unavailable. Only commands are blocked while genuinely offline, with a clear error.

## RTK Map & Address

For Vision Cloud / RTK mowers, a camera entity renders the boundary, excluded areas, station, the day's mowing trail and the robot turned to its heading as SVG from the private Worx map endpoint. It is not a video stream: it updates when new data arrives. The trail covers the full local day like the Worx app, resets at local midnight, survives a restart, and keeps the last known map if a fetch briefly fails.

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
- On a Vision mower, one-time mowing takes no runtime, as in the Worx app: the mower mows the chosen zones through. Start resumes everything the mower still has to mow, every unfinished zone included, like the app's play button, so use one-time mowing to send it to given zones. A command sent while the mower is not talking to the cloud is lost, not queued: a zone job the mower does not acknowledge is checked against its next report and sent once more only if it did not start, and a repair issue says so if the second attempt does not start either.
- Mower home time and charging time can read `0` permanently for some accounts, because the API does not populate them for every model. Both sensors are disabled by default; enable them if your account reports real values.

## Credits

- Uses [`pyworxcloud`](https://github.com/MTrab/pyworxcloud).
- Integration originally prepared by Smart Service.
