"""Tests for the nmcli output parsers (pure functions, no shell needed)."""

from wifi_manager.backends.linux import (
    _split_terse,
    parse_saved,
    parse_scan,
    parse_status,
)


def test_split_terse_handles_escaped_colons():
    # A BSSID field escapes its colons as \:
    line = r"*:MyNet:80:WPA2:11"
    assert _split_terse(line) == ["*", "MyNet", "80", "WPA2", "11"]

    escaped = r"no:Cafe\: Free:42:--:6"
    assert _split_terse(escaped) == ["no", "Cafe: Free", "42", "--", "6"]


def test_parse_scan_sorts_and_dedups():
    output = "\n".join(
        [
            "*:HomeNet:78:WPA2:6",
            " :HomeNet:40:WPA2:6",  # weaker duplicate, should be dropped
            " :Cafe:90:--:11",
            " ::55:WPA2:1",  # hidden network, no SSID -> skipped
        ]
    )
    nets = parse_scan(output)
    assert [n.ssid for n in nets] == ["Cafe", "HomeNet"]  # strongest first
    home = next(n for n in nets if n.ssid == "HomeNet")
    assert home.signal == 78  # kept the stronger sighting
    assert home.in_use is True
    cafe = next(n for n in nets if n.ssid == "Cafe")
    assert cafe.is_open is True
    assert cafe.channel == 11


def test_parse_status_finds_active():
    output = "\n".join([" :Cafe:90", "*:HomeNet:78"])
    st = parse_status(output)
    assert st.connected is True
    assert st.ssid == "HomeNet"
    assert st.signal == 78


def test_parse_status_none_active():
    output = "\n".join([" :Cafe:90", " :HomeNet:78"])
    assert parse_status(output).connected is False


def test_parse_saved_filters_wireless():
    output = "\n".join(
        [
            "HomeNet:802-11-wireless",
            "Wired connection 1:802-3-ethernet",
            "Cafe:802-11-wireless",
        ]
    )
    assert parse_saved(output) == ["HomeNet", "Cafe"]
