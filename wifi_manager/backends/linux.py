"""Linux backend built on NetworkManager's ``nmcli``."""

from __future__ import annotations

from typing import List, Optional

from ..models import ConnectionStatus, Network
from .base import WifiBackend, WifiError, run


def _unescape(field: str) -> str:
    """Undo nmcli terse-mode escaping (``\\:`` and ``\\\\``)."""
    out = []
    it = iter(field)
    for ch in it:
        if ch == "\\":
            out.append(next(it, ""))
        else:
            out.append(ch)
    return "".join(out)


def _split_terse(line: str) -> List[str]:
    """Split an nmcli ``-t`` line on unescaped colons."""
    fields: List[str] = []
    buf: List[str] = []
    i = 0
    while i < len(line):
        ch = line[i]
        if ch == "\\" and i + 1 < len(line):
            buf.append(line[i : i + 2])
            i += 2
            continue
        if ch == ":":
            fields.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
        i += 1
    fields.append("".join(buf))
    return [_unescape(f) for f in fields]


def parse_scan(output: str) -> List[Network]:
    """Parse ``nmcli -t -f IN-USE,SSID,SIGNAL,SECURITY,CHAN device wifi list``."""
    networks: List[Network] = []
    for raw in output.splitlines():
        if not raw.strip():
            continue
        fields = _split_terse(raw)
        if len(fields) < 5:
            continue
        in_use, ssid, signal, security, chan = fields[:5]
        if not ssid:
            continue  # hidden network with no advertised SSID
        try:
            signal_val = int(signal)
        except ValueError:
            signal_val = 0
        try:
            chan_val: Optional[int] = int(chan)
        except ValueError:
            chan_val = None
        networks.append(
            Network(
                ssid=ssid,
                signal=signal_val,
                security=security or "",
                channel=chan_val,
                in_use=in_use.strip() == "*",
            )
        )
    # Strongest first, de-duplicated by SSID (keep the strongest sighting).
    best: dict[str, Network] = {}
    for net in networks:
        existing = best.get(net.ssid)
        if existing is None or net.signal > existing.signal:
            best[net.ssid] = net
    return sorted(best.values(), key=lambda n: n.signal, reverse=True)


def parse_status(output: str) -> ConnectionStatus:
    """Parse ``nmcli -t -f IN-USE,SSID,SIGNAL device wifi list`` for the active row."""
    for raw in output.splitlines():
        fields = _split_terse(raw)
        if len(fields) < 3:
            continue
        in_use, ssid, signal = fields[:3]
        if in_use.strip() == "*":
            try:
                sig: Optional[int] = int(signal)
            except ValueError:
                sig = None
            return ConnectionStatus(connected=True, ssid=ssid, signal=sig)
    return ConnectionStatus(connected=False)


def parse_saved(output: str) -> List[str]:
    """Parse ``nmcli -t -f NAME,TYPE connection show`` keeping wifi entries."""
    saved: List[str] = []
    for raw in output.splitlines():
        fields = _split_terse(raw)
        if len(fields) < 2:
            continue
        name, ctype = fields[0], fields[1]
        if "wireless" in ctype and name:
            saved.append(name)
    return saved


class LinuxBackend(WifiBackend):
    name = "linux/nmcli"

    def _wifi_device(self) -> str:
        output = run(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "device"])
        for raw in output.splitlines():
            fields = _split_terse(raw)
            if len(fields) >= 2 and fields[1] == "wifi":
                return fields[0]
        raise WifiError("No WiFi device found via nmcli.")

    def scan(self) -> List[Network]:
        # Ask nmcli to trigger a rescan so results are fresh.
        run(["nmcli", "device", "wifi", "rescan"], check=False)
        output = run(
            ["nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY,CHAN", "device", "wifi", "list"]
        )
        return parse_scan(output)

    def status(self) -> ConnectionStatus:
        output = run(["nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL", "device", "wifi", "list"])
        st = parse_status(output)
        if st.connected:
            return ConnectionStatus(
                connected=True, ssid=st.ssid, signal=st.signal, interface=self._wifi_device()
            )
        return st

    def saved_networks(self) -> List[str]:
        output = run(["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show"])
        return parse_saved(output)

    def connect(self, ssid: str, password: Optional[str] = None) -> None:
        cmd = ["nmcli", "device", "wifi", "connect", ssid]
        if password:
            cmd += ["password", password]
        run(cmd, timeout=60)

    def disconnect(self) -> None:
        run(["nmcli", "device", "disconnect", self._wifi_device()])
