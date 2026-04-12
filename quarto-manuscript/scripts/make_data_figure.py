#!/usr/bin/env python3
"""Create a reproducible data-figure spec, wrapper script, and exports."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from detect_figure_context import analyze_repo, infer_figure_mode
from figure_common import build_output_map, ensure_caption_stub, normalize_formats, rel_path, write_json, wrapper_script_text


def build_spec(args: argparse.Namespace) -> tuple[dict, Path, Path]:
    repo_root = Path(args.repo).resolve()
    context = analyze_repo(repo_root, description=args.description, input_paths=[args.input])
    mode, _ = infer_figure_mode(args.description, [args.input])
    if mode != "data-figure":
        raise ValueError("`make_data_figure.py` requires repo-local data inputs.")

    input_path = (repo_root / args.input).resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Input file does not exist: {input_path}")

    figure_layout = context["figure_layout"]
    spec_path = repo_root / figure_layout["specs_dir"] / f"{args.figure_id}.json"
    script_path = repo_root / figure_layout["data_script_dir"] / f"{args.figure_id}.py"

    spec = {
        "figure_id": args.figure_id,
        "mode": "data-figure",
        "title": args.title or args.figure_id,
        "description": args.description or "",
        "repo_root": str(repo_root),
        "manuscript_files": args.manuscript_file or context["manuscript_files"],
        "figure_layout": figure_layout,
        "inputs": [
            {
                "path": rel_path(input_path, repo_root),
                "exists": True,
                "kind": "repo-local-table",
            }
        ],
        "parameters": {
            "plot_kind": args.plot_kind,
            "x": args.x,
            "y": args.y,
            "group": args.group,
            "label": args.label,
            "delimiter": args.delimiter,
            "figure_size": [args.width, args.height],
        },
        "export_formats": normalize_formats(args.output_format),
        "source_script": rel_path(script_path, repo_root),
        "created_with": {
            "skill": "quarto-manuscript",
            "helper": "make_data_figure.py",
        },
    }
    spec["outputs"] = build_output_map(spec)
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
    parser.add_argument("--input", required=True, help="Repo-local processed table or matrix path")
    parser.add_argument("--plot-kind", default="auto", choices=["auto", "scatter", "line", "bar", "heatmap"])
    parser.add_argument("--x", help="Column name for x values")
    parser.add_argument("--y", help="Column name for y values")
    parser.add_argument("--group", help="Column name used for grouping")
    parser.add_argument("--label", help="Column name used for point labels")
    parser.add_argument("--title", help="Figure title")
    parser.add_argument("--description", help="Figure description or caption scaffold text")
    parser.add_argument("--manuscript-file", action="append", default=[], help="Relevant manuscript file path")
    parser.add_argument("--output-format", action="append", default=[], help="Export format: svg, png, or pdf")
    parser.add_argument("--delimiter", help="Override table delimiter")
    parser.add_argument("--width", type=float, default=6.0, help="Figure width in inches")
    parser.add_argument("--height", type=float, default=4.0, help="Figure height in inches")
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
