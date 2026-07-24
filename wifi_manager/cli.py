"""Command-line interface for the WiFi manager."""

from __future__ import annotations

import argparse
import getpass
import sys
from typing import List, Optional

from .backends import WifiError, get_backend
from .models import Network


def _format_scan(networks: List[Network]) -> str:
    if not networks:
        return "No networks found."
    ssid_w = max(4, min(32, max(len(n.ssid) for n in networks)))
    header = f"{'':1} {'SSID':<{ssid_w}}  {'SIGNAL':>6}  {'BARS':<4}  SECURITY"
    rows = [header, "-" * len(header)]
    for net in networks:
        marker = "*" if net.in_use else " "
        ssid = net.ssid if len(net.ssid) <= ssid_w else net.ssid[: ssid_w - 1] + "…"
        sec = net.security or ("open" if net.is_open else "")
        rows.append(
            f"{marker} {ssid:<{ssid_w}}  {net.signal:>5}%  {net.bars():<4}  {sec}"
        )
    return "\n".join(rows)


def cmd_scan(args: argparse.Namespace) -> int:
    backend = get_backend()
    networks = backend.scan()
    print(_format_scan(networks))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    backend = get_backend()
    print(backend.status().describe())
    return 0


def cmd_saved(args: argparse.Namespace) -> int:
    backend = get_backend()
    saved = backend.saved_networks()
    if not saved:
        print("No saved networks.")
    else:
        for name in saved:
            print(name)
    return 0


def cmd_connect(args: argparse.Namespace) -> int:
    backend = get_backend()
    password: Optional[str] = args.password
    if args.ask_password and not password:
        password = getpass.getpass(f"Password for '{args.ssid}': ")
    backend.connect(args.ssid, password or None)
    print(backend.status().describe())
    return 0


def cmd_disconnect(args: argparse.Namespace) -> int:
    backend = get_backend()
    backend.disconnect()
    print("Disconnected.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wifi",
        description="Scan, inspect, and manage WiFi connections (Linux / macOS / Windows).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_scan = sub.add_parser("scan", help="List visible networks, strongest first.")
    p_scan.set_defaults(func=cmd_scan)

    p_status = sub.add_parser("status", help="Show the current connection.")
    p_status.set_defaults(func=cmd_status)

    p_saved = sub.add_parser("saved", help="List saved/known networks.")
    p_saved.set_defaults(func=cmd_saved)

    p_connect = sub.add_parser("connect", help="Connect to a network by SSID.")
    p_connect.add_argument("ssid", help="Network name to connect to.")
    p_connect.add_argument(
        "-p", "--password", help="Network password (omit for open networks)."
    )
    p_connect.add_argument(
        "-a",
        "--ask-password",
        action="store_true",
        help="Prompt for the password interactively (avoids shell history).",
    )
    p_connect.set_defaults(func=cmd_connect)

    p_disc = sub.add_parser("disconnect", help="Disconnect the active WiFi interface.")
    p_disc.set_defaults(func=cmd_disconnect)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except WifiError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\naborted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
