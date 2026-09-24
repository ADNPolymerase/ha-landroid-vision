/*
 * Worx Landroid Vision card, for the worx_vision_cloud integration
 * (ha-landroid-vision). One file, no build step.
 *
 * Entities are never guessed from their entity_id, which is localized and
 * renamable: the card starts from the configured lawn_mower, takes its
 * device, and picks that device's worx_vision_cloud entities by
 * translation_key. Zones come from the zone_id / zone_name attributes of the
 * per-zone pattern and angle sensors.
 */

const DOMAIN = "worx_vision_cloud";
const FEATURE_START = 1;
const FEATURE_PAUSE = 2;
const FEATURE_DOCK = 4;
const UNUSABLE = ["unknown", "unavailable"];

const I18N = {
  en: {
    party: "Party mode", party_banner: "Party mode: the mower will not go out, even during the schedule.",
    rain_banner: "Rain detected", rain_resume: "Can resume in {d}", rain_delay_of: "{d} rain delay", rain_wait: "The mower waits for the rain to stop",
    now_slot: "Current slot: {range}",
    blades: "Blades", reset: "Reset", reset_title: "Reset the blade time to zero?", reset_body: "Only after replacing the blades. The current {time} will be lost.", cancel: "Cancel", of_threshold: "{pct} % of the service threshold ({h} h)", replaced_on: "replaced {date}", since: "Since {time}", ago: "{d} ago", ed_show_blades: "Blades", ed_show_values: "Values (battery %, Wi-Fi dBm)",
    schedule: "Schedule", next: "Next", no_slots: "No mowing slot", wifi: "Wi-Fi", ed_show_info: "Wi-Fi, readiness and errors", ed_show_schedule: "Schedule",
    start: "Start", pause: "Pause", dock: "Dock", zones: "Zones", zone: "Zone",
    one_time: "One-time mowing", order: "Order", order_fixed: "Special",
    order_auto: "Auto", edge: "Edge cut", go: "Start", pick: "Tick at least one zone",
    sent: "Sent to the mower", failed: "Failed", map_unavailable: "RTK map unavailable",
    no_entity: "Entity not found", not_worx: "Pick a Worx Landroid Vision PLUS mower",
    ed_entity: "Mower", ed_title: "Title (optional)",
    ed_show_map: "RTK map", ed_show_zones: "One-time mowing", ed_show_controls: "Controls",
    ed_refresh_interval: "Map refresh (s)",
  },
  fr: {
    party: "Mode festif", party_banner: "Mode festif : la tondeuse ne sortira pas, même pendant le programme.",
    rain_banner: "Pluie détectée", rain_resume: "Reprise possible dans {d}", rain_delay_of: "délai pluie de {d}", rain_wait: "La tondeuse attend la fin de la pluie",
    now_slot: "Créneau en cours : {range}",
    blades: "Lames", reset: "Réinitialiser", reset_title: "Remettre le temps des lames à zéro ?", reset_body: "À faire seulement après avoir changé les lames. Les {time} actuelles seront perdues.", cancel: "Annuler", of_threshold: "{pct} % du seuil d'entretien ({h} h)", replaced_on: "changées le {date}", since: "Depuis {time}", ago: "il y a {d}", ed_show_blades: "Lames", ed_show_values: "Valeurs (batterie %, Wi-Fi dBm)",
    schedule: "Programme", next: "Prochaine", no_slots: "Aucun créneau de tonte", wifi: "Wi-Fi", ed_show_info: "Wi-Fi, aptitude et erreurs", ed_show_schedule: "Programme",
    start: "Démarrer", pause: "Pause", dock: "Maison", zones: "Zones", zone: "Zone",
    one_time: "Tonte unique", order: "Ordre", order_fixed: "Spécial",
    order_auto: "Auto", edge: "Bordure", go: "Démarrer", pick: "Cochez au moins une zone",
    sent: "Envoyé à la tondeuse", failed: "Échec", map_unavailable: "Carte RTK indisponible",
    no_entity: "Entité introuvable", not_worx: "Choisissez une tondeuse Worx Landroid Vision PLUS",
    ed_entity: "Tondeuse", ed_title: "Titre (facultatif)",
    ed_show_map: "Carte RTK", ed_show_zones: "Tonte unique", ed_show_controls: "Commandes",
    ed_refresh_interval: "Rafraîchissement de la carte (s)",
  },
  de: {
    party: "Partymodus", party_banner: "Partymodus: Der Mäher fährt nicht los, auch nicht während des Zeitplans.",
    rain_banner: "Regen erkannt", rain_resume: "Weiter möglich in {d}", rain_delay_of: "Regenverzögerung {d}", rain_wait: "Der Mäher wartet, bis der Regen aufhört",
    now_slot: "Aktuelles Zeitfenster: {range}",
    blades: "Messer", reset: "Zurücksetzen", reset_title: "Messerzeit auf null setzen?", reset_body: "Nur nach dem Messerwechsel. Die aktuellen {time} gehen verloren.", cancel: "Abbrechen", of_threshold: "{pct} % der Wartungsschwelle ({h} h)", replaced_on: "gewechselt am {date}", since: "Seit {time}", ago: "vor {d}", ed_show_blades: "Messer", ed_show_values: "Werte (Akku %, WLAN dBm)",
    schedule: "Zeitplan", next: "Nächste", no_slots: "Kein Mähzeitraum", wifi: "WLAN", ed_show_info: "WLAN, Mähbereitschaft und Fehler", ed_show_schedule: "Zeitplan",
    start: "Starten", pause: "Pause", dock: "Zur Station", zones: "Zonen", zone: "Zone",
    one_time: "Einmaliges Mähen", order: "Reihenfolge", order_fixed: "Speziell",
    order_auto: "Auto", edge: "Kantenschnitt", go: "Starten", pick: "Mindestens eine Zone auswählen",
    sent: "An den Mäher gesendet", failed: "Fehlgeschlagen", map_unavailable: "RTK-Karte nicht verfügbar",
    no_entity: "Entität nicht gefunden", not_worx: "Einen Worx Landroid Vision PLUS Mäher wählen",
    ed_entity: "Mäher", ed_title: "Titel (optional)",
    ed_show_map: "RTK-Karte", ed_show_zones: "Einmaliges Mähen", ed_show_controls: "Steuerung",
    ed_refresh_interval: "Kartenaktualisierung (s)",
  },
  es: {
    party: "Modo fiesta", party_banner: "Modo fiesta: el cortacésped no saldrá, ni siquiera durante el programa.",
    rain_banner: "Lluvia detectada", rain_resume: "Puede reanudar en {d}", rain_delay_of: "retraso por lluvia de {d}", rain_wait: "El cortacésped espera a que pare la lluvia",
    now_slot: "Franja actual: {range}",
    blades: "Cuchillas", reset: "Restablecer", reset_title: "¿Poner a cero el tiempo de las cuchillas?", reset_body: "Solo tras cambiar las cuchillas. Se perderán las {time} actuales.", cancel: "Cancelar", of_threshold: "{pct} % del umbral de mantenimiento ({h} h)", replaced_on: "cambiadas el {date}", since: "Desde {time}", ago: "hace {d}", ed_show_blades: "Cuchillas", ed_show_values: "Valores (batería %, Wi-Fi dBm)",
    schedule: "Programa", next: "Próximo", no_slots: "Ningún tramo de corte", wifi: "Wi-Fi", ed_show_info: "Wi-Fi, disponibilidad y errores", ed_show_schedule: "Programa",
    start: "Iniciar", pause: "Pausa", dock: "A la base", zones: "Zonas", zone: "Zona",
    one_time: "Corte único", order: "Orden", order_fixed: "Especial",
    order_auto: "Auto", edge: "Corte de bordes", go: "Iniciar", pick: "Marca al menos una zona",
    sent: "Enviado al cortacésped", failed: "Error", map_unavailable: "Mapa RTK no disponible",
    no_entity: "Entidad no encontrada", not_worx: "Elige un cortacésped Worx Landroid Vision PLUS",
    ed_entity: "Cortacésped", ed_title: "Título (opcional)",
    ed_show_map: "Mapa RTK", ed_show_zones: "Corte único", ed_show_controls: "Controles",
    ed_refresh_interval: "Actualización del mapa (s)",
  },
  it: {
    party: "Modalità festa", party_banner: "Modalità festa: il robot non uscirà, nemmeno durante il programma.",
    rain_banner: "Pioggia rilevata", rain_resume: "Può ripartire tra {d}", rain_delay_of: "ritardo pioggia di {d}", rain_wait: "Il robot aspetta che smetta di piovere",
    now_slot: "Fascia in corso: {range}",
    blades: "Lame", reset: "Azzera", reset_title: "Azzerare il tempo delle lame?", reset_body: "Solo dopo aver cambiato le lame. Le {time} attuali andranno perse.", cancel: "Annulla", of_threshold: "{pct} % della soglia di manutenzione ({h} h)", replaced_on: "cambiate il {date}", since: "Dalle {time}", ago: "{d} fa", ed_show_blades: "Lame", ed_show_values: "Valori (batteria %, Wi-Fi dBm)",
    schedule: "Programma", next: "Prossimo", no_slots: "Nessuna fascia di taglio", wifi: "Wi-Fi", ed_show_info: "Wi-Fi, disponibilità ed errori", ed_show_schedule: "Programma",
    start: "Avvia", pause: "Pausa", dock: "Alla base", zones: "Zone", zone: "Zona",
    one_time: "Taglio singolo", order: "Ordine", order_fixed: "Speciale",
    order_auto: "Auto", edge: "Taglio bordi", go: "Avvia", pick: "Seleziona almeno una zona",
    sent: "Inviato al robot", failed: "Errore", map_unavailable: "Mappa RTK non disponibile",
    no_entity: "Entità non trovata", not_worx: "Scegli un robot Worx Landroid Vision PLUS",
    ed_entity: "Robot tagliaerba", ed_title: "Titolo (facoltativo)",
    ed_show_map: "Mappa RTK", ed_show_zones: "Taglio singolo", ed_show_controls: "Comandi",
    ed_refresh_interval: "Aggiornamento mappa (s)",
  },
  nl: {
    party: "Feestmodus", party_banner: "Feestmodus: de maaier gaat niet naar buiten, ook niet tijdens het schema.",
    rain_banner: "Regen gedetecteerd", rain_resume: "Kan hervatten over {d}", rain_delay_of: "regenvertraging van {d}", rain_wait: "De maaier wacht tot de regen stopt",
    now_slot: "Huidige periode: {range}",
    blades: "Messen", reset: "Resetten", reset_title: "Messentijd op nul zetten?", reset_body: "Alleen na het vervangen van de messen. De huidige {time} gaan verloren.", cancel: "Annuleren", of_threshold: "{pct} % van de onderhoudsdrempel ({h} u)", replaced_on: "vervangen op {date}", since: "Sinds {time}", ago: "{d} geleden", ed_show_blades: "Messen", ed_show_values: "Waarden (accu %, wifi dBm)",
    schedule: "Schema", next: "Volgende", no_slots: "Geen maaiperiode", wifi: "Wifi", ed_show_info: "Wifi, maaigereedheid en fouten", ed_show_schedule: "Schema",
    start: "Starten", pause: "Pauze", dock: "Naar basis", zones: "Zones", zone: "Zone",
    one_time: "Eenmalig maaien", order: "Volgorde", order_fixed: "Speciaal",
    order_auto: "Auto", edge: "Randen maaien", go: "Starten", pick: "Vink minstens één zone aan",
    sent: "Naar de maaier gestuurd", failed: "Mislukt", map_unavailable: "RTK-kaart niet beschikbaar",
    no_entity: "Entiteit niet gevonden", not_worx: "Kies een Worx Landroid Vision PLUS maaier",
    ed_entity: "Maaier", ed_title: "Titel (optioneel)",
    ed_show_map: "RTK-kaart", ed_show_zones: "Eenmalig maaien", ed_show_controls: "Bediening",
    ed_refresh_interval: "Kaartverversing (s)",
  },
  pl: {
    party: "Tryb imprezy", party_banner: "Tryb imprezy: kosiarka nie wyjedzie, nawet w czasie harmonogramu.",
    rain_banner: "Wykryto deszcz", rain_resume: "Wznowienie możliwe za {d}", rain_delay_of: "opóźnienie deszczowe {d}", rain_wait: "Kosiarka czeka, aż przestanie padać",
    now_slot: "Bieżące okno: {range}",
    blades: "Noże", reset: "Resetuj", reset_title: "Wyzerować czas pracy noży?", reset_body: "Tylko po wymianie noży. Obecne {time} zostaną utracone.", cancel: "Anuluj", of_threshold: "{pct} % progu serwisowego ({h} h)", replaced_on: "wymienione {date}", since: "Od {time}", ago: "{d} temu", ed_show_blades: "Noże", ed_show_values: "Wartości (bateria %, Wi-Fi dBm)",
    schedule: "Harmonogram", next: "Następne", no_slots: "Brak okien koszenia", wifi: "Wi-Fi", ed_show_info: "Wi-Fi, gotowość i błędy", ed_show_schedule: "Harmonogram",
    start: "Start", pause: "Pauza", dock: "Do bazy", zones: "Strefy", zone: "Strefa",
    one_time: "Koszenie jednorazowe", order: "Kolejność", order_fixed: "Specjalna",
    order_auto: "Auto", edge: "Koszenie krawędzi", go: "Start", pick: "Zaznacz co najmniej jedną strefę",
    sent: "Wysłano do kosiarki", failed: "Błąd", map_unavailable: "Mapa RTK niedostępna",
    no_entity: "Nie znaleziono encji", not_worx: "Wybierz kosiarkę Worx Landroid Vision PLUS",
    ed_entity: "Kosiarka", ed_title: "Tytuł (opcjonalnie)",
    ed_show_map: "Mapa RTK", ed_show_zones: "Koszenie jednorazowe", ed_show_controls: "Sterowanie",
    ed_refresh_interval: "Odświeżanie mapy (s)",
  },
  ru: {
    party: "Режим вечеринки", party_banner: "Режим вечеринки: косилка не выедет, даже по расписанию.",
    rain_banner: "Обнаружен дождь", rain_resume: "Возобновление через {d}", rain_delay_of: "задержка из-за дождя {d}", rain_wait: "Косилка ждёт, пока закончится дождь",
    now_slot: "Текущий интервал: {range}",
    blades: "Ножи", reset: "Сбросить", reset_title: "Обнулить время работы ножей?", reset_body: "Только после замены ножей. Текущие {time} будут потеряны.", cancel: "Отмена", of_threshold: "{pct} % порога обслуживания ({h} ч)", replaced_on: "заменены {date}", since: "С {time}", ago: "{d} назад", ed_show_blades: "Ножи", ed_show_values: "Значения (батарея %, Wi-Fi дБм)",
    schedule: "Расписание", next: "Следующее", no_slots: "Нет интервалов кошения", wifi: "Wi-Fi", ed_show_info: "Wi-Fi, готовность и ошибки", ed_show_schedule: "Расписание",
    start: "Старт", pause: "Пауза", dock: "На базу", zones: "Зоны", zone: "Зона",
    one_time: "Разовое кошение", order: "Порядок", order_fixed: "Особый",
    order_auto: "Авто", edge: "Стрижка кромки", go: "Старт", pick: "Отметьте хотя бы одну зону",
    sent: "Отправлено косилке", failed: "Ошибка", map_unavailable: "Карта RTK недоступна",
    no_entity: "Объект не найден", not_worx: "Выберите косилку Worx Landroid Vision PLUS",
    ed_entity: "Косилка", ed_title: "Заголовок (необязательно)",
    ed_show_map: "Карта RTK", ed_show_zones: "Разовое кошение", ed_show_controls: "Управление",
    ed_refresh_interval: "Обновление карты (с)",
  },
  sv: {
    party: "Festläge", party_banner: "Festläge: klipparen kör inte ut, inte ens under schemat.",
    rain_banner: "Regn upptäckt", rain_resume: "Kan återuppta om {d}", rain_delay_of: "regnfördröjning {d}", rain_wait: "Klipparen väntar tills regnet slutar",
    now_slot: "Pågående tid: {range}",
    blades: "Knivar", reset: "Återställ", reset_title: "Nollställa knivtiden?", reset_body: "Bara efter knivbyte. Nuvarande {time} går förlorade.", cancel: "Avbryt", of_threshold: "{pct} % av servicegränsen ({h} h)", replaced_on: "bytta {date}", since: "Sedan {time}", ago: "för {d} sedan", ed_show_blades: "Knivar", ed_show_values: "Värden (batteri %, wifi dBm)",
    schedule: "Schema", next: "Nästa", no_slots: "Inga klipptider", wifi: "Wi-Fi", ed_show_info: "Wi-Fi, klippberedskap och fel", ed_show_schedule: "Schema",
    start: "Starta", pause: "Paus", dock: "Till basen", zones: "Zoner", zone: "Zon",
    one_time: "Engångsklippning", order: "Ordning", order_fixed: "Special",
    order_auto: "Auto", edge: "Kantklippning", go: "Starta", pick: "Markera minst en zon",
    sent: "Skickat till klipparen", failed: "Misslyckades", map_unavailable: "RTK-karta ej tillgänglig",
    no_entity: "Entiteten hittades inte", not_worx: "Välj en Worx Landroid Vision PLUS-klippare",
    ed_entity: "Klippare", ed_title: "Titel (valfritt)",
    ed_show_map: "RTK-karta", ed_show_zones: "Engångsklippning", ed_show_controls: "Reglage",
    ed_refresh_interval: "Kartuppdatering (s)",
  },
  no: {
    party: "Festmodus", party_banner: "Festmodus: klipperen kjører ikke ut, heller ikke i tidsplanen.",
    rain_banner: "Regn oppdaget", rain_resume: "Kan fortsette om {d}", rain_delay_of: "regnforsinkelse {d}", rain_wait: "Klipperen venter til regnet stopper",
    now_slot: "Pågående tid: {range}",
    blades: "Kniver", reset: "Tilbakestill", reset_title: "Nullstille knivtiden?", reset_body: "Bare etter knivbytte. Nåværende {time} går tapt.", cancel: "Avbryt", of_threshold: "{pct} % av servicegrensen ({h} t)", replaced_on: "byttet {date}", since: "Siden {time}", ago: "for {d} siden", ed_show_blades: "Kniver", ed_show_values: "Verdier (batteri %, wifi dBm)",
    schedule: "Tidsplan", next: "Neste", no_slots: "Ingen klippetider", wifi: "Wi-Fi", ed_show_info: "Wi-Fi, klarhet og feil", ed_show_schedule: "Tidsplan",
    start: "Start", pause: "Pause", dock: "Til basen", zones: "Soner", zone: "Sone",
    one_time: "Engangsklipping", order: "Rekkefølge", order_fixed: "Spesial",
    order_auto: "Auto", edge: "Kantklipping", go: "Start", pick: "Kryss av minst én sone",
    sent: "Sendt til klipperen", failed: "Mislyktes", map_unavailable: "RTK-kart utilgjengelig",
    no_entity: "Fant ikke entiteten", not_worx: "Velg en Worx Landroid Vision PLUS-klipper",
    ed_entity: "Klipper", ed_title: "Tittel (valgfritt)",
    ed_show_map: "RTK-kart", ed_show_zones: "Engangsklipping", ed_show_controls: "Kontroller",
    ed_refresh_interval: "Kartoppdatering (s)",
  },
  da: {
    party: "Festtilstand", party_banner: "Festtilstand: robotten kører ikke ud, heller ikke i tidsplanen.",
    rain_banner: "Regn registreret", rain_resume: "Kan genoptage om {d}", rain_delay_of: "regnforsinkelse {d}", rain_wait: "Robotten venter, til regnen stopper",
    now_slot: "Igangværende tid: {range}",
    blades: "Knive", reset: "Nulstil", reset_title: "Nulstille knivtiden?", reset_body: "Kun efter knivskift. De nuværende {time} går tabt.", cancel: "Annuller", of_threshold: "{pct} % af servicegrænsen ({h} t)", replaced_on: "skiftet {date}", since: "Siden {time}", ago: "for {d} siden", ed_show_blades: "Knive", ed_show_values: "Værdier (batteri %, wifi dBm)",
    schedule: "Tidsplan", next: "Næste", no_slots: "Ingen klippetider", wifi: "Wi-Fi", ed_show_info: "Wi-Fi, klarhed og fejl", ed_show_schedule: "Tidsplan",
    start: "Start", pause: "Pause", dock: "Til basen", zones: "Zoner", zone: "Zone",
    one_time: "Engangsklipning", order: "Rækkefølge", order_fixed: "Speciel",
    order_auto: "Auto", edge: "Kantklipning", go: "Start", pick: "Markér mindst én zone",
    sent: "Sendt til robotten", failed: "Mislykkedes", map_unavailable: "RTK-kort utilgængeligt",
    no_entity: "Entitet ikke fundet", not_worx: "Vælg en Worx Landroid Vision PLUS-robot",
    ed_entity: "Robotplæneklipper", ed_title: "Titel (valgfri)",
    ed_show_map: "RTK-kort", ed_show_zones: "Engangsklipning", ed_show_controls: "Betjening",
    ed_refresh_interval: "Kortopdatering (s)",
  },
};

const LANGUAGE_ALIASES = { nb: "no", nn: "no" };

function language(hass) {
  const raw = String(hass?.locale?.language || hass?.language || "en").toLowerCase();
  const base = raw.split(/[-_]/u)[0];
  const code = LANGUAGE_ALIASES[base] || base;
  return I18N[code] ? code : "en";
}

function t(hass, key, vars) {
  const text = I18N[language(hass)][key] ?? I18N.en[key] ?? key;
  return vars ? text.replace(/\{(\w+)\}/gu, (m, k) => (k in vars ? String(vars[k]) : m)) : text;
}

/** Colour class of the battery: good from 50 %, warn from 20 %, bad below. */
function batteryLevel(pct) {
  return pct >= 50 ? "lvl-good" : pct >= 20 ? "lvl-warn" : "lvl-bad";
}

/** Colour class of the Wi-Fi signal: good from -65 dBm, warn from -75 dBm, bad below. */
function wifiLevel(dbm) {
  return dbm >= -65 ? "lvl-good" : dbm >= -75 ? "lvl-warn" : "lvl-bad";
}

/** "3 h 47", or "12 min" under an hour. */
function formatMinutes(total) {
  const minutes = Math.max(0, Math.round(Number(total)));
  if (!Number.isFinite(minutes)) return "";
  if (minutes < 60) return `${minutes} min`;
  return `${Math.floor(minutes / 60)} h ${String(minutes % 60).padStart(2, "0")}`;
}

const MINUTES_PER_UNIT = { s: 1 / 60, min: 1, h: 60, d: 1440 };

/** A duration sensor's value in minutes, whatever display unit was chosen. */
function durationMinutes(stateObj) {
  if (!usable(stateObj)) return NaN;
  const factor = MINUTES_PER_UNIT[stateObj.attributes?.unit_of_measurement ?? "min"];
  const value = Number(stateObj.state);
  return factor === undefined ? NaN : value * factor;
}

function localeOf(hass) {
  return hass?.locale?.language || hass?.language || "en";
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/gu, "&amp;")
    .replace(/</gu, "&lt;")
    .replace(/>/gu, "&gt;")
    .replace(/"/gu, "&quot;")
    .replace(/'/gu, "&#39;");
}

function usable(stateObj) {
  return Boolean(stateObj) && !UNUSABLE.includes(stateObj.state);
}

/** Key-order independent JSON, so an echoed config compares equal. */
function stableStringify(value) {
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.keys(value).sort()
      .map((k) => `${JSON.stringify(k)}:${stableStringify(value[k])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

/**
 * Everything the card shows for one mower, found through the device.
 * Returns null when the entity is not a worx_vision_cloud entity.
 */
function resolveEntities(hass, entityId) {
  const registry = hass?.entities || {};
  const own = registry[entityId];
  if (!own || own.platform !== DOMAIN || !own.device_id) return null;
  const related = Object.values(registry).filter(
    (e) => e.device_id === own.device_id && e.platform === DOMAIN
  );
  const find = (domain, key) =>
    related.find((e) => e.translation_key === key && e.entity_id.startsWith(`${domain}.`))
      ?.entity_id;

  const mower = entityId.startsWith("lawn_mower.")
    ? entityId
    : related.find((e) => e.entity_id.startsWith("lawn_mower."))?.entity_id;
  const zoneSelect = find("select", "one_time_mowing_zones");

  const zones = new Map();
  const zoneOf = (id) => {
    if (!zones.has(id)) zones.set(id, { id, name: null, pattern: null, angle: null });
    return zones.get(id);
  };
  for (const e of related) {
    const kind = { zone_mowing_pattern: "pattern", zone_mowing_angle: "angle" }[e.translation_key];
    if (!kind || !e.entity_id.startsWith("sensor.")) continue;
    const attrs = hass.states?.[e.entity_id]?.attributes || {};
    const id = Number(attrs.zone_id);
    if (!Number.isInteger(id) || id < 1) continue;
    const zone = zoneOf(id);
    zone[kind] = e.entity_id;
    zone.name = zone.name || attrs.zone_name || null;
  }
  const available = hass.states?.[zoneSelect]?.attributes?.available_zone_ids;
  if (Array.isArray(available)) {
    for (const raw of available) {
      const id = Number(raw);
      if (Number.isInteger(id) && id > 0) zoneOf(id);
    }
  }

  return {
    deviceId: own.device_id,
    mower,
    status: find("sensor", "status"),
    battery: find("sensor", "battery_percent"),
    zoneCurrent: find("sensor", "zone_current"),
    rssi: find("sensor", "rssi"),
    readiness: find("sensor", "mowing_readiness"),
    error: find("sensor", "error"),
    schedule: find("sensor", "schedule"),
    nextSchedule: find("sensor", "next_schedule"),
    calendar: find("calendar", "schedule"),
    party: find("switch", "party_mode"),
    rainRemaining: find("sensor", "rain_remaining"),
    progress: find("sensor", "estimated_daily_progress"),
    rainDelay: find("number", "rain_delay_minutes"),
    maintenance: find("sensor", "maintenance_status"),
    bladeCurrent: find("sensor", "blade_runtime_current"),
    bladeReset: find("button", "reset_blade_counter"),
    camera: find("camera", "rtk_map_camera"),
    zoneSelect,
    zones: [...zones.values()].sort((a, b) => a.id - b.id),
  };
}

/** Attributes that make an element open the entity's more-info dialog. */
function moreInfo(entityId) {
  return entityId
    ? ` data-action="more-info" data-entity="${escapeHtml(entityId)}" role="button" tabindex="0"`
    : "";
}

const WEEKDAYS = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"];

/**
 * The slot the mower is in right now, from the integration's schedule
 * calendar: on during a slot, with start and end already in Home Assistant's
 * time zone ("2026-09-24 08:00:00"), so the browser's own zone never matters.
 */
function currentSlot(calendarObj) {
  if (calendarObj?.state !== "on") return null;
  const start = String(calendarObj.attributes?.start_time ?? "");
  const end = String(calendarObj.attributes?.end_time ?? "");
  const match = /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}:\d{2})/u.exec(start);
  const endMatch = /[ T](\d{2}:\d{2})/u.exec(end);
  if (!match || !endMatch) return null;
  const weekday = new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3]))).getUTCDay();
  return { day: WEEKDAYS[weekday], start: match[4], end: endMatch[1] };
}

function formatState(hass, stateObj) {
  if (!stateObj) return "";
  try {
    if (typeof hass?.formatEntityState === "function") {
      return hass.formatEntityState(stateObj);
    }
  } catch (_err) {
    // Fall through to the raw state.
  }
  return stateObj.state;
}

const DEFAULTS = {
  show_map: true,
  show_zones: true,
  show_controls: true,
  show_info: true,
  show_schedule: true,
  show_blades: true,
  show_values: true,
  refresh_interval: 30,
  fit: "contain",
  aspect_ratio: "900 / 620",
};

class WorxVisionCard extends HTMLElement {
  static getConfigElement() {
    return document.createElement("worx-vision-card-editor");
  }

  static getStubConfig(hass) {
    const mower = Object.values(hass?.entities || {}).find(
      (e) => e.platform === DOMAIN && e.entity_id.startsWith("lawn_mower.")
    );
    return { entity: mower ? mower.entity_id : "" };
  }

  constructor() {
    super();
    this._selected = [];
    this._order = "fixed";
    this._edge = false;
    this._busy = false;
    this._notice = null;
    this._cacheBuster = Date.now();
    this._signature = null;
    this._scheduleOpen = false;
    this._confirmReset = false;
    this._zonesOpen = false;
    this._settingsKey = null;
  }

  setConfig(config) {
    if (!config || typeof config.entity !== "string" || !config.entity) {
      throw new Error("worx-vision-card: entity is required");
    }
    // Lovelace hands over a frozen object: copy, never write on it.
    this._userConfig = config;
    this._config = { ...DEFAULTS, ...config };
    this._loadZoneSettings(config.entity);
    this._signature = null;
    this._render();
    this._resetTimer();
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._translationsRequested && typeof hass?.loadBackendTranslation === "function") {
      this._translationsRequested = true;
      Promise.resolve(hass.loadBackendTranslation("entity", DOMAIN))
        .then(() => { this._signature = null; this._render(); })
        .catch(() => {});
    }
    this._render();
  }

  get hass() {
    return this._hass;
  }

  connectedCallback() {
    this._resetTimer();
  }

  disconnectedCallback() {
    this._clearTimer();
  }

  getCardSize() {
    return 6;
  }

  getGridOptions() {
    return { columns: 12, min_columns: 6 };
  }

  _resetTimer() {
    this._clearTimer();
    const seconds = Number(this._config?.refresh_interval);
    if (!Number.isFinite(seconds) || seconds <= 0 || typeof window?.setInterval !== "function") {
      return;
    }
    this._timer = window.setInterval(() => {
      this._cacheBuster = Date.now();
      const img = this.shadowRoot?.querySelector?.("img.map");
      const src = this._mapUrl();
      if (img && src) img.src = src;
    }, seconds * 1000);
  }

  _clearTimer() {
    if (this._timer) {
      window.clearInterval(this._timer);
      this._timer = undefined;
    }
  }

  _entities() {
    return resolveEntities(this._hass, this._config.entity);
  }

  _mapUrl() {
    const camera = this._entities()?.camera;
    const stateObj = camera ? this._hass?.states?.[camera] : undefined;
    if (!usable(stateObj)) return "";
    const base = stateObj.attributes?.entity_picture || `/api/camera_proxy/${camera}`;
    return `${base}${base.includes("?") ? "&" : "?"}worx_vision=${this._cacheBuster}`;
  }

  /** Legacy worx-map-rtk-card configs point at the camera and only want the map. */
  _legacy() {
    return this._config.entity.startsWith("camera.");
  }

  _show(key) {
    if (this._legacy() && key !== "show_map") return this._userConfig[key] === true;
    return this._config[key] !== false;
  }

  _computeSignature(ents) {
    const states = this._hass?.states || {};
    const ids = ents
      ? [ents.mower, ents.status, ents.battery, ents.zoneCurrent, ents.camera, ents.zoneSelect,
        ents.rssi, ents.readiness, ents.error, ents.schedule, ents.nextSchedule,
        ents.maintenance, ents.bladeReset, ents.calendar, ents.party, ents.bladeCurrent,
        ents.rainRemaining, ents.rainDelay, ents.progress,
        ...ents.zones.flatMap((z) => [z.pattern, z.angle])]
      : [this._config.entity];
    const snap = ids.filter(Boolean).map((id) => {
      const s = states[id];
      return s ? [id, s.state, s.attributes?.entity_picture, s.attributes?.charging,
        s.attributes?.supported_features, s.attributes?.rain_delay, s.attributes?.zone_name, s.attributes?.by_day,
        s.attributes?.blade_runtime_since_reset, s.attributes?.blade_service_threshold_minutes,
        s.attributes?.blade_runtime_reset_at, s.attributes?.start_time, s.attributes?.end_time,
        s.last_changed] : [id];
    });
    return stableStringify([snap, this._selected, this._order, this._edge, this._busy,
      this._notice, this._scheduleOpen, this._confirmReset, this._zonesOpen, language(this._hass), this._config]);
  }

  _render() {
    if (!this._config) return;
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
      this.shadowRoot.addEventListener("click", (ev) => this._onClick(ev));
      this.shadowRoot.addEventListener("keydown", (ev) => {
        if (ev.key === "Enter" || ev.key === " ") {
          ev.preventDefault?.();
          this._onClick(ev);
        }
      });
    }
    if (!this._hass) return;
    const ents = this._entities();
    const signature = this._computeSignature(ents);
    if (signature === this._signature) return;
    this._signature = signature;
    this.shadowRoot.innerHTML = `<style>${STYLES}</style><ha-card>${this._body(ents)}</ha-card>`;
  }

  _body(ents) {
    const hass = this._hass;
    if (!hass.states?.[this._config.entity]) {
      return `<div class="warning">${escapeHtml(t(hass, "no_entity"))}: ${escapeHtml(this._config.entity)}</div>`;
    }
    if (!ents) {
      return `<div class="warning">${escapeHtml(t(hass, "not_worx"))}</div>`;
    }
    return [
      ents.mower ? this._header(ents) : "",
      ents.mower && this._show("show_info") ? this._errorBanner(ents) : "",
      ents.mower && this._show("show_info") ? this._rainBanner(ents) : "",
      ents.mower && this._show("show_info") ? this._partyBanner(ents) : "",
      ents.mower && this._show("show_info") ? this._info(ents) : "",
      ents.mower && this._show("show_controls") ? this._controls(ents) : "",
      this._show("show_map") ? this._map(ents) : "",
      this._show("show_zones") ? this._zones(ents) : "",
      ents.mower && this._show("show_schedule") ? this._schedule(ents) : "",
      ents.mower && this._show("show_blades") ? this._blades(ents) : "",
    ].join("");
  }

  _title(ents) {
    if (this._config.title) return this._config.title;
    const device = this._hass.devices?.[ents.deviceId];
    return device?.name_by_user || device?.name
      || this._hass.states[ents.mower]?.attributes?.friendly_name || "";
  }

  _header(ents) {
    const hass = this._hass;
    const mowerObj = hass.states[ents.mower];
    const statusObj = hass.states[ents.status];
    const status = usable(statusObj) ? formatState(hass, statusObj) : formatState(hass, mowerObj);
    const zoneObj = hass.states[ents.zoneCurrent];
    const parts = [];
    if (status) {
      parts.push(`<span class="link"${moreInfo(usable(statusObj) ? ents.status : ents.mower)}>${escapeHtml(status)}</span>`);
    }
    if (usable(zoneObj)) {
      parts.push(`<span class="link"${moreInfo(ents.zoneCurrent)}>${escapeHtml(zoneObj.state)}</span>`);
    }

    let battery = "";
    const batteryObj = hass.states[ents.battery];
    if (usable(batteryObj)) {
      const pct = Math.round(Number(batteryObj.state));
      const charging = batteryObj.attributes?.charging === true;
      const level = Math.max(10, Math.min(100, Math.round(pct / 10) * 10));
      const icon = charging ? `mdi:battery-charging-${level}` : (level === 100 ? "mdi:battery" : `mdi:battery-${level}`);
      const values = this._show("show_values");
      battery = `<div class="battery link ${batteryLevel(pct)}" title="${escapeHtml(pct)} %"${moreInfo(ents.battery)}><ha-icon icon="${icon}"></ha-icon>`
        + (values ? `<span>${escapeHtml(pct)} %</span>` : "")
        + `</div>`;
    }
    const wifi = this._show("show_info") ? this._wifi(ents) : "";
    return `<div class="header"><div class="titles"><div class="title link"${moreInfo(ents.mower)}>${escapeHtml(this._title(ents))}</div>`
      + `<div class="status">${parts.join(" · ")}</div></div>`
      + `<div class="corner-col"><div class="corner">${wifi}${battery}</div>${this._partyButton(ents)}</div></div>`;
  }

  _partyButton(ents) {
    const partyObj = this._hass.states[ents.party];
    if (!partyObj || !this._show("show_controls")) return "";
    const on = partyObj.state === "on";
    return `<button class="party${on ? " on" : ""}" data-action="party" aria-pressed="${on}"${usable(partyObj) ? "" : " disabled"}>`
      + `<ha-icon icon="mdi:party-popper"></ha-icon><span>${escapeHtml(t(this._hass, "party"))}</span></button>`;
  }

  _partyBanner(ents) {
    const partyObj = this._hass.states[ents.party];
    if (partyObj?.state !== "on") return "";
    return `<div class="party-banner"><ha-icon icon="mdi:party-popper"></ha-icon>`
      + `<span>${escapeHtml(t(this._hass, "party_banner"))}</span></div>`;
  }

  /** Whether the mower is held back by rain, from any of the places saying so. */
  _raining(ents) {
    const states = this._hass.states;
    return states[ents.mower]?.attributes?.rain_delay === true
      || states[ents.error]?.state === "rain_delay"
      || states[ents.status]?.state === "rain_delay";
  }

  _rainBanner(ents) {
    const hass = this._hass;
    if (!this._raining(ents)) return "";
    const remaining = durationMinutes(hass.states[ents.rainRemaining]);
    const delay = durationMinutes(hass.states[ents.rainDelay]);
    let detail;
    if (remaining > 0) {
      detail = t(hass, "rain_resume", { d: formatMinutes(remaining) });
      if (delay > 0) detail += ` · ${t(hass, "rain_delay_of", { d: formatMinutes(delay) })}`;
    } else {
      detail = t(hass, "rain_wait");
    }
    const target = ents.rainRemaining || ents.rainDelay || ents.mower;
    return `<div class="rain-banner link"${moreInfo(target)}>`
      + `<ha-icon icon="mdi:weather-pouring"></ha-icon><div>`
      + `<div class="rain-title">${escapeHtml(t(hass, "rain_banner"))}</div>`
      + `<div class="rain-detail">${escapeHtml(detail)}</div>`
      + `</div></div>`;
  }

  _wifi(ents) {
    const hass = this._hass;
    const rssiObj = hass.states[ents.rssi];
    if (!usable(rssiObj)) return "";
    const dbm = Math.round(Number(rssiObj.state));
    const bars = dbm >= -60 ? 4 : dbm >= -70 ? 3 : dbm >= -80 ? 2 : 1;
    return `<div class="wifi link ${wifiLevel(dbm)}" title="${escapeHtml(t(hass, "wifi"))} ${escapeHtml(dbm)} dBm"${moreInfo(ents.rssi)}>`
      + `<ha-icon icon="mdi:wifi-strength-${bars}"></ha-icon>`
      + (this._show("show_values") ? `<span>${escapeHtml(dbm)} dBm</span>` : "")
      + `</div>`;
  }

  _info(ents) {
    const hass = this._hass;
    const chips = [];
    const readyObj = hass.states[ents.readiness];
    const errorObj = hass.states[ents.error];
    const bannerShown = usable(errorObj) && errorObj.state !== "no_error" && errorObj.state !== "rain_delay";
    const raining = this._raining(ents);
    // A banner already says it: a readiness of "error" or "rain_delay" would repeat it.
    if (usable(readyObj) && !(bannerShown && readyObj.state === "error")
      && !(raining && readyObj.state === "rain_delay")) {
      const ok = readyObj.state === "ready" || readyObj.state === "mowing" || readyObj.state === "charging";
      chips.push(`<span class="chip link ${ok ? "good" : "warn"}"${moreInfo(ents.readiness)}>`
        + `<ha-icon icon="${ok ? "mdi:check-circle-outline" : "mdi:alert-outline"}"></ha-icon>`
        + `${escapeHtml(formatState(hass, readyObj))}</span>`);
    }
    return chips.length ? `<div class="chips">${chips.join("")}</div>` : "";
  }

  _errorBanner(ents) {
    const hass = this._hass;
    const errorObj = hass.states[ents.error];
    // Rain is a wait, not a fault: the rain banner shows it instead.
    if (!usable(errorObj) || errorObj.state === "no_error" || errorObj.state === "rain_delay") return "";
    let when = "";
    const since = Date.parse(errorObj.last_changed);
    if (Number.isFinite(since)) {
      const format = hass?.locale?.time_format;
      const hour12 = format === "12" ? true : format === "24" ? false : undefined;
      const time = new Date(since).toLocaleTimeString(localeOf(hass), { hour: "2-digit", minute: "2-digit", hour12 });
      const elapsed = formatMinutes((Date.now() - since) / 60000);
      when = `${t(hass, "since", { time })} · ${t(hass, "ago", { d: elapsed })}`;
    }
    return `<div class="error-banner link"${moreInfo(ents.error)}>`
      + `<ha-icon icon="mdi:alert-octagon-outline"></ha-icon><div>`
      + `<div class="error-title">${escapeHtml(formatState(hass, errorObj))}</div>`
      + (when ? `<div class="error-when">${escapeHtml(when)}</div>` : "")
      + `</div></div>`;
  }

  _blades(ents) {
    const hass = this._hass;
    const maint = hass.states[ents.maintenance];
    // The mower's own current blade counter, as in the Worx app.
    const minutes = durationMinutes(hass.states[ents.bladeCurrent]);
    if (!Number.isFinite(minutes)) return "";
    const threshold = Number(maint?.attributes?.blade_service_threshold_minutes);
    const pct = Number.isFinite(threshold) && threshold > 0
      ? Math.min(100, Math.round((100 * minutes) / threshold)) : null;
    const level = pct === null ? "" : pct >= 100 ? " bad" : pct >= 80 ? " warn" : " good";
    const resetAt = Date.parse(maint?.attributes?.blade_runtime_reset_at);
    const date = Number.isFinite(resetAt)
      ? new Date(resetAt).toLocaleDateString(localeOf(hass), { day: "2-digit", month: "2-digit" }) : "";
    const details = [
      pct === null ? "" : t(hass, "of_threshold", { pct, h: Math.round(threshold / 60) }),
      date ? t(hass, "replaced_on", { date }) : "",
    ].filter(Boolean).join(" · ");
    const time = formatMinutes(minutes);
    const canReset = Boolean(ents.bladeReset) && this._show("show_controls");

    let action = "";
    if (canReset && this._confirmReset) {
      action = `<div class="confirm" role="alertdialog">`
        + `<div class="confirm-title"><ha-icon icon="mdi:alert-outline"></ha-icon>${escapeHtml(t(hass, "reset_title"))}</div>`
        + `<div class="confirm-body">${escapeHtml(t(hass, "reset_body", { time }))}</div>`
        + `<div class="confirm-actions"><button class="plain" data-action="reset-cancel">${escapeHtml(t(hass, "cancel"))}</button>`
        + `<button class="danger" data-action="reset-confirm"${this._busy ? " disabled" : ""}>${escapeHtml(t(hass, "reset"))}</button></div></div>`;
    }
    const button = canReset && !this._confirmReset
      ? `<button class="toggle" data-action="reset-ask"><ha-icon icon="mdi:restore"></ha-icon><span>${escapeHtml(t(hass, "reset"))}</span></button>`
      : "";
    return `<div class="blades"><div class="blades-row">`
      + `<span><ha-icon icon="mdi:saw-blade"></ha-icon> ${escapeHtml(t(hass, "blades"))} `
      + `<b>${escapeHtml(time)}</b></span>${button}</div>`
      + (pct === null ? "" : `<div class="bar"><div class="bar-fill${level}" style="width:${pct}%"></div></div>`)
      + (details ? `<div class="blades-details">${escapeHtml(details)}</div>` : "")
      + `${action}${this._notice && canReset ? `<div class="notice ${this._notice.ok ? "ok" : "error"}">${escapeHtml(this._notice.text)}</div>` : ""}</div>`;
  }

  async _toggleParty() {
    const ents = this._entities();
    const partyObj = ents?.party ? this._hass.states[ents.party] : undefined;
    if (!usable(partyObj)) return;
    try {
      await this._hass.callService("switch", partyObj.state === "on" ? "turn_off" : "turn_on", {}, { entity_id: ents.party });
    } catch (err) {
      this._notify(false, err);
    }
  }

  _askReset() {
    this._confirmReset = true;
    this._render();
    if (this._resetTimer) clearTimeout(this._resetTimer);
    if (typeof setTimeout === "function") {
      this._resetTimer = setTimeout(() => { this._confirmReset = false; this._render(); }, 10000);
    }
  }

  _cancelReset() {
    if (this._resetTimer) clearTimeout(this._resetTimer);
    this._confirmReset = false;
    this._render();
  }

  async _confirmBladeReset() {
    const ents = this._entities();
    if (!this._confirmReset || !ents?.bladeReset || this._busy) return;
    if (this._resetTimer) clearTimeout(this._resetTimer);
    this._busy = true;
    this._render();
    try {
      await this._hass.callService("button", "press", {}, { entity_id: ents.bladeReset });
      this._confirmReset = false;
      this._notify(true);
    } catch (err) {
      this._notify(false, err);
    } finally {
      this._busy = false;
      this._render();
    }
  }

  _schedule(ents) {
    const hass = this._hass;
    const scheduleObj = hass.states[ents.schedule];
    if (!scheduleObj) return "";
    const days = Array.isArray(scheduleObj.attributes?.by_day) ? scheduleObj.attributes.by_day : [];
    const nextObj = hass.states[ents.nextSchedule];
    const current = currentSlot(hass.states[ents.calendar]);
    const next = current
      ? `<span class="now">${escapeHtml(t(hass, "now_slot", { range: `${current.start}-${current.end}` }))}</span>`
      : usable(nextObj)
        ? `<span>${escapeHtml(`${t(hass, "next")} : ${formatState(hass, nextObj)}`)}</span>`
        : "";
    const open = this._scheduleOpen;
    const head = `<button class="sched-head" data-action="schedule" aria-expanded="${open}">`
      + `<ha-icon icon="mdi:calendar-clock"></ha-icon><span class="sched-title">${escapeHtml(t(hass, "schedule"))}</span>`
      + `<span class="sched-next">${next}</span>`
      + `<ha-icon class="chevron" icon="${open ? "mdi:chevron-up" : "mdi:chevron-down"}"></ha-icon></button>`;
    if (!open) return `<div class="schedule">${head}</div>`;
    const rows = days.length ? days.map((day) => {
      const slots = (Array.isArray(day?.slots) ? day.slots : []).map((slot) => {
        const zones = Array.isArray(slot?.zone_names) && slot.zone_names.length
          ? slot.zone_names.join(", ") : "";
        const order = slot?.zone_order === "ordered" ? t(hass, "order_fixed")
          : (slot?.zone_order === "auto" && zones ? t(hass, "order_auto") : "");
        const extra = [zones, order, slot?.boundary ? t(hass, "edge") : ""].filter(Boolean).join(" · ");
        const isNow = Boolean(current) && day?.day === current.day && slot?.start === current.start;
        return `<div class="slot${isNow ? " current" : ""}"><span class="slot-time">${escapeHtml(slot?.start)}-${escapeHtml(slot?.end)}</span>`
          + `<span class="slot-extra">${escapeHtml(extra)}</span></div>`;
      }).join("");
      return `<div class="day"><span class="day-label">${escapeHtml(day?.day_label ?? day?.day)}</span>`
        + `<div class="day-slots">${slots}</div></div>`;
    }).join("") : `<div class="notice">${escapeHtml(t(hass, "no_slots"))}</div>`;
    return `<div class="schedule">${head}<div class="sched-body">${rows}</div></div>`;
  }

  _controls(ents) {
    const hass = this._hass;
    const mowerObj = hass.states[ents.mower];
    const features = Number(mowerObj?.attributes?.supported_features) || 0;
    const state = mowerObj?.state;
    const alive = usable(mowerObj);
    const buttons = [
      ["start_mowing", FEATURE_START, "mdi:play", "start", state !== "mowing"],
      ["pause", FEATURE_PAUSE, "mdi:pause", "pause", state === "mowing" || state === "returning"],
      ["dock", FEATURE_DOCK, "mdi:home-import-outline", "dock", state !== "docked" && state !== "returning"],
    ].filter(([, bit]) => features & bit);
    if (!buttons.length) return "";
    return `<div class="controls">${buttons.map(([service, , icon, label, enabled]) =>
      `<button class="control" data-action="mower" data-service="${service}"${alive && enabled ? "" : " disabled"}>`
      + `<ha-icon icon="${icon}"></ha-icon><span>${escapeHtml(t(hass, label))}</span></button>`).join("")}</div>`;
  }

  _map(ents) {
    const url = this._mapUrl();
    if (!ents.camera) return "";
    if (!url) return `<div class="map-empty">${escapeHtml(t(this._hass, "map_unavailable"))}</div>` + this._progressBar(ents);
    const fit = ["contain", "cover", "fill", "scale-down"].includes(this._config.fit) ? this._config.fit : "contain";
    const ratio = /^[\d.\s/]+$/u.test(String(this._config.aspect_ratio)) ? this._config.aspect_ratio : DEFAULTS.aspect_ratio;
    return `<div class="map-wrap" style="aspect-ratio:${ratio}"><img class="map link" alt="RTK" style="object-fit:${fit}" src="${escapeHtml(url)}"${moreInfo(ents.camera)}></div>`
      + this._progressBar(ents);
  }

  /** A thin bar under the map: the day's estimated progress, nothing else. */
  _progressBar(ents) {
    const hass = this._hass;
    const progressObj = hass.states[ents.progress];
    if (!usable(progressObj)) return "";
    const pct = Math.max(0, Math.min(100, Number(progressObj.state)));
    if (!Number.isFinite(pct)) return "";
    return `<div class="map-progress link" title="${escapeHtml(formatState(hass, progressObj))}"${moreInfo(ents.progress)}>`
      + `<div class="map-progress-fill" style="width:${Math.round(pct * 10) / 10}%"></div></div>`;
  }

  _zones(ents) {
    const hass = this._hass;
    if (!ents.zones.length || !ents.mower || !this._show("show_controls")) return "";
    const known = new Set(ents.zones.map((z) => z.id));
    this._selected = this._selected.filter((id) => known.has(id));
    const fixed = this._order === "fixed";

    const chips = ents.zones.map((zone) => {
      const name = zone.name || `${t(hass, "zone")} ${zone.id}`;
      const rank = this._selected.indexOf(zone.id);
      const checked = rank >= 0;
      const mark = checked ? (fixed ? rank + 1 : "✓") : "";
      return `<button class="zone-chip${checked ? " on" : ""}" role="checkbox" aria-checked="${checked}"`
        + ` data-action="zone" data-zone="${zone.id}" title="${escapeHtml(name)}">`
        + `<span class="check${checked ? " on" : ""}" aria-hidden="true">${mark}</span>`
        + `<span class="zone-name">${escapeHtml(name)}</span></button>`;
    }).join("");

    const mowerAlive = usable(hass.states[ents.mower]);
    const ready = this._selected.length > 0 && mowerAlive && !this._busy;
    const notice = this._notice
      ? `<div class="notice ${this._notice.ok ? "ok" : "error"}">${escapeHtml(this._notice.text)}</div>`
      : "";
    const go = `<button class="go" data-action="go" title="${escapeHtml(this._selected.length ? t(hass, "go") : t(hass, "pick"))}"${ready ? "" : " disabled"}>`
      + `<ha-icon icon="mdi:play"></ha-icon><span>${escapeHtml(t(hass, "go"))}</span></button>`;
    const open = this._zonesOpen;
    const head = `<div class="zones-head">`
      + `<button class="zones-toggle" data-action="zones-toggle" aria-expanded="${open}">`
      + `<ha-icon icon="${open ? "mdi:chevron-down" : "mdi:chevron-right"}"></ha-icon>`
      + `<span class="zones-titles"><span class="section">${escapeHtml(t(hass, "one_time"))}</span>`
      + `<span class="zones-summary">${escapeHtml(this._zoneSummary(ents))}</span></span></button>${go}</div>`;
    if (!open) return `<div class="zones">${head}${notice}</div>`;

    const actions = `<div class="zone-actions">`
      + `<div class="segmented" role="group" aria-label="${escapeHtml(t(hass, "order"))}">`
      + `<button data-action="order" data-order="fixed" aria-pressed="${fixed}" class="${fixed ? "on" : ""}">${escapeHtml(t(hass, "order_fixed"))}</button>`
      + `<button data-action="order" data-order="auto" aria-pressed="${!fixed}" class="${fixed ? "" : "on"}">${escapeHtml(t(hass, "order_auto"))}</button></div>`
      + `<button class="toggle${this._edge ? " on" : ""}" data-action="edge" aria-pressed="${this._edge}">`
      + `<ha-icon icon="mdi:border-outside"></ha-icon><span>${escapeHtml(t(hass, "edge"))}</span></button></div>`;

    return `<div class="zones">${head}<div class="zone-chips">${chips}</div>${actions}${notice}</div>`;
  }

  /** One line saying what Start will send: the zones, the order and the edge cut. */
  _zoneSummary(ents) {
    const hass = this._hass;
    if (!this._selected.length) return t(hass, "pick");
    const byId = new Map(ents.zones.map((z) => [z.id, z.name || `${t(hass, "zone")} ${z.id}`]));
    const ids = this._order === "fixed" ? this._selected : [...this._selected].sort((a, b) => a - b);
    const parts = [ids.map((id) => byId.get(id)).filter(Boolean).join(", "),
      t(hass, this._order === "fixed" ? "order_fixed" : "order_auto")];
    if (this._edge) parts.push(t(hass, "edge"));
    return parts.join(" · ");
  }

  /** The last one-time settings, kept per mower in this browser only. */
  _loadZoneSettings(entity) {
    const key = `worx-vision-card:${entity}`;
    if (this._settingsKey === key) return;
    this._settingsKey = key;
    try {
      const saved = JSON.parse(globalThis.localStorage?.getItem(key) || "null");
      if (!saved || typeof saved !== "object") return;
      if (Array.isArray(saved.zones)) {
        this._selected = saved.zones.map(Number).filter((id) => Number.isInteger(id) && id > 0);
      }
      if (saved.order === "fixed" || saved.order === "auto") this._order = saved.order;
      if (typeof saved.edge === "boolean") this._edge = saved.edge;
    } catch (_err) {
      // Private window, blocked storage or a damaged value: start from the defaults.
    }
  }

  _saveZoneSettings() {
    if (!this._settingsKey) return;
    try {
      globalThis.localStorage?.setItem(this._settingsKey,
        JSON.stringify({ zones: this._selected, order: this._order, edge: this._edge }));
    } catch (_err) {
      // Storage unavailable: the settings only last until the page is reloaded.
    }
  }

  _onClick(ev) {
    const path = typeof ev.composedPath === "function" ? ev.composedPath() : [ev.target];
    const target = path.find((node) => node?.dataset?.action);
    if (!target || target.disabled) return;
    const { action } = target.dataset;
    if (action === "more-info") this._moreInfo(target.dataset.entity);
    else if (action === "mower") this._callMower(target.dataset.service);
    else if (action === "zone") this._toggleZone(Number(target.dataset.zone));
    else if (action === "order") this._setOrder(target.dataset.order);
    else if (action === "edge") this._setEdge(!this._edge);
    else if (action === "zones-toggle") { this._zonesOpen = !this._zonesOpen; this._render(); }
    else if (action === "go") this._startZones();
    else if (action === "schedule") { this._scheduleOpen = !this._scheduleOpen; this._render(); }
    else if (action === "party") this._toggleParty();
    else if (action === "reset-ask") this._askReset();
    else if (action === "reset-cancel") this._cancelReset();
    else if (action === "reset-confirm") this._confirmBladeReset();
  }

  _moreInfo(entityId) {
    if (!entityId || !this._hass?.states?.[entityId]) return;
    this.dispatchEvent(new CustomEvent("hass-more-info", {
      detail: { entityId }, bubbles: true, composed: true,
    }));
  }

  _toggleZone(id) {
    if (!Number.isInteger(id) || id < 1) return;
    this._notice = null;
    this._selected = this._selected.includes(id)
      ? this._selected.filter((z) => z !== id)
      : [...this._selected, id];
    this._saveZoneSettings();
    this._render();
  }

  _setOrder(order) {
    if (order !== "fixed" && order !== "auto") return;
    this._order = order;
    this._saveZoneSettings();
    this._render();
  }

  _setEdge(value) {
    this._edge = Boolean(value);
    this._saveZoneSettings();
    this._render();
  }

  async _callMower(service) {
    const ents = this._entities();
    if (!ents?.mower || !["start_mowing", "pause", "dock"].includes(service)) return;
    try {
      await this._hass.callService("lawn_mower", service, {}, { entity_id: ents.mower });
    } catch (err) {
      this._notify(false, err);
    }
  }

  /** The payload of worx_vision_cloud.start_zone_mowing, or null if nothing is ticked. */
  _zonePayload() {
    const ents = this._entities();
    if (!ents?.mower || !this._selected.length) return null;
    const zones = this._order === "fixed"
      ? [...this._selected]
      : [...this._selected].sort((a, b) => a - b);
    return { entity_id: ents.mower, zones, zone_order: this._order, edge_cut: this._edge };
  }

  async _startZones() {
    const payload = this._zonePayload();
    if (!payload || this._busy) return;
    this._busy = true;
    this._notice = null;
    this._render();
    try {
      await this._hass.callService(DOMAIN, "start_zone_mowing", payload);
      this._notify(true);
    } catch (err) {
      this._notify(false, err);
    } finally {
      this._busy = false;
      this._render();
    }
  }

  _notify(ok, err) {
    const text = ok ? t(this._hass, "sent") : `${t(this._hass, "failed")}: ${err?.message || err || ""}`;
    this._notice = { ok, text };
    this._render();
    if (this._noticeTimer) clearTimeout(this._noticeTimer);
    if (typeof setTimeout === "function") {
      this._noticeTimer = setTimeout(() => { this._notice = null; this._render(); }, 6000);
    }
  }
}

const STYLES = `
  :host { display: block; }
  ha-card { overflow: hidden; }
  .header { display: flex; align-items: center; gap: 12px; padding: 16px 16px 8px; }
  .titles { flex: 1; min-width: 0; }
  .title { font-size: 1.2em; font-weight: 500; color: var(--primary-text-color); }
  .status { color: var(--secondary-text-color); margin-top: 2px; }
  .link { cursor: pointer; }
  .link:hover { text-decoration: underline; text-underline-offset: 2px; }
  img.link:hover, .chip.link:hover, .battery.link:hover, .wifi.link:hover { text-decoration: none; filter: brightness(1.08); }
  .error-banner { display: flex; gap: 10px; align-items: center; margin: 0 16px 10px; padding: 10px 12px;
    border-radius: 10px; background: rgba(219, 68, 55, 0.12); color: var(--error-color, #db4437);
    border: 1px solid var(--error-color, #db4437); }
  .error-title { font-weight: 500; }
  .error-when { font-size: 0.85em; opacity: 0.9; }
  .blades { padding: 10px 16px 14px; border-top: 1px solid var(--divider-color); }
  .blades-row { display: flex; align-items: center; justify-content: space-between; gap: 8px; color: var(--primary-text-color); }
  .blades-row b { font-weight: 500; }
  .bar { height: 6px; border-radius: 3px; background: var(--secondary-background-color); margin-top: 8px; overflow: hidden; }
  .bar-fill { height: 100%; border-radius: 3px; background: var(--success-color, #43a047); }
  .bar-fill.warn { background: var(--warning-color, #ff9800); }
  .bar-fill.bad { background: var(--error-color, #db4437); }
  .blades-details { font-size: 0.8em; color: var(--secondary-text-color); margin-top: 4px; }
  .confirm { margin-top: 10px; padding: 10px 12px; border-radius: 10px; background: rgba(255, 152, 0, 0.12);
    border: 1px solid var(--warning-color, #ff9800); color: var(--primary-text-color); }
  .confirm-title { display: flex; align-items: center; gap: 6px; font-weight: 500; }
  .confirm-body { font-size: 0.9em; margin: 4px 0 10px; color: var(--secondary-text-color); }
  .confirm-actions { display: flex; justify-content: flex-end; gap: 8px; }
  .confirm-actions button { padding: 6px 12px; border-radius: 16px; }
  .confirm-actions .plain { background: var(--secondary-background-color); color: var(--primary-text-color); }
  .confirm-actions .danger { background: var(--error-color, #db4437); color: #fff; }
  .corner-col { display: flex; flex-direction: column; align-items: flex-end; gap: 6px; }
  .party { display: inline-flex; align-items: center; gap: 4px; padding: 3px 10px; border-radius: 14px;
    font-size: 0.85em; background: var(--secondary-background-color); color: var(--primary-text-color);
    border: 1px solid transparent; }
  .party ha-icon { --mdc-icon-size: 16px; width: 16px; height: 16px; }
  .party.on { background: rgba(21, 101, 192, 0.14); color: #1565c0; border-color: #1565c0; }
  .rain-banner { display: flex; gap: 10px; align-items: center; margin: 0 16px 10px; padding: 10px 12px;
    border-radius: 10px; background: rgba(3, 169, 244, 0.12); color: #0277bd; border: 1px solid #03a9f4; }
  .rain-title { font-weight: 500; }
  .rain-detail { font-size: 0.85em; }
  .party-banner { display: flex; gap: 8px; align-items: center; margin: 0 16px 10px; padding: 8px 12px;
    border-radius: 10px; background: rgba(21, 101, 192, 0.12); color: #1565c0; font-size: 0.9em; }
  .corner { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; justify-content: flex-end; }
  .wifi { display: flex; align-items: center; gap: 4px; color: var(--primary-text-color); white-space: nowrap; }
  .battery { display: flex; align-items: center; gap: 4px; color: var(--primary-text-color); white-space: nowrap; }
  .battery ha-icon, .wifi ha-icon { --mdc-icon-size: 18px; width: 18px; height: 18px; }
  .lvl-good { color: var(--success-color, #43a047); }
  .lvl-warn { color: var(--warning-color, #ff9800); }
  .lvl-bad { color: var(--error-color, #db4437); }
  .muted { color: var(--secondary-text-color); font-size: 0.85em; }
  .controls { display: flex; gap: 8px; padding: 4px 16px 12px; flex-wrap: wrap; }
  button { font: inherit; cursor: pointer; border: none; }
  button[disabled] { cursor: default; opacity: 0.4; }
  .control, .toggle, .go { display: inline-flex; align-items: center; gap: 6px; padding: 8px 12px;
    border-radius: 18px; background: var(--secondary-background-color); color: var(--primary-text-color); }
  .control { flex: 1; justify-content: center; }
  .map-wrap { width: 100%; background: #050607; }
  img.map { display: block; width: 100%; height: 100%; }
  .map-empty, .warning { padding: 24px 16px; text-align: center; color: var(--secondary-text-color); }
  .warning { color: var(--error-color, #db4437); }
  .zones { padding: 4px 16px 12px; }
  .zones-head { display: flex; align-items: center; gap: 8px; }
  .zones-toggle { flex: 1; min-width: 0; display: flex; align-items: center; gap: 6px; padding: 4px 0;
    background: transparent; color: var(--primary-text-color); text-align: left; }
  .zones-toggle ha-icon { flex: none; color: var(--secondary-text-color); }
  .zones-titles { min-width: 0; display: flex; flex-direction: column; }
  .zones-titles .section { margin: 0; }
  .zones-summary { font-size: 0.85em; color: var(--secondary-text-color); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .zones-head + .zone-chips { margin-top: 8px; }
  .map-progress { height: 4px; background: var(--secondary-background-color); }
  .map-progress-fill { height: 100%; background: var(--success-color, #43a047); }
  .section { font-weight: 500; margin: 4px 0 6px; color: var(--primary-text-color); }
  .zone-chips { display: flex; flex-wrap: wrap; gap: 6px; }
  .zone-chip { flex: 1 1 calc(50% - 6px); min-width: 0; display: flex; align-items: center; gap: 8px;
    padding: 6px 10px; border-radius: 10px; background: var(--secondary-background-color);
    color: var(--primary-text-color); border: 1px solid transparent; text-align: left; }
  .zone-chip.on { border-color: var(--primary-color); }
  .check { flex: none; width: 20px; height: 20px; border-radius: 6px; border: 2px solid var(--secondary-text-color);
    display: grid; place-items: center; font-size: 0.75em; font-weight: 700; box-sizing: border-box; }
  .check.on { background: var(--primary-color); border-color: var(--primary-color); color: var(--text-primary-color, #fff); }
  .zone-name { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .zone-actions { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-top: 8px; }
  .segmented { display: inline-flex; border-radius: 18px; overflow: hidden; background: var(--secondary-background-color); }
  .segmented button { padding: 8px 12px; background: transparent; color: var(--primary-text-color); }
  .segmented button.on, .toggle.on { background: var(--primary-color); color: var(--text-primary-color, #fff); }
  .go { flex: none; margin-left: auto; background: var(--primary-color); color: var(--text-primary-color, #fff); }
  .notice { margin-top: 8px; color: var(--secondary-text-color); font-size: 0.9em; }
  .notice.ok { color: var(--success-color, #43a047); }
  .notice.error { color: var(--error-color, #db4437); }
  .chips { display: flex; flex-wrap: wrap; gap: 6px; padding: 0 16px 10px; }
  .chip { display: inline-flex; align-items: center; gap: 4px; padding: 3px 10px; border-radius: 12px;
    font-size: 0.85em; background: var(--secondary-background-color); color: var(--primary-text-color); }
  .chip ha-icon { --mdc-icon-size: 16px; width: 16px; height: 16px; }
  .chip.good ha-icon { color: var(--success-color, #43a047); }
  .chip.warn ha-icon { color: var(--warning-color, #ff9800); }
  .chip.bad { color: var(--error-color, #db4437); }
  .schedule { padding: 0 16px 12px; }
  .sched-head { display: flex; align-items: center; gap: 8px; width: 100%; padding: 10px 0;
    background: transparent; color: var(--primary-text-color); border-top: 1px solid var(--divider-color); text-align: left; }
  .sched-title { font-weight: 500; }
  .sched-next { flex: 1; color: var(--secondary-text-color); font-size: 0.9em; text-align: right; }
  .day { display: grid; grid-template-columns: 3.5em 1fr; gap: 8px; padding: 6px 0; border-bottom: 1px solid var(--divider-color); }
  .day-label { font-weight: 500; text-transform: capitalize; color: var(--primary-text-color); }
  .slot { display: flex; flex-wrap: wrap; gap: 4px 10px; }
  .slot-time { color: var(--primary-text-color); font-variant-numeric: tabular-nums; }
  .slot.current .slot-time { color: var(--primary-color); font-weight: 500; }
  .sched-next .now { color: var(--primary-color); font-weight: 500; }
  .slot-extra { color: var(--secondary-text-color); font-size: 0.9em; }
`;

const EDITOR_SCHEMA = [
  { name: "entity", required: true, selector: { entity: { domain: "lawn_mower", integration: DOMAIN } } },
  { name: "title", selector: { text: {} } },
  // Two switches per row: ha-form rows have a fixed height, so a grid is
  // the only reliable way to shorten the editor.
  {
    type: "grid", name: "", flatten: true, column_min_width: "150px",
    schema: [
      { name: "show_info", selector: { boolean: {} } },
      { name: "show_controls", selector: { boolean: {} } },
      { name: "show_map", selector: { boolean: {} } },
      { name: "show_zones", selector: { boolean: {} } },
      { name: "show_schedule", selector: { boolean: {} } },
      { name: "show_blades", selector: { boolean: {} } },
      { name: "show_values", selector: { boolean: {} } },
    ],
  },
  { name: "refresh_interval", selector: { number: { min: 0, max: 3600, mode: "box", unit_of_measurement: "s" } } },
];

class WorxVisionCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = { ...config };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    if (this._form) this._form.hass = hass;
    else this._render();
  }

  _render() {
    if (!this._hass || !this._config) return;
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.computeLabel = (schema) => t(this._hass, `ed_${schema.name}`);
      this._form.addEventListener("value-changed", (ev) => this._valueChanged(ev));
      for (const name of ["focusin", "pointerdown", "keydown"]) {
        this.addEventListener(name, () => { this._touched = true; });
      }
      this.appendChild(this._form);
    }
    this._form.hass = this._hass;
    this._form.schema = EDITOR_SCHEMA;
    this._form.data = { ...DEFAULTS, ...this._config };
  }

  _valueChanged(ev) {
    const value = { ...(ev?.detail?.value || {}) };
    // A freshly built picker can announce an empty value before it knows its
    // own: never let that wipe a configured mower unless the user did it.
    if (!value.entity && this._config?.entity && !this._touched) return;
    if (!value.title) delete value.title;
    for (const [key, def] of Object.entries(DEFAULTS)) {
      if (value[key] === def && !(key in (this._config || {}))) delete value[key];
    }
    const next = { ...this._config, ...value };
    if (!value.title) delete next.title;
    if (stableStringify(next) === stableStringify(this._config)) return;
    this._config = next;
    this.dispatchEvent(new CustomEvent("config-changed", {
      detail: { config: next }, bubbles: true, composed: true,
    }));
  }
}

// The standalone RTK map card this one replaces. Same element names, so the
// dashboards that used it keep working: pointed at the camera, it shows the map.
class WorxMapRtkCard extends WorxVisionCard {}
class WorxMapRtkInfoCard extends WorxVisionCard {}

const ELEMENTS = [
  ["worx-vision-card", WorxVisionCard],
  ["worx-vision-card-editor", WorxVisionCardEditor],
  ["worx-map-rtk-card", WorxMapRtkCard],
  ["worx-map-rtk-info-card", WorxMapRtkInfoCard],
];
for (const [name, cls] of ELEMENTS) {
  if (!customElements.get(name)) customElements.define(name, cls);
}

window.customCards = window.customCards || [];
if (!window.customCards.some((c) => c.type === "worx-vision-card")) {
  window.customCards.push({
    type: "worx-vision-card",
    name: "Worx Landroid Vision",
    description: "Status, controls, RTK map and one-time zone mowing for Worx Landroid Vision and RTK mowers.",
    preview: true,
    documentationURL: "https://github.com/ADNPolymerase/ha-landroid-vision",
  });
}

WorxVisionCard.resolveEntities = resolveEntities;
WorxVisionCard.I18N = I18N;
WorxVisionCard.stableStringify = stableStringify;
