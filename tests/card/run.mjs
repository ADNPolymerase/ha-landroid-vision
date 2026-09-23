process.env.TZ = "UTC";
/**
 * Tests for custom_components/worx_vision_cloud/worx-vision-card.js.
 * Run: node tests/card/run.mjs   (WORX_CARD=/path/to/other.js to test another build)
 * All names below are fictional.
 */
import { loadCard, markup, check, contains, report, freezeClock } from "./harness.mjs";
import { fileURLToPath, pathToFileURL } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const CARD = process.env.WORX_CARD
  || path.join(here, "..", "..", "custom_components", "worx_vision_cloud", "worx-vision-card.js");

// Timers only matter in the browser; keep the process from waiting on them.
globalThis.setInterval = () => 0;
globalThis.clearInterval = () => {};
globalThis.setTimeout = () => 0;
globalThis.clearTimeout = () => {};

const registry = await loadCard(pathToFileURL(CARD).href);
const Card = registry.get("worx-vision-card");
const Editor = registry.get("worx-vision-card-editor");

// ── fixtures ────────────────────────────────────────────────────────────────

const D = "worx_vision_cloud";
function reg(entity_id, device_id, translation_key, platform = D) {
  return { entity_id, device_id, translation_key, platform };
}
function st(state, attributes = {}) {
  return { state, attributes };
}

function makeHass(overrides = {}) {
  const calls = [];
  const hass = {
    language: "en",
    locale: { language: "en" },
    calls,
    callService: async (domain, service, data, target) => {
      calls.push({ domain, service, data, target });
      if (hass.failNext) { hass.failNext = false; throw new Error("boom"); }
    },
    formatEntityState: (s) => `F(${s.state})`,
    devices: { dev1: { name: "Robot One" }, dev2: { name: "Old Robot" } },
    entities: {
      // Same device, other integration, listed first: must be ignored.
      "sensor.robot_other_status": reg("sensor.robot_other_status", "dev1", "status", "other"),
      // A zone key on something that is not a sensor: must be ignored.
      "number.robot_odd": reg("number.robot_odd", "dev1", "zone_mowing_angle"),
      // Renamed, localized ids on purpose: the card must never read them.
      "lawn_mower.robot": reg("lawn_mower.robot", "dev1", undefined),
      "sensor.robot_etat": reg("sensor.robot_etat", "dev1", "status"),
      "sensor.robot_bat": reg("sensor.robot_bat", "dev1", "battery_percent"),
      "sensor.robot_ici": reg("sensor.robot_ici", "dev1", "zone_current"),
      "camera.robot_carte": reg("camera.robot_carte", "dev1", "rtk_map_camera"),
      "select.robot_zones": reg("select.robot_zones", "dev1", "one_time_mowing_zones"),
      "sensor.robot_p_back": reg("sensor.robot_p_back", "dev1", "zone_mowing_pattern"),
      "sensor.robot_a_back": reg("sensor.robot_a_back", "dev1", "zone_mowing_angle"),
      "sensor.robot_p_front": reg("sensor.robot_p_front", "dev1", "zone_mowing_pattern"),
      "sensor.robot_a_front": reg("sensor.robot_a_front", "dev1", "zone_mowing_angle"),
      "calendar.robot_schedule": reg("calendar.robot_schedule", "dev1", "status"),
      "sensor.robot_wifi": reg("sensor.robot_wifi", "dev1", "rssi"),
      "sensor.robot_apte": reg("sensor.robot_apte", "dev1", "mowing_readiness"),
      "sensor.robot_err": reg("sensor.robot_err", "dev1", "error"),
      "sensor.robot_prog": reg("sensor.robot_prog", "dev1", "schedule"),
      "calendar.robot_prog": reg("calendar.robot_prog", "dev1", "schedule"),
      "sensor.robot_next": reg("sensor.robot_next", "dev1", "next_schedule"),
      "sensor.old_prog": reg("sensor.old_prog", "dev2", "schedule"),
      "sensor.robot_maint": reg("sensor.robot_maint", "dev1", "maintenance_status"),
      "switch.robot_fete": reg("switch.robot_fete", "dev1", "party_mode"),
      "sensor.robot_lames": reg("sensor.robot_lames", "dev1", "blade_runtime_current"),
      "button.robot_reset_blades": reg("button.robot_reset_blades", "dev1", "reset_blade_counter"),
      "sensor.robot_pluie": reg("sensor.robot_pluie", "dev1", "rain_remaining"),
      "sensor.robot_avance": reg("sensor.robot_avance", "dev1", "estimated_daily_progress"),
      "number.robot_delai": reg("number.robot_delai", "dev1", "rain_delay_minutes"),
      // Other mower's zone: must not leak into dev1's list.
      "sensor.old_p": reg("sensor.old_p", "dev4", "zone_mowing_pattern"),
      "lawn_mower.old": reg("lawn_mower.old", "dev2", undefined),
      "sensor.old_status": reg("sensor.old_status", "dev2", "status"),
      "sensor.old_bat": reg("sensor.old_bat", "dev2", "battery_percent"),
      "camera.old_map": reg("camera.old_map", "dev2", "rtk_map_camera"),
      "lawn_mower.foreign": reg("lawn_mower.foreign", "dev3", undefined, "husqvarna"),
    },
    states: {
      "lawn_mower.robot": st("docked", { supported_features: 7, friendly_name: "Robot One" }),
      "sensor.robot_etat": st("searching_zone"),
      "sensor.robot_bat": st("80", { charging: true }),
      "sensor.robot_ici": st("Front lawn"),
      "camera.robot_carte": st("idle", { entity_picture: "/api/camera_proxy/camera.robot_carte?token=abc" }),
      "select.robot_zones": st("Back lawn", { available_zone_ids: [1, 2], selected_zone_ids: [2] }),
      "sensor.robot_p_back": st("parallel", { zone_id: 2, zone_name: "Back lawn" }),
      "sensor.robot_a_back": st("314", { zone_id: 2, zone_name: "Back lawn" }),
      "sensor.robot_p_front": st("diamond", { zone_id: 1, zone_name: "Front <b>lawn</b>" }),
      "sensor.robot_a_front": st("342", { zone_id: 1, zone_name: "Front <b>lawn</b>" }),
      "calendar.robot_schedule": st("off"),
      "sensor.robot_wifi": st("-81"),
      "sensor.robot_apte": st("ready"),
      "sensor.robot_err": st("no_error"),
      "sensor.robot_prog": st("Mon 08:00-12:30", { by_day: [
        { day: "monday", day_label: "Mon", slots: [
          { start: "08:00", end: "12:30", zone_names: ["Back lawn", "Front lawn"], zone_order: "ordered", boundary: true },
          { start: "14:00", end: "18:00", zone_names: ["Front lawn"], zone_order: "auto", boundary: false },
        ] },
        { day: "wednesday", day_label: "Wed", slots: [{ start: "09:00", end: "10:00", zone_names: null, zone_order: null, boundary: false }] },
      ] }),
      "calendar.robot_prog": st("off", { message: "CALENDAR_DECOY" }),
      "sensor.robot_next": st("2026-01-01T06:00:00+00:00"),
      "sensor.old_prog": st("", { by_day: [] }),
      "sensor.robot_maint": st("ok", {
        blade_runtime_since_reset: 227, blade_service_threshold_minutes: 6000,
        blade_runtime_reset_at: "2026-01-10T04:11:30+00:00", battery_cycles_since_reset: 10,
      }),
      "button.robot_reset_blades": st("unknown"),
      "switch.robot_fete": st("off"),
      "sensor.robot_lames": st("380", { unit_of_measurement: "min" }),
      "sensor.robot_pluie": st("0", { unit_of_measurement: "min" }),
      "sensor.robot_avance": st("62.4", { unit_of_measurement: "%" }),
      "number.robot_delai": st("180", { unit_of_measurement: "min" }),
      "number.robot_odd": st("7", { zone_id: 5, zone_name: "Odd" }),
      "sensor.robot_other_status": st("WRONG_STATUS"),
      "sensor.old_p": st("checker", { zone_id: 9, zone_name: "Elsewhere" }),
      "lawn_mower.old": st("mowing", { supported_features: 7 }),
      "sensor.old_status": st("mowing"),
      "sensor.old_bat": st("15", { charging: false }),
      "camera.old_map": st("unavailable"),
      "lawn_mower.foreign": st("docked"),
    },
    ...overrides,
  };
  return hass;
}

function make(config, hass = makeHass()) {
  const card = new Card();
  // Lovelace freezes the stored config: the card must survive that.
  card.setConfig(Object.freeze({ refresh_interval: 0, ...config }));
  card.hass = hass;
  return card;
}

function click(card, dataset) {
  card._onClick({ composedPath: () => [{ dataset }] });
}

const flush = () => new Promise((r) => setImmediate(r));

// ── entity discovery ────────────────────────────────────────────────────────

{
  const hass = makeHass();
  const ents = Card.resolveEntities(hass, "lawn_mower.robot");
  check("status found by translation_key", ents.status, "sensor.robot_etat");
  check("battery found by translation_key", ents.battery, "sensor.robot_bat");
  check("current zone found", ents.zoneCurrent, "sensor.robot_ici");
  check("camera found", ents.camera, "camera.robot_carte");
  check("zones sorted by id, own device only", ents.zones.map((z) => z.id).join(","), "1,2");
  check("zone 2 pattern entity", ents.zones[1].pattern, "sensor.robot_p_back");
  check("zone 1 angle entity", ents.zones[0].angle, "sensor.robot_a_front");
  check("non-worx entity is rejected", Card.resolveEntities(hass, "lawn_mower.foreign"), null);
  const fromCamera = Card.resolveEntities(hass, "camera.robot_carte");
  check("mower reached from the camera", fromCamera.mower, "lawn_mower.robot");
  const stub = Card.getStubConfig(hass);
  check("stub config picks a worx mower", stub.entity.startsWith("lawn_mower.") && hass.entities[stub.entity].platform === D, true);
}

{
  const hass = makeHass();
  hass.states["sensor.robot_p_back"] = st("unavailable", {});
  hass.states["sensor.robot_a_back"] = st("unavailable", {});
  const ents = Card.resolveEntities(hass, "lawn_mower.robot");
  check("zone kept from available_zone_ids when its sensors are down", ents.zones.map((z) => z.id).join(","), "1,2");
}

// ── rendering ───────────────────────────────────────────────────────────────

{
  const card = make({ entity: "lawn_mower.robot" });
  const html = markup(card);
  contains("title from the device name", html, "Robot One");
  contains("detailed status, translated", html, "F(searching_zone)");
  contains("current zone next to it", html, 'F(searching_zone)</span> · <span class="link" data-action="more-info" data-entity="sensor.robot_ici" role="button" tabindex="0">Front lawn</span>');
  check("status of another integration ignored", html.includes("WRONG_STATUS"), false);
  contains("battery shown", html, "80 %");
  contains("charging shown", html, "charging");
  check("zone pattern no longer shown", html.includes("F(parallel)"), false);
  check("zone angle no longer shown", html.includes("314°"), false);
  check("one-time mowing folded by default", html.includes('class="zone-chips"'), false);
  contains("folded row says what to do", html, '<span class="zones-summary">Tick at least one zone</span>');
  click(card, { action: "zones-toggle" });
  const open = markup(card);
  contains("unfolded on a click", open, 'data-action="zones-toggle" aria-expanded="true"');
  contains("zones as side-by-side chips", open, 'class="zone-chips"><button class="zone-chip"');
  contains("full zone name kept as a tooltip", open, 'title="Front &lt;b&gt;lawn&lt;/b&gt;"');
  contains("zone name escaped", open, "Front &lt;b&gt;lawn&lt;/b&gt;");
  check("no raw html from a zone name when open", open.includes("<b>lawn"), false);
  check("no raw html from a zone name", html.includes("<b>lawn"), false);
  contains("map image from the camera", html, "/api/camera_proxy/camera.robot_carte?token=abc&amp;worx_vision=");
  check("other mower's zone absent", html.includes("Elsewhere"), false);
  check("no undefined in markup", html.includes("undefined"), false);
  contains("start enabled while docked", html, 'data-service="start_mowing">');
  contains("dock disabled while docked", html, 'data-service="dock" disabled');
  contains("pause disabled while docked", html, 'data-service="pause" disabled');
  contains("go disabled with nothing ticked, and says why", html, 'data-action="go" title="Tick at least one zone" disabled');
  check("no hint line under the buttons any more", html.includes('<div class="notice">'), false);
  contains("hint to tick a zone", html, "Tick at least one zone");
}

{
  // Old Landroid, protocol 0: no zones, no RTK map. Clean and useful.
  const card = make({ entity: "lawn_mower.old" });
  const html = markup(card);
  contains("old mower: status", html, "F(mowing)");
  check("old mower: no zone section", html.includes('class="zones"'), false);
  check("old mower: no zone list", html.includes("One-time mowing"), false);
  contains("old mower: map unavailable text", html, "RTK map unavailable");
  contains("old mower: low battery flagged", html, "battery link low");
  contains("old mower: pause enabled while mowing", html, 'data-service="pause">');
  check("old mower: no undefined", html.includes("undefined"), false);
}

{
  const card = make({ entity: "lawn_mower.robot", show_map: false, show_zones: false, show_controls: false });
  const html = markup(card);
  check("show_map false hides the map", html.includes("<img"), false);
  check("show_zones false hides zones", html.includes('class="zones"'), false);
  check("show_controls false hides controls", html.includes('class="controls"'), false);
}

{
  const card = make({ entity: "lawn_mower.robot", show_controls: false });
  const html = markup(card);
  check("no zone picker without controls", html.includes('class="zones"'), false);
  check("no zone checkboxes without controls", html.includes('data-action="zone"'), false);
}

{
  // Old worx-map-rtk-card configs point at the camera and want the map.
  const card = new (registry.get("worx-map-rtk-card"))();
  card.setConfig(Object.freeze({ entity: "camera.robot_carte", refresh_interval: 0 }));
  card.hass = makeHass();
  const html = markup(card);
  contains("legacy element renders the map", html, "worx_vision=");
  check("legacy element has no controls", html.includes('class="controls"'), false);
  check("legacy element has no zone picker", html.includes('data-action="zone"'), false);
}

{
  const card = make({ entity: "lawn_mower.missing" });
  contains("missing entity reported", markup(card), "Entity not found");
  const card2 = make({ entity: "lawn_mower.foreign" });
  contains("foreign mower reported", markup(card2), "Worx Landroid Vision PLUS");
  let threw = false;
  try { new Card().setConfig(Object.freeze({})); } catch (_e) { threw = true; }
  check("entity is required", threw, true);
}

// ── info chips and schedule ─────────────────────────────────────────────────

{
  const hass = makeHass();
  const card = make({ entity: "lawn_mower.robot" }, hass);
  let html = markup(card);
  contains("wifi shown in dBm", html, "-81 dBm");
  contains("weak wifi flagged", html, 'class="wifi link weak" title="Wi-Fi"');
  contains("wifi sits in the corner with the battery", html, '<div class="corner"><div class="wifi link weak"');
  check("wifi is no longer a chip", html.includes('class="chip warn" title="Wi-Fi"'), false);
  contains("readiness shown, translated", html, "F(ready)");
  contains("ready is green", html, 'class="chip link good"');
  check("no error chip without an error", html.includes("chip bad"), false);
  contains("schedule header", html, "Schedule");
  contains("next mowing in the header", html, "Next : F(2026-01-01T06:00:00+00:00)");
  check("schedule folded by default", html.includes("08:00-12:30"), false);
  click(card, { action: "schedule" });
  html = markup(card);
  contains("unfolds on click", html, 'aria-expanded="true"');
  contains("day label", html, ">Mon<");
  contains("slot time", html, "08:00-12:30");
  contains("slot zones, order and edge", html, "Back lawn, Front lawn · Special · Edge cut");
  contains("auto order shown for zoned slot", html, "Front lawn · Auto");
  contains("slot without zones stays clean", html, '09:00-10:00</span><span class="slot-extra"></span>');
  check("calendar with the same key ignored", html.includes("CALENDAR_DECOY"), false);
  const changed = makeHass();
  changed.states["sensor.robot_prog"] = st("Mon 08:00-12:30", { by_day: [
    { day: "monday", day_label: "Mon", slots: [
      { start: "07:15", end: "08:00", zone_names: ["<i>Odd</i>"], zone_order: "auto", boundary: false },
    ] },
  ] });
  card.hass = changed;
  html = markup(card);
  contains("new week from the cloud shown although the state text is the same", html, "07:15-08:00");
  contains("zone name escaped in the schedule", html, "&lt;i&gt;Odd&lt;/i&gt;");
  card.hass = hass;
  click(card, { action: "schedule" });
  check("folds back", markup(card).includes("08:00-12:30"), false);

  hass.states["sensor.robot_err"] = st("lifted");
  hass.states["sensor.robot_apte"] = st("battery_low");
  hass.states["sensor.robot_wifi"] = st("-55");
  card.hass = { ...hass };
  html = markup(card);
  contains("error banner when there is one", html, 'class="error-banner link"');
  contains("error translated in the banner", html, '<div class="error-title">F(lifted)</div>');
  check("no error chip any more", html.includes("chip link bad"), false);
  contains("not ready is orange", html, 'class="chip link warn" data-action="more-info" data-entity="sensor.robot_apte" role="button" tabindex="0"><ha-icon icon="mdi:alert-outline"');
  contains("strong wifi", html, "mdi:wifi-strength-4");
}

{
  const card = make({ entity: "lawn_mower.old" });
  click(card, { action: "schedule" });
  contains("empty week says so", markup(card), "No mowing slot");
  const off = make({ entity: "lawn_mower.robot", show_info: false, show_schedule: false });
  check("show_info false hides chips", markup(off).includes('class="chips"'), false);
  check("show_info false hides the wifi too", markup(off).includes('class="wifi'), false);
  check("show_schedule false hides schedule", markup(off).includes('class="schedule"'), false);
}

// ── current slot ────────────────────────────────────────────────────────────

{
  const hass = makeHass();
  // 2026-01-12 is a Monday; the fixture's Monday has 08:00-12:30 and 14:00-18:00.
  hass.states["calendar.robot_prog"] = st("on", {
    start_time: "2026-01-12 08:00:00", end_time: "2026-01-12 12:30:00", message: "Mowing",
  });
  const card = make({ entity: "lawn_mower.robot" }, hass);
  let html = markup(card);
  contains("current slot instead of the next one", html, "Current slot: 08:00-12:30");
  check("next mowing not shown during a slot", html.includes("Next :"), false);
  check("current slot is not clickable", html.includes('data-entity="calendar.robot_prog"'), false);
  click(card, { action: "schedule" });
  html = markup(card);
  contains("the running slot is highlighted", html, '<div class="slot current"><span class="slot-time">08:00-12:30');
  check("only that slot is highlighted", html.split("slot current").length - 1, 1);

  const afternoon = makeHass();
  afternoon.states["calendar.robot_prog"] = st("on", {
    start_time: "2026-01-12 14:00:00", end_time: "2026-01-12 18:00:00",
  });
  const pm = make({ entity: "lawn_mower.robot" }, afternoon);
  click(pm, { action: "schedule" });
  contains("afternoon slot highlighted, not the morning one", markup(pm), '<div class="slot current"><span class="slot-time">14:00-18:00');

  const otherDay = makeHass();
  otherDay.states["calendar.robot_prog"] = st("on", {
    start_time: "2026-01-14 08:00:00", end_time: "2026-01-14 12:30:00",
  });
  const wed = make({ entity: "lawn_mower.robot" }, otherDay);
  click(wed, { action: "schedule" });
  check("a Wednesday slot does not light up Monday's", markup(wed).includes('slot current"><span class="slot-time">08:00-12:30'), false);

  const off = markup(make({ entity: "lawn_mower.robot" }));
  contains("outside a slot, the next mowing", off, "Next : F(2026-01-01T06:00:00+00:00)");
  // An idle calendar still carries the NEXT slot's times, as seen live.
  const idle = makeHass();
  idle.states["calendar.robot_prog"] = st("off", {
    start_time: "2026-01-15 08:00:00", end_time: "2026-01-15 12:30:00",
  });
  const idleHtml = markup(make({ entity: "lawn_mower.robot" }, idle));
  check("an idle calendar's upcoming slot is not called current", idleHtml.includes("Current slot"), false);
  contains("an idle calendar leaves the next mowing", idleHtml, "Next : F(");
  const broken = makeHass();
  broken.states["calendar.robot_prog"] = st("on", { start_time: "soon" });
  contains("unreadable calendar falls back to next", markup(make({ entity: "lawn_mower.robot" }, broken)), "Next : F(");
  const fr = makeHass({ language: "fr", locale: { language: "fr" } });
  fr.states["calendar.robot_prog"] = hass.states["calendar.robot_prog"];
  contains("French wording", markup(make({ entity: "lawn_mower.robot" }, fr)), "Créneau en cours : 08:00-12:30");
}

// ── party mode ──────────────────────────────────────────────────────────────

{
  const hass = makeHass();
  const card = make({ entity: "lawn_mower.robot" }, hass);
  let html = markup(card);
  contains("party button under the battery", html, '</div><button class="party" data-action="party" aria-pressed="false">');
  check("no party banner while off", html.includes('class="party-banner'), false);
  click(card, { action: "party" });
  await flush();
  check("off: a click turns party mode on", `${hass.calls[0]?.domain}.${hass.calls[0]?.service}`, "switch.turn_on");
  check("the party switch is targeted", hass.calls[0]?.target?.entity_id, "switch.robot_fete");

  const on = makeHass();
  on.states["switch.robot_fete"] = st("on");
  const onCard = make({ entity: "lawn_mower.robot" }, on);
  html = markup(onCard);
  contains("button shows it is on", html, 'class="party on" data-action="party" aria-pressed="true"');
  contains("banner says the mower stays home", html, "Party mode: the mower will not go out, even during the schedule.");
  contains("party banner shown", html, '<div class="party-banner"><ha-icon');
  check("party banner is not clickable", html.includes('data-entity="switch.robot_fete"'), false);
  click(onCard, { action: "party" });
  await flush();
  check("on: a click turns party mode off", on.calls[0]?.service, "turn_off");

  const fr = makeHass({ language: "fr", locale: { language: "fr" } });
  fr.states["switch.robot_fete"] = st("on");
  contains("French banner", markup(make({ entity: "lawn_mower.robot" }, fr)), "Mode festif : la tondeuse ne sortira pas, même pendant le programme.");

  const noCtl = markup(make({ entity: "lawn_mower.robot", show_controls: false }, on));
  check("no party button without controls", noCtl.includes('data-action="party"'), false);
  contains("banner still shown without controls", noCtl, 'class="party-banner');
  check("no banner with show_info off", markup(make({ entity: "lawn_mower.robot", show_info: false }, on)).includes('class="party-banner'), false);

  const down = makeHass();
  down.states["switch.robot_fete"] = st("unavailable");
  const downCard = make({ entity: "lawn_mower.robot" }, down);
  contains("button disabled while the switch is unavailable", markup(downCard), 'data-action="party" aria-pressed="false" disabled');
  click(downCard, { action: "party" });
  await flush();
  check("an unavailable switch is not toggled", down.calls.length, 0);
  check("old mower without party mode shows no button", markup(make({ entity: "lawn_mower.old" })).includes('data-action="party"'), false);
}

// ── error banner ────────────────────────────────────────────────────────────

{
  freezeClock("2026-01-15T19:16:00Z");
  const hass = makeHass();
  hass.states["sensor.robot_err"] = { state: "trapped_timeout", attributes: {}, last_changed: "2026-01-15T17:11:00Z" };
  const card = make({ entity: "lawn_mower.robot" }, hass);
  const html = markup(card);
  contains("banner says since when, in the language's clock", html, "Since 05:11 PM · 2 h 05 ago");
  const h24 = makeHass({ locale: { language: "en", time_format: "24" } });
  h24.states["sensor.robot_err"] = hass.states["sensor.robot_err"];
  contains("24-hour clock from the user profile", markup(make({ entity: "lawn_mower.robot" }, h24)), "Since 17:11 · 2 h 05 ago");
  check("banner comes right under the header", html.indexOf('class="error-banner') < html.indexOf('class="controls"'), true);
  contains("banner opens the error history", html, 'class="error-banner link" data-action="more-info" data-entity="sensor.robot_err"');
  const fr = makeHass({ language: "fr", locale: { language: "fr" } });
  fr.states["sensor.robot_err"] = { state: "trapped_timeout", attributes: {}, last_changed: "2026-01-15T19:04:00Z" };
  contains("banner in French, minutes under an hour", markup(make({ entity: "lawn_mower.robot" }, fr)), "Depuis 19:04 · il y a 12 min");
  const none = markup(make({ entity: "lawn_mower.robot" }));
  check("no banner without an error", none.includes('class="error-banner'), false);
  const off = makeHass();
  off.states["sensor.robot_err"] = st("unavailable");
  const dup = makeHass();
  dup.states["sensor.robot_err"] = { state: "lifted", attributes: {}, last_changed: "2026-01-15T19:00:00Z" };
  dup.states["sensor.robot_apte"] = st("error");
  const dupHtml = markup(make({ entity: "lawn_mower.robot" }, dup));
  check("readiness 'error' not repeated under the banner", dupHtml.includes("F(error)"), false);
  dup.states["sensor.robot_apte"] = st("battery_low");
  contains("another readiness still shows with the banner", markup(make({ entity: "lawn_mower.robot" }, dup)), "F(battery_low)");
  check("no banner when the error sensor is unavailable", markup(make({ entity: "lawn_mower.robot" }, off)).includes('class="error-banner'), false);
}

// ── blades ──────────────────────────────────────────────────────────────────

{
  const hass = makeHass();
  const card = make({ entity: "lawn_mower.robot" }, hass);
  let html = markup(card);
  contains("current blade time, as the mower counts it", html, "Blades <b>6 h 20</b>");
  check("not the count since the integration's reset", html.includes("3 h 47"), false);
  contains("progress toward the service threshold", html, 'class="bar-fill good" style="width:6%"');
  contains("threshold and replacement date", html, "6 % of the service threshold (100 h) · replaced 01/10");
  check("blade time is not clickable", html.includes('data-entity="sensor.robot_maint"') || html.includes('data-entity="sensor.robot_lames"'), false);
  contains("reset button shown", html, 'data-action="reset-ask"');
  check("no confirmation yet", html.includes("reset-confirm"), false);

  click(card, { action: "reset-ask" });
  html = markup(card);
  contains("confirmation asked", html, "Reset the blade time to zero?");
  contains("confirmation says what is lost", html, "The current 6 h 20 will be lost.");
  check("nothing pressed on the first click", hass.calls.length, 0);
  check("reset button replaced by the confirmation", html.includes('data-action="reset-ask"'), false);

  click(card, { action: "reset-cancel" });
  check("cancel closes the confirmation", markup(card).includes("reset-confirm"), false);
  check("cancel presses nothing", hass.calls.length, 0);

  await card._confirmBladeReset();
  check("confirm without asking first presses nothing", hass.calls.length, 0);

  click(card, { action: "reset-ask" });
  await card._confirmBladeReset();
  const call = hass.calls[0];
  check("confirm presses the reset button", `${call?.domain}.${call?.service}`, "button.press");
  check("the integration's reset button is targeted", call?.target?.entity_id, "button.robot_reset_blades");
  check("confirmation closed after success", markup(card).includes("reset-confirm"), false);
  contains("success notice", markup(card), "Sent to the mower");
}

{
  const hass = makeHass();
  hass.states["sensor.robot_lames"] = st("5000", { unit_of_measurement: "min" });
  hass.states["sensor.robot_maint"] = st("blade_service_due", {
    blade_runtime_since_reset: 1, blade_service_threshold_minutes: 6000, blade_runtime_reset_at: null,
  });
  let html = markup(make({ entity: "lawn_mower.robot" }, hass));
  contains("orange past 80 %", html, 'class="bar-fill warn" style="width:83%"');
  check("no date when never reset", html.includes("replaced"), false);
  hass.states["sensor.robot_lames"] = st("7000", { unit_of_measurement: "min" });
  hass.states["sensor.robot_maint"] = st("blade_service_due", { blade_service_threshold_minutes: 6000 });
  html = markup(make({ entity: "lawn_mower.robot" }, hass));
  contains("red and capped at 100 %", html, 'class="bar-fill bad" style="width:100%"');

  const failing = makeHass();
  const card = make({ entity: "lawn_mower.robot" }, failing);
  click(card, { action: "reset-ask" });
  failing.failNext = true;
  await card._confirmBladeReset();
  contains("failure shown near the blades", markup(card), "Failed: boom");
  check("confirmation stays open after a failure", markup(card).includes("reset-confirm"), true);

  const noControls = markup(make({ entity: "lawn_mower.robot", show_controls: false }));
  contains("blade time still shown without controls", noControls, "<b>6 h 20</b>");
  const hours = makeHass();
  hours.states["sensor.robot_lames"] = st("6.3333", { unit_of_measurement: "h" });
  contains("a display unit in hours is converted back", markup(make({ entity: "lawn_mower.robot" }, hours)), "<b>6 h 20</b>");
  const odd = makeHass();
  odd.states["sensor.robot_lames"] = st("12", { unit_of_measurement: "weeks" });
  check("an unknown unit shows nothing rather than a wrong time", markup(make({ entity: "lawn_mower.robot" }, odd)).includes('class="blades"'), false);
  const noMaint = makeHass();
  delete noMaint.states["sensor.robot_maint"];
  const noMaintHtml = markup(make({ entity: "lawn_mower.robot" }, noMaint));
  contains("blade time without the maintenance sensor", noMaintHtml, "<b>6 h 20</b>");
  check("no bar without a threshold", noMaintHtml.includes('class="bar"'), false);
  check("no reset without controls", noControls.includes("reset-ask"), false);
  check("show_blades false hides the section", markup(make({ entity: "lawn_mower.robot", show_blades: false })).includes('class="blades"'), false);
  check("old mower without maintenance data shows no blades", markup(make({ entity: "lawn_mower.old" })).includes('class="blades"'), false);
}

// ── more-info on click ──────────────────────────────────────────────────────

{
  const card = make({ entity: "lawn_mower.robot" });
  const html = markup(card);
  const opens = (label, id) => {
    contains(`${label} is clickable`, html, `data-action="more-info" data-entity="${id}"`);
    card.events.length = 0;
    click(card, { action: "more-info", entity: id });
    const ev = card.events.at(-1);
    check(`${label} opens more-info`, ev?.type, "hass-more-info");
    check(`${label} more-info carries the entity`, ev?.detail?.entityId, id);
    check(`${label} more-info bubbles out of the shadow root`, ev?.bubbles && ev?.composed, true);
  };
  opens("title", "lawn_mower.robot");
  opens("state", "sensor.robot_etat");
  opens("current zone", "sensor.robot_ici");
  opens("battery", "sensor.robot_bat");
  opens("wifi", "sensor.robot_wifi");
  opens("readiness", "sensor.robot_apte");
  opens("map", "camera.robot_carte");
  check("next mowing is not clickable", html.includes('data-entity="sensor.robot_next"'), false);

  card.events.length = 0;
  click(card, { action: "more-info", entity: "sensor.does_not_exist" });
  check("unknown entity opens nothing", card.events.length, 0);
  const before = card._selected.length;
  check("more-info ticks no zone", card._selected.length, before);

  const hass = makeHass();
  hass.states["sensor.robot_err"] = st("lifted");
  const errCard = make({ entity: "lawn_mower.robot" }, hass);
  contains("error chip is clickable", markup(errCard), 'data-entity="sensor.robot_err"');
  hass.states["sensor.robot_etat"] = st("unavailable");
  const fallback = make({ entity: "lawn_mower.robot" }, hass);
  contains("state falls back to the mower's more-info", markup(fallback), 'data-entity="lawn_mower.robot" role="button" tabindex="0">F(docked)');
}

// ── one-time zone mowing ────────────────────────────────────────────────────

{
  const hass = makeHass();
  const card = make({ entity: "lawn_mower.robot" }, hass);
  click(card, { action: "zones-toggle" });
  click(card, { action: "zone", zone: "2" });
  click(card, { action: "zone", zone: "1" });
  let html = markup(card);
  contains("tick order shown as rank", html, 'aria-checked="true" data-action="zone" data-zone="2" title="Back lawn"><span class="check on" aria-hidden="true">1</span>');
  contains("second ticked zone ranked 2", html, 'data-zone="1" title="Front &lt;b&gt;lawn&lt;/b&gt;"><span class="check on" aria-hidden="true">2</span>');
  contains("go enabled once ticked", html, 'data-action="go" title="Start">');
  await card._startZones();
  check("one call", hass.calls.length, 1);
  const call = hass.calls[0];
  check("zone job domain", call.domain, D);
  check("zone job service", call.service, "start_zone_mowing");
  check("zones in tick order (Special)", JSON.stringify(call.data.zones), "[2,1]");
  check("order fixed", call.data.zone_order, "fixed");
  check("edge off by default", call.data.edge_cut, false);
  check("the lawn_mower entity is targeted", call.data.entity_id, "lawn_mower.robot");
  check("no duration is sent", "runtime" in call.data, false);
  contains("success notice", markup(card), "Sent to the mower");
  check("settings kept after success", card._selected.join(","), "2,1");
}

{
  const hass = makeHass();
  const card = make({ entity: "lawn_mower.robot" }, hass);
  click(card, { action: "zone", zone: "2" });
  click(card, { action: "zone", zone: "1" });
  click(card, { action: "order", order: "auto" });
  click(card, { action: "edge" });
  contains("summary while folded", markup(card), '<span class="zones-summary">Front &lt;b&gt;lawn&lt;/b&gt;, Back lawn · Auto · Edge cut</span>');
  check("go stays on the folded row", markup(card).includes('data-action="go" title="Start">'), true);
  click(card, { action: "zones-toggle" });
  contains("auto order shown", markup(card), 'aria-pressed="true" class="on">Auto');
  click(card, { action: "go" });
  await flush();
  const call = hass.calls[0];
  check("auto sends ids ascending", JSON.stringify(call?.data?.zones), "[1,2]");
  check("auto order", call?.data?.zone_order, "auto");
  check("edge cut on", call?.data?.edge_cut, true);
}

{
  const hass = makeHass();
  const card = make({ entity: "lawn_mower.robot" }, hass);
  click(card, { action: "zone", zone: "1" });
  click(card, { action: "zone", zone: "1" });
  await card._startZones();
  check("untick removes the zone, nothing sent", hass.calls.length, 0);
  click(card, { action: "go", disabled: true });
  click(card, { action: "zone", zone: "all" });
  click(card, { action: "zone", zone: "0" });
  check("no bogus zone id accepted", card._selected.length, 0);
}

{
  const hass = makeHass();
  const card = make({ entity: "lawn_mower.robot" }, hass);
  click(card, { action: "zone", zone: "2" });
  hass.failNext = true;
  await card._startZones();
  const html = markup(card);
  contains("error shown in the card", html, "Failed: boom");
  check("selection kept after a failure", card._selected.join(","), "2");
  check("not left busy", card._busy, false);
}

{
  const hass = makeHass();
  const card = make({ entity: "lawn_mower.robot" }, hass);
  click(card, { action: "zone", zone: "2" });
  const next = makeHass();
  delete next.states["sensor.robot_p_back"];
  delete next.states["sensor.robot_a_back"];
  next.states["select.robot_zones"] = st("Front", { available_zone_ids: [1] });
  card.hass = next;
  check("a zone that disappeared is unticked", card._selected.length, 0);
}

{
  const hass = makeHass();
  hass.states["lawn_mower.robot"] = st("unavailable", { supported_features: 7 });
  const card = make({ entity: "lawn_mower.robot" }, hass);
  click(card, { action: "zone", zone: "1" });
  contains("go disabled while mower unavailable, tooltip not asking to tick", markup(card), 'data-action="go" title="Start" disabled');
  contains("controls disabled while unavailable", markup(card), 'data-service="start_mowing" disabled');
}

// ── mower commands ──────────────────────────────────────────────────────────

{
  const hass = makeHass();
  const card = make({ entity: "lawn_mower.robot" }, hass);
  click(card, { action: "mower", service: "start_mowing" });
  await flush();
  check("start uses the lawn_mower service", `${hass.calls[0]?.domain}.${hass.calls[0]?.service}`, "lawn_mower.start_mowing");
  check("start targets the mower", hass.calls[0]?.target?.entity_id, "lawn_mower.robot");
  click(card, { action: "mower", service: "send_raw_command" });
  await flush();
  check("no free-form command reaches HA", hass.calls.length, 1);
}

{
  const hass = makeHass();
  hass.states["lawn_mower.robot"] = st("docked", { supported_features: 4 });
  const html = markup(make({ entity: "lawn_mower.robot" }, hass));
  check("unsupported start hidden", html.includes('data-service="start_mowing"'), false);
}

// ── event wiring (real listeners, not direct calls) ────────────────────────

{
  const listeners = [];
  const proto = Object.getPrototypeOf(new Card().attachShadow());
  const original = proto.addEventListener;
  proto.addEventListener = function (type, fn) { listeners.push([type, fn]); };
  const card = make({ entity: "lawn_mower.robot" });
  proto.addEventListener = original;
  const onClick = listeners.find(([type]) => type === "click")?.[1];
  onClick?.({ composedPath: () => [{ dataset: { action: "zone", zone: "1" } }] });
  check("click listener on the shadow root toggles a zone", card._selected.join(","), "1");
  const onKey = listeners.find(([type]) => type === "keydown")?.[1];
  onKey?.({ key: "Enter", composedPath: () => [{ dataset: { action: "zone", zone: "2" } }] });
  check("Enter toggles a zone", card._selected.join(","), "1,2");
}

// ── rain banner ─────────────────────────────────────────────────────────────

function rainy(extra = {}) {
  const hass = makeHass(extra);
  hass.states["lawn_mower.robot"] = st("docked", { supported_features: 7, rain_delay: true });
  hass.states["sensor.robot_pluie"] = st("155", { unit_of_measurement: "min" });
  return hass;
}

{
  const dry = markup(make({ entity: "lawn_mower.robot" }));
  check("no rain banner without rain", dry.includes('class="rain-banner'), false);

  const hass = rainy();
  const html = markup(make({ entity: "lawn_mower.robot" }, hass));
  contains("rain banner title", html, '<div class="rain-title">Rain detected</div>');
  contains("time left and the delay set", html, "Can resume in 2 h 35 · 3 h 00 rain delay");
  contains("banner opens the remaining delay history", html, 'class="rain-banner link" data-action="more-info" data-entity="sensor.robot_pluie"');
  check("banner comes before the controls", html.indexOf('class="rain-banner') < html.indexOf('class="controls"'), true);

  const errOnly = makeHass();
  errOnly.states["sensor.robot_err"] = { state: "rain_delay", attributes: {}, last_changed: "2026-01-15T19:00:00Z" };
  const errHtml = markup(make({ entity: "lawn_mower.robot" }, errOnly));
  check("rain is not shown as a red error", errHtml.includes('class="error-banner'), false);
  contains("error state alone raises the rain banner", errHtml, "Rain detected");

  const statusOnly = makeHass();
  statusOnly.states["sensor.robot_etat"] = st("rain_delay");
  contains("status alone raises the rain banner", markup(make({ entity: "lawn_mower.robot" }, statusOnly)), "Rain detected");

  const waiting = rainy();
  waiting.states["sensor.robot_pluie"] = st("0", { unit_of_measurement: "min" });
  contains("no countdown yet: waits for the rain to stop", markup(make({ entity: "lawn_mower.robot" }, waiting)), "The mower waits for the rain to stop");

  const noDelay = rainy();
  noDelay.states["number.robot_delai"] = st("unavailable");
  const noDelayHtml = markup(make({ entity: "lawn_mower.robot" }, noDelay));
  contains("countdown without the delay setting", noDelayHtml, "Can resume in 2 h 35</div>");

  const hours = rainy();
  hours.states["sensor.robot_pluie"] = st("2.5", { unit_of_measurement: "h" });
  contains("remaining shown in hours is converted", markup(make({ entity: "lawn_mower.robot" }, hours)), "Can resume in 2 h 30");

  const both = rainy();
  both.states["sensor.robot_err"] = { state: "lifted", attributes: {}, last_changed: "2026-01-15T19:00:00Z" };
  const bothHtml = markup(make({ entity: "lawn_mower.robot" }, both));
  contains("a real error stays red next to the rain", bothHtml, 'class="error-banner');
  contains("and the rain banner still shows", bothHtml, 'class="rain-banner');

  const chip = rainy();
  chip.states["sensor.robot_apte"] = st("rain_delay");
  check("readiness 'rain_delay' not repeated under the banner", markup(make({ entity: "lawn_mower.robot" }, chip)).includes("F(rain_delay)"), false);

  check("no rain banner with show_info off", markup(make({ entity: "lawn_mower.robot", show_info: false }, rainy())).includes('class="rain-banner'), false);

  const card = make({ entity: "lawn_mower.robot" }, rainy());
  const later = rainy();
  later.states["sensor.robot_pluie"] = st("20", { unit_of_measurement: "min" });
  card.hass = later;
  contains("countdown follows the sensor", markup(card), "Can resume in 20 min");
  const cleared = makeHass();
  card.hass = cleared;
  check("banner goes when the rain delay ends", markup(card).includes('class="rain-banner'), false);

  const starting = make({ entity: "lawn_mower.robot" });
  const firstDrop = makeHass();
  firstDrop.states["lawn_mower.robot"] = st("docked", { supported_features: 7, rain_delay: true });
  starting.hass = firstDrop;
  contains("banner appears when only the mower's rain flag changes", markup(starting), "The mower waits for the rain to stop");

  const old = makeHass();
  old.states["sensor.old_status"] = st("rain_delay");
  const oldHtml = markup(make({ entity: "lawn_mower.old" }, old));
  contains("mower without rain sensors still gets the banner", oldHtml, "The mower waits for the rain to stop");
  contains("and it opens the mower", oldHtml, 'class="rain-banner link" data-action="more-info" data-entity="lawn_mower.old"');

  for (const lang of ["da", "de", "en", "es", "fr", "it", "nl", "no", "pl", "ru", "sv"]) {
    const table = Card.I18N[lang];
    const h = rainy({ language: lang, locale: { language: lang } });
    const out = markup(make({ entity: "lawn_mower.robot" }, h));
    const title = table.rain_banner;
    const detail = `${table.rain_resume.replace("{d}", "2 h 35")} · ${table.rain_delay_of.replace("{d}", "3 h 00")}`;
    contains(`${lang}: rain banner title`, out, `<div class="rain-title">${title}</div>`);
    contains(`${lang}: rain banner detail`, out, `<div class="rain-detail">${detail}</div>`);
    check(`${lang}: no placeholder left`, /\{d\}/u.test(out), false);
    if (lang !== "en") check(`${lang}: not the English text`, title === Card.I18N.en.rain_banner, false);
  }
  const fr = markup(make({ entity: "lawn_mower.robot" }, rainy({ language: "fr", locale: { language: "fr" } })));
  contains("French wording", fr, "Reprise possible dans 2 h 35 · délai pluie de 3 h 00");
}

// ── progress bar under the map ──────────────────────────────────────────────

{
  const html = markup(make({ entity: "lawn_mower.robot" }));
  contains("progress bar right under the map", html, '</div><div class="map-progress link" title="F(62.4)" data-action="more-info" data-entity="sensor.robot_avance"');
  contains("bar filled to the estimate", html, '<div class="map-progress-fill" style="width:62.4%"></div>');
  check("no text next to the bar", /map-progress[^>]*>[^<]/u.test(html), false);

  const over = makeHass();
  over.states["sensor.robot_avance"] = st("137", { unit_of_measurement: "%" });
  contains("capped at a full bar", markup(make({ entity: "lawn_mower.robot" }, over)), 'style="width:100%"');

  const down = makeHass();
  down.states["sensor.robot_avance"] = st("unavailable");
  check("no bar without an estimate", markup(make({ entity: "lawn_mower.robot" }, down)).includes('class="map-progress'), false);

  check("no bar with the map hidden", markup(make({ entity: "lawn_mower.robot", show_map: false })).includes('class="map-progress'), false);

  const noMap = makeHass();
  noMap.states["camera.robot_carte"] = st("unavailable");
  const noMapHtml = markup(make({ entity: "lawn_mower.robot" }, noMap));
  contains("bar still under the map placeholder", noMapHtml, 'class="map-empty"');
  contains("with the estimate", noMapHtml, 'class="map-progress-fill"');

  const live = make({ entity: "lawn_mower.robot" });
  const later = makeHass();
  later.states["sensor.robot_avance"] = st("80", { unit_of_measurement: "%" });
  live.hass = later;
  contains("bar follows the estimate", markup(live), 'style="width:80%"');

  check("old mower without the sensor has no bar", markup(make({ entity: "lawn_mower.old" })).includes('class="map-progress'), false);
}

// ── one-time settings remembered ────────────────────────────────────────────

{
  const store = new Map();
  globalThis.localStorage = {
    getItem: (k) => (store.has(k) ? store.get(k) : null),
    setItem: (k, v) => store.set(k, String(v)),
  };
  const first = make({ entity: "lawn_mower.robot" });
  click(first, { action: "zone", zone: "2" });
  click(first, { action: "zone", zone: "1" });
  check("ticking alone is saved", store.get("worx-vision-card:lawn_mower.robot"), '{"zones":[2,1],"order":"fixed","edge":false}');
  click(first, { action: "order", order: "auto" });
  click(first, { action: "edge" });
  check("settings saved per mower", store.get("worx-vision-card:lawn_mower.robot"), '{"zones":[2,1],"order":"auto","edge":true}');

  const again = make({ entity: "lawn_mower.robot" });
  check("zones back after a reload", again._selected.join(","), "2,1");
  check("order back after a reload", again._order, "auto");
  check("edge cut back after a reload", again._edge, true);
  check("still folded after a reload", markup(again).includes('class="zone-chips"'), false);
  contains("reloaded summary", markup(again), "Front &lt;b&gt;lawn&lt;/b&gt;, Back lawn · Auto · Edge cut");

  const other = make({ entity: "lawn_mower.old" });
  check("another mower keeps its own settings", other._selected.length, 0);

  store.set("worx-vision-card:lawn_mower.robot", "{not json");
  const damaged = make({ entity: "lawn_mower.robot" });
  check("damaged value ignored", damaged._selected.length + damaged._order + damaged._edge, "0fixedfalse");

  store.set("worx-vision-card:lawn_mower.robot", '{"zones":["x",-1,2],"order":"sideways","edge":"yes"}');
  const odd = make({ entity: "lawn_mower.robot" });
  check("only valid zone ids kept", odd._selected.join(","), "2");
  check("unknown order ignored", odd._order, "fixed");
  check("non-boolean edge ignored", odd._edge, false);

  globalThis.localStorage = {
    getItem: () => { throw new Error("blocked"); },
    setItem: () => { throw new Error("blocked"); },
  };
  const blocked = make({ entity: "lawn_mower.robot" });
  click(blocked, { action: "zone", zone: "1" });
  check("blocked storage does not break the card", blocked._selected.join(","), "1");
  delete globalThis.localStorage;
}

// ── translations ────────────────────────────────────────────────────────────

{
  const langs = ["da", "de", "en", "es", "fr", "it", "nl", "no", "pl", "ru", "sv"];
  const keys = Object.keys(Card.I18N.en);
  for (const lang of langs) {
    const table = Card.I18N[lang] || {};
    const missing = keys.filter((k) => !table[k]);
    check(`${lang}: every string translated`, missing.join(","), "");
  }
  const fr = makeHass({ language: "fr", locale: { language: "fr" } });
  contains("French labels", markup(make({ entity: "lawn_mower.robot" }, fr)), "Tonte unique");
  const nb = makeHass({ language: "nb", locale: { language: "nb" } });
  contains("Norwegian Bokmål maps to no", markup(make({ entity: "lawn_mower.robot" }, nb)), "Engangsklipping");
  const pt = makeHass({ language: "pt", locale: { language: "pt" } });
  contains("unknown language falls back to English", markup(make({ entity: "lawn_mower.robot" }, pt)), "One-time mowing");
}

// ── editor ──────────────────────────────────────────────────────────────────

{
  const listeners = {};
  const hostListeners = {};
  const realCreate = document.createElement;
  document.createElement = (tag) => {
    const node = realCreate(tag);
    node.addEventListener = (type, fn) => { listeners[type] = fn; };
    return node;
  };
  const editor = new Editor();
  editor.addEventListener = (type, fn) => { hostListeners[type] = fn; };
  editor.setConfig(Object.freeze({ entity: "lawn_mower.robot" }));
  editor.hass = makeHass();
  document.createElement = realCreate;

  const fire = (value) => {
    try { listeners["value-changed"]?.({ detail: { value } }); } catch (err) { console.log(`     editor threw: ${err.message}`); }
  };
  const last = () => editor.events.at(-1);

  const schema = editor._form?.schema || [];
  const grid = schema.find((item) => item.type === "grid");
  check("switches grouped in a grid to shorten the editor", grid?.schema?.length, 6);
  check("grid adds no key of its own to the config", grid?.name === "" && grid?.flatten === true, true);
  check("every switch is in the grid", schema.filter((item) => item.selector?.boolean).length, 0);
  const frEditor = new Editor();
  frEditor.setConfig(Object.freeze({ entity: "lawn_mower.robot" }));
  frEditor.hass = makeHass({ language: "fr", locale: { language: "fr" } });
  check("zone option labelled like the section, in French", frEditor._form?.computeLabel?.({ name: "show_zones" }), "Tonte unique");

  fire({ entity: "lawn_mower.robot", show_map: false });
  check("config-changed dispatched", last()?.type, "config-changed");
  check("detail.config really carried", last()?.detail?.config?.show_map, false);
  check("entity kept", last()?.detail?.config?.entity, "lawn_mower.robot");

  const count = editor.events.length;
  fire({ entity: "", show_map: false });
  check("empty pick before any touch is ignored", editor.events.length, count);

  fire({ show_map: false, entity: "lawn_mower.robot" });
  check("echo in another key order is not re-sent", editor.events.length, count);

  hostListeners.pointerdown?.();
  fire({ entity: "", show_map: false });
  check("user can clear the entity once touched", last()?.detail?.config?.entity, "");
}

report();
