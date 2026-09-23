# Changelog

## 2.8.1 - 2026-09-23

### Added

- **Each RTK zone's mowing pattern and angle.** Two sensors per mowing zone, named after it as in the Worx app: the pattern (natural, parallel, diamond or checker) and the angle in degrees. Both names start the same way, "Mowing pattern" and "Mowing pattern angle", so a zone's settings sit together in the device's sensor list rather than the angles being sorted apart. They are read from the mower's own per-zone config, which it updates once a change made in the app is activated, so they show what the mower will actually mow, zone by zone, whether the zones share the same settings or not. A pattern code not named yet reads `other`, with the code in the `code` attribute. Display only: the settings are still changed in the Worx app.

### Changed

- **No One-time mowing runtime on a Vision mower.** Since 2.8.0 a Vision mower's one-time job carries no duration, as in the Worx app, so the runtime number did nothing there. It is no longer created for a Vision mower, and removed from an existing setup. Older mowers keep it.
- **Diagnostics show how the RTK map identifies its zones**, without any of its geometry. Each zone now includes the plain fields of its `summary`, and a new `rtk_map_layout` section describes the map's structure: identifiers, types and names are kept, lists of points are reduced to their length, and any key naming a position is redacted.

### Fixed

- **The Start zone mowing button stayed on the device page, greyed out, after 2.8.0 removed it.** Its leftover registry entry is now removed on setup. Start one-time mowing does the same job.

## 2.8.0 - 2026-09-23

### Added

- **Send the mower to the zones you pick, the way the Worx app does it.** Watched live on Vision firmware 3.46.0+47 with pyworxcloud's MQTT log at debug level, the app's one-time mowing is `cmd` 1 with a top-level `cut` block: the zones, whether their order is imposed, and the edge routine. The mower answers by creating a new task on those zones, which replaces any task it had on hold, and mows them through before going home. The new `worx_vision_cloud.start_zone_mowing` action sends exactly that: `zones` in mowing order, `zone_order` (`fixed`, the app's Special mode, or `auto`) and `edge_cut`. An automation calling it at a given time is how to schedule a zone job.
  - There is no duration, as in the app. The mower estimates the time left per zone itself, and a zone it had started keeps its progress: sending it back to a half-mowed zone finishes that zone rather than mowing it again. A zone it had already finished is mowed again.
  - **A job the mower does not acknowledge is checked, then sent once more if needed.** Docked and charged, a Vision mower sleeps and only listens for a moment every five to seven minutes, and a command sent in between is lost, not queued: it happened twice in one afternoon while the Worx app showed the mower online. A missing answer does not always mean a lost job, though: seen live, the mower created the task two seconds after the command while its first report only came a minute later. So when no answer comes, the mower's next report is read first, and the job counts as received if its task list shows it. Only if it does not is the job sent a second time, as soon as the mower reports in, or after 15 minutes at most. If that one does not show up either, a repair issue says the job did not start, and it clears on the next zone job the mower acknowledges. The action no longer fails on the first miss, so an automation that schedules a zone job is not stopped by a sleeping mower.

### Changed

- **One-time mowing on a Vision mower is now the app's one-time mowing.** The action and the Start one-time mowing button send the command above, with the zones picked, or every zone of the map when none is, and the edge cut setting. Until now they sent the schedule's `once` block with a runtime: the mower turned it into a task that kept the zones of whatever task it had on hold, so a job sent after an interrupted slot mowed the front lawn when the back had been asked for. The runtime is ignored on a Vision mower, as the app no longer offers one; older mowers still run for the chosen time.
- **On-demand edge cutting on a Vision mower sends `cmd` 101 directly**, instead of going through one-time mowing with a zero runtime.
- **The weekly schedule sensor is readable at a glance.** A week of ten slots read as `Mon 08:00-12:30, Mon 14:00-18:00, Tue 08:00-12:30, Tue 14:00-18:00, Wed ...`, one entry per slot, with the day repeated every time and nothing to tell one day from the next. It now reads `Mon 08:00-12:30, 14:00-18:00 · Tue 08:00-12:30, 14:00-18:00 · Wed 08:00-12:30`: the day is written once, its time ranges follow, and a middle dot separates the days so the eye finds them without reading the whole line. A day whose slots are scattered through the list is gathered into one block rather than appearing twice.
  - When every slot of a day cuts the edge, the marker is written once for the day instead of after each range, which is what the mower reports in practice since the Worx app sends the same edge value to all slots.
  - Two new attributes carry what a single line never will: `by_day` groups the slots per day, each with its own text and its zones, so a markdown card can lay the week out one day per line; `text` holds the whole week whatever its length. A state is capped at 255 characters, and a long week used to fall back to "10 active slots" and lose the schedule entirely; `text` keeps it.
- **The five capability sensors now read as capabilities.** "Random mowing pattern supported" was read as a setting rather than as what the mower is able to do, which it is: the state comes from the capability list the Worx cloud publishes for the model, and says nothing about the pattern actually in use. They now lead with the support, as Polish and Russian already did: "Supports random mowing pattern", "Supports map training", and so on, in the nine other languages.

### Fixed

- **The current zone sensor flickered to `unknown` while the mower was mowing.** An RTK position drifts outside its zone for a few seconds when the mower hugs a contour, and crossing the corridor between two areas takes under a minute; both read `unknown`, which broke the history into unreadable pieces. Seen live on one morning: seven gaps, most of them between four and twenty seconds, in the middle of normal mowing. The last known zone is now held for up to 30 seconds before the sensor gives up, and the `held_last_known` attribute says when the state is held rather than measured.
  - Past those 30 seconds the sensor reads `unknown` again. A real trip between two areas takes minutes, and naming a zone for that long would be worse than saying nothing.
  - Docking needs no special case: a charging station sits inside a mowing zone, so the live lookup names it like any other position.

### Notes

- The 2.8.x test builds that came before this release ran zone jobs as a temporary weekly slot, on the belief that the firmware ignored the zones of a one-time job. It does not: the zones were lost to the task on hold. And the slots never took effect either: a bare schedule write was never applied in three attempts, and the variant sent with `cmd` 0 was never confirmed. That mechanism is gone, and the store it kept in Home Assistant is deleted on setup so no stale schedule can ever be written back.

## 2.7.2 - 2026-09-22

### Fixed

- **The error sensor read `unknown` for nearly every real error.** It looked the error text up in the table of mower statuses, which holds no error at all, so only "no error" and "rain delay" ever came through. A mower lifted, trapped, upside down or with a camera error showed `unknown`, with the real error hidden in an attribute. Seen live: a mower lifted to check its blades read `unknown` for four minutes. The sensor now maps the error id to one of 42 named errors, in the eleven supported languages, and reads `other_error` for an id it does not know. It is keyed on the id rather than the text, because pyworxcloud describes the most recent Vision and RTK errors (calibration needed, unsupported blade height, manual firmware update required, area limit exceeded, undocking error) as "unknown" while still passing their id.

## 2.7.1 - 2026-09-22

### Fixed

- **The mowing calendar filled every week it was asked for, years back and years ahead.** The schedule repeats weekly, and the calendar generated an occurrence for each slot across whatever range the calendar view requested, so browsing months or opening a long list view showed a schedule that never existed in the past and may not exist in the future. It now only publishes occurrences from one week before today to one week after.

### Added

- **An option to set that calendar window**, from 1 to 90 days before and after today, in the integration options. The current or next mowing event used by the calendar entity state is not affected.

## 2.7.0 - 2026-09-21

### Added

- **The zones of each weekly slot are now visible.** The Worx app lets a slot be limited to some zones, in an imposed order or not, and Vision firmware honours it. None of that reached Home Assistant: pyworxcloud drops the cut block of a slot, so the schedule sensor and the calendar only knew day, time, duration and edge cut. Each slot is now matched to its raw twin on day and start time, and carries:
  - `zones`: the zone ids, in the order set in the app;
  - `zone_names`: the same zones by the names given in the app;
  - `zone_order`: `ordered` when the order was imposed (the app's Special mode), `auto` when the mower picks it.

  They are in the `slots` attribute of the schedule sensor, for cards and templates. Calendar events name the zones in their title, "Mowing: Back lawn, Front lawn", and state the order in their description, so the Home Assistant calendar shows the week as the app does. Protocol 1 mowers only; other mowers read `None`.

### Fixed

- **The schedule sensor and the calendar were only in English, German, French and Polish**, while the README announced eleven languages for both. Dutch, Spanish, Italian, Swedish, Norwegian, Danish and Russian users got English day names and event text. All eleven languages are now covered, zone labels included.

## 2.6.2 - 2026-09-21

First stable release since 2.5.1. It carries everything from the 2.6.0 and 2.6.1 pre-releases: the five mower statuses that used to read `unknown`, and the full cut block sent for a one-time job.

### Documentation

- **Zones now have a verified answer.** Tested on a Vision Cloud mower, firmware 3.46.0+47:
  - **A weekly schedule slot honours its zones, order included.** A slot set in the Worx app to zone 2 then zone 1 left the base, reported "searching zone" while it crossed zone 1 without cutting, went through the corridor, and only started mowing once in zone 2.
  - **A one-time job ignores them.** The same mower, sent the exact cut block the app writes to that slot, mowed its usual area. Status "searching zone" never appeared. Nothing in the shape of the request is left to change, so the selection is dropped by the firmware for this kind of job.
  - The 2.5.0 claim that slot zones are honoured was right, but the evidence given at the time proved nothing and it was withdrawn in 2.5.1. It is restored here, with a real test behind it.
- To mow a given zone today, set it on a weekly schedule slot in the Worx app. The README and the zones field description, in the eleven supported languages, now say so. The one-time zone list is still sent, in case a later firmware reads it.

## 2.6.1 - 2026-09-21

### Changed

- **The one-time cut block now carries the over border field, like every block the mower accepts.** Three dumps of the same Vision Cloud mower, taken either side of a change made in the Worx app, show one rule without exception: a slot with the edge cut on carries no `ob` at all, a slot with it off always carries `ob: 0`. What this integration sent was an edge cut turned off and no `ob`, a shape the app never writes, and the default for a one-time job is exactly that. It is now the most likely reason a selected zone looked ignored. The block sent for a one-time job is now identical in shape to a weekly slot the firmware already accepts.

### Documentation

- **Corrected the reasoning published in 2.6.0 about the zone order flag.** It claimed the flag is what tells the firmware the zone list is a restriction rather than the whole lawn. That is wrong: the app's automatic mode carries a restricted list too, seen live on a slot holding a single zone with the flag at 0. The flag only says whether an order was imposed. Sending it is still correct, and it is what makes the list order meaningful, but it does not explain an ignored selection. Zone selection remains experimental and unconfirmed.

## 2.6.0 - 2026-09-21

### Added

- **Five mower statuses that used to read `unknown`.** A Vision or RTK mower reports `searching zone` while it drives to a zone without cutting, `searching home`, `zoning`, `border crossing` and `exploring lawn`, and none of them had a mapping, so the status sensor went blank during perfectly normal operation. `searching zone` is the one seen on any zone targeted job, which made a zone run unreadable from start to finish. All five are now states of their own, in the eleven supported languages. Same class of gap as status 33 in 2.4.0, and wider than it looked.

### Changed

- **One-time mowing now sends the zone selection the way the Worx app writes it.** Reading the raw weekly schedule of a Vision Cloud mower showed that the app never sends a zone list on its own: it pairs it with a second field that says whether the list is a deliberate ordered selection or simply means the whole lawn. A slot left on the app's automatic setting still carries every zone in the list, so the list alone decides nothing and the firmware reads the flag to know. Earlier releases sent the list without it, which reads as "mow everything" and is the most likely reason a selected zone looked ignored while the same job started from the app reached its zone. The flag is now sent, set from whether a selection was made.
- **The zone list is ordered.** The first id is mowed first, matching the order the app lets you set. The `zones` field of the `worx_vision_cloud.start_one_time_mowing` action takes the order as given; the zone picker entity keeps offering combinations in id order.

### Documentation

- Zone selection stays marked experimental. Sending that flag is a hypothesis built on what the app writes to the weekly schedule, tested against nothing yet. The README says so rather than claiming a fix.

## 2.5.1 - 2026-09-20

### Fixed

- **The SIM card ICCID and IMSI appeared in clear in downloaded diagnostics.** A mower with a 4G module reports both inside `module_status`, and the redaction list matches key names, so the account level `sim` entry never reached them. Anyone attaching a diagnostics file to an issue was publishing the identifiers of their SIM. Both are now redacted, in either spelling. Same class of leak as the PIN code fixed in 2.4.0: if you have shared a diagnostics file from a 4G mower, those identifiers are out.

### Documentation

- **Withdrawn: the 2.5.0 claim that zones attached to a weekly schedule slot are honoured by the firmware.** The mower it rested on carried every zone on every slot, so nothing was ever restricted and nothing was proven. A slot limited to a single zone is now under observation. Until there is a result, the README, this changelog and the zones field description in all eleven languages state only what has actually been seen: that the one-time selection is ignored, and that zones can also be set per slot in the Worx app.

## 2.5.0 - 2026-09-20

### Added

- **Diagnostics now carry the raw `cfg.sc` schedule block.** The parsed schedule this integration reads keeps only day, start, duration and border cut: pyworxcloud normalizes slots and drops every field it does not model, which on RTK mowers means the zone list attached to each weekly slot and the whole one-time job block. Neither was reachable anywhere, not in the schedule sensor, not in the calendar, not even in a downloaded diagnostics file, so a zone set per slot in the Worx app was invisible here. The raw block is now included next to the parsed one, verbatim.

### Documentation

- **Zones attached to a weekly schedule slot are honoured by Vision firmware, only the one-time selection is ignored.** Verified on 3.46.0+47: a mower whose weekly slots carry a zone list mows the zone of the running slot, while the same zone passed to a one-time job is ignored. The 2.4.0 notes concluded from unchanged diagnostics that the Worx app must reach a one-time zone through a separate cloud route. That conclusion does not hold: the diagnostics compared could not show zones at all, so the comparison proved nothing either way. How the app runs a one-time job in a chosen zone is open again.

## 2.4.0 - 2026-09-16

### Added

- **A repair issue when the mower is left stopped away from its base.** A Vision mower whose STOP button is pressed in the field, for example by an obstacle holding it down, reports a plain idle status with no error. It then sits there until the battery runs flat, with nothing in Home Assistant pointing at it. After 10 minutes stopped, not charging and more than 1 m from the station, a Repairs issue now says so, and it clears itself once the mower moves or charges again. Observed live: a mower wedged under a shelter next to its station drained from 51 % to 7 % in 80 minutes without a single alert.

### Fixed

- **The mower PIN code appeared in clear in downloaded diagnostics.** Anyone attaching a diagnostics file to an issue was publishing it. It is now redacted like the other personal fields. If you have shared a diagnostics file before, consider changing the PIN in the Worx app.
- The status sensor read `unknown` while the mower drives to a zone picked in the Worx app. That phase, status 33, now shows as its own state, "Heading to zone".
- A mower stopped by its STOP button made the `lawn_mower` entity read `unknown`. It now reads paused.
- The connectivity sensors granted a fresh grace period after every Home Assistant restart, so a mower that had been offline for hours showed as connected again for 30 minutes. The start of an ongoing disconnection now survives a restart.
- The current zone sensor showed the name of a corridor, such as "1", while the mower crossed from one mowing area to another. Corridors carry no cutting settings and are now skipped.

### Documentation

- **Zone selection for one-time mowing is ignored by current Vision firmware.** Tested on 3.46.0+47: with a zone selected, the command is accepted but the mower mows its usual area. The same mowing started from the Worx app does go to the chosen zone, yet it changes nothing in the data this integration reads, so the app goes through a separate cloud route. The selection is now marked experimental in the README and in the action description.

## 2.3.1 - 2026-09-03

### Fixed

- **Stopped calling the deprecated `device_registry.async_get_device`.** Home Assistant deprecated it because device identifiers are no longer unique across config entries, and it was warning about both call sites on every start, with a deadline of Home Assistant 2027.8. The non-deprecated `async_get_device_by_identifier` is now used when available, keeping the old call as a fallback for the older Home Assistant versions still supported.
- Zone picker labels ("All zones", "Zone", "Zones") were translated into only four of the eleven languages the integration supports everywhere else. All eleven are now covered.

### Documentation

- Added a Cards section covering [landroid-card](https://github.com/Barma-lej/landroid-card) and the RTK map card bundled in this repository, which was not documented anywhere, and shortened the README.

## 2.3.0 - 2026-09-02

### Added

- **A `set_firmware_notes` action**, to attach release notes to a firmware version by hand. Worx publishes notes only while an update is pending, and its account portal can withdraw the catalogue entry of a build that has already shipped, so the notes of the firmware a mower is running can end up unrecoverable. They can now be pasted in from the portal, for the mower firmware, the vision head, or both. Recorded notes appear in the update dialog exactly like the ones captured automatically since 2.2.1.

### Documentation

- **An update that only touches the vision head is invisible to the integration.** Worx ships firmware as a pair, vision head and mower, but the upgrade endpoint reports availability by comparing mower versions alone. A new head build published against an unchanged mower version therefore raises no update at all, and the version the head is currently running is not exposed either. Both follow from the API rather than from this integration, and the Worx app remains the reference for head firmware. Observed live: a head build was republished against the same mower version and no update was reported.
- Documented why release notes disappear once an update is installed, and how to bring them back.

## 2.2.1 - 2026-09-02

### Fixed

- **Release notes stay readable after an update is installed.** Worx describes a firmware only while it is still on offer: once the mower runs it, the upgrade route answers 404 and the notes are gone for good. The 2.2.0 dialog was therefore empty again as soon as the update was applied. The notes of an offered firmware are now recorded as they go past, keyed by the version being offered, so that once that version is installed it can be looked up by the version the mower actually runs. Up to ten versions are kept per mower, and they survive a Home Assistant restart.
  - Known limitation: nothing can be recovered retroactively. The firmware a mower runs today has no notes, because they were not recorded when it was offered. The local history starts at the next update.
  - This is also why the release summary line is empty while a mower is up to date: it is built from the offered versions, which Worx stops sending.

### Removed

- The firmware catalogue probe shipped in the 2.2.1 pre-releases. It answered its question: the account portal lists the firmware history as server-rendered HTML behind its own login, not through the API the app uses, so there is no route to call. Its own control also showed that the upgrade route returns 404 once a mower is up to date, which is what made the fix above possible.

## 2.2.0 - 2026-09-01

Everything below comes from watching a real firmware update run end to end on a Vision Cloud400, from 3.46.0+40 to 3.46.0+47.

### Added

- **Commands are refused while the mower is installing a firmware update.** Worx asks that the mower stays on its charging station and is left alone for the whole update, so a command sent meanwhile reaches a device that is rewriting its own firmware. Start, pause, dock and every setting write now raise a clear error instead. The mower reports status 102 for the entire update, from the first byte downloaded until it has rebooted, which is what this relies on. If the status cannot be read or looks malformed the command is allowed through, so a corrupt reading cannot lock you out of your own mower.
  - Known limitation: the vision head is updated after the mower and its own phase is not reflected in the mower status. The Worx app still showed "restarting" while Home Assistant already reported the mower back on its dock, so the guard covers the mower phase only. Wait for the app to declare the update finished.
- **The update entity now reports progress.** Worx never sets any in-progress flag in its OTA payload, verified across a complete update, so the mower status is used instead.

### Fixed

- **The update dialog was empty.** Release notes were looked up at the top level of the OTA payload, but Worx nests them inside its `product` and `head` sections, keyed by language. The dialog now shows one section per component, titled with that component's version. Section titles follow the Home Assistant language in the eleven languages the integration already supports; the note text itself stays as Worx publishes it, which today means English only.
- **When Worx offers an update with no notes at all**, which is common, the dialog points at the Landroid app instead of showing nothing.
- The release summary line was read from keys Worx never fills, so it was always empty. It now lists the offered versions of both components, for example `Mower firmware 3.46.0+47 · Vision head firmware 2.5.7+12`. A real summary from Worx still takes priority if one ever appears.

## 2.1.0 - 2026-09-01

### Fixed

- **The firmware update entity reported "Up to date" while an update was pending.** Worx numbers its firmware as `3.46.0+40` and `3.46.0+47`. Semantic versioning treats everything after a plus sign as build metadata and requires it to be ignored when comparing precedence, so Home Assistant rated `3.46.0+47` as not newer than `3.46.0+40` and kept the entity off, even though the versions shown in its own dialog clearly differed. The versions handed to Home Assistant now use a dot instead of the plus sign, which restores the ordering without losing a single digit.
  - Side effect on display: the entity now shows `3.46.0.40` rather than `3.46.0+40`. Home Assistant compares the exact strings an update entity reports and its state property cannot be overridden, so this was the only way to make the comparison correct. The untouched values stay available as the `installed_version_reported` and `latest_version_reported` attributes.

### Added

- The firmware entity exposes `latest_head_version` and `latest_product_version`. The Worx app shows a pair such as `2.5.7+12 - 3.46.0+47`, the vision head first and the mower second. The OTA endpoint only reports the version the mower currently runs, so the entity tracks the mower firmware and these attributes make a pending head update visible too.
- The firmware entity exposes `installed_version_reported` and `latest_version_reported`, holding the versions exactly as Worx writes them.

## 2.0.1 - 2026-09-01

- The map camera reports its zone attributes correctly right after a restart. They were read only from the last rendered image, so `zone_count` and `mowing_zone_count` read 0 until something displayed the camera for the first time. The coordinator's cached map is now used as a fallback.
- Documented a caveat on daily attribution in the README: Today mowed area and Daily progress follow the moment Worx publishes a session, not the moment the mower mowed. Observed live: a session running from 14:02 to 17:54 was only published at 03:26 the next morning, so its 310 m² were credited to the following day. Total mowed area stays correct, and the locally computed estimate sensors track the current day as it happens.
- Documented how lawn area is derived, including the exclusion of transit zones.

## 2.0.0 - 2026-09-01

### Breaking changes

- **Zone picker labels changed.** The one-time mowing zone select now shows the zone names configured in the Worx app instead of generic numbering, so an option previously labelled `Zone 1` now reads with the name that zone has in the app, and a combination such as `Zones 1, 2` reads as the two names joined with a plus sign. Automations that call `select.select_option` with a literal `Zone 1` must be updated to the new label. The selection itself is stored by zone id, so what the mower will actually mow is unaffected, and zones fall back to their numeric label when no name can be resolved.
- **The Current zone sensor no longer reports `0` on Vision/RTK mowers.** It now resolves the real zone from the live map, so its state becomes a zone name. Conditions or templates comparing this sensor to `"0"` need revisiting. Zone `0` stays meaningful on older boundary-wire mowers, which have no map to resolve from.

### Changed values

These are not breaking by themselves, but the numbers move, so dashboards and history will show a step.

- **Lawn area** now sums the mowed zones of a multi-zone RTK map instead of reporting only the first one. On a real three-zone map this went from 305.45 m² to 339.15 m², matching the 339.1 m² the Worx app reports.
- **Daily progress, remaining progress and estimated progress** follow that corrected lawn area, so percentages drop slightly and stop hitting a false 100%. On the same map, a full day went from a capped 100% to a meaningful 99.7%.

### Added

- **Computed dock time** and **Computed error time** diagnostic sensors. Worx exposes lifetime home, charging and error counters but leaves them at 0 on some accounts and models (confirmed on both a WR143E and a Vision Cloud400 whose work-time counter updates normally), so these are measured locally and answer a different question: how long the mower has been in its current state. Each resets to 0 the moment the mower leaves that state, and both survive a Home Assistant restart because the start timestamps are persisted, so a mower docked for three hours still reads three hours after a restart. A restored timestamp is dropped as soon as the first refresh shows the mower is no longer in that state. Known trade-off: a full leave-and-return cycle happening while Home Assistant is down cannot be detected. Rain delay does not count as an error, being a normal waiting state rather than a fault.
- The map camera exposes explicit `current_zone_name`, `current_zone_area_m2`, `first_zone_name`, `first_zone_area_m2`, `first_zone_perimeter_m`, `zone_count` and `mowing_zone_count` attributes. The existing `zone_name`, `zone_area_m2` and `zone_perimeter_m` described the map's first zone despite their names suggesting the current one; they are kept unchanged so existing dashboards and templates keep working.
- Diagnostics include an RTK map zone summary: id, name, area, perimeter, available keys and contour count per zone, without any coordinates, so the dump stays safe to share. This makes transit zones visible when troubleshooting lawn-area figures.

### Fixed

- Mowed zones are identified by their cutting metadata (`cut_type` / `cut_direction`, mirroring the per-zone cutting config in `cfg.rtk.zs`), so transit corridors the mower only drives through are excluded from the lawn area. Maps without any cutting metadata keep the previous first-zone behaviour, and the cloud's own `lawn_size` still wins when the account provides one.
- Zone names are paired with zone ids on their cutting direction when every direction is distinct, and by map order otherwise. A name reused across zones gets its id appended so option labels stay unambiguous.
- Current zone resolution ported from upstream SmartServicePL 1.4.0.

## 1.13.0 - 2026-08-28

Now in the HACS default store, installable directly from HACS without adding a custom repository (hacs/default#9049, thanks @frenck for the review and merge).

- Localized the two placeholder strings rendered inside the map camera SVG ("No RTK map from the API" / "RTK map contains no points") in all 11 languages, resolved from the Home Assistant UI language with an English fallback. This was the follow-up point from the HACS review. They previously showed in English regardless of locale (and in Polish before 1.12.0).
- README: the installation section now covers both paths, the HACS default store (recommended) and a direct copy from the repository, and the HACS badge reflects the default-store status.

## 1.12.3 - 2026-08-22

- Rebuilt the brand logo from a vector source: the original 478×215 PNG was traced into an exact SVG (logo.svg at the repository root, single-color #EE7700, 27 contours), and both logo.png (478×215) and a genuine logo@2x.png (956×430, real double resolution rather than a copy) are now rendered from it with a transparent background. The previous PNG carried an opaque white background, which showed up as a white box on Home Assistant's dark theme; the new assets blend into both themes. Addresses the remaining brand-asset point from the HACS review.
- The icons now come from the same vector source (icon.svg at the repository root: the logo lockup centered in a square, same placement as before): icon.png (256) and icon@2x.png (512) are rendered transparent instead of on an opaque white square.
- Removed the three image copies at the integration root (icon.png, icon@2x.png, logo.png). Correction to the 1.12.2 note: Home Assistant's local brand serving reads the integration's brand/ directory (loader.has_branding checks for a brand folder, and the brands view resolves images inside it with its own dark/2x fallbacks), the same directory HACS validates, so the root copies were never read by anything. brand/ is now the single source of the served assets, alongside the two root-level files GitHub and HACS display for the repository itself.

## 1.12.2 - 2026-08-22

- Restored the brand/ directory inside the integration (icon.png, icon@2x.png, logo.png: genuine files only, no dark/2x placeholder copies): the 1.12.0 asset cleanup removed it, but HACS validation specifically requires custom_components/<domain>/brand/icon.png for repositories not listed in home-assistant/brands, which failed the HACS check on 1.12.0/1.12.1. The copies at the integration root remain: Home Assistant's local brand serving (HA 2026.3+) reads those, while HACS validation reads brand/; the two locations serve different consumers.

## 1.12.1 - 2026-08-22

- The 5-minute periodic refresh no longer pings mowers that are disabled in the Home Assistant device registry. A retired mower still registered on the Worx cloud account would time out on every ping (observed live: one MQTT "Timeout waiting for device response" warning every 5 minutes, ~288 per day, each tying up a worker for 30 seconds) even though all its entities are disabled and nothing consumes the data. The registry is checked live on each pass, so re-enabling the device resumes its refreshes within one cycle.

## 1.12.0 - 2026-08-22

Hardening pass following the HACS review of the store submission (thanks @frenck).

- Security: the start_one_time_mowing and set_rtk_map_id services now require admin privileges (async_register_admin_service): the first one starts the blades, the second rewrites persisted state.
- Security: the map_id service input is now strictly validated as a UUID, and the value is URL-quoted before being interpolated into the private Worx map API path, closing a path-injection vector.
- Localization: services.yaml no longer carries hard-coded Polish text: service names, descriptions and field labels now come from the translations (all 11 languages), and the two remaining Polish placeholder strings in the map camera SVG are gone.
- Consistency: the minimum Home Assistant version is now declared as 2026.3.0 everywhere (hacs.json and README): that has been the effective requirement since 1.6.1, when the bundled brand images started relying on HA 2026.3's local brand serving.
- Brand assets: removed 17 byte-identical placeholder files (fake dark_* variants and a fake logo@2x that were exact copies of the light/1x versions, plus two duplicated brand/ directories). The logo is a single-color orange mark that renders identically on light and dark themes, and Home Assistant falls back to the light/1x assets automatically, so nothing changes visually.

## 1.11.0 - 2026-08-13

- Made the maintenance thresholds configurable in the integration options (Settings > Devices & services > Worx Landroid Vision PLUS > Configure), and replaced the unrealistic hard-coded defaults inherited from the original integration. Blade service was flagged after only 12 hours of cutting (roughly 9 days of typical mowing) and now defaults to 100 hours, in line with real-world pivot blade life (a change every 6-8 weeks). Battery service was flagged at 500 charge cycles and now defaults to 800, the top of the rated cycle life for the Li-Ion chemistry Worx PowerShare packs use (500-800 cycles, 2-5 year replacement window). Both the maintenance sensor and the Repairs alerts follow the configured values, existing over-eager alerts clear automatically on upgrade, and the previous behavior can be restored by setting the old values in the options.

## 1.10.0 - 2026-08-09

- The connectivity sensors now react to pyworxcloud's MQTT connection events instead of waiting for the next data push or 5-minute refresh. Before this, a disconnection was only noticed on the next refresh (so the grace-period timestamp could start up to 5 minutes late, delaying a real outage's appearance to up to ~35 minutes with the default 30-minute grace), and a reconnection could keep showing as disconnected for a few minutes. Both edges are now picked up the moment the MQTT session state changes, with the event hopping from the MQTT thread onto the event loop before touching any entity state.

## 1.9.1 - 2026-08-04

- Fixed a thread-safety RuntimeError introduced in 1.9.0 (#2): the callback that flips a connectivity sensor right when the grace period expires was scheduled without the @callback decorator, so Home Assistant ran it in the executor thread pool instead of the event loop: logged as "calls async_write_ha_state from a thread other than the event loop" once per grace expiry. The state flip still happened within 5 minutes via the periodic refresh, so the visible impact was limited to log spam and a delayed flip. The callback now runs in the event loop as intended.

## 1.9.0 - 2026-07-31

- The Online and MQTT connected sensors no longer flood the logbook and recorder with connected/disconnected churn: short drops (AWS IoT reconnects, wifi blips, mower sleep) are now hidden behind a configurable grace period, and a disconnection only shows once it has lasted longer than that delay. Reconnection always shows immediately. The delay is a new integration option (Settings > Devices & services > Worx Landroid Vision PLUS > Configure), default 30 minutes, one shared setting for both sensors: set it to 0 to keep the old live behavior. For automations that still want to react instantly, both sensors expose the raw state in a live_connected attribute plus a disconnected_since timestamp. In-memory only: after a Home Assistant restart an already-offline mower gets one fresh grace period before showing as disconnected.

## 1.8.0 - 2026-07-28

Feature sync with upstream SmartServicePL 1.3.0/1.3.1, adapted to this fork's entity layer.

- Fixed the Current zone sensor staying unknown on Vision/RTK mowers: when the legacy Worx zone field is empty (common on these models), the sensor now resolves the mower's live RTK position against the map zone polygons (point-in-polygon, honoring exclusion holes) and reports the matching zone name, falling back to `Zone <id>` when the zone is unnamed. Attributes expose the resolution source (`legacy` vs `rtk_map`) alongside the legacy fields. Ships with unit tests.
- Made mower commands resilient to stale cloud sessions: the Worx MQTT connection is now checked and reconnected before edge-cut and one-time-mowing commands, with one automatic retry if the publish still hits a dead connection. The post-command state refresh is now best effort: an accepted command is no longer reported as failed just because the immediate refresh timed out.
- The Border distance select now shows the real configured value when the mower reports it back (newer Vision firmwares expose it in `cfg.cut.bd`/`co` and in per-zone cutting configs), and only falls back to the last value set through Home Assistant otherwise. A `source` attribute says which one you're looking at, and setting a distance updates the cached raw config immediately.
- Improved Smart edge cutting state detection on protocol 1 mowers: the switch (and its attributes) now also reads the per-zone cutting configs (`cfg.rtk.zs[].cfg.cut.ob` / `cfg.mz.s[].cfg.cut.ob`) instead of only the top-level flag and map metadata, and toggling it updates all zone configs in the cached state.
- Added five diagnostic capability sensors read from the Worx product item: PIN setting supported, Vision disable supported, random mowing pattern supported, map training supported and diagnostic upload supported. Status only for now: pyworxcloud does not expose safe control methods for these functions. Translated in all 11 languages.
- The schedule Time extension number now accepts 1% steps instead of 10% (allowed by pyworxcloud 6.4.2, already shipped in 1.7.1).

## 1.7.2 - 2026-07-27

- The "Cloud statistics updated" timestamp now only changes when the Worx product statistics actually change, instead of on every 5-minute poll. Observed live: ~236 recorder writes per day for a sensor that mostly repeated itself; it now only moves during mowing/charging activity. The polling cadence itself is unchanged -- only the sensor state updates are deduplicated.
- Removed the "Last update age" sensor. Its minute-counter state changed ~600 times per day in the recorder, and it duplicated what Home Assistant already renders for free from the "Last update" timestamp sensor ("5 minutes ago", refreshed in the UI without any database writes). The orphaned entity is cleaned from the registry automatically on upgrade; if you used it in an automation, trigger on the "Last update" timestamp instead.

## 1.7.1 - 2026-07-27

- Bumped pyworxcloud from 6.4.1 to 6.4.2. Upstream now decodes the GPS position natively from `dat.rtk.pos` for Vision/RTK mowers, and the `time_extension` step requirement was relaxed to 1 for finer mowing-time adjustments. No functional change in the integration itself; the native GPS decode opens the door to simplifying the map trail parsing in a future release.

## 1.7.0 - 2026-07-26

- Added a NearLink connection diagnostic sensor, contributed by @Razzertaz (#1). It exposes the mower's active NearLink peer as a translated enum state (Dock / RadioLink adapter / Disconnected / Unknown) with detailed attributes: NearLink module status and error, link RSSI, peer MAC and firmware, and robot/peer Wi-Fi status and RSSI. The sensor is only created for mowers whose payload actually reports an `NL` module, the private payload is parsed defensively, and the type→peer mapping (1 = dock, 2 = RadioLink adapter) is a best-effort mapping live-validated on a WR342E with a WA0900 adapter: unknown future peer types show as Unknown while keeping the raw type in attributes. Ships with translations in all 11 languages and unit tests.

## 1.6.4 - 2026-07-10

- Fixed the map camera still rendering only the last 120 trail points despite the full-day trail introduced in 1.6.2. The coordinator kept (and persisted) the whole day correctly, but the camera's trail accessor had a leftover `max_points=120` default from the old rolling-window design, so the start of the trail silently slid out of the rendered map as the mower kept adding points: visible as the morning's mowing disappearing from the card during the afternoon. The accessor now returns the full day's trail by default.

## 1.6.3 - 2026-07-09

- Added a set_rtk_map_id service to manually seed or correct the cached RTK map id when Worx doesn't resend it promptly (observed live: it can go quiet for a long stretch, even during active mowing with a good GPS fix). The last known value can be recovered from the RTK map sensor's own state history and set through this service to unblock the map camera and the lawn-area-dependent sensors immediately, without waiting for Worx's cloud to cooperate.
- Persisted the RTK map id cache to Home Assistant storage, so the map camera and RTK map sensor no longer need to wait for the mower to send a fresh cfg payload with the rtk block after a restart (observed: docked/idle mowers can go a while without one, only sending it again once mowing resumes). The stored value is a single short string per mower and only gets written when it actually changes, so this stays tiny over time rather than accumulating.
- Added Russian translation.
- Fixed the RTK map camera and sensor going unavailable/unknown again after
  several hours, even without any restart. The 1.6.2 fix compared the
  coordinator's "previous" device object against the newly pushed one to
  restore a missing rtk block, but pyworxcloud reuses and mutates a single
  DeviceHandler instance per mower in place, so those two references were
  actually the same object: there was never a real "before" snapshot to
  restore from once pyworxcloud itself had already overwritten the rtk
  block with a partial cfg push. Replaced with an independent last-known-id
  cache on the coordinator, decoupled entirely from pyworxcloud's own
  object graph, used by both the camera and the RTK map sensor.

## 1.6.2 - 2026-07-08

- Fixed WorxMowingTimeTodaySensor being registered twice in async_setup_entry, which logged "Platform worx_vision_cloud does not generate unique IDs" and silently dropped the duplicate at startup.
- The RTK trail shown on the map camera now covers the full local day like the Worx app, instead of a fixed 6-hour window capped at 300 in-memory points: it resets at local midnight instead, is persisted so a Home Assistant restart mid-day doesn't lose the morning's trail, and a generous per-day point cap replaces the old rolling window so a long mowing day no longer silently evicts its own earlier segments.
- Fixed the primary lawn_mower entity (and third-party cards built on it, such as landroid-card) going fully unavailable/blank whenever the mower lost wifi. Availability no longer depends on the mower's own online flag, so the last known status/activity keeps showing during a connectivity blip instead of the whole card collapsing to a bare "not available" placeholder. `online` stays available as a state attribute, and start/pause/dock commands sent while offline now fail with a clear error instead of being silently blocked by Home Assistant.
- Fixed the RTK map camera going unavailable, and the lawn area, daily
  progress, remaining progress and estimated daily progress sensors going
  unknown, whenever Worx sent a partial MQTT config update that momentarily
  omitted the RTK block. The coordinator now preserves the last known RTK
  map id and zones across such partial updates instead of losing them, the
  same way it already preserved REST-derived data.
- Fixed the map camera rendering a blank image on a fetch failure instead
  of keeping the last successfully rendered map.
- Fixed a related bug where a missing RTK map id was converted to the
  literal string "None" before being sent to the coordinator, which passed
  validation and fired a needless request against the private Worx map API
  (visible in logs as repeated 404s).

## 1.6.1 - 2026-07-07

- Rebranding release, no code changes: the official Landroid Vision logo is
  now used everywhere (README, HACS, and the Home Assistant UI through the
  bundled brand/ images served locally since HA 2026.3), with icons at the
  canonical 256/512 sizes.
- The integration title shown in the Home Assistant UI is now Worx Landroid
  Vision PLUS in all 10 languages, new pairings are titled Worx Landroid
  Vision (account e-mail), and existing entry titles are migrated
  automatically at startup.

## 1.6.0 - 2026-07-07

- Renamed the repository to `ADNPolymerase/ha-landroid-vision` and the
  integration display name to Worx Landroid Vision PLUS. GitHub redirects
  the old repository name and HACS tracks installations by repository ID,
  so existing installs are unaffected; the `worx_vision_cloud` domain and
  all entity IDs are unchanged.
- Added Home Assistant Repairs integration: when the blade cutting time or
  battery charge cycles exceed the maintenance thresholds (12 h / 500
  cycles, the same ones the maintenance sensor uses), an actionable issue
  appears in Settings > Repairs and clears automatically after the matching
  reset button is pressed. Mowers disabled in the device registry never
  raise repairs.
- Added a Border distance select (50/100/150/200 mm) for Vision mowers.
  The Worx API accepts writing this setting but never reports it back, so
  the entity is optimistic: it shows the last value set through Home
  Assistant (persisted across restarts) and stays unknown until used once.
- Fixed the Next schedule sensor going unknown on Vision protocol 1 mowers:
  pyworxcloud reports `schedules["active"]` as False on these models even
  while the weekly schedule genuinely runs, so the inactive flag now only
  suppresses the sensor when the library offers no future start either. The
  library timestamp parser also accepts offset-aware values
  (e.g. `2026-07-08 08:00:00+02:00`) and datetime objects, both observed on
  real devices.
- Added a Restart mower button (diagnostic) to reboot the mower baseboard
  remotely when it is stuck.
- Added an MQTT connected diagnostic binary sensor exposing the live push
  connection state, complementing the registration-only MQTT registered
  sensor.
- Moved the daily area/progress baselines and the local mowing-time counter
  from per-entity restored state into a coordinator-level tracker persisted in
  Home Assistant storage (synced back from upstream SmartServicePL 1.2.0):
  every daily sensor now shares one baseline per mower, survives entity
  renames, and handles cloud counter resets and multi-day gaps without
  attributing several days of mowing to today.
- Added a Mowing time today sensor exposing the locally observed mowing
  minutes the estimated sensors are computed from.
- Added a Cloud statistics updated diagnostic timestamp showing when the
  cumulative Worx REST statistics were last fetched.
- Mowing efficiency now prefers blade-active time over total mower runtime
  (which includes driving and idling), improving the estimated daily figures.
- Next schedule now returns nothing while the native schedule is disabled or
  party mode is active, ignores stale library values, and looks up to 14 days
  ahead (synced from upstream 1.2.0).
- Added Download diagnostics support with automatic redaction of coordinates,
  addresses and account/device identifiers, for safe GitHub issue reports.
- Device names no longer repeat the account e-mail, the account e-mail is no
  longer suggested as a Home Assistant area (existing e-mail areas are
  detached automatically), and entity IDs that inherited the e-mail prefix
  are migrated (synced from upstream 1.2.0).
- Entities removed by the 1.5.0 consolidation are now cleaned from the entity
  registry automatically instead of lingering as restored orphans.
- Removed the deprecated device-tracker battery_level property override while
  keeping the value as a state attribute, preventing a Home Assistant 2027.7
  break (synced from upstream 1.2.0).
- Passed the config entry explicitly to the coordinator for Home Assistant
  2026.8 compatibility (synced from upstream 1.2.0).
- Added unit tests for the daily statistics tracker and next-schedule
  calculation, now run by the validation workflow.
- The release workflow is manual-only so code pushes can never silently
  re-tag the current stable release.

## 1.5.0 - 2026-07-06

- Added a party mode switch (previously only a read-only sensor).
- Added ACS, off limits, cutting height and torque controls, gated on pyworxcloud's live per-device capability detection instead of a manual model list, so they only appear when your mower reports the matching hardware module.
- Removed entities that duplicated the same value as both a switch and a read-only binary sensor: lock, smart edge cutting, save the hedgehogs and party mode. Also removed a duplicate rain delay sensor that repeated the existing rain delay number.
- Fixed rain delay, cutting height and torque numbers showing a spurious decimal (e.g. `180.0` instead of `180`).
- Disabled the torque number and the mower home time / charging time sensors by default: torque is an advanced setting most users won't touch, and home/charging time can permanently read `0` on accounts where the Worx API doesn't populate those two fields (mower work time is unaffected and still updates normally).
- Off limits and ACS entities can legitimately show as `unavailable` on a supported mower until the corresponding module shows up in the mower's live data; for off limits this can require configuring at least one off-limit zone once in the Worx app. This is a data limitation of the underlying API, not a bug (the community `landroid_cloud` integration has the same behavior).

## 1.0.11 - 2026-06-18

- Allowed the one-time mowing service to accept `runtime: 0`, so automations can explicitly start an edge-only pass after normal mowing.
- Updated the Home Assistant service description to show `runtime: 0` as the supported edge-only mode.
- Mapped Vision Cloud `runtime: 0` with `edge_cut: true` to the dedicated edge-cut command (`cmd: 101`), while keeping normal one-time mowing on the app-like `cmd: 10` payload.

## 1.0.10 - 2026-06-17

- Changed Vision one-time mowing with edge cutting back to the app-like one-time mowing payload (`cmd: 10` with `cfg.cut.b: 1`) so the mower performs normal mowing first and edge cutting at the end instead of doing an edge-only run.

## 1.0.9 - 2026-06-13

- Changed Vision one-time mowing with edge cutting and no selected zones to use the firmware command that starts edge cutting followed by the normal mowing cycle.
- Kept the standalone edge-cut button edge-only by continuing to use the zero-minute one-time mowing command for that button.

## 1.0.8 - 2026-06-12

- Added the official HACS validation workflow required for default HACS repository submissions.
- Updated HACS repository metadata so the integration passes the current HACS Action checks.

## 1.0.7 - 2026-06-12

- Removed RTK-based status overriding so mower state always follows the raw Worx Cloud status.
- Kept RTK station proximity as diagnostic attributes for automations without changing the displayed mower status.
- Allowed the one-time mowing service to run for 1 minute so automations can send a short status-refresh command when Worx Cloud gets stuck.
- Increased RTK address reverse-geocoding precision to 7 decimal places and kept the address based only on RTK coordinates.

## 1.0.6 - 2026-06-11

- Improved the RTK map trail so recent mower movement is rendered as a darker mowed grass swath instead of a thin GPS line.
- Calculated the mowed swath width from the mower model cutting width and the current map scale; WR308E/WR303E-class mowers use 18 cm.
- Clipped the mowed swath to the lawn contour so it stays inside the mapped grass area.

## 1.0.5 - 2026-06-11

- Added RTK station-based status correction so Home Assistant can show the mower as docked when Worx Cloud is stuck on stale mowing/returning/searching-home states.
- Preserved cached RTK map and product details across MQTT-only push updates so status correction keeps access to the base station marker.
- Changed the Vision edge-cut button to send a zero-minute one-time schedule with edge cutting enabled instead of `cmd:101`, because firmware 3.46.x can continue into full mowing after `cmd:101`.
- Added one-time mowing controls and service with runtime, edge-cut and optional RTK zone selection.
- Added a robot-lifted binary sensor based on Worx Cloud `lifted` and `upside down` error states.
- Removed the unavailable schedule edge procedure entities.
- Removed the radio link validation pending binary sensor.
- Removed the duplicate read-only lawn perimeter sensor.
- Added Polish state labels for the status and mowing-readiness sensors.

## 1.0.4

- Fixed the edge cutting button for Vision mowers whose Worx Cloud schedule payload does not expose the derived edge-cut capability.
- The integration now sends the border-cut MQTT command directly instead of relying on `pyworxcloud.edgecut()`, which could silently do nothing.

## 1.0.3

- Removed the `auto_schedule` switch completely.
- Added entity-registry cleanup for the removed automatic schedule switch.

## 1.0.2

- Removed the unreliable battery charging binary sensor.
- Removed the unreliable distance covered sensor.
- Added entity-registry cleanup for both removed entities.

## 1.0.1

- Fixed mower command refresh for `pyworxcloud==6.3.6` by removing an unsupported `timeout` argument from device update requests.
- Restored button and mower commands that previously failed with `WorxCloud.update() got an unexpected keyword argument 'timeout'`.

## 1.0.0

- Promoted the integration to the first stable `1.0.0` release.
- Added a native Home Assistant firmware update entity with release notes and OTA install support when exposed by Worx Cloud.
- Added configurable rain delay, schedule time-extension, lawn area and lawn perimeter number entities.
- Added switches for firmware auto update, mower lock, native schedule and Worx auto schedule.
- Added cloud/MQTT diagnostics, mowing-readiness status, API capabilities and push notification state sensors.
- Added extended mowing statistics: lawn area/perimeter, distance covered, efficiency and mower time at home, charging and in error.
- Added maintenance tracking for blade runtime and battery cycles, including reset timestamps and a battery cycle reset button.
- Added recent RTK trail storage, a diagnostic trail sensor and a trail overlay on the RTK map camera.

## 0.3.5

- Added an on-demand edge cutting button that starts the mower in border-only cutting mode.

## 0.3.4

- Added root-level `icon.png` and `logo.png` compatibility files so HACS can resolve the repository image in places that do not read `brand/icon.png`.
- Updated the release workflow to publish icon-only fixes.

## 0.3.3

- Added Home Assistant switches for Smart edge cutting, Save the hedgehogs and schedule edge procedure.
- Renamed the Polish rain binary sensor label to `Czujnik opadów deszczu`.
- Removed the standard total driven distance sensor because the Worx payload does not update it reliably.
- Added entity-registry cleanup for the removed total driven distance sensor.
- Added integration-root icon and logo files so Home Assistant and HACS update cards can resolve the brand image more reliably.

## 0.3.2

- Moved Smart mowing schedule blueprint to a separate automation repository.
- Updated documentation to link to the separated automation repository.

## 0.3.1

- Added Smart mowing schedule Home Assistant blueprint.
- Added My Home Assistant import button for the blueprint.
- Added blueprint setup documentation and optional helper package example.

## 0.3.0

- Added diagnostic entities for Smart edge cutting, Save the hedgehogs and schedule edge procedure API fields.
- Added button to reset blade runtime after blade replacement.

## 0.2.2

- Added root-level HACS brand assets so the repository icon appears in HACS.

## 0.2.1

- Updated integration brand icon and logo assets.

## 0.2.0

- Added disabled-by-default RTK address sensor using OpenStreetMap Nominatim reverse geocoding.
- Added 24-hour address lookup cache, rounded-coordinate lookups and a one-request-per-second geocoding throttle.

## 0.1.0

- Initial public release.
- Added Home Assistant `lawn_mower` support.
- Added useful sensors and binary sensors.
- Added mowing schedule sensor and calendar entity.
- Added RTK map camera rendered from Worx map API data.
- Added RTK position `device_tracker`.
- Added daily progress, remaining progress and mowed area sensors when available.
- Added Polish and English translations.
- Added integration icon and Smart Service attribution.
