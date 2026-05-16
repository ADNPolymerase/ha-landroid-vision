# Worx Vision Cloud PLUS

Custom Home Assistant integration for Worx Landroid Vision / Vision Cloud / RTK mowers.

This integration is built on top of the community `pyworxcloud` library and adds a cleaner Home Assistant entity layer for Vision mowers: mower controls, useful sensors, diagnostics, schedule calendar, RTK map rendering and live-ish robot position tracking.

Integration prepared by **Smart Service**.

## Support

If this integration helps you, you can support Smart Service:

[Donate via Revolut](https://revolut.me/smartserwis)

## Features

- Native Home Assistant `lawn_mower` entity.
- Start, pause and dock commands.
- Battery, status, error and connectivity sensors.
- Useful maintenance and diagnostic sensors.
- Schedule sensor and Home Assistant calendar entity.
- RTK map camera rendered from the Worx private map API.
- RTK robot position as a `device_tracker`.
- Optional RTK address sensor using OpenStreetMap Nominatim reverse geocoding, disabled by default.
- Daily mowing progress, remaining progress and mowed area sensors when available from the API.
- Smart mowing schedule blueprint driven by grass growth, lawn area and weather sensors.
- Polish and English translations.
- Optional raw payload entities for debugging, disabled by default.

## Installation With HACS

1. Open HACS.
2. Add this repository as a custom repository.
3. Select category `Integration`.
4. Install **Worx Vision Cloud PLUS**.
5. Restart Home Assistant.
6. Go to `Settings > Devices & services > Add integration`.
7. Search for `Worx Vision Cloud PLUS`.

## Manual Installation

Copy this directory:

```text
custom_components/worx_vision_cloud
```

to your Home Assistant config directory:

```text
/config/custom_components/worx_vision_cloud
```

Then restart Home Assistant and add the integration from `Settings > Devices & services`.

## Configuration

Use the same e-mail and password as in the Worx Landroid app.

Supported cloud selector values:

- `worx`
- `kress`
- `landxcape`

Most users should keep SSL verification enabled.

## Entities

The exact entity list depends on what your mower reports. Typical entities include:

- `lawn_mower` mower control
- `button` refresh
- `calendar` mowing schedule
- `camera` RTK map
- `device_tracker` RTK robot position
- `sensor` battery, status, error, RSSI, schedule, rain delay, RTK map, daily progress, remaining progress, mowed area, runtime and maintenance values
- `binary_sensor` online, locked, charging, rain, party mode and pause mode

See [docs/entities.md](docs/entities.md) for a more detailed list.

## Smart Mowing Schedule

The repository includes a Home Assistant automation blueprint for an intelligent mower schedule:

[![Open your Home Assistant instance and import this blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FSmartServicePL%2Fworx_vision_cloud_plus_github%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fworx_vision_cloud_plus%2Fsmart_mowing_schedule.yaml)

```text
blueprints/automation/worx_vision_cloud_plus/smart_mowing_schedule.yaml
```

It estimates grass growth from garden temperature, rain/weather, optional soil moisture and sunlight/UV, then chooses mowing runtime from the lawn area and selected WORX mower model. You can use normal Home Assistant sensors or a `weather` entity; 24 h statistics sensors are optional for better accuracy. If there is no soil moisture probe, the blueprint estimates virtual soil moisture from rain and temperature. An optional `input_datetime` helper can show the next calculated mowing slot on a dashboard. See [docs/smart-mowing-schedule.md](docs/smart-mowing-schedule.md) for setup and tuning notes.

Disable the mowing schedule in the WORX app before using this blueprint, so Home Assistant is the only scheduler controlling mower starts.

## RTK Map

For compatible Vision Cloud / RTK mowers the integration tries to read the private Worx map endpoint and renders a Home Assistant camera entity as SVG.

The map can include:

- mowing boundary
- excluded areas
- markers and station information when available
- current robot position from RTK payload

The map is not a video stream. It updates when Home Assistant receives new data from Worx Cloud or when the integration refreshes cached API data.

## RTK Address

The integration includes a disabled-by-default `RTK address` sensor. When enabled, it reverse-geocodes the mower's rounded RTK coordinates with OpenStreetMap Nominatim and caches the result for 24 hours.

Enable this entity only if you accept sending approximate mower coordinates to the reverse-geocoding provider. This is intentionally opt-in because RTK coordinates can reveal a home or garden location. Lookups are rounded, cached and throttled to respect the public Nominatim service.

## Privacy

RTK maps and address lookups can contain precise garden geometry and coordinates. Do not publish debug dumps, Home Assistant storage files, access tokens, serial numbers, raw API responses or screenshots showing exact locations.

Before opening an issue, remove private data from logs and screenshots. See [SECURITY.md](SECURITY.md).

## Limitations

The Worx / Positec cloud API is not officially public. Some endpoints used here are reverse-engineered and can change without notice. This is a best-effort custom integration, not official Worx software.

## Credits

- Uses [`pyworxcloud`](https://github.com/MTrab/pyworxcloud).
- Integration prepared by **Smart Service**.
