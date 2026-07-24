"""macOS backend built on ``airport`` and ``networksetup``.

Note: Apple removed the ``airport -s`` scan output on very recent macOS
releases. Where scanning is unavailable the backend raises a clear error rather
than returning misleading empty results.
"""

from __future__ import annotations

import re
from typing import List, Optional

from ..models import ConnectionStatus, Network
from .base import WifiBackend, WifiError, run

AIRPORT = (
    "/System/Library/PrivateFrameworks/Apple80211.framework"
    "/Versions/Current/Resources/airport"
)


def rssi_to_quality(rssi: int) -> int:
    """Convert a dBm RSSI value to a rough 0-100 quality percentage.

    -50 dBm or better maps to 100; -100 dBm or worse maps to 0.
    """
    if rssi >= -50:
        return 100
    if rssi <= -100:
        return 0
    return 2 * (rssi + 100)


def parse_scan(output: str) -> List[Network]:
    """Parse the columnar output of ``airport -s``.

    Columns: SSID BSSID RSSI CHANNEL HT CC SECURITY
    SSIDs may contain spaces, so we anchor on the BSSID (six colon-separated
    hex pairs) to find where the fixed columns begin.
    """
    bssid_re = re.compile(r"([0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5})")
    networks: List[Network] = []
    lines = output.splitlines()
    for raw in lines[1:]:  # skip header row
        if not raw.strip():
            continue
        m = bssid_re.search(raw)
        if not m:
            continue
        ssid = raw[: m.start()].strip()
        bssid = m.group(1)
        rest = raw[m.end() :].split()
        if len(rest) < 2:
            continue
        try:
            rssi = int(rest[0])
        except ValueError:
            continue
        try:
            channel: Optional[int] = int(rest[1].split(",")[0])
        except ValueError:
            channel = None
        # Columns after BSSID: RSSI CHANNEL HT CC SECURITY
        security = " ".join(rest[4:]) if len(rest) > 4 else ""
        networks.append(
            Network(
                ssid=ssid,
                signal=rssi_to_quality(rssi),
                security=security,
                channel=channel,
                bssid=bssid,
            )
        )
    best: dict[str, Network] = {}
    for net in networks:
        existing = best.get(net.ssid)
        if existing is None or net.signal > existing.signal:
            best[net.ssid] = net
    return sorted(best.values(), key=lambda n: n.signal, reverse=True)


def parse_status(output: str) -> ConnectionStatus:
    """Parse ``airport -I`` key/value output."""
    info: dict[str, str] = {}
    for raw in output.splitlines():
        if ":" in raw:
            key, _, val = raw.partition(":")
            info[key.strip()] = val.strip()
    ssid = info.get("SSID", "")
    if not ssid or info.get("AirPort") == "Off":
        return ConnectionStatus(connected=False)
    signal: Optional[int] = None
    if "agrCtlRSSI" in info:
        try:
            signal = rssi_to_quality(int(info["agrCtlRSSI"]))
        except ValueError:
            signal = None
    return ConnectionStatus(connected=True, ssid=ssid, signal=signal)


def parse_saved(output: str) -> List[str]:
    """Parse ``networksetup -listpreferredwirelessnetworks`` output."""
    saved: List[str] = []
    for raw in output.splitlines():
        line = raw.strip()
        if not line or line.startswith("Preferred networks"):
            continue
        saved.append(line)
    return saved


class MacOSBackend(WifiBackend):
    name = "macos/airport"

    def _wifi_device(self) -> str:
        output = run(["networksetup", "-listallhardwareports"])
        lines = output.splitlines()
        for i, line in enumerate(lines):
            if "Wi-Fi" in line or "AirPort" in line:
                for follow in lines[i + 1 : i + 3]:
                    if follow.strip().startswith("Device:"):
                        return follow.split(":", 1)[1].strip()
        return "en0"

    def scan(self) -> List[Network]:
        output = run([AIRPORT, "-s"])
        nets = parse_scan(output)
        if not nets and "SSID" not in output:
            raise WifiError(
                "Scanning returned no data. On recent macOS the 'airport -s' "
                "scan API was removed; use the macOS WiFi menu to scan."
            )
        return nets

    def status(self) -> ConnectionStatus:
        output = run([AIRPORT, "-I"])
        st = parse_status(output)
        if st.connected:
            return ConnectionStatus(
                connected=True, ssid=st.ssid, signal=st.signal, interface=self._wifi_device()
            )
        return st

    def saved_networks(self) -> List[str]:
        output = run(
            ["networksetup", "-listpreferredwirelessnetworks", self._wifi_device()]
        )
        return parse_saved(output)

    def connect(self, ssid: str, password: Optional[str] = None) -> None:
        cmd = ["networksetup", "-setairportnetwork", self._wifi_device(), ssid]
        if password:
            cmd.append(password)
        run(cmd, timeout=60)

    def disconnect(self) -> None:
        # airport -z disassociates without turning the radio off.
        run(["sudo", AIRPORT, "-z"], check=False)
