"""`python -m locale_gate` giriş noktası."""

from __future__ import annotations

import sys

from locale_gate.cli import main

if __name__ == "__main__":
    sys.exit(main())
