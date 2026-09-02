"""Update platform for Worx Vision Cloud Plus."""
from __future__ import annotations

from typing import Any

from homeassistant.components.update import UpdateEntity, UpdateEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .entity import WorxVisionEntity
from .helpers import get_dict_value, is_firmware_updating

SUPPORTED_UPDATE_FEATURES = UpdateEntityFeature.INSTALL
if hasattr(UpdateEntityFeature, "RELEASE_NOTES"):
    SUPPORTED_UPDATE_FEATURES |= UpdateEntityFeature.RELEASE_NOTES


def _product_item(device) -> dict[str, Any]:
    """Return cached product item details from the private API."""
    value = getattr(device, "_worx_vision_product_item", {}) or {}
    return value if isinstance(value, dict) else {}


def _firmware_info(device) -> dict[str, Any]:
    """Return cached firmware upgrade metadata."""
    value = getattr(device, "_worx_vision_firmware_upgrade", {}) or {}
    return value if isinstance(value, dict) else {}


def _capabilities(device) -> list[str]:
    """Return product item capabilities."""
    capabilities = get_dict_value(_product_item(device), "capabilities", []) or []
    return list(capabilities) if isinstance(capabilities, list | tuple) else []


def _firmware_version(device) -> str | None:
    """Return current firmware version from all known sources."""
    firmware = getattr(device, "firmware", None)
    if isinstance(firmware, dict):
        value = firmware.get("version")
        if value is not None:
            return str(value)

    value = getattr(firmware, "version", None)
    if value is not None:
        return str(value)

    value = get_dict_value(_product_item(device), "firmware_version")
    return None if value is None else str(value)


DEFAULT_LANGUAGE = "en"

# Worx nests each component's changelog inside the "product" and "head"
# payloads, keyed by language. These label the two sections and cover the case
# where Worx ships an update with no notes at all, which happens often.
HEADING_MOWER = {
    "en": "Mower firmware",
    "fr": "Firmware de la tondeuse",
    "de": "Mäher-Firmware",
    "pl": "Oprogramowanie kosiarki",
    "nl": "Maaier-firmware",
    "es": "Firmware del robot",
    "it": "Firmware del robot",
    "sv": "Klipparens firmware",
    "no": "Klipperens fastvare",
    "da": "Klipperens firmware",
    "ru": "Прошивка газонокосилки",
}
HEADING_HEAD = {
    "en": "Vision head firmware",
    "fr": "Firmware de la tête Vision",
    "de": "Firmware des Vision-Kopfes",
    "pl": "Oprogramowanie głowicy Vision",
    "nl": "Firmware van de Vision-kop",
    "es": "Firmware del cabezal Vision",
    "it": "Firmware della testa Vision",
    "sv": "Firmware för Vision-huvudet",
    "no": "Fastvare for Vision-hodet",
    "da": "Firmware til Vision-hovedet",
    "ru": "Прошивка модуля Vision",
}
NOTES_UNAVAILABLE = {
    "en": "Worx published no release notes for this update. See the Landroid app for details.",
    "fr": "Worx n'a publié aucune note de version pour cette mise à jour. Voir l'application Landroid pour le détail.",
    "de": "Worx hat für dieses Update keine Versionshinweise veröffentlicht. Einzelheiten finden Sie in der Landroid-App.",
    "pl": "Worx nie opublikował informacji o tej aktualizacji. Szczegóły znajdziesz w aplikacji Landroid.",
    "nl": "Worx heeft geen release-informatie voor deze update gepubliceerd. Zie de Landroid-app voor details.",
    "es": "Worx no ha publicado notas de versión para esta actualización. Consulta la aplicación Landroid para más detalles.",
    "it": "Worx non ha pubblicato note di rilascio per questo aggiornamento. Consulta l'app Landroid per i dettagli.",
    "sv": "Worx har inte publicerat några versionsanteckningar för den här uppdateringen. Se Landroid-appen för detaljer.",
    "no": "Worx har ikke publisert versjonsmerknader for denne oppdateringen. Se Landroid-appen for detaljer.",
    "da": "Worx har ikke offentliggjort udgivelsesnoter til denne opdatering. Se Landroid-appen for detaljer.",
    "ru": "Worx не опубликовал примечания к этому обновлению. Подробности смотрите в приложении Landroid.",
}


def _build_sections(source: dict[str, Any], language: str) -> list[str]:
    """Render one markdown section per firmware component that has notes.

    Takes either the live OTA payload or a record kept from a past update:
    both hold the component payloads under "product" and "head".
    """
    sections: list[str] = []
    for table, key in ((HEADING_MOWER, "product"), (HEADING_HEAD, "head")):
        text = _component_changelog(source.get(key), language)
        if not text:
            continue
        version = _sub_version(source, key)
        heading = _localized(table, language)
        title = f"{heading} {version}" if version else heading
        sections.append(f"## {title}\n\n{text}")
    return sections


def _localized(table: dict[str, str], language: str) -> str:
    """Pick a translation, falling back to the base language then English."""
    return (
        table.get(language)
        or table.get(language.split("-")[0])
        or table[DEFAULT_LANGUAGE]
    )


def _component_changelog(payload: Any, language: str) -> str | None:
    """Return one component's changelog text in the best available language."""
    if not isinstance(payload, dict):
        return None
    for key in ("changelog_markdown", "changelog", "release_notes"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if not isinstance(value, dict):
            continue
        for candidate in (language, language.split("-")[0], DEFAULT_LANGUAGE):
            text = value.get(candidate)
            if isinstance(text, str) and text.strip():
                return text.strip()
        for text in value.values():
            if isinstance(text, str) and text.strip():
                return text.strip()
    return None


def _sub_version(info: dict[str, Any], key: str) -> str | None:
    """Return the offered version of one firmware component.

    The Worx app shows a pair such as "2.5.7+12 - 3.46.0+47": the vision
    head first, then the mower. The OTA endpoint only reports the version
    the mower currently runs, so the entity tracks the mower firmware and
    surfaces both offered versions here.
    """
    payload = info.get(key)
    if not isinstance(payload, dict):
        return None
    value = payload.get("version")
    return str(value) if value is not None else None


def _comparable_version(value: Any) -> str | None:
    """Return a firmware version Home Assistant can order correctly.

    Worx numbers its firmware as "3.46.0+47", where the part after the plus
    sign is a meaningful, incrementing build number. Semantic versioning
    treats anything after a plus sign as build metadata and requires it to
    be ignored when comparing precedence, so Home Assistant's version
    comparison rates 3.46.0+47 as not newer than 3.46.0+40 and reports the
    mower as up to date while an update is genuinely pending. Turning the
    plus into a dot keeps every digit visible and restores the ordering.
    The untouched values stay available as attributes.
    """
    if value is None:
        return None
    text = str(value)
    head, plus, build = text.partition("+")
    if plus and build and build.replace(".", "").isdigit():
        return f"{head}.{build}"
    return text


def _info_text(info: dict[str, Any], *keys: str) -> str | None:
    """Return first non-empty text field from firmware metadata."""
    for key in keys:
        value = info.get(key)
        if value:
            return str(value)
    return None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up firmware update entities."""
    runtime = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            WorxVisionFirmwareUpdate(runtime.coordinator, entry, serial_number)
            for serial_number in runtime.coordinator.data
        ]
    )


class WorxVisionFirmwareUpdate(WorxVisionEntity, UpdateEntity):
    """Native Home Assistant firmware update entity."""

    _attr_supported_features = SUPPORTED_UPDATE_FEATURES
    _attr_translation_key = "firmware"
    _attr_title = "Firmware"

    def __init__(self, coordinator, entry, serial_number: str) -> None:
        """Initialize firmware update entity."""
        super().__init__(coordinator, entry, serial_number, "firmware")

    @property
    def available(self) -> bool:
        """Return entity availability."""
        info = _firmware_info(self.device)
        ota_supported = info.get("ota_supported")
        return super().available and (
            ota_supported is True
            or "ota_upgrade" in _capabilities(self.device)
            or bool(info)
        )

    @property
    def _language(self) -> str:
        """Return the Home Assistant UI language, lowercased."""
        return (getattr(self.hass.config, "language", None) or DEFAULT_LANGUAGE).lower()

    def _raw_installed_version(self) -> str | None:
        """Return the installed version exactly as Worx reports it."""
        info = _firmware_info(self.device)
        value = info.get("current_version")
        return str(value) if value is not None else _firmware_version(self.device)

    def _raw_latest_version(self) -> str | None:
        """Return the latest version exactly as Worx reports it."""
        info = _firmware_info(self.device)
        value = info.get("latest_version")
        if value is not None:
            return str(value)
        return self._raw_installed_version()

    @property
    def installed_version(self) -> str | None:
        """Return installed firmware version."""
        return _comparable_version(self._raw_installed_version())

    @property
    def latest_version(self) -> str | None:
        """Return latest firmware version."""
        return _comparable_version(self._raw_latest_version())

    @property
    def in_progress(self) -> bool:
        """Return whether an update appears to be in progress."""
        info = _firmware_info(self.device)
        if info.get("in_progress") or info.get("installing") or info.get("upgrade_in_progress"):
            return True
        # Worx never sets any of those keys, verified live through a complete
        # update, so the mower status is the only usable signal.
        return is_firmware_updating(self.device)

    @property
    def release_summary(self) -> str | None:
        """Return a one-line summary of what the update contains."""
        info = _firmware_info(self.device)
        provided = _info_text(info, "release_summary", "summary")
        if provided:
            return provided
        language = self._language
        parts = [
            f"{_localized(table, language)} {version}"
            for table, version in (
                (HEADING_MOWER, _sub_version(info, "product")),
                (HEADING_HEAD, _sub_version(info, "head")),
            )
            if version
        ]
        return " · ".join(parts) if parts else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return firmware metadata attributes."""
        info = _firmware_info(self.device)
        product_item = _product_item(self.device)
        attrs = {
            "installed_version_reported": self._raw_installed_version(),
            "latest_version_reported": self._raw_latest_version(),
            "update_available": info.get("update_available"),
            "mandatory": info.get("mandatory"),
            "ota_supported": info.get("ota_supported"),
            "auto_upgrade": info.get("auto_upgrade")
            if info.get("auto_upgrade") is not None
            else product_item.get("firmware_auto_upgrade"),
            "upgrade_failed": info.get("upgrade_failed"),
            "latest_product_version": _sub_version(info, "product"),
            "latest_head_version": _sub_version(info, "head"),
            "product": info.get("product"),
            "head": info.get("head"),
        }
        return {key: value for key, value in attrs.items() if value is not None}

    async def async_update(self) -> None:
        """Refresh firmware metadata."""
        info = await self.coordinator.async_get_firmware_upgrade_info(
            self._serial_number, force=True
        )
        if info is not None:
            setattr(self.device, "_worx_vision_firmware_upgrade", info)

    async def async_install(
        self,
        version: str | None,
        backup: bool,
        **kwargs: Any,
    ) -> None:
        """Install the latest available firmware."""
        del version, backup, kwargs
        await self.coordinator.async_start_firmware_upgrade(self._serial_number)

    async def async_release_notes(self) -> str | None:
        """Return firmware release notes when the cloud provides them."""
        info = await self.coordinator.async_get_firmware_upgrade_info(
            self._serial_number, force=True
        )
        if info is None:
            info = _firmware_info(self.device)

        language = self._language
        sections = _build_sections(info, language)
        if sections:
            return "\n\n".join(sections)

        # Worx describes a firmware only while it is still being offered: once
        # installed, the upgrade route answers 404 and the live payload is
        # empty. Fall back to what was recorded when this very version was the
        # one on offer.
        stored = self.coordinator.firmware_notes(
            self._serial_number, self._raw_installed_version()
        )
        if isinstance(stored, dict):
            sections = _build_sections(stored, language)
            if sections:
                return "\n\n".join(sections)

        return _localized(NOTES_UNAVAILABLE, language)
