"""Abstract backend interface plus a small subprocess helper."""

from __future__ import annotations

import subprocess
from abc import ABC, abstractmethod
from typing import List, Optional, Sequence

from ..models import ConnectionStatus, Network


class WifiError(RuntimeError):
    """Raised when a WiFi operation fails or a required tool is missing."""


def run(cmd: Sequence[str], *, check: bool = True, timeout: int = 30) -> str:
    """Run a command and return its stdout as text.

    Raises WifiError (rather than leaking subprocess exceptions) so the CLI can
    present a clean message.
    """
    try:
        proc = subprocess.run(
            list(cmd),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        raise WifiError(
            f"Required tool '{cmd[0]}' not found. Is it installed and on PATH?"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise WifiError(f"Command timed out after {timeout}s: {' '.join(cmd)}") from exc

    if check and proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise WifiError(f"Command failed ({proc.returncode}): {' '.join(cmd)}\n{detail}")
    return proc.stdout


class WifiBackend(ABC):
    """Platform-specific implementation of WiFi operations."""

    name = "base"

    @abstractmethod
    def scan(self) -> List[Network]:
        """Return the list of currently visible networks."""

    @abstractmethod
    def status(self) -> ConnectionStatus:
        """Return the current association state."""

    @abstractmethod
    def saved_networks(self) -> List[str]:
        """Return SSIDs of saved/known networks."""

    @abstractmethod
    def connect(self, ssid: str, password: Optional[str] = None) -> None:
        """Connect to ``ssid``, optionally supplying ``password``."""

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect the active WiFi interface."""
