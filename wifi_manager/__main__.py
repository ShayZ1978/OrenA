"""Enable ``python -m wifi_manager``."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
