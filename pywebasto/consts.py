"""Constants used for Webasto."""

API_URL = "https://my.webastoconnect.com/webapi"
APP_API_URL = "https://control.webastoconnect.com"
APP_USER_AGENT = "Google-HTTP-Java-Client/1.24.1 (gzip)"
APP_CLIENT_INFO = "Android 3.2.0 0"

CMD_HEATER_ON = "OUT H ON"
CMD_HEATER_OFF = "OUT H OFF"

CMD_VENTILATION_ON = "OUT V ON"
CMD_VENTILATION_OFF = "OUT V OFF"

CMD_AUX1_ON = "OUT 1 ON"
CMD_AUX1_OFF = "OUT 1 OFF"

CMD_AUX2_ON = "OUT 2 ON"
CMD_AUX2_OFF = "OUT 2 OFF"

# Alarm control output (OUTA). The Webasto app uses it for its geofence button.
# Which command activates the geofence is inferred, not observed; see
# `WebastoConnect.set_geofence` and docs/protocol.md.
CMD_ALARM_ON = "OUT A ON"
CMD_ALARM_OFF = "OUT A OFF"

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0"
