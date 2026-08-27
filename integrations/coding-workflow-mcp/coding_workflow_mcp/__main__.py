"""Run the canonical coding-workflow MCP over local stdio."""

from ._canonical import canonical_server


def main() -> None:
    canonical_server().run(transport="stdio")


if __name__ == "__main__":
    main()
