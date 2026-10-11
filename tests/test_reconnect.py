"""Tests for stopping the previous MQTT client before reconnecting.

pyworxcloud 6.4.2's connect() creates a new MQTT client and leaves the old
one running, so every reconnect done by the integration would leave one more
paho client behind, reconnecting on its own and delivering the same updates.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
import unittest

from test_zone_job_retry import COORDINATOR, NoConnectionError


class ReconnectCloud:
    """WorxCloud stand-in that records the order of reconnect steps."""

    def __init__(self) -> None:
        self.mqtt_connected = False
        self.mqtt = object()
        self.events: list[str] = []
        self.disconnect_error: Exception | None = None
        self._mqtt_retry_task = None

    async def _disconnect_mqtt(self, _logger) -> None:
        self.events.append("disconnect_mqtt")
        try:
            if self.disconnect_error is not None:
                raise self.disconnect_error
        finally:
            self.mqtt = None

    async def connect(self) -> None:
        self.events.append(
            f"connect(old_client={'yes' if self.mqtt is not None else 'no'})"
        )
        await asyncio.sleep(0)
        self.mqtt = FakeClient(self)
        self.mqtt_connected = True


class FakeClient:
    def __init__(self, cloud: ReconnectCloud, fail: bool = False) -> None:
        self.cloud = cloud
        self.fail = fail
        self.sent = 0

    async def apublish(self, *_args) -> None:
        if self.fail:
            raise NoConnectionError("stale")
        self.sent += 1


def _coordinator(cloud: ReconnectCloud):
    coordinator = object.__new__(COORDINATOR.WorxVisionCoordinator)
    coordinator.cloud = cloud
    coordinator._mqtt_reconnect_lock = asyncio.Lock()
    return coordinator


class ReconnectTests(unittest.IsolatedAsyncioTestCase):
    async def test_previous_client_is_stopped_before_connect(self) -> None:
        cloud = ReconnectCloud()
        await _coordinator(cloud)._async_ensure_mqtt_connected()
        self.assertEqual(cloud.events, ["disconnect_mqtt", "connect(old_client=no)"])

    async def test_library_retry_task_is_cancelled(self) -> None:
        cloud = ReconnectCloud()
        cloud._mqtt_retry_task = asyncio.create_task(asyncio.sleep(3600))
        await asyncio.sleep(0)
        task = cloud._mqtt_retry_task
        # Without the cancel, awaiting the retry task would hang.
        await asyncio.wait_for(_coordinator(cloud)._async_ensure_mqtt_connected(), 2)
        self.assertTrue(task.cancelled())
        self.assertIsNone(cloud._mqtt_retry_task)

    async def test_without_previous_client_only_connects(self) -> None:
        cloud = ReconnectCloud()
        cloud.mqtt = None
        await _coordinator(cloud)._async_ensure_mqtt_connected()
        self.assertEqual(cloud.events, ["connect(old_client=no)"])

    async def test_failing_disconnect_does_not_block_reconnect(self) -> None:
        cloud = ReconnectCloud()
        cloud.disconnect_error = RuntimeError("socket already closed")
        await _coordinator(cloud)._async_ensure_mqtt_connected()
        self.assertEqual(cloud.events, ["disconnect_mqtt", "connect(old_client=no)"])
        self.assertTrue(cloud.mqtt_connected)

    async def test_connected_client_is_left_alone(self) -> None:
        cloud = ReconnectCloud()
        cloud.mqtt_connected = True
        await _coordinator(cloud)._async_ensure_mqtt_connected()
        self.assertEqual(cloud.events, [])

    async def test_library_without_private_helper_still_connects(self) -> None:
        cloud = ReconnectCloud()
        cloud._disconnect_mqtt = None
        await _coordinator(cloud)._async_ensure_mqtt_connected()
        self.assertEqual(cloud.events, ["connect(old_client=yes)"])

    async def test_simultaneous_commands_open_one_connection(self) -> None:
        cloud = ReconnectCloud()
        coordinator = _coordinator(cloud)
        await asyncio.gather(
            coordinator._async_ensure_mqtt_connected(),
            coordinator._async_ensure_mqtt_connected(),
        )
        self.assertEqual(cloud.events, ["disconnect_mqtt", "connect(old_client=no)"])

    async def test_stale_publish_replaces_the_client_it_failed_on(self) -> None:
        cloud = ReconnectCloud()
        cloud.mqtt_connected = True
        stale = FakeClient(cloud, fail=True)
        cloud.mqtt = stale
        await _coordinator(cloud)._async_publish_command("SN", "topic", {}, 1)
        self.assertEqual(cloud.events, ["disconnect_mqtt", "connect(old_client=no)"])
        self.assertIsNot(cloud.mqtt, stale)
        self.assertEqual(cloud.mqtt.sent, 1)


if __name__ == "__main__":
    unittest.main()
