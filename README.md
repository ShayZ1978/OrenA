# wifi-manager

A small, dependency-free **cross-platform WiFi scanner and connection manager**
CLI. It wraps each operating system's native WiFi tooling behind one interface:

| Platform | Tools used |
|----------|-----------------------------------------|
| Linux    | `nmcli` (NetworkManager)                |
| macOS    | `airport`, `networksetup`               |
| Windows  | `netsh wlan`                            |

> **Note:** This is a tool for managing WiFi on the machine it runs on. It does
> not — and cannot — connect a headless cloud/CI container to a remote WiFi
> router, since those environments have no WiFi radio and no line of sight to
> your LAN. Run it on a laptop/desktop with a wireless adapter.

## Install

```bash
# From the repo root
pip install .

# Or run without installing
python -m wifi_manager --help
```

## Usage

```bash
wifi scan                        # list visible networks, strongest first
wifi status                      # show the current connection
wifi saved                       # list saved / known networks
wifi connect "My Network" -a     # connect, prompting for the password
wifi connect "Cafe WiFi"         # connect to an open network
wifi connect "My Net" -p s3cret  # connect with an inline password
wifi disconnect                  # drop the active WiFi connection
```

Example `scan` output:

```
  SSID              SIGNAL  BARS  SECURITY
--------------------------------------------
* HomeNet             82%  ████  WPA2
  Cafe Free           60%  ███_  open
  Neighbour           35%  ██__  WPA2
```

The `*` marks the network you're currently connected to. Signal is normalised
to a 0–100% quality value on every platform (macOS dBm/RSSI is converted), so
results are comparable regardless of OS.

### Passwords

Prefer `-a/--ask-password` to be prompted interactively — this keeps the
password out of your shell history and process list. `-p/--password` is provided
for scripting but exposes the password to anything that can read the process
table.

## Permissions

Some operations need elevated privileges depending on the OS and its
configuration:

- **Linux:** connecting usually works for the logged-in desktop user; on locked
  down systems you may need `sudo` or a polkit rule.
- **macOS:** `disconnect` uses `airport -z`, which requires `sudo`.
- **Windows:** connecting to a *new* network creates a WLAN profile; run the
  terminal as Administrator if profile creation is restricted.

## Library use

```python
from wifi_manager import get_backend

backend = get_backend()          # picks the right backend for this OS
for net in backend.scan():
    print(f"{net.ssid:20} {net.signal}%  {net.security}")

print(backend.status().describe())
backend.connect("HomeNet", password="s3cret")
```

## Development

The OS command **parsing** is isolated in pure functions so it can be tested
without any real WiFi hardware, using captured sample output:

```bash
pip install -e ".[dev]"
pytest
```

## Layout

```
wifi_manager/
├── __init__.py          # public API
├── __main__.py          # python -m wifi_manager
├── cli.py               # argparse CLI
├── models.py            # Network / ConnectionStatus dataclasses
└── backends/
    ├── __init__.py      # get_backend() picks by platform
    ├── base.py          # abstract backend + subprocess helper
    ├── linux.py         # nmcli
    ├── macos.py         # airport / networksetup
    └── windows.py       # netsh
tests/                   # parser tests using sample command output
```

## License

MIT
