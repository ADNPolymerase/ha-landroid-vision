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


Home Assistant integration for Worx Landroid Vision, Vision Cloud and RTK mowers, built on [`pyworxcloud`](https://github.com/MTrab/pyworxcloud), with its own dashboard card.

> 🇫🇷 [Lire en français](README.fr.md)

## Features

- `lawn_mower` entity: start, pause, dock, one-time mowing and edge cutting.
- One-time zone mowing as in the Worx app: zones, fixed or automatic order, edge routine. Also as the `worx_vision_cloud.start_zone_mowing` action, for automations.
- Each RTK zone's mowing pattern and angle, read only.
- Mower settings: lock, schedule, smart edge cut, save the hedgehogs, party mode, rain delay, and cutting height, torque, off limits or ACS when the mower has them.
- Daily mowed area and progress kept by the integration, plus a local estimate that keeps moving when the Worx statistics lag.
- Schedule sensor and calendar with each slot's zones, RTK map camera with the day's trail, robot position.
- Status, error, readiness, battery and maintenance sensors, with Repairs alerts for blade and battery service and for a mower stopped away from its base.
- Diagnostics with coordinates and identifiers redacted. 11 languages.

See [docs/entities.md](docs/entities.md) for the full entity list.

## Installation

In HACS, search for `Worx Landroid Vision PLUS`, download it, restart Home Assistant, then add the integration in `Settings > Devices & services`. Sign in with your mower app's e-mail and password and pick your brand's cloud: `worx`, `kress` or `landxcape`.

Without HACS, copy `custom_components/worx_vision_cloud` into `/config/custom_components/` and restart.

## Card

The integration ships the **Worx Landroid Vision** card and registers it itself: reload the browser and pick it in the card list.

```yaml
type: custom:worx-vision-card
entity: lawn_mower.your_mower
```

It shows the detailed state (searching a zone, crossing a border...), battery and Wi-Fi, error and rain banners, party mode, start, pause and dock, the RTK map with the day's estimated progress as a thin bar under it, one-time zone mowing, the weekly schedule and the blade time with its reset. One-time mowing stays folded on one line, with its settings summed up and Start on the right; unfold it to pick the zones, the order and the edge cut. The last settings are remembered in the browser. A click on a value opens its history. Only `entity` is needed: the card finds the rest of the mower by itself. Optional: `title`, `show_info`, `show_controls`, `show_map`, `show_zones`, `show_schedule`, `show_blades`, `show_values` (battery % and Wi-Fi dBm next to their icons) and `refresh_interval` (map, in seconds). Battery and Wi-Fi turn green, orange or red with their level. On an older Landroid, it shows the state, the controls and the schedule.

*With Lovelace resources in YAML, add `/worx_vision_cloud_frontend/worx-vision-card.js` as a `module` resource yourself.*

[landroid-card](https://github.com/Barma-lej/landroid-card) by Barma-lej works with these entities too.

## Good to know

- The RTK map and coordinates are precise: don't publish dumps or screenshots showing them. The address sensor is off by default. See [SECURITY.md](SECURITY.md).
- Mowed area is covered area, so overlapping passes can exceed the lawn size. The cloud publishes a session late, sometimes the next day: the estimate sensors follow the current day.
- A Vision one-time job takes no duration. Start resumes every unfinished zone, like the app's play button. A command sent while the mower sleeps is lost: a zone job is checked and sent once more, and a Repairs alert says so if it still does not start.
- The Worx cloud API is not public and can change without notice. This is not official Worx software.

## Credits

Uses [`pyworxcloud`](https://github.com/MTrab/pyworxcloud). Originally prepared by Smart Service.
