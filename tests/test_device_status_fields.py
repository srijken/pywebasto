"""Tests for device status and settings fields read from app data."""

import unittest

from pywebasto.device import WebastoDevice

# Sanitized from app-backend `/all?api_v=8` data and webapi settings observed on
# 2026-11-17 (ids, check id, phone numbers and location removed).
APP_DATA = {
    "assocStatus": "ok",
    "temperature": "9C",
    "voltage": "10.1V",
    "outputs": [
        {
            "line": "OUTH",
            "name": "Heater",
            "icon": "car_heat",
            "state": "OFF",
            "ontime": 0,
            "parking_heating_mode_available": True,
            "ventilation_mode_available": True,
            "eco_mode_available": False,
            "boost_mode_available": False,
            "water_heater_continuous_heating": False,
            "timers": [],
        }
    ],
    "seen": 97,
    "location": {"state": "ON"},
    "subscription": {"status": "ok", "expiration": 1796831722, "message": ""},
    "alarms": "ON",
    "connection_lost": False,
    "vwarn": True,
    "location_services": "ON",
    "geofence_enabled": True,
}

SETTINGS = {
    "hw_version": "35.0",
    "sw_version": 152,
    "sw_variant": 3,
    "sw_external": "141",
    "settings_tab": [
        {
            "group": "general",
            "options": [
                {"key": "allow_GPS", "type": "bool", "value": True},
                {
                    "key": "geofence",
                    "type": "geofence",
                    "enabled": True,
                    "value": 1.0,
                    "unit": "km",
                },
                {"key": "low_voltage_cutoff", "type": "range", "value": 10.3},
                {"key": "def_output", "type": "select", "value": "automatic"},
                {"key": "ext_temp_comp", "type": "range", "value": 0.0},
                {
                    "key": "sig_lost_off",
                    "type": "range",
                    "enabled": False,
                    "value": 10,
                    "unit": "mins",
                },
            ],
        },
        {
            "group": "webasto",
            "options": [
                {
                    "key": "webasto_emul_mode",
                    "type": "select",
                    "value": "thermoconnect",
                },
                {"key": "OUTH", "type": "output", "timeout": 7200},
                {"key": "OUTV", "type": "output", "timeout": 3600},
            ],
        },
    ],
}


class TestDeviceStatusFields(unittest.TestCase):
    """Validate fields parsed from observed app data and settings."""

    def setUp(self) -> None:
        self.device = WebastoDevice("123", "Heater")
        self.device.app_data = APP_DATA
        self.device.settings = SETTINGS

    def test_app_data_fields(self) -> None:
        self.assertTrue(self.device.low_voltage_warning)
        self.assertEqual(self.device.last_seen_seconds, 97)
        self.assertEqual(self.device.alarm_state, "ON")
        self.assertTrue(self.device.geofence_enabled)
        self.assertEqual(self.device.subscription_status, "ok")

    def test_settings_fields(self) -> None:
        self.assertEqual(self.device.geofence_radius, 1.0)
        self.assertEqual(self.device.default_output, "automatic")
        self.assertFalse(self.device.signal_lost_shutdown_enabled)
        self.assertEqual(self.device.signal_lost_shutdown_minutes, 10)
        self.assertEqual(self.device.emulation_mode, "thermoconnect")

    def test_versions_from_settings(self) -> None:
        self.assertEqual(self.device.hardware_version, "35.0")
        self.assertEqual(self.device.software_version, "152")
        self.assertEqual(self.device.software_variant, "3")
        self.assertEqual(self.device.software_external_version, "141")

    def test_output_main_features(self) -> None:
        self.assertEqual(
            self.device.output_main_features,
            {
                "parking_heating_mode_available": True,
                "ventilation_mode_available": True,
                "eco_mode_available": False,
                "boost_mode_available": False,
            },
        )

    def test_missing_fields_return_none(self) -> None:
        device = WebastoDevice("123", "Heater")
        device.app_data = {
            "assocStatus": "ok",
            "temperature": "9C",
            "voltage": "10.1V",
            "outputs": [],
        }
        device.settings = {"settings_tab": []}

        self.assertIsNone(device.low_voltage_warning)
        self.assertIsNone(device.last_seen_seconds)
        self.assertIsNone(device.alarm_state)
        self.assertIsNone(device.geofence_enabled)
        self.assertIsNone(device.subscription_status)
        self.assertIsNone(device.geofence_radius)
        self.assertIsNone(device.default_output)
        self.assertIsNone(device.signal_lost_shutdown_enabled)
        self.assertIsNone(device.signal_lost_shutdown_minutes)
        self.assertIsNone(device.emulation_mode)
        self.assertIsNone(device.software_external_version)
        self.assertEqual(device.output_main_features, {})


if __name__ == "__main__":
    unittest.main()
