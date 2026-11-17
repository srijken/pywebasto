"""Tests for smart timer support and preserving non-simple timers."""

import json
import unittest
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock

from pywebasto import WebastoConnect
from pywebasto.device import WebastoDevice
from pywebasto.enums import Outputs
from pywebasto.exceptions import InvalidRequestException
from pywebasto.timer import (
    SimpleTimer,
    SmartTimer,
    UnknownTimer,
    timer_from_api_dict,
)

# Sanitized from an app-backend `/all?api_v=8` response observed on 2026-11-17
# (one-off smart timer, departure 23:40 CET, max 30 minutes, comfort level 5).
OBSERVED_SMART_TIMER = {
    "type": "smart",
    "repeat": 0,
    "start": 1360,
    "maxDuration": 1800,
    "comfortLevel": 5,
    "location": {"lat": "REDACTED_LAT", "lon": "REDACTED_LON"},
    "enabled": True,
}

# What the library sends for OBSERVED_SMART_TIMER: `departure` is added because
# the app and the web API send it when saving.
SAVED_SMART_TIMER = {**OBSERVED_SMART_TIMER, "departure": 1360}

SIMPLE_TIMER = {
    "type": "simple",
    "repeat": 127,
    "start": 1349,
    "duration": 5400,
    "enabled": False,
}


class TestSmartTimer(unittest.TestCase):
    """Validate smart timer parsing and serialization."""

    def test_from_api_dict_parses_observed_payload(self) -> None:
        timer = SmartTimer.from_api_dict(OBSERVED_SMART_TIMER)

        self.assertEqual(timer.start, 1360)
        self.assertEqual(timer.max_duration, 1800)
        self.assertEqual(timer.comfort_level, 5)
        self.assertEqual(timer.repeat, 0)
        self.assertEqual(timer.latitude, "REDACTED_LAT")
        self.assertEqual(timer.longitude, "REDACTED_LON")
        self.assertTrue(timer.enabled)

    def test_to_api_dict_sends_start_and_departure(self) -> None:
        timer = SmartTimer.from_api_dict(OBSERVED_SMART_TIMER)

        self.assertEqual(timer.to_api_dict(), SAVED_SMART_TIMER)

    def test_to_api_dict_allows_missing_location(self) -> None:
        timer = SmartTimer(start=480, max_duration=1800, comfort_level=3, repeat=31)

        payload = timer.to_api_dict()

        self.assertNotIn("location", payload)
        self.assertEqual(payload["departure"], 480)

    def test_from_api_dict_accepts_webapi_departure_field(self) -> None:
        # The web API dump also carries `departure` and omits `enabled`.
        timer = SmartTimer.from_api_dict(
            {
                "type": "smart",
                "start": 830,
                "repeat": 30,
                "maxDuration": 3000,
                "comfortLevel": 5,
                "departure": 830,
            }
        )

        self.assertEqual(timer.start, 830)
        self.assertTrue(timer.enabled)

    def test_validate_rejects_non_positive_values(self) -> None:
        for field in ("start", "max_duration", "comfort_level"):
            values = {"start": 480, "max_duration": 1800, "comfort_level": 5}
            values[field] = 0
            with self.subTest(field=field), self.assertRaises(ValueError):
                SmartTimer(repeat=0, **values).validate()

    def test_from_api_dict_rejects_other_types(self) -> None:
        with self.assertRaises(ValueError):
            SmartTimer.from_api_dict(SIMPLE_TIMER)


class TestTimerFromApiDict(unittest.TestCase):
    """Validate dispatching raw timers to the matching model."""

    def test_dispatches_by_type(self) -> None:
        self.assertIsInstance(timer_from_api_dict(SIMPLE_TIMER), SimpleTimer)
        self.assertIsInstance(timer_from_api_dict(OBSERVED_SMART_TIMER), SmartTimer)

    def test_unknown_type_is_kept_unchanged(self) -> None:
        raw = {"type": "future", "foo": 1}

        timer = timer_from_api_dict(raw)

        self.assertIsInstance(timer, UnknownTimer)
        self.assertEqual(timer.to_api_dict(), raw)


class TestTimerExtractionAndMerge(unittest.TestCase):
    """Validate extracting every timer type and merging simple timers."""

    def test_extract_all_timers_includes_smart(self) -> None:
        payload = {
            "outputs": [
                {"line": "OUTH", "timers": [SIMPLE_TIMER, OBSERVED_SMART_TIMER]}
            ]
        }

        timers = WebastoConnect._extract_all_timers_from_data(payload, "OUTH")

        self.assertEqual(len(timers), 2)
        self.assertIsInstance(timers[0], SimpleTimer)
        self.assertIsInstance(timers[1], SmartTimer)

    def test_extract_all_timers_rejects_invalid_smart_timer(self) -> None:
        payload = {"outputs": [{"line": "OUTH", "timers": [{"type": "smart"}]}]}

        with self.assertRaises(InvalidRequestException):
            WebastoConnect._extract_all_timers_from_data(payload, "OUTH")

    def test_merge_keeps_smart_timer_in_place(self) -> None:
        raw = [SIMPLE_TIMER, OBSERVED_SMART_TIMER]
        edited = SimpleTimer(start=600, duration=1800, repeat=1, enabled=True)

        merged = WebastoConnect._merge_simple_timers(raw, [edited])

        self.assertEqual(merged, [edited.to_api_dict(), SAVED_SMART_TIMER])

    def test_merge_deleting_last_simple_timer_keeps_smart(self) -> None:
        merged = WebastoConnect._merge_simple_timers(
            [SIMPLE_TIMER, OBSERVED_SMART_TIMER], []
        )

        self.assertEqual(merged, [SAVED_SMART_TIMER])

    def test_merge_appends_new_simple_timers(self) -> None:
        new = SimpleTimer(start=600, duration=1800, repeat=1)

        merged = WebastoConnect._merge_simple_timers([OBSERVED_SMART_TIMER], [new])

        self.assertEqual(merged, [SAVED_SMART_TIMER, new.to_api_dict()])


class TestSaveTimers(IsolatedAsyncioTestCase):
    """Validate the timers2 payloads sent for mixed timer lists."""

    def _cloud_with_device(self) -> tuple[WebastoConnect, WebastoDevice]:
        cloud = WebastoConnect(client_id="client", client_secret="secret")
        cloud._app_call = AsyncMock()  # type: ignore[method-assign]
        cloud.update = AsyncMock()  # type: ignore[method-assign]
        device = WebastoDevice("123", "Heater")
        device.last_data = {
            "temperature": "9C",
            "voltage": "10.1V",
            "location": {"state": "OFF"},
            "outputs": [
                {
                    "line": "OUTH",
                    "icon": "car_heat",
                    "timers": [OBSERVED_SMART_TIMER],
                }
            ],
        }
        cloud.devices["123"] = device
        return cloud, device

    @staticmethod
    def _sent_timers(cloud: WebastoConnect) -> list[dict]:
        payload = cloud._app_call.await_args.kwargs["payload"]  # type: ignore[attr-defined]
        body = json.loads(payload)
        assert body["output"] == "H"
        return body["timers"]

    async def test_save_timers_preserves_smart_timers(self) -> None:
        cloud, device = self._cloud_with_device()
        new = SimpleTimer(start=600, duration=1800, repeat=1)

        await cloud.save_timers(device, [new], line=Outputs.HEATER)

        self.assertEqual(
            self._sent_timers(cloud), [SAVED_SMART_TIMER, new.to_api_dict()]
        )

    async def test_save_all_timers_replaces_full_list(self) -> None:
        cloud, device = self._cloud_with_device()
        smart = SmartTimer(start=420, max_duration=2400, comfort_level=4, repeat=31)

        await cloud.save_all_timers(device, [smart], line=Outputs.HEATER)

        self.assertEqual(self._sent_timers(cloud), [smart.to_api_dict()])

    async def test_get_all_timers_returns_smart_timers(self) -> None:
        cloud, device = self._cloud_with_device()

        timers = await cloud.get_all_timers(device, line=Outputs.HEATER)

        self.assertEqual(timers, [SmartTimer.from_api_dict(OBSERVED_SMART_TIMER)])


if __name__ == "__main__":
    unittest.main()
