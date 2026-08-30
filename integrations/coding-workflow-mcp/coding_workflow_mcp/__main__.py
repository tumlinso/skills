"""Historical executable forwarding to Project Control's Codex profile."""

from __future__ import annotations

from typing import Sequence

from .compat import run_codex


def main(argv: Sequence[str] | None = None) -> int:
    return run_codex(argv)


if __name__ == "__main__":
    raise SystemExit(main())
