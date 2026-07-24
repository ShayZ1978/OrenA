"""Tests for the netsh output parsers."""

from wifi_manager.backends.windows import (
    build_profile_xml,
    parse_saved,
    parse_scan,
    parse_status,
)

SHOW_NETWORKS = """
Interface name : Wi-Fi
There are 2 networks currently visible.

SSID 1 : HomeNet
    Network type            : Infrastructure
    Authentication          : WPA2-Personal
    Encryption              : CCMP
    BSSID 1                 : aa:bb:cc:dd:ee:ff
         Signal             : 82%
         Radio type         : 802.11ac
         Channel            : 36

SSID 2 : Cafe Free
    Network type            : Infrastructure
    Authentication          : Open
    Encryption              : None
    BSSID 1                 : 11:22:33:44:55:66
         Signal             : 60%
         Channel            : 6
"""

SHOW_INTERFACES = """
There is 1 interface on the system:

    Name                   : Wi-Fi
    State                  : connected
    SSID                   : HomeNet
    Signal                 : 82%
    Channel                : 36
"""

SHOW_PROFILES = """
Profiles on interface Wi-Fi:

User profiles
-------------
    All User Profile     : HomeNet
    All User Profile     : Cafe Free
"""


def test_parse_scan():
    nets = parse_scan(SHOW_NETWORKS)
    assert [n.ssid for n in nets] == ["HomeNet", "Cafe Free"]
    home = nets[0]
    assert home.signal == 82
    assert home.channel == 36
    assert "WPA2" in home.security
    assert nets[1].is_open is True


def test_parse_status_connected():
    st = parse_status(SHOW_INTERFACES)
    assert st.connected is True
    assert st.ssid == "HomeNet"
    assert st.signal == 82
    assert st.interface == "Wi-Fi"


def test_parse_status_disconnected():
    output = SHOW_INTERFACES.replace("connected", "disconnected")
    assert parse_status(output).connected is False


def test_parse_saved():
    assert parse_saved(SHOW_PROFILES) == ["HomeNet", "Cafe Free"]


def test_build_profile_xml_open_vs_secured():
    secured = build_profile_xml("HomeNet", "s3cret")
    assert "WPA2PSK" in secured
    assert "s3cret" in secured

    open_net = build_profile_xml("Cafe", None)
    assert "<authentication>open</authentication>" in open_net
    assert "sharedKey" not in open_net
