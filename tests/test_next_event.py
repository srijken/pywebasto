"""Tests for the `nextEvent` field from app-backend data."""

import unittest

from pywebasto import NextEvent
from pywebasto.device import WebastoDevice

# Sanitized `nextEvent` values from app-backend `/all?api_v=8` data observed on
# 2026-11-17 (a Tuesday). Timer start values are minutes after midnight UTC.
# 1. Enabled simple timers: every day at 1349 and Monday at 390.
OBS_EVERY_DAY = {"line": "OUTH", "type": "normal", "day": 4, "time": 1349}
# 2. Only the Monday simple timer at 390 enabled.
OBS_MONDAY = {"line": "OUTH", "type": "normal", "day": 1, "time": 390}
# 3. Only a one-off smart timer departing at 1360 (already passed that day).
OBS_SMART_ONE_OFF = {"line": "OUTH", "type": "smart", "day": 4, "time": 1360}
# 4. No enabled timers.
OBS_EMPTY: dict = {}


def _device(next_event: object = None, include: bool = True) -> WebastoDevice:
    data = {
        "assocStatus": "ok",
        "temperature": "9C",
        "voltage": "12.6V",
        "location": {"state": "ON"},
        "outputs": [],
    }
    if include:
        data["nextEvent"] = next_event
    device = WebastoDevice("123", "Camper")
    device.app_data = data
    return device


class TestNextEvent(unittest.TestCase):
    """Validate parsing of observed `nextEvent` values."""

    def test_simple_every_day(self) -> None:
        event = _device(OBS_EVERY_DAY).next_event
        self.assertEqual(
            event,
            NextEvent(
                line="OUTH",
                type="normal",
                time_utc_minutes=1349,
                day=4,
                raw=OBS_EVERY_DAY,
            ),
        )

    def test_simple_monday(self) -> None:
        event = _device(OBS_MONDAY).next_event
        self.assertIsNotNone(event)
        self.assertEqual(event.line, "OUTH")
        self.assertEqual(event.type, "normal")
        self.assertEqual(event.time_utc_minutes, 390)
        self.assertEqual(event.day, 1)

    def test_smart_one_off(self) -> None:
        event = _device(OBS_SMART_ONE_OFF).next_event
        self.assertIsNotNone(event)
        self.assertEqual(event.type, "smart")
        self.assertEqual(event.time_utc_minutes, 1360)
        self.assertEqual(event.day, 4)
        self.assertEqual(event.raw, OBS_SMART_ONE_OFF)

    def test_empty_missing_or_not_a_dict(self) -> None:
        self.assertIsNone(_device(OBS_EMPTY).next_event)
        self.assertIsNone(_device(include=False).next_event)
        self.assertIsNone(_device(None).next_event)
        self.assertIsNone(_device([1, 2]).next_event)
        self.assertIsNone(_device("OUTH").next_event)

    def test_no_data(self) -> None:
        device = WebastoDevice("123", "Camper")
        self.assertIsNone(device.next_event)
        device.last_data = None
        self.assertIsNone(device.next_event)

    def test_wrong_field_types(self) -> None:
        raw = {"line": 1, "type": None, "day": "4", "time": True}
        event = _device(raw).next_event
        self.assertEqual(
            event,
            NextEvent(line=None, type=None, time_utc_minutes=None, day=None, raw=raw),
        )

    def test_raw_is_a_copy(self) -> None:
        raw = dict(OBS_MONDAY)
        event = NextEvent.from_api_dict(raw)
        raw["time"] = 0
        self.assertEqual(event.raw["time"], 390)


if __name__ == "__main__":
    unittest.main()
