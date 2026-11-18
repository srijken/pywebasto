"""Tests for the experimental geofence control (alarm output OUTA)."""

import unittest
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock

from pywebasto import WebastoConnect
from pywebasto.consts import CMD_ALARM_OFF, CMD_ALARM_ON
from pywebasto.device import WebastoDevice
from pywebasto.enums import Outputs
from pywebasto.exceptions import InvalidRequestException


def _app_data(outa_state: str | None, alarms: str = "ON") -> dict:
    """Build sanitized app data shaped like `/all?api_v=8` (2026-11-18)."""
    outputs: list[dict] = [
        {"line": "OUTH", "name": "", "icon": "car_heat", "state": "OFF"},
    ]
    if outa_state is not None:
        outputs.append(
            {"line": "OUTA", "name": "", "icon": "alert_on", "state": outa_state}
        )
    return {
        "assocStatus": "ok",
        "temperature": "9C",
        "voltage": "12.5V",
        "outputs": outputs,
        "seen": 14,
        "location": {"state": "ON"},
        "alarms": alarms,
    }


class TestGeofenceProperties(unittest.TestCase):
    """Validate the OUTA-based geofence properties."""

    def test_outa_off_means_geofence_active(self) -> None:
        device = WebastoDevice("123", "Heater")
        device.app_data = _app_data("OFF", alarms="OFF")

        self.assertEqual(device.alarm_output["line"], "OUTA")
        self.assertTrue(device.geofence_active)
        self.assertEqual(device.alarm_state, "OFF")

    def test_outa_on_means_geofence_inactive(self) -> None:
        device = WebastoDevice("123", "Heater")
        device.app_data = _app_data("ON", alarms="ON")

        self.assertFalse(device.geofence_active)
        self.assertEqual(device.alarm_state, "ON")

    def test_missing_outa_returns_none(self) -> None:
        device = WebastoDevice("123", "Heater")
        device.app_data = _app_data(None)

        self.assertIsNone(device.alarm_output)
        self.assertIsNone(device.geofence_active)

    def test_unknown_outa_state_returns_none(self) -> None:
        device = WebastoDevice("123", "Heater")
        device.app_data = _app_data("CONF")

        self.assertIsNotNone(device.alarm_output)
        self.assertIsNone(device.geofence_active)

    def test_outa_in_disabled_outputs_is_ignored(self) -> None:
        device = WebastoDevice("123", "Heater")
        data = _app_data(None)
        data["disabled_outputs"] = [{"line": "OUTA", "icon": "", "state": "OFF"}]
        device.app_data = data

        self.assertIsNone(device.alarm_output)
        self.assertIsNone(device.geofence_active)

    def test_no_data_returns_none(self) -> None:
        device = WebastoDevice("123", "Heater")

        self.assertIsNone(device.alarm_output)
        self.assertIsNone(device.geofence_active)

    def test_alarm_output_enum(self) -> None:
        self.assertEqual(Outputs.ALARM.value, "OUTA")


class TestSetGeofence(IsolatedAsyncioTestCase):
    """Validate the inferred command mapping of `set_geofence`."""

    def setUp(self) -> None:
        self.cloud = WebastoConnect(client_id="client", client_secret="secret")
        self.cloud._app_call = AsyncMock()  # type: ignore[method-assign]
        self.cloud.update = AsyncMock()  # type: ignore[method-assign]
        self.device = WebastoDevice("123", "Heater")

    def test_command_constants(self) -> None:
        self.assertEqual(CMD_ALARM_ON, "OUT A ON")
        self.assertEqual(CMD_ALARM_OFF, "OUT A OFF")

    async def test_activate_sends_out_a_off(self) -> None:
        await self.cloud.set_geofence(self.device, True)

        self.cloud._app_call.assert_awaited_once_with(
            "POST",
            "/remote/client/client/device/123/cmd",
            payload="OUT A OFF",
        )
        self.cloud.update.assert_awaited_once_with(device_id="123", force=True)

    async def test_deactivate_sends_out_a_on(self) -> None:
        await self.cloud.set_geofence(self.device, False)

        self.cloud._app_call.assert_awaited_once_with(
            "POST",
            "/remote/client/client/device/123/cmd",
            payload="OUT A ON",
        )
        self.cloud.update.assert_awaited_once_with(device_id="123", force=True)

    async def test_pending_device_is_rejected(self) -> None:
        self.device.app_data = {"id": "123", "assocStatus": "pending"}

        with self.assertRaises(InvalidRequestException):
            await self.cloud.set_geofence(self.device, True)

        self.cloud._app_call.assert_not_awaited()
        self.cloud.update.assert_not_awaited()
