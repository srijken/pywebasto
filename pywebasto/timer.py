"""Timer models for Webasto timer operations."""

from dataclasses import dataclass


@dataclass(slots=True)
class SimpleTimer:
    """Representation of an observed `simple` timer payload."""

    start: int
    duration: int
    repeat: int
    latitude: str | None = None
    longitude: str | None = None
    enabled: bool = True

    def validate(self) -> None:
        """Validate timer fields based on observed payload constraints."""
        if self.start <= 0:
            raise ValueError("start must be > 0")
        if self.duration <= 0:
            raise ValueError("duration must be > 0")
        if self.repeat < 0:
            raise ValueError("repeat must be >= 0")
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude and longitude must both be set or both be None")
        if self.latitude is not None and self.latitude == "":
            raise ValueError("latitude must be a non-empty string when provided")
        if self.longitude is not None and self.longitude == "":
            raise ValueError("longitude must be a non-empty string when provided")

    def to_api_dict(self) -> dict:
        """Serialize to the observed API shape."""
        self.validate()
        payload = {
            "type": "simple",
            "start": self.start,
            "duration": self.duration,
            "repeat": self.repeat,
            "enabled": self.enabled,
        }
        if self.latitude is not None and self.longitude is not None:
            payload["location"] = {"lat": self.latitude, "lon": self.longitude}
        return payload

    @classmethod
    def from_api_dict(cls, data: dict) -> "SimpleTimer":
        """Build from a timer dict returned by API data endpoints."""
        if data.get("type") != "simple":
            raise ValueError("timer type must be 'simple'")

        latitude, longitude = _parse_location(data.get("location"))
        timer = cls(
            start=int(data["start"]),
            duration=int(data["duration"]),
            repeat=int(data["repeat"]),
            latitude=latitude,
            longitude=longitude,
            enabled=bool(data.get("enabled", True)),
        )
        timer.validate()
        return timer


@dataclass(slots=True)
class SmartTimer:
    """Representation of an observed `smart` timer payload.

    A smart timer has a departure time instead of a start time; the heater
    decides itself when to start, limited by `max_duration`. `start` holds the
    departure time in minutes after midnight UTC, as returned by API data.
    """

    start: int
    max_duration: int
    comfort_level: int
    repeat: int
    latitude: str | None = None
    longitude: str | None = None
    enabled: bool = True

    def validate(self) -> None:
        """Validate timer fields based on observed payload constraints."""
        if self.start <= 0:
            raise ValueError("start must be > 0")
        if self.max_duration <= 0:
            raise ValueError("max_duration must be > 0")
        if self.comfort_level <= 0:
            raise ValueError("comfort_level must be > 0")
        if self.repeat < 0:
            raise ValueError("repeat must be >= 0")
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude and longitude must both be set or both be None")
        if self.latitude is not None and self.latitude == "":
            raise ValueError("latitude must be a non-empty string when provided")
        if self.longitude is not None and self.longitude == "":
            raise ValueError("longitude must be a non-empty string when provided")

    def to_api_dict(self) -> dict:
        """Serialize to the observed app-backend API shape."""
        self.validate()
        payload = {
            "type": "smart",
            "start": self.start,
            # The app sends `departure`; the web API sends `start` and
            # `departure` with the same value. API data only returns `start`.
            "departure": self.start,
            "maxDuration": self.max_duration,
            "comfortLevel": self.comfort_level,
            "repeat": self.repeat,
            "enabled": self.enabled,
        }
        if self.latitude is not None and self.longitude is not None:
            payload["location"] = {"lat": self.latitude, "lon": self.longitude}
        return payload

    @classmethod
    def from_api_dict(cls, data: dict) -> "SmartTimer":
        """Build from a timer dict returned by API data endpoints."""
        if data.get("type") != "smart":
            raise ValueError("timer type must be 'smart'")

        latitude, longitude = _parse_location(data.get("location"))
        timer = cls(
            start=int(data["start"]),
            max_duration=int(data["maxDuration"]),
            comfort_level=int(data["comfortLevel"]),
            repeat=int(data["repeat"]),
            latitude=latitude,
            longitude=longitude,
            enabled=bool(data.get("enabled", True)),
        )
        timer.validate()
        return timer


@dataclass(slots=True)
class UnknownTimer:
    """A timer of a type this library does not model.

    The raw payload is kept so it can be sent back unchanged when the full
    timer list is saved.
    """

    data: dict

    def to_api_dict(self) -> dict:
        """Return the raw payload unchanged."""
        return dict(self.data)


Timer = SimpleTimer | SmartTimer | UnknownTimer


def _parse_location(location: object) -> tuple[str | None, str | None]:
    """Parse an optional timer location into latitude and longitude."""
    if location is None:
        return None, None
    if not isinstance(location, dict):
        raise TypeError("timer location must be a dict when provided")
    return str(location["lat"]), str(location["lon"])


def timer_from_api_dict(data: dict) -> Timer:
    """Build the matching timer model for a timer dict from the API."""
    timer_type = data.get("type")
    if timer_type == "simple":
        return SimpleTimer.from_api_dict(data)
    if timer_type == "smart":
        return SmartTimer.from_api_dict(data)
    return UnknownTimer(data=dict(data))
