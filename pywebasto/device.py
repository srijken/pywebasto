"""Device class for Webasto devices."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class NextEvent:
    """Next timer event as reported by the app backend (`nextEvent`).

    Observed fields (see `docs/protocol.md`):
    - `line`: output line of the event, e.g. `OUTH`.
    - `type`: `normal` for simple timers, `smart` for smart timers.
    - `time`: the timer start in minutes after midnight UTC.
    - `day`: an integer whose meaning is unknown; do not derive a date from it.
    """

    line: str | None
    type: str | None
    time_utc_minutes: int | None
    day: int | None
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_api_dict(cls, value: Any) -> "NextEvent | None":
        """Parse a raw `nextEvent` value; None when missing, empty or not a dict."""
        if not isinstance(value, dict) or not value:
            return None
        return cls(
            line=_typed(value.get("line"), str),
            type=_typed(value.get("type"), str),
            time_utc_minutes=_int_or_none(value.get("time")),
            day=_int_or_none(value.get("day")),
            raw=dict(value),
        )


def _typed(value: Any, expected_type: type) -> Any:
    """Return value when it has the expected type, otherwise None."""
    return value if isinstance(value, expected_type) else None


def _int_or_none(value: Any) -> int | None:
    """Return an int value (booleans excluded), otherwise None."""
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


class WebastoDevice:
    """Webasto Device representation."""

    def __init__(self, device_id: str, name: str) -> None:
        """Initialize the device."""
        self.__device_id: str = device_id
        self.__name: str = name
        self.__temperature: int = 0
        self.__voltage: float = 0.0
        self.__location: dict = {}
        self.__output_main: dict = {}
        self.__output_aux1: dict = {}
        self.__output_aux2: dict = {}
        self.__ventilation: bool = False
        self.__iscelcius: bool = False
        self.__hardware_version: str = ""
        self.__software_version: str = ""
        self.__software_variant: str = ""
        self.__allow_location: bool = False
        self.__low_voltage_cutoff: float = 0.0
        self.__temperature_compensation: float = 0.0
        self.__subscription_expiration: datetime | None = None
        self.__connection_lost: bool | None = None
        self.__last_data: dict | None = {}
        self.__dev_data: dict | None = {}
        self.__settings: dict | None = {}
        self.__icon_vent: str = ""
        self.__icon_heat: str = ""
        self.__icon_aux1: str = ""
        self.__icon_aux2: str = ""
        self.__timeout_heat: int = 0
        self.__timeout_vent: int = 0
        self.__timeout_aux1: int = 0
        self.__timeout_aux2: int = 0
        self.__association_status: str | None = None
        self.__pending_approval: bool = False

    @property
    def timeout_heat(self) -> int:
        """Returns the heater timeout in seconds."""
        return self.__timeout_heat

    @timeout_heat.setter
    def timeout_heat(self, value: int) -> None:
        """Sets the heater timeout in seconds."""
        self.__timeout_heat = value

    @property
    def timeout_vent(self) -> int:
        """Returns the ventilation timeout in seconds."""
        return self.__timeout_vent

    @timeout_vent.setter
    def timeout_vent(self, value: int) -> None:
        """Sets the ventilation timeout in seconds."""
        self.__timeout_vent = value

    @property
    def timeout_aux1(self) -> int:
        """Returns the aux1 timeout in seconds."""
        return self.__timeout_aux1

    @timeout_aux1.setter
    def timeout_aux1(self, value: int) -> None:
        """Sets the aux1 timeout in seconds."""
        self.__timeout_aux1 = value

    @property
    def timeout_aux2(self) -> int:
        """Returns the aux2 timeout in seconds."""
        return self.__timeout_aux2

    @timeout_aux2.setter
    def timeout_aux2(self, value: int) -> None:
        """Sets the aux2 timeout in seconds."""
        self.__timeout_aux2 = value

    @property
    def icon_vent(self) -> str:
        """Returns the ventilation icon."""
        return self.__icon_vent

    @property
    def icon_heat(self) -> str:
        """Returns the heater icon."""
        return self.__icon_heat

    @property
    def icon_aux1(self) -> str:
        """Returns the aux1 icon."""
        return self.__icon_aux1

    @property
    def icon_aux2(self) -> str:
        """Returns the aux2 icon."""
        return self.__icon_aux2

    @property
    def last_data(self) -> dict | None:
        """Returns the last data dictionary."""
        return self.__last_data

    @last_data.setter
    def last_data(self, value: dict | None) -> None:
        """Sets the last data dictionary."""
        self.__last_data = value

        if self.__last_data is None:
            return

        if self.__last_data["temperature"][-1] == "C":
            self.__iscelcius = True

        self.__temperature = int(
            self.__last_data["temperature"][: len(self.__last_data["temperature"]) - 1]
        )
        self.__voltage = float(
            self.__last_data["voltage"][: len(self.__last_data["voltage"]) - 1]
        )
        self.__location = self.__last_data["location"]
        connection_lost = self.__last_data.get("connection_lost")
        if isinstance(connection_lost, bool):
            self.__connection_lost = connection_lost

        for output in self.__last_data["outputs"]:
            if output["line"] == "OUTH" or output["line"] == "OUTV":
                self.__output_main = output
                if output["line"] == "OUTH":
                    self.__ventilation = False
                    self.__icon_heat = output["icon"]
                else:
                    self.__ventilation = True
                    self.__icon_vent = output["icon"]
            elif output["line"] == "OUT1":
                self.__output_aux1 = output
                self.__icon_aux1 = output["icon"]
            elif output["line"] == "OUT2":
                self.__output_aux2 = output
                self.__icon_aux2 = output["icon"]

    @property
    def app_data(self) -> dict | None:
        """Returns the last app data dictionary."""
        return self.__last_data

    @app_data.setter
    def app_data(self, value: dict | None) -> None:
        """Sets data from the Android app backend."""
        self.__last_data = value
        self.__dev_data = value

        if value is None:
            return

        self.__association_status = value.get("assocStatus")
        self.__pending_approval = self.__association_status == "pending"
        if self.__pending_approval:
            return

        temperature = value.get("temperature")
        if isinstance(temperature, str) and temperature:
            self.__iscelcius = temperature[-1] == "C"
            try:
                self.__temperature = int(temperature[:-1])
            except ValueError:
                self.__temperature = 0
        elif isinstance(temperature, int | float):
            self.__temperature = int(temperature)

        voltage = value.get("voltage")
        if isinstance(voltage, str) and voltage:
            try:
                self.__voltage = float(voltage[:-1])
            except ValueError:
                self.__voltage = 0.0
        elif isinstance(voltage, int | float):
            self.__voltage = float(voltage)

        self.__location = value.get("location", {"state": "OFF"})
        connection_lost = value.get("connection_lost")
        if isinstance(connection_lost, bool):
            self.__connection_lost = connection_lost

        subscription = value.get("subscription")
        if isinstance(subscription, dict) and isinstance(
            subscription.get("expiration"), int | float
        ):
            self.__subscription_expiration = datetime.fromtimestamp(
                subscription["expiration"], UTC
            )

        self.__output_main = {}
        self.__output_aux1 = {}
        self.__output_aux2 = {}

        for section in ("outputs", "disabled_outputs"):
            for output in value.get(section) or []:
                if not isinstance(output, dict):
                    continue
                line = output.get("line")
                icon = output.get("icon", "")
                if line == "OUTH" or line == "OUTV":
                    if line == "OUTH":
                        self.__icon_heat = icon
                        if section == "outputs":
                            self.__ventilation = False
                    else:
                        self.__icon_vent = icon
                        if section == "outputs":
                            self.__ventilation = True
                    if section == "outputs":
                        self.__output_main = output
                elif line == "OUT1":
                    self.__output_aux1 = output
                    self.__icon_aux1 = icon
                elif line == "OUT2":
                    self.__output_aux2 = output
                    self.__icon_aux2 = icon

    @property
    def dev_data(self) -> dict | None:
        """Returns the device data dictionary."""
        return self.__dev_data

    @dev_data.setter
    def dev_data(self, value: dict | None) -> None:
        """Sets the device data dictionary."""
        self.__dev_data = value
        if self.__dev_data is None:
            return

        self.__subscription_expiration = datetime.fromtimestamp(
            value["subscription"]["expiration"], UTC
        )
        connection_lost = value.get("connection_lost")
        if isinstance(connection_lost, bool):
            self.__connection_lost = connection_lost

    @property
    def settings(self) -> dict | None:
        """Returns the settings dictionary."""
        return self.__settings

    @settings.setter
    def settings(self, value: dict | None) -> None:
        """Sets the settings dictionary."""
        self.__settings = value

        if value is None:
            return

        hardware_version = value.get("hw_version")
        if hardware_version is not None:
            self.__hardware_version = str(hardware_version)
        software_version = value.get("sw_version")
        if software_version is not None:
            self.__software_version = str(software_version)
        software_variant = value.get("sw_variant")
        if software_variant is not None:
            self.__software_variant = str(software_variant)

        self.__allow_location = self.__get_value("general", "allow_GPS")
        self.__low_voltage_cutoff = self.__get_value("general", "low_voltage_cutoff")
        self.__temperature_compensation = self.__get_value("general", "ext_temp_comp")

        # self.timeout_heat = self.__get_value("settings_tab", "OUTH")
        # self.timeout_vent = self.__get_value("settings_tab", "OUTV")
        # self.timeout_aux1 = self.__get_value("settings_tab", "OUT1")
        # self.timeout_aux2 = self.__get_value("settings_tab", "OUT2")
        self.__get_timeouts()

    @property
    def temperature(self) -> int:
        """Returns the current temperature."""
        return self.__temperature

    @property
    def voltage(self) -> float:
        """Returns the current voltage."""
        return self.__voltage

    @property
    def location(self) -> dict | bool:
        """Returns the current location."""
        return self.__location if self.__location.get("state") == "ON" else False

    @property
    def output_main(self) -> bool:
        """Get the main output state."""
        if "state" in self.__output_main:
            return self.__output_main["state"] != "OFF"
        else:
            return False

    @property
    def output_main_ontime(self) -> int | None:
        """Get the unix timestamp for when the main output will stop."""
        if self.__output_main.get("state") != "ON":
            return None

        ontime = self.__output_main.get("ontime")
        if isinstance(ontime, int | float) and ontime > 0:
            return int(ontime)

        return None

    @property
    def output_main_end_time(self) -> datetime | None:
        """Get the UTC timestamp for when the main output will stop."""
        if (ontime := self.output_main_ontime) is None:
            return None

        return datetime.fromtimestamp(ontime, UTC)

    @property
    def output_aux1(self) -> bool:
        """Get the aux output state."""
        if "state" in self.__output_aux1:
            return self.__output_aux1["state"] != "OFF"
        else:
            return False

    @property
    def output_aux2(self) -> bool:
        """Get the aux output state."""
        if "state" in self.__output_aux2:
            return self.__output_aux2["state"] != "OFF"
        else:
            return False

    @property
    def is_ventilation(self) -> bool:
        """Get the mode of the output channel."""
        return self.__ventilation

    @property
    def temperature_unit(self) -> str:
        """Get the temperature unit."""
        return "°C" if self.__iscelcius else "°F"

    @property
    def hardware_version(self) -> str:
        """Get the hardware version."""
        return self.__hardware_version

    @property
    def software_version(self) -> str:
        """Get the software version."""
        return self.__software_version

    @property
    def software_variant(self) -> str:
        """Get the software variant."""
        return self.__software_variant

    @property
    def allow_location(self) -> bool:
        """Get the location setting."""
        return self.__allow_location

    @property
    def low_voltage_cutoff(self) -> float:
        """Get the low_voltage_cutoff setting."""
        return self.__low_voltage_cutoff

    @property
    def temperature_compensation(self) -> float:
        """Get the ext_temp_comp setting."""
        return self.__temperature_compensation

    @property
    def device_id(self) -> str:
        """Get the ID of the device (QR code ID)"""
        return self.__device_id

    @property
    def name(self) -> str:
        """Get the name of the device."""
        return self.__name

    @property
    def output_main_name(self) -> str | bool:
        """Get the main output name."""
        if "name" in self.__output_main:
            return self.__output_main["name"] or "Primary"
        else:
            return False

    @property
    def output_aux1_name(self) -> str | bool:
        """Get the aux1 output name."""
        if "name" in self.__output_aux1:
            return self.__output_aux1["name"] or "Output 1"
        else:
            return False

    @property
    def output_aux2_name(self) -> str | bool:
        """Get the aux2 output name."""
        if "name" in self.__output_aux2:
            return self.__output_aux2["name"] or "Output 2"
        else:
            return False

    @property
    def subscription_expiration(self) -> datetime:
        """Get subscription expiration."""
        return self.__subscription_expiration

    @property
    def connection_lost(self) -> bool | None:
        """Get the raw cloud connection state from API data."""
        return self.__connection_lost

    @property
    def is_connected(self) -> bool | None:
        """Get whether the device currently appears connected to cloud."""
        if self.__connection_lost is None:
            return None

        return not self.__connection_lost

    @property
    def association_status(self) -> str | None:
        """Get the app association status."""
        return self.__association_status

    @property
    def pending_approval(self) -> bool:
        """Return whether the device is waiting for association approval."""
        return self.__pending_approval

    @property
    def software_external_version(self) -> str | None:
        """Get the external software version (`sw_external` in settings)."""
        value = (self.__settings or {}).get("sw_external")
        return None if value is None else str(value)

    @property
    def low_voltage_warning(self) -> bool | None:
        """Get the low-voltage warning flag (`vwarn` in app data).

        Observed `true` while the voltage was below the low-voltage cutoff;
        the exact backend rule is not documented.
        """
        return self.__data_value("vwarn", bool)

    @property
    def last_seen_seconds(self) -> int | None:
        """Get the time since the device last contacted the cloud (`seen`).

        Interpreted as seconds from observed values; not confirmed by docs.
        """
        value = self.__data_value("seen", int | float)
        return None if value is None else int(value)

    @property
    def alarm_state(self) -> str | None:
        """Get the raw alarm state (`alarms` in app data, e.g. `ON` or `CONF`)."""
        return self.__data_value("alarms", str)

    @property
    def alarm_output(self) -> dict | None:
        """Get the alarm control output (`OUTA` in `outputs`), or None.

        Only the `outputs` section of the latest data is searched.
        """
        if not isinstance(self.__last_data, dict):
            return None
        for output in self.__last_data.get("outputs") or []:
            if isinstance(output, dict) and output.get("line") == "OUTA":
                return output
        return None

    @property
    def geofence_active(self) -> bool | None:
        """Get whether the geofence is active (EXPERIMENTAL).

        Observed: the app's geofence button switches `OUTA` (and `alarms`)
        inverted, so `OUTA` state `"OFF"` means the geofence is active and
        `"ON"` means it is not. Returns None when `OUTA` is missing or has
        another state.
        """
        output = self.alarm_output
        if output is None:
            return None
        state = output.get("state")
        if state == "OFF":
            return True
        if state == "ON":
            return False
        return None

    @property
    def geofence_enabled(self) -> bool | None:
        """Get whether the geofence is enabled (`geofence_enabled` in app data)."""
        return self.__data_value("geofence_enabled", bool)

    @property
    def geofence_radius(self) -> float | None:
        """Get the geofence radius in kilometers from settings."""
        option = self.__get_option("general", "geofence")
        if option is None or not isinstance(option.get("value"), int | float):
            return None
        return float(option["value"])

    @property
    def subscription_status(self) -> str | None:
        """Get the subscription status (`subscription.status` in app data)."""
        subscription = self.__data_value("subscription", dict)
        if subscription is None or not isinstance(subscription.get("status"), str):
            return None
        return subscription["status"]

    @property
    def default_output(self) -> str | None:
        """Get the default output setting (`def_output`)."""
        value = self.__get_value("general", "def_output")
        return value if isinstance(value, str) else None

    @property
    def signal_lost_shutdown_enabled(self) -> bool | None:
        """Get whether outputs switch off after the signal is lost (`sig_lost_off`)."""
        option = self.__get_option("general", "sig_lost_off")
        if option is None or not isinstance(option.get("enabled"), bool):
            return None
        return option["enabled"]

    @property
    def signal_lost_shutdown_minutes(self) -> int | None:
        """Get the minutes after signal loss before outputs switch off."""
        option = self.__get_option("general", "sig_lost_off")
        if option is None or not isinstance(option.get("value"), int | float):
            return None
        return int(option["value"])

    @property
    def emulation_mode(self) -> str | None:
        """Get the Webasto emulation mode setting (`webasto_emul_mode`)."""
        value = self.__get_value("webasto", "webasto_emul_mode")
        return value if isinstance(value, str) else None

    @property
    def output_main_features(self) -> dict[str, bool]:
        """Get the `*_available` feature flags of the active main output."""
        return {
            key: value
            for key, value in self.__output_main.items()
            if key.endswith("_available") and isinstance(value, bool)
        }

    @property
    def next_event(self) -> NextEvent | None:
        """Get the next timer event reported by the backend (`nextEvent`).

        `time_utc_minutes` matched the timer start in observations; the
        meaning of `day` is unknown and kept raw.
        """
        if not isinstance(self.__last_data, dict):
            return None
        return NextEvent.from_api_dict(self.__last_data.get("nextEvent"))

    def __data_value(self, key: str, expected_type: Any) -> Any:
        """Get a typed top-level value from the latest app data."""
        if not isinstance(self.__last_data, dict):
            return None
        value = self.__last_data.get(key)
        return value if isinstance(value, expected_type) else None

    def __get_option(self, group: str, key: str) -> dict | None:
        """Get a full option dict from the settings dict."""
        if not isinstance(self.settings, dict):
            return None

        for g in self.settings.get("settings_tab", []):
            if not isinstance(g, dict) or g.get("group") != group:
                continue

            for o in g.get("options", []):
                if isinstance(o, dict) and o.get("key") == key:
                    return o
        return None

    def __get_value(self, group: str, key: str) -> Any:
        """Get a value from the settings dict."""
        if self.settings is None:
            return None

        for g in self.settings["settings_tab"]:
            if g["group"] != group:
                continue

            for o in g["options"]:
                if o["key"] == key:
                    return o["value"]

    def __get_timeouts(self) -> None:
        """Get output timeouts from the settings dict."""
        if self.settings is None:
            return

        for g in self.settings["settings_tab"]:
            if g["group"] not in ["webasto", "outputs"]:
                continue

            for o in g["options"]:
                if o["key"] == "OUTH":
                    self.__timeout_heat = o["timeout"]
                elif o["key"] == "OUTV":
                    self.__timeout_vent = o["timeout"]
                elif o["key"] == "OUT1":
                    self.__timeout_aux1 = o["timeout"]
                elif o["key"] == "OUT2":
                    self.__timeout_aux2 = o["timeout"]
