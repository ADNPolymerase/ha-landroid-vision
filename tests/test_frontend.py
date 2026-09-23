"""Tests for the Lovelace resource that loads the bundled Worx Vision card."""

from __future__ import annotations

import asyncio
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType
import unittest

COMPONENT = Path(__file__).parents[1] / "custom_components" / "worx_vision_cloud"

# frontend.py only needs DOMAIN from const.py, which itself pulls in Home
# Assistant. A two-module stand-in package keeps the test free of it.
PACKAGE = ModuleType("wvc_frontend_pkg")
PACKAGE.__path__ = []
CONST = ModuleType("wvc_frontend_pkg.const")
CONST.DOMAIN = "worx_vision_cloud"
sys.modules["wvc_frontend_pkg"] = PACKAGE
sys.modules["wvc_frontend_pkg.const"] = CONST
SPEC = importlib.util.spec_from_file_location(
    "wvc_frontend_pkg.frontend", COMPONENT / "frontend.py"
)
assert SPEC is not None and SPEC.loader is not None
FRONTEND = importlib.util.module_from_spec(SPEC)
sys.modules["wvc_frontend_pkg.frontend"] = FRONTEND
SPEC.loader.exec_module(FRONTEND)

NEW_URL = "/worx_vision_cloud_frontend/worx-vision-card.js?v=9.9.9"


class FakeResources:
    """Mimics Lovelace's lazily loaded resource collection."""

    def __init__(self, stored, loaded=False):
        self._stored = [dict(item) for item in stored]
        self._items = [dict(item) for item in stored] if loaded else []
        self.loaded = loaded
        self.load_calls = 0
        self._next = 100

    async def async_load(self):
        self.load_calls += 1
        self._items = [dict(item) for item in self._stored]

    def async_items(self):
        return self._items

    async def async_create_item(self, data):
        self._next += 1
        self._items.append({"id": str(self._next), **data})

    async def async_update_item(self, item_id, data):
        for item in self._items:
            if item["id"] == item_id:
                item.update(data)

    async def async_delete_item(self, item_id):
        self._items = [item for item in self._items if item["id"] != item_id]

    def urls(self):
        return sorted(item["url"] for item in self._items)


def reconcile(resources):
    return asyncio.run(FRONTEND.async_reconcile_card_resource(resources, NEW_URL))


OTHER = {"id": "1", "res_type": "module", "url": "/hacsfiles/other-card/other-card.js"}


class ReconcileTest(unittest.TestCase):
    def test_adds_the_resource_once(self):
        resources = FakeResources([OTHER])
        reconcile(resources)
        self.assertEqual(resources.urls(), sorted([OTHER["url"], NEW_URL]))

    def test_loads_a_lazy_collection_before_reading_it(self):
        # Read unloaded, the collection looks empty: a copy would be added on
        # every restart, and the other cards' resources would be ignored.
        resources = FakeResources(
            [OTHER, {"id": "2", "res_type": "module", "url": NEW_URL}]
        )
        reconcile(resources)
        self.assertEqual(resources.load_calls, 1)
        self.assertEqual(resources.urls(), sorted([OTHER["url"], NEW_URL]))

    def test_restart_is_idempotent(self):
        resources = FakeResources([OTHER])
        reconcile(resources)
        reconcile(resources)
        self.assertEqual(resources.urls().count(NEW_URL), 1)

    def test_updates_the_version_in_place(self):
        old = {
            "id": "7",
            "res_type": "module",
            "url": "/worx_vision_cloud_frontend/worx-vision-card.js?v=1.0.0",
        }
        resources = FakeResources([OTHER, old], loaded=True)
        reconcile(resources)
        ids = {item["url"]: item["id"] for item in resources.async_items()}
        self.assertEqual(ids.get(NEW_URL), "7")
        self.assertEqual(len(resources.async_items()), 2)

    def test_removes_the_legacy_map_card_and_duplicates(self):
        resources = FakeResources(
            [
                OTHER,
                {"id": "2", "res_type": "module", "url": "/local/worx-map-rtk-card.js?v=3"},
                {"id": "3", "res_type": "module", "url": "/local/worx-vision-card.js"},
                {"id": "4", "res_type": "module", "url": NEW_URL},
                {"id": "5", "res_type": "module", "url": NEW_URL},
            ],
            loaded=True,
        )
        removed = reconcile(resources)
        self.assertEqual(resources.urls(), sorted([OTHER["url"], NEW_URL]))
        self.assertEqual(len(removed), 3)

    def test_leaves_unrelated_resources_alone(self):
        similar = {"id": "9", "res_type": "module", "url": "/local/worx-map-rtk-card-extra.js"}
        resources = FakeResources([OTHER, similar], loaded=True)
        reconcile(resources)
        self.assertIn(similar["url"], resources.urls())
        self.assertIn(OTHER["url"], resources.urls())


class PackagingTest(unittest.TestCase):
    def test_bundle_is_shipped_where_it_is_served_from(self):
        self.assertTrue((COMPONENT / FRONTEND.CARD_FILENAME).is_file())

    def test_legacy_card_is_gone_from_the_repository(self):
        self.assertFalse((COMPONENT.parents[1] / "lovelace" / "worx-map-rtk-card.js").exists())

    def test_manifest_declares_what_the_card_needs(self):
        manifest = json.loads((COMPONENT / "manifest.json").read_text())
        self.assertIn("http", manifest["dependencies"])
        self.assertIn("lovelace", manifest["after_dependencies"])

    def test_url_is_versioned(self):
        self.assertEqual(
            FRONTEND.card_url("2.9.0"),
            "/worx_vision_cloud_frontend/worx-vision-card.js?v=2.9.0",
        )


if __name__ == "__main__":
    unittest.main()
