"""Historical owner command forwarding to Project Control administration."""

from __future__ import annotations

from typing import Sequence

from .compat import run_admin


def main(argv: Sequence[str] | None = None) -> int:
    return run_admin(argv)


if __name__ == "__main__":
    raise SystemExit(main())
