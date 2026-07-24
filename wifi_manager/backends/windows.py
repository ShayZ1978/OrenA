"""Windows backend built on ``netsh wlan``."""

from __future__ import annotations

import os
import tempfile
from typing import List, Optional

from ..models import ConnectionStatus, Network
from .base import WifiBackend, WifiError, run


def _kv(line: str) -> tuple[str, str]:
    key, _, val = line.partition(":")
    return key.strip(), val.strip()


def parse_scan(output: str) -> List[Network]:
    """Parse ``netsh wlan show networks mode=bssid``."""
    networks: List[Network] = []
    ssid: Optional[str] = None
    security = ""
    signal = 0
    channel: Optional[int] = None
    have_ssid = False

    def flush() -> None:
        nonlocal have_ssid
        if have_ssid and ssid:
            networks.append(
                Network(
                    ssid=ssid,
                    signal=signal,
                    security=security,
                    channel=channel,
                )
            )
        have_ssid = False

    for raw in output.splitlines():
        line = raw.strip()
        if line.startswith("SSID ") and ":" in line:
            flush()
            _, ssid = _kv(line)
            security = ""
            signal = 0
            channel = None
            have_ssid = True
        elif line.startswith("Authentication"):
            _, security = _kv(line)
        elif line.startswith("Signal"):
            _, val = _kv(line)
            try:
                signal = int(val.rstrip("%"))
            except ValueError:
                signal = 0
        elif line.startswith("Channel"):
            _, val = _kv(line)
            try:
                channel = int(val)
            except ValueError:
                channel = None
    flush()

    best: dict[str, Network] = {}
    for net in networks:
        existing = best.get(net.ssid)
        if existing is None or net.signal > existing.signal:
            best[net.ssid] = net
    return sorted(best.values(), key=lambda n: n.signal, reverse=True)


def parse_status(output: str) -> ConnectionStatus:
    """Parse ``netsh wlan show interfaces``."""
    info: dict[str, str] = {}
    for raw in output.splitlines():
        if ":" in raw:
            key, val = _kv(raw)
            if key:
                info[key] = val
    state = info.get("State", "").strip().lower()
    # netsh reports "connected" or "disconnected"; match exactly so the
    # substring "connected" inside "disconnected" isn't a false positive.
    if state != "connected":
        return ConnectionStatus(connected=False, interface=info.get("Name", ""))
    signal: Optional[int] = None
    if "Signal" in info:
        try:
            signal = int(info["Signal"].rstrip("%"))
        except ValueError:
            signal = None
    return ConnectionStatus(
        connected=True,
        ssid=info.get("SSID", ""),
        signal=signal,
        interface=info.get("Name", ""),
    )


def parse_saved(output: str) -> List[str]:
    """Parse ``netsh wlan show profiles``."""
    saved: List[str] = []
    for raw in output.splitlines():
        if "All User Profile" in raw or "User Profile" in raw:
            _, name = _kv(raw)
            if name:
                saved.append(name)
    return saved


def build_profile_xml(ssid: str, password: Optional[str]) -> str:
    """Build a WLAN profile XML for an open or WPA2-PSK network."""
    if password:
        security = f"""
        <authEncryption>
            <authentication>WPA2PSK</authentication>
            <encryption>AES</encryption>
            <useOneX>false</useOneX>
        </authEncryption>
        <sharedKey>
            <keyType>passPhrase</keyType>
            <protected>false</protected>
            <keyMaterial>{password}</keyMaterial>
        </sharedKey>"""
    else:
        security = """
        <authEncryption>
            <authentication>open</authentication>
            <encryption>none</encryption>
            <useOneX>false</useOneX>
        </authEncryption>"""
    return f"""<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>{ssid}</name>
    <SSIDConfig>
        <SSID>
            <name>{ssid}</name>
        </SSID>
    </SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>auto</connectionMode>
    <MSM>
        <security>{security}
        </security>
    </MSM>
</WLANProfile>"""


class WindowsBackend(WifiBackend):
    name = "windows/netsh"

    def scan(self) -> List[Network]:
        output = run(["netsh", "wlan", "show", "networks", "mode=bssid"])
        return parse_scan(output)

    def status(self) -> ConnectionStatus:
        output = run(["netsh", "wlan", "show", "interfaces"])
        return parse_status(output)

    def saved_networks(self) -> List[str]:
        output = run(["netsh", "wlan", "show", "profiles"])
        return parse_saved(output)

    def connect(self, ssid: str, password: Optional[str] = None) -> None:
        saved = self.saved_networks()
        if ssid not in saved:
            # netsh can only connect to an existing profile, so create one.
            xml = build_profile_xml(ssid, password)
            fd, path = tempfile.mkstemp(suffix=".xml")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as fh:
                    fh.write(xml)
                run(["netsh", "wlan", "add", "profile", f"filename={path}"])
            finally:
                try:
                    os.remove(path)
                except OSError:
                    pass
        run(["netsh", "wlan", "connect", f"name={ssid}", f"ssid={ssid}"], timeout=60)

    def disconnect(self) -> None:
        run(["netsh", "wlan", "disconnect"])
