"""Data structures shared across the WiFi manager backends."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Network:
    """A single WiFi network discovered during a scan.

    signal is normalised to a 0-100 quality percentage regardless of what the
    underlying OS tool reports (nmcli already uses 0-100, macOS reports dBm,
    netsh reports a percentage), so callers can compare across platforms.
    """

    ssid: str
    signal: int
    security: str = ""
    channel: Optional[int] = None
    bssid: str = ""
    in_use: bool = False

    @property
    def is_open(self) -> bool:
        sec = self.security.strip().lower()
        return sec in ("", "--", "none", "open")

    def bars(self) -> str:
        """A small textual signal meter, e.g. ``▂▄▆_``."""
        levels = "_▂▄▆█"
        # Map 0-100 onto 0-4 filled bars.
        filled = min(4, max(0, round(self.signal / 25)))
        return "".join(levels[4] if i < filled else levels[0] for i in range(4))


@dataclass(frozen=True)
class ConnectionStatus:
    """The current WiFi association state of an interface."""

    connected: bool
    ssid: str = ""
    signal: Optional[int] = None
    interface: str = ""

    def describe(self) -> str:
        if not self.connected:
            return "Not connected to any WiFi network"
        parts = [f"Connected to '{self.ssid}'"]
        if self.signal is not None:
            parts.append(f"signal {self.signal}%")
        if self.interface:
            parts.append(f"on {self.interface}")
        return ", ".join(parts)
