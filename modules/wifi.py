import network
import time
import asyncio
import settings
import tildagon_helpers

_STA_IF = network.WLAN(network.STA_IF)
_AP_IF = network.WLAN(network.AP_IF)

DEFAULT_CONNECT_TIMEOUT = 20
DEFAULT_TX_POWER = 80
DEFAULT_SSID = "emf2024"
DEFAULT_USERNAME = "badge"
DEFAULT_PASSWORD = "badge"

WIFI_AUTH_OPEN = 0
WIFI_AUTH_WEP = 1
WIFI_AUTH_WPA_PSK = 2
WIFI_AUTH_WPA2_PSK = 3
WIFI_AUTH_WPA_WPA2_PSK = 4
WIFI_AUTH_WPA2_ENTERPRISE = 5
WIFI_AUTH_WPA3_PSK = 6
WIFI_AUTH_WPA2_WPA3_PSK = 7
WIFI_AUTH_WAPI_PSK = 8


def get_default_ssid():
    return settings.get("wifi_ssid", DEFAULT_SSID)


def get_default_username():
    val = settings.get("wifi_wpa2ent_username", None)
    if val is None and get_default_ssid() == DEFAULT_SSID:
        # In case of settings.json that doesn't specify wifi_wpa2ent_username
        val = DEFAULT_USERNAME
    return val


def get_default_password():
    return settings.get("wifi_password", DEFAULT_PASSWORD)


def get_sta_status():
    return _STA_IF.status()


def get_ssid():
    if ssid := _STA_IF.config("essid"):
        return ssid
    else:
        return get_default_ssid()


def get_ip():
    if status():
        return ifconfig()[0]
    else:
        return None


def accesspoint_get_ip():
    if accesspoint_status():
        return accesspoint_ifconfig()[0]
    else:
        return None


def active():
    return _STA_IF.active()


def get_connection_timeout():
    return settings.get("wifi_connection_timeout", DEFAULT_CONNECT_TIMEOUT)


def save_defaults(ssid, password, username):
    settings.set("wifi_ssid", ssid)
    settings.set("wifi_wpa2ent_username", username)
    settings.set("wifi_password", password)
    settings.save()


# Rest of file is adapted from https://github.com/badgeteam/ESP32-platform-firmware/blob/master/firmware/python_modules/shared/wifi.py
# See license info https://github.com/badgeteam/ESP32-platform-firmware#license-and-information

# STATION MODE
# ------------


def connect(ssid=None, password=None, username=None):
    """
    Connect to a WiFi network
    :param ssid: optional, ssid of network to connect to
    :param password: optional, password of network to connect to
    :param username: optional, WPA2-Enterprise username of network to connect to
    """
    _STA_IF.active(True)
    # 20 = 5 dBm according to https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/network/esp_wifi.html?highlight=esp_wifi_set_max_tx_power#_CPPv425esp_wifi_set_max_tx_power6int8_t
    # Anything above 8 dBm causes too much interference in the crystal circuit
    # which basically breaks all ability to transmit
    tildagon_helpers.esp_wifi_set_max_tx_power(
        settings.get("wifi_tx_power", DEFAULT_TX_POWER)
    )
    if not ssid:
        ssid = get_default_ssid()
        username = get_default_username()
        password = get_default_password()
    if username:
        tildagon_helpers.esp_wifi_sta_wpa2_ent_set_identity(username)
        tildagon_helpers.esp_wifi_sta_wpa2_ent_set_username(username)
        tildagon_helpers.esp_wifi_sta_wpa2_ent_set_password(password)
        password = None  # Don't pass to WLAN.connect()

    tildagon_helpers.esp_wifi_sta_wpa2_ent_enable(username is not None)
    _STA_IF.connect(ssid, password)


def disconnect():
    """
    Disconnect from the WiFi network
    """
    if _STA_IF.status() != network.STAT_IDLE:
        _STA_IF.disconnect()


def stop():
    """
    Disconnect from the WiFi network and disable the station interface
    """
    disconnect()
    _STA_IF.active(False)


def status():
    """
    Connection status of the station interface
    :return: boolean, connected
    """
    return _STA_IF.isconnected()


def wait(duration=None):
    """
    Wait until connection has been made to a network using the station interface
    :return: boolean, connected
    """
    if duration is None:
        duration = get_connection_timeout()
    t = duration
    while not status():
        if t <= 0:
            break
        t -= 1
        time.sleep(1)
    return status()


async def async_wait(duration=None):
    """
    Wait until connection has been made to a network using the station interface
    :return: boolean, connected
    """
    if duration is None:
        duration = get_connection_timeout()
    t = duration
    while not status():
        if t <= 0:
            break
        t -= 1
        asyncio.sleep(1)
    return status()


def scan():
    """
    Scan for WiFi networks
    :return: list, wifi networks [SSID, BSSID, CHANNEL, RSSI, AUTHMODE1, AUTHMODE2, HIDDEN]
    """
    _STA_IF.active(True)
    return _STA_IF.scan()


def ifconfig(newConfig=None):
    """
    Get or set the interface configuration of the station interface
    :return: tuple, (ip, subnet, gateway, dns)
    """
    if newConfig:
        return _STA_IF.ifconfig(newConfig)
    else:
        return _STA_IF.ifconfig()


# ACCESS POINT MODE
# -----------------


def accesspoint_start(ssid, password=None):
    """
    Create a WiFi access point
    :param ssid: SSID of the network
    :param password: Password of the network (optional)
    """
    if password and len(password) < 8:
        raise Exception("Password too short: must be at least 8 characters long")
    _AP_IF.active(True)
    if password:
        _AP_IF.config(essid=ssid, authmode=network.AUTH_WPA2_PSK, password=password)
    else:
        _AP_IF.config(essid=ssid, authmode=network.AUTH_OPEN)


def accesspoint_status():
    """
    Accesspoint status
    :return: boolean, active
    """
    return _AP_IF.active()


def accesspoint_stop():
    """
    Disable the accesspoint
    """
    _AP_IF.active(False)


def accesspoint_ifconfig(newConfig=None):
    """
    Get or set the interface configuration of the accesspoint interface
    :return: tuple, (ip, subnet, gateway, dns)
    """
    if newConfig:
        return _AP_IF.ifconfig(newConfig)
    else:
        return _AP_IF.ifconfig()


# EXTRAS
# -----------------

# NOTE(tomsci): RTC.ntp_sync() not a thing in our micropython version

# def ntp(onlyIfNeeded=True, server='pool.ntp.org'):
#     '''
#     Synchronize the system clock with NTP
#     :return: boolean, synchronized
#     '''
#     if onlyIfNeeded and time.time() > 1482192000:
#         return True #RTC is already set, sync not needed
#     rtc = machine.RTC()
#     if not status():
#         return False # Not connected to a WiFi network
#     return rtc.ntp_sync(server)
