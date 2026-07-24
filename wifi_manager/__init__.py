"""wifi_manager: a small cross-platform WiFi scanner and connection manager.

The package wraps each OS's native WiFi tooling behind a common interface:

    from wifi_manager import get_backend

    backend = get_backend()
    for net in backend.scan():
        print(net.ssid, net.signal)
"""

from __future__ import annotations

from .backends import WifiBackend, WifiError, get_backend
from .models import ConnectionStatus, Network

__version__ = "0.1.0"

__all__ = [
    "get_backend",
    "WifiBackend",
    "WifiError",
    "Network",
    "ConnectionStatus",
    "__version__",
]
