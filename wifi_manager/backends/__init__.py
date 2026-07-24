"""Backend selection for the current platform."""

from __future__ import annotations

import platform

from .base import WifiBackend, WifiError


def get_backend() -> WifiBackend:
    """Return the WiFi backend appropriate for the host OS."""
    system = platform.system()
    if system == "Linux":
        from .linux import LinuxBackend

        return LinuxBackend()
    if system == "Darwin":
        from .macos import MacOSBackend

        return MacOSBackend()
    if system == "Windows":
        from .windows import WindowsBackend

        return WindowsBackend()
    raise WifiError(f"Unsupported platform: {system!r}")


__all__ = ["get_backend", "WifiBackend", "WifiError"]
