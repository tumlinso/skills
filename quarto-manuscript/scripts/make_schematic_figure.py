#!/usr/bin/env python3
"""Create a schematic-figure spec, wrapper script, and exports."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

from detect_figure_context import analyze_repo, infer_figure_mode
from figure_common import build_output_map, ensure_caption_stub, normalize_formats, rel_path, write_json, wrapper_script_text


def split_description(description: str) -> list[str]:
    if "->" in description:
        parts = [item.strip() for item in description.split("->")]
    elif ";" in description:
        parts = [item.strip() for item in description.split(";")]
    else:
        parts = [item.strip() for item in re.split(r"\n+", description)]
    return [item for item in parts if item]


def build_nodes(description: str | None, panels: list[str]) -> list[dict[str, str]]:
    labels = panels or split_description(description or "")
    if not labels and description:
        labels = [description.strip()]
    if not labels:
        raise ValueError("Provide --description or at least one --panel for a schematic figure.")
    return [{"id": f"panel-{index + 1}", "label": label} for index, label in enumerate(labels)]


def build_spec(args: argparse.Namespace) -> tuple[dict, Path, Path]:
    repo_root = Path(args.repo).resolve()
    context = analyze_repo(repo_root, description=args.description, input_paths=None)
    mode, _ = infer_figure_mode(args.description, None)
    if mode != "schematic-figure" and not args.panel:
        raise ValueError("`make_schematic_figure.py` requires a schematic-style description.")

    figure_layout = context["figure_layout"]
    spec_path = repo_root / figure_layout["specs_dir"] / f"{args.figure_id}.json"
    script_path = repo_root / figure_layout["schematic_script_dir"] / f"{args.figure_id}.py"
    nodes = build_nodes(args.description, args.panel)

    spec = {
        "figure_id": args.figure_id,
        "mode": "schematic-figure",
        "title": args.title or args.figure_id,
        "description": args.description or "",
        "repo_root": str(repo_root),
        "manuscript_files": args.manuscript_file or context["manuscript_files"],
        "figure_layout": figure_layout,
        "inputs": [],
        "parameters": {
            "description": args.description or "",
            "nodes": nodes,
            "panel_labels": args.panel_label_style,
            "emphasis": args.emphasis,
        },
        "export_formats": normalize_formats(args.output_format),
        "created_with": {
            "skill": "quarto-manuscript",
            "helper": "make_schematic_figure.py",
        },
        "source_script": rel_path(script_path, repo_root),
    }
    spec["outputs"] = build_output_map(spec)
    spec["source_editable"] = spec["outputs"].get("svg")
    spec["caption_stub"] = ensure_caption_stub(repo_root, spec)
    return spec, spec_path, script_path


def write_wrapper(script_path: Path, spec_path: Path) -> None:
    helper_path = Path(__file__).resolve().parent / "export_figure_assets.py"
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(wrapper_script_text(helper_path, spec_path), encoding="utf-8")
    script_path.chmod(0o755)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="Repo or manuscript directory")
    parser.add_argument("--figure-id", required=True, help="Stable figure identifier")
    parser.add_argument("--description", help="Structured or semi-structured figure description")
    parser.add_argument("--title", help="Figure title")
    parser.add_argument("--panel", action="append", default=[], help="Explicit panel or node label")
    parser.add_argument("--panel-label-style", default="letters", choices=["letters", "numbers", "none"])
    parser.add_argument("--emphasis", help="Node label to emphasize")
    parser.add_argument("--manuscript-file", action="append", default=[], help="Relevant manuscript file path")
    parser.add_argument("--output-format", action="append", default=[], help="Export format: svg, png, or pdf")
    parser.add_argument("--no-render", action="store_true", help="Write spec and source script without rendering outputs")
    args = parser.parse_args()

    spec, spec_path, script_path = build_spec(args)
    write_json(spec_path, spec)
    write_wrapper(script_path, spec_path)

    if not args.no_render:
        subprocess.run([sys.executable, str(Path(__file__).resolve().parent / "export_figure_assets.py"), str(spec_path)], check=True)
    print(spec_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
