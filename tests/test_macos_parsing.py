"""Tests for the macOS airport/networksetup parsers."""

from wifi_manager.backends.macos import (
    parse_saved,
    parse_scan,
    parse_status,
    rssi_to_quality,
)

AIRPORT_SCAN = """\
                            SSID BSSID             RSSI CHANNEL HT CC SECURITY
                         HomeNet aa:bb:cc:dd:ee:ff  -45 36      Y  US WPA2(PSK/AES/AES)
                       Cafe Free 11:22:33:44:55:66  -72 6       Y  US NONE
"""

AIRPORT_INFO = """\
     agrCtlRSSI: -45
     agrExtRSSI: 0
          state: running
        op mode: station
           SSID: HomeNet
          BSSID: aa:bb:cc:dd:ee:ff
"""

PREFERRED = """\
Preferred networks on en0:
	HomeNet
	Cafe Free
"""


def test_rssi_to_quality_bounds():
    assert rssi_to_quality(-40) == 100
    assert rssi_to_quality(-100) == 0
    assert rssi_to_quality(-75) == 50


def test_parse_scan_with_spaced_ssids():
    nets = parse_scan(AIRPORT_SCAN)
    assert [n.ssid for n in nets] == ["HomeNet", "Cafe Free"]  # strongest first
    home = nets[0]
    assert home.bssid == "aa:bb:cc:dd:ee:ff"
    assert home.channel == 36
    assert home.signal == 100
    assert nets[1].is_open is True


def test_parse_status():
    st = parse_status(AIRPORT_INFO)
    assert st.connected is True
    assert st.ssid == "HomeNet"
    assert st.signal == 100


def test_parse_status_off():
    assert parse_status("AirPort: Off").connected is False


def test_parse_saved():
    assert parse_saved(PREFERRED) == ["HomeNet", "Cafe Free"]
