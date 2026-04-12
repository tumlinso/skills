#!/usr/bin/env python3
"""Update a figure spec while preserving reproducible figure state."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from figure_common import build_output_map, normalize_formats, read_json, write_json


def parse_value(raw: str):
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def set_nested(payload: dict, dotted_key: str, value) -> None:
    parts = dotted_key.split(".")
    cursor = payload
    for part in parts[:-1]:
        if part not in cursor or not isinstance(cursor[part], dict):
            cursor[part] = {}
        cursor = cursor[part]
    cursor[parts[-1]] = value


def validate_spec(spec: dict) -> None:
    for key in ("figure_id", "mode", "figure_layout", "export_formats", "outputs"):
        if key not in spec:
            raise ValueError(f"Missing required spec field: {key}")
    if spec["mode"] == "data-figure":
        if "source_script" not in spec or not spec.get("inputs"):
            raise ValueError("Data-figure specs require source_script and inputs.")
    elif spec["mode"] == "schematic-figure":
        if "source_script" not in spec:
            raise ValueError("Schematic-figure specs require source_script.")
    else:
        raise ValueError(f"Unknown figure mode: {spec['mode']}")


def sync_outputs(spec: dict) -> None:
    spec["export_formats"] = normalize_formats(spec.get("export_formats"))
    spec["outputs"] = build_output_map(spec)
    if spec["mode"] == "schematic-figure":
        spec["source_editable"] = spec["outputs"].get("svg")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", help="Path to the figure spec JSON")
    parser.add_argument("--title", help="Replace the figure title")
    parser.add_argument("--description", help="Replace the figure description")
    parser.add_argument("--set", action="append", default=[], help="Set dotted-key JSON or string value, e.g. parameters.x=score")
    parser.add_argument("--add-output-format", action="append", default=[], help="Add svg, png, or pdf")
    parser.add_argument("--remove-output-format", action="append", default=[], help="Remove svg, png, or pdf")
    parser.add_argument("--pretty", action="store_true", help="Print the updated spec to stdout")
    args = parser.parse_args()

    spec_path = Path(args.spec).resolve()
    spec = read_json(spec_path)

    if args.title:
        spec["title"] = args.title
    if args.description is not None:
        spec["description"] = args.description
        spec.setdefault("parameters", {})["description"] = args.description

    for item in args.set:
        if "=" not in item:
            raise ValueError(f"Invalid --set value: {item}")
        dotted_key, raw_value = item.split("=", 1)
        set_nested(spec, dotted_key, parse_value(raw_value))

    formats = normalize_formats(spec.get("export_formats"))
    for fmt in normalize_formats(args.add_output_format) if args.add_output_format else []:
        if fmt not in formats:
            formats.append(fmt)
    for fmt in normalize_formats(args.remove_output_format) if args.remove_output_format else []:
        formats = [item for item in formats if item != fmt]
    spec["export_formats"] = formats

    sync_outputs(spec)
    validate_spec(spec)
    write_json(spec_path, spec)
    if args.pretty:
        print(json.dumps(spec, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
