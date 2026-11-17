"""Tests for the main output timeout settings payload."""

import json
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock

from pywebasto import WebastoConnect
from pywebasto.device import WebastoDevice


def _settings(emulation_mode: str) -> dict:
    """Return sanitized webapi settings with the given emulation mode."""
    return {
        "settings_tab": [
            {
                "group": "webasto",
                "options": [
                    {
                        "key": "webasto_emul_mode",
                        "type": "select",
                        "value": emulation_mode,
                    },
                    {"key": "OUTH", "type": "output", "timeout": 7200},
                    {"key": "OUTV", "type": "output", "timeout": 3600},
                ],
            }
        ]
    }


class TestSetMainTimeout(IsolatedAsyncioTestCase):
    """Validate that changing the main timeout keeps the emulation mode."""

    async def _sent_device_settings(self, device: WebastoDevice) -> dict:
        cloud = WebastoConnect("user", "pass")
        cloud._ensure_webapi_session = AsyncMock()  # type: ignore[method-assign]
        cloud._change_device = AsyncMock()  # type: ignore[method-assign]
        cloud._call = AsyncMock()  # type: ignore[method-assign]
        cloud.update = AsyncMock()  # type: ignore[method-assign]

        await cloud.set_main_timeout(device, heater=5400)

        payload = json.loads(cloud._call.await_args.args[1])
        return payload["device_settings"]

    async def test_keeps_current_emulation_mode(self) -> None:
        device = WebastoDevice("123", "Heater")
        device.settings = _settings("telestart")

        device_settings = await self._sent_device_settings(device)

        self.assertEqual(device_settings["webasto_emul_mode"], "telestart")
        self.assertEqual(device_settings["OUTH_timeout_h"], 1)
        self.assertEqual(device_settings["OUTH_timeout_min"], 30)

    async def test_falls_back_to_thermoconnect_without_settings(self) -> None:
        device = WebastoDevice("123", "Heater")

        device_settings = await self._sent_device_settings(device)

        self.assertEqual(device_settings["webasto_emul_mode"], "thermoconnect")
