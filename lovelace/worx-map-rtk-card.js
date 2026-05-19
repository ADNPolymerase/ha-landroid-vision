class WorxMapRtkCard extends HTMLElement {
  static getStubConfig() {
    return {
      entity: "camera.halina_mapa_rtk",
      refresh_interval: 30,
      show_info: true,
    };
  }

  setConfig(config) {
    if (!config || (!config.entity && !config.camera_entity)) {
      throw new Error("Worx Map RTK card requires a camera entity");
    }

    this._config = {
      refresh_interval: 30,
      fit: "contain",
      aspect_ratio: "900 / 620",
      show_info: true,
      ...config,
    };
    this._entity = this._config.entity || this._config.camera_entity;
    this._cacheBuster = Date.now();
    this._render();
    this._resetTimer();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  connectedCallback() {
    this._resetTimer();
  }

  disconnectedCallback() {
    this._clearTimer();
  }

  getCardSize() {
    return 4;
  }

  _resetTimer() {
    this._clearTimer();
    const seconds = Number(this._config?.refresh_interval);
    if (!Number.isFinite(seconds) || seconds <= 0) {
      return;
    }
    this._timer = window.setInterval(() => {
      this._cacheBuster = Date.now();
      this._render();
    }, seconds * 1000);
  }

  _clearTimer() {
    if (this._timer) {
      window.clearInterval(this._timer);
      this._timer = undefined;
    }
  }

  _imageUrl(state) {
    const entityPicture = state?.attributes?.entity_picture;
    const baseUrl = entityPicture || `/api/camera_proxy/${this._entity}`;
    const separator = baseUrl.includes("?") ? "&" : "?";
    return `${baseUrl}${separator}worx_map_rtk=${this._cacheBuster}`;
  }

  _robotSlug() {
    const objectId = this._entity?.split(".")?.[1] || "";
    return objectId
      .replace(/_mapa_rtk$/u, "")
      .replace(/_rtk_map$/u, "")
      .replace(/_map$/u, "");
  }

  _pushCandidates(target, values) {
    const list = Array.isArray(values) ? values : [values];
    for (const value of list) {
      if (value && !target.includes(value)) {
        target.push(value);
      }
    }
  }

  _entityCandidates(kind) {
    const slug = this._robotSlug();
    const candidates = [];

    if (kind === "battery") {
      this._pushCandidates(candidates, this._config.battery_entity);
      this._pushCandidates(candidates, [
        `sensor.${slug}_bateria`,
        `sensor.${slug}_bateria_2`,
        `sensor.${slug}_battery_percent`,
        `sensor.${slug}_battery_percent_2`,
        `sensor.${slug}_battery`,
        `sensor.${slug}_battery_2`,
      ]);
    }

    if (kind === "signal") {
      this._pushCandidates(candidates, this._config.signal_entity);
      this._pushCandidates(candidates, [
        `sensor.${slug}_rssi`,
        `sensor.${slug}_rssi_2`,
        `sensor.${slug}_sygnal_wifi`,
        `sensor.${slug}_sygnal_wifi_2`,
        `sensor.${slug}_sila_sygnalu_wifi`,
        `sensor.${slug}_sila_sygnalu_wifi_2`,
        `sensor.${slug}_wifi_signal`,
        `sensor.${slug}_wifi_signal_2`,
        `sensor.${slug}_signal_strength`,
        `sensor.${slug}_signal_strength_2`,
      ]);
    }

    if (kind === "status") {
      this._pushCandidates(candidates, this._config.status_entity);
      this._pushCandidates(candidates, [
        `sensor.${slug}_status`,
        `sensor.${slug}_status_2`,
        `lawn_mower.${slug}_kosiarka`,
        `lawn_mower.${slug}_kosiarka_2`,
        `lawn_mower.${slug}`,
        `lawn_mower.${slug}_2`,
      ]);
    }

    if (kind === "mower") {
      this._pushCandidates(candidates, this._config.mower_entity);
      this._pushCandidates(candidates, [
        `lawn_mower.${slug}_kosiarka`,
        `lawn_mower.${slug}_kosiarka_2`,
        `lawn_mower.${slug}`,
        `lawn_mower.${slug}_2`,
      ]);
    }

    return candidates;
  }

  _isUsableState(state) {
    return state && !["unknown", "unavailable"].includes(state.state);
  }

  _firstState(kind) {
    const states = this._hass?.states || {};
    for (const entityId of this._entityCandidates(kind)) {
      const state = states[entityId];
      if (this._isUsableState(state)) {
        return { entityId, state };
      }
    }
    return undefined;
  }

  _numberFrom(value) {
    if (value === undefined || value === null || value === "") {
      return undefined;
    }
    const parsed = Number.parseFloat(String(value).replace(",", "."));
    return Number.isFinite(parsed) ? parsed : undefined;
  }

  _clampPercent(value) {
    const number = this._numberFrom(value);
    if (number === undefined) {
      return undefined;
    }
    return Math.max(0, Math.min(100, Math.round(number)));
  }

  _attrNumber(state, names) {
    for (const name of names) {
      const value = this._numberFrom(state?.attributes?.[name]);
      if (value !== undefined) {
        return value;
      }
    }
    return undefined;
  }

  _batteryInfo() {
    const battery = this._firstState("battery")?.state;
    const mower = this._firstState("mower")?.state;
    const percent =
      this._clampPercent(battery?.state) ??
      this._clampPercent(
        this._attrNumber(mower, ["battery_percent", "battery_level", "battery"])
      );
    const charging =
      battery?.attributes?.charging === true ||
      this._normalize(this._firstState("status")?.state?.state).includes("ladow");

    return {
      label: percent === undefined ? "--" : `${percent}%`,
      icon: this._batteryIcon(percent, charging),
      percent,
      charging,
    };
  }

  _batteryIcon(percent, charging) {
    if (charging) {
      return "mdi:battery-charging";
    }
    if (percent === undefined) {
      return "mdi:battery-unknown";
    }
    if (percent >= 90) {
      return "mdi:battery-high";
    }
    if (percent >= 40) {
      return "mdi:battery-medium";
    }
    return "mdi:battery-low";
  }

  _signalInfo() {
    const signal = this._firstState("signal")?.state;
    const raw =
      this._numberFrom(signal?.state) ??
      this._attrNumber(signal, ["rssi", "wifi_signal", "signal_strength"]);
    const unit = String(signal?.attributes?.unit_of_measurement || "").toLowerCase();
    let percent;

    if (raw !== undefined && (unit.includes("dbm") || raw < 0)) {
      percent = this._clampPercent((raw + 100) * 2);
    } else {
      percent = this._clampPercent(raw);
    }

    return {
      label: percent === undefined ? "--" : `${percent}%`,
      icon: this._signalIcon(percent),
      percent,
    };
  }

  _signalIcon(percent) {
    if (percent === undefined) {
      return "mdi:wifi-strength-alert-outline";
    }
    if (percent >= 75) {
      return "mdi:wifi-strength-4";
    }
    if (percent >= 50) {
      return "mdi:wifi-strength-3";
    }
    if (percent >= 25) {
      return "mdi:wifi-strength-2";
    }
    return "mdi:wifi-strength-1";
  }

  _workMode() {
    const status = this._firstState("status")?.state;
    const mower = this._firstState("mower")?.state;
    const values = [
      status?.state,
      status?.attributes?.raw_description,
      status?.attributes?.status_description,
      mower?.state,
      mower?.attributes?.activity,
      mower?.attributes?.status_description,
    ];
    const normalized = values.map((value) => this._normalize(value)).join(" ");

    if (
      normalized.includes("krawed") ||
      normalized.includes("obrzez") ||
      normalized.includes("obzer") ||
      normalized.includes("edge") ||
      normalized.includes("border")
    ) {
      return {
        label: "Obrze\u017ca",
        icon: "mdi:border-outside",
        tone: "edge",
      };
    }

    if (
      normalized.includes("koszenie") ||
      normalized.includes("mowing") ||
      normalized.includes("cutting") ||
      normalized.includes("mow")
    ) {
      return {
        label: "Koszenie",
        icon: "mdi:robot-mower",
        tone: "mowing",
      };
    }

    if (normalized.includes("ladow") || normalized.includes("charging")) {
      return {
        label: "\u0141adowanie",
        icon: "mdi:battery-charging",
        tone: "idle",
      };
    }

    if (
      normalized.includes("wraca") ||
      normalized.includes("powrot") ||
      normalized.includes("return")
    ) {
      return {
        label: "Wraca",
        icon: "mdi:home-import-outline",
        tone: "idle",
      };
    }

    if (
      normalized.includes("baza") ||
      normalized.includes("docked") ||
      normalized.includes("home")
    ) {
      return {
        label: "W bazie",
        icon: "mdi:home-map-marker",
        tone: "idle",
      };
    }

    return {
      label: status?.state || mower?.state || "Brak danych",
      icon: "mdi:information-outline",
      tone: "idle",
    };
  }

  _normalize(value) {
    return String(value ?? "")
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/gu, "");
  }

  _escape(value) {
    return String(value ?? "")
      .replace(/&/gu, "&amp;")
      .replace(/</gu, "&lt;")
      .replace(/>/gu, "&gt;")
      .replace(/"/gu, "&quot;")
      .replace(/'/gu, "&#39;");
  }

  _infoHtml() {
    if (this._config.show_info === false) {
      return "";
    }

    const battery = this._batteryInfo();
    const signal = this._signalInfo();
    const mode = this._workMode();

    return `
      <div class="info" aria-label="Informacje z robota">
        ${this._tileHtml({
          title: "Bateria",
          value: battery.label,
          icon: battery.icon,
          tone: battery.percent !== undefined && battery.percent < 25 ? "warn" : "",
        })}
        ${this._tileHtml({
          title: "Sygna\u0142 Wi-Fi",
          value: signal.label,
          icon: signal.icon,
          tone: signal.percent !== undefined && signal.percent < 25 ? "warn" : "",
        })}
        ${this._tileHtml({
          title: "Tryb pracy",
          value: mode.label,
          icon: mode.icon,
          tone: mode.tone,
        })}
      </div>
    `;
  }

  _tileHtml({ title, value, icon, tone }) {
    return `
      <div class="tile ${this._escape(tone)}">
        <ha-icon icon="${this._escape(icon)}"></ha-icon>
        <div class="tile-text">
          <div class="tile-title">${this._escape(title)}</div>
          <div class="tile-value">${this._escape(value)}</div>
        </div>
      </div>
    `;
  }

  _render() {
    if (!this._config) {
      return;
    }

    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
    }

    const state = this._hass?.states?.[this._entity];
    const unavailable = !state || ["unavailable", "unknown"].includes(state.state);
    const imageUrl = unavailable ? "" : this._imageUrl(state);
    const fit = ["contain", "cover", "fill", "scale-down"].includes(this._config.fit)
      ? this._config.fit
      : "contain";

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
        }
        ha-card {
          overflow: hidden;
          background: #050607;
          border-radius: var(--ha-card-border-radius, 12px);
        }
        .map {
          position: relative;
          width: 100%;
          aspect-ratio: ${this._config.aspect_ratio};
          background: #050607;
        }
        img {
          display: block;
          width: 100%;
          height: 100%;
          object-fit: ${fit};
          background: #050607;
        }
        .info {
          position: absolute;
          left: 10px;
          right: 10px;
          bottom: 10px;
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 8px;
          pointer-events: none;
        }
        .tile {
          min-width: 0;
          display: grid;
          grid-template-columns: 22px minmax(0, 1fr);
          align-items: center;
          gap: 8px;
          padding: 8px 10px;
          border: 1px solid rgba(255, 255, 255, 0.12);
          border-radius: 10px;
          background: rgba(4, 6, 7, 0.76);
          box-shadow: 0 8px 22px rgba(0, 0, 0, 0.28);
          color: #f4f7f2;
          backdrop-filter: blur(8px);
        }
        .tile ha-icon {
          width: 22px;
          height: 22px;
          color: #d9e1d5;
        }
        .tile-text {
          min-width: 0;
        }
        .tile-title {
          overflow: hidden;
          color: rgba(244, 247, 242, 0.66);
          font: 700 10px/1.2 var(--paper-font-body1_-_font-family, sans-serif);
          text-overflow: ellipsis;
          text-transform: uppercase;
          white-space: nowrap;
        }
        .tile-value {
          overflow: hidden;
          margin-top: 2px;
          color: #f9fbf7;
          font: 800 15px/1.15 var(--paper-font-body1_-_font-family, sans-serif);
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .tile.mowing ha-icon,
        .tile.mowing .tile-value {
          color: #8bea5c;
        }
        .tile.edge ha-icon,
        .tile.edge .tile-value {
          color: #ffb15f;
        }
        .tile.warn ha-icon,
        .tile.warn .tile-value {
          color: #ff715f;
        }
        .empty {
          min-height: 220px;
          display: grid;
          place-items: center;
          color: var(--secondary-text-color, #a8b0b8);
          font: 500 15px/1.4 var(--paper-font-body1_-_font-family, sans-serif);
          text-align: center;
          padding: 24px;
        }
        @media (max-width: 420px) {
          .info {
            grid-template-columns: 1fr;
            right: auto;
            width: min(210px, calc(100% - 20px));
          }
        }
      </style>
      <ha-card>
        ${
          unavailable
            ? `<div class="empty">Mapa RTK jest niedost\u0119pna</div>`
            : `<div class="map"><img alt="Worx Map RTK" src="${imageUrl}">${this._infoHtml()}</div>`
        }
      </ha-card>
    `;
  }
}

class WorxMapRtkInfoCard extends WorxMapRtkCard {}

if (!customElements.get("worx-map-rtk-info-card")) {
  customElements.define("worx-map-rtk-info-card", WorxMapRtkInfoCard);
}

if (!customElements.get("worx-map-rtk-card")) {
  customElements.define("worx-map-rtk-card", WorxMapRtkCard);
}

window.customCards = window.customCards || [];
window.customCards.push({
  type: "worx-map-rtk-info-card",
  name: "Worx Map RTK",
  description: "RTK map card for Worx Vision Cloud mowers.",
});
