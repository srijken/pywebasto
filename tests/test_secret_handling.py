"""Tests for secret handling and tolerance of malformed API data."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import IsolatedAsyncioTestCase

from pywebasto import AppCredentials, WebastoConnect, _error_body
from pywebasto.device import WebastoDevice


class TestSecretHandling(IsolatedAsyncioTestCase):
    """Validate that the client secret does not leak."""

    def test_repr_hides_client_secret(self) -> None:
        credentials = AppCredentials("client", "very-secret")

        self.assertNotIn("very-secret", repr(credentials))
        self.assertIn("client", repr(credentials))

    async def test_credential_file_is_private(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "credentials.json"
            cloud = WebastoConnect(
                client_id="client",
                client_secret="secret",
                credential_store_path=path,
            )

            await cloud._save_credentials()

            self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)
            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8")),
                {"client_id": "client", "client_secret": "secret"},
            )
            self.assertEqual(
                sorted(p.name for p in Path(directory).iterdir()), ["credentials.json"]
            )


class TestErrorBody(unittest.TestCase):
    """Validate shortening of response bodies in exceptions."""

    def test_short_body_is_kept(self) -> None:
        self.assertEqual(
            _error_body(" Expected three components "), "Expected three components"
        )

    def test_long_body_is_truncated(self) -> None:
        body = '{"id": "1234567890", "check_id": "abcd"}' + "x" * 500

        shortened = _error_body(body)

        self.assertTrue(shortened.startswith(body[:200]))
        self.assertIn(f"({len(body)} characters)", shortened)
        self.assertLess(len(shortened), 250)


class TestMalformedOutputs(unittest.TestCase):
    """Validate that odd output entries do not raise."""

    def test_outputs_without_line_or_icon(self) -> None:
        device = WebastoDevice("123", "Heater")

        device.app_data = {
            "assocStatus": "ok",
            "temperature": "9C",
            "voltage": "12.1V",
            "outputs": [{"line": "OUTH"}, {"icon": "x"}, "junk", None],
            "disabled_outputs": None,
        }

        self.assertEqual(device.icon_heat, "")
        self.assertFalse(device.is_ventilation)


if __name__ == "__main__":
    unittest.main()
