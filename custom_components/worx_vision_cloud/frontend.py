"""Serve the Worx Vision card and register it as a Lovelace resource.

The card ships inside the integration, so HACS delivers both together. On
start the file is served under CARD_URL_BASE and a single Lovelace module
resource points at it, versioned with the integration so browsers pick up a
new card after an update. Only a storage-mode Lovelace is ever written to.
"""
from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CARD_FILENAME = "worx-vision-card.js"
CARD_URL_BASE = f"/{DOMAIN}_frontend"
CARD_URL_PATH = f"{CARD_URL_BASE}/{CARD_FILENAME}"

# The standalone RTK map card this bundle replaces. Its element names are
# defined by the bundle too, so a leftover resource would only load a second
# copy that fights ours over them.
LEGACY_FILENAMES = frozenset({"worx-map-rtk-card.js"})


def card_url(version: str | None) -> str:
    """Return the resource URL, versioned so an update busts browser caches."""
    return f"{CARD_URL_PATH}?v={version or '0'}"


def _filename(url: str) -> str:
    return urlparse(url).path.rsplit("/", 1)[-1]


def is_card_resource(url: str) -> bool:
    """Return True for any resource loading this card or the one it replaces."""
    name = _filename(url)
    return name == CARD_FILENAME or name in LEGACY_FILENAMES


async def async_reconcile_card_resource(resources: Any, new_url: str) -> list[str]:
    """Leave exactly one Lovelace resource pointing at the bundled card.

    Returns the URLs of the resources that were removed.
    """
    # The collection loads lazily: read before it is loaded, it looks empty
    # and a new copy of our resource would be added on every restart. An
    # unknown collection counts as not loaded, never the other way round.
    if not getattr(resources, "loaded", False):
        await resources.async_load()
        resources.loaded = True

    own = None
    stale: list[dict[str, Any]] = []
    # Collect first, mutate after: the items must not change while iterated.
    for item in list(resources.async_items()):
        url = item.get("url", "")
        if not is_card_resource(url):
            continue
        if own is None and urlparse(url).path == CARD_URL_PATH:
            own = item
        else:
            stale.append(item)

    for item in stale:
        _LOGGER.info(
            "Removing Lovelace resource %s: the Worx Vision card now ships "
            "with the integration",
            item.get("url"),
        )
        await resources.async_delete_item(item.get("id"))

    if own is None:
        await resources.async_create_item({"res_type": "module", "url": new_url})
    elif own.get("url") != new_url:
        await resources.async_update_item(own.get("id"), {"url": new_url})

    return [item.get("url", "") for item in stale]


async def async_register_card(hass: Any, version: str | None) -> None:
    """Serve the card, then reconcile the Lovelace resource once HA runs."""
    from homeassistant.components.http import StaticPathConfig
    from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
    from homeassistant.core import CoreState

    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                url_path=CARD_URL_PATH,
                path=hass.config.path(f"custom_components/{DOMAIN}/{CARD_FILENAME}"),
                cache_headers=True,
            )
        ]
    )
    new_url = card_url(version)

    async def _async_register_resource(_event: Any = None) -> None:
        lovelace = hass.data.get("lovelace")
        resources = getattr(lovelace, "resources", None)
        if lovelace is None or resources is None:
            _LOGGER.warning(
                "Lovelace is not loaded, add %s as a module resource by hand", new_url
            )
            return
        mode = getattr(lovelace, "resource_mode", None) or getattr(
            lovelace, "mode", "storage"
        )
        if mode != "storage":
            _LOGGER.warning(
                "Lovelace resources are in %s mode, which the integration never "
                "writes to: add %s as a module resource in your configuration",
                mode,
                new_url,
            )
            return
        try:
            await async_reconcile_card_resource(resources, new_url)
        except Exception:  # noqa: BLE001 - never block the integration on this
            _LOGGER.warning(
                "Could not register the Worx Vision card resource", exc_info=True
            )

    if hass.state == CoreState.running:
        await _async_register_resource()
    else:
        hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STARTED, _async_register_resource
        )
