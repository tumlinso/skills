#!/usr/bin/env python3
"""Render manuscript-ready figure assets from an existing figure spec."""

from __future__ import annotations

import argparse
import html
import json
import math
from collections import defaultdict
from pathlib import Path

from figure_common import (
    build_output_map,
    coerce_float,
    normalize_formats,
    numeric_columns,
    read_json,
    read_table,
    repo_root_from_spec_path,
    write_json,
)


PALETTE = ["#2f5f8f", "#b45309", "#3f8f5f", "#9a3412", "#7c3aed", "#047857"]


def load_pillow():
    from PIL import Image, ImageDraw, ImageFont

    return Image, ImageDraw, ImageFont


def choose_xy(rows: list[dict[str, str]], parameters: dict) -> tuple[str, str]:
    x_column = parameters.get("x")
    y_column = parameters.get("y")
    columns = numeric_columns(rows)
    if x_column and y_column:
        return x_column, y_column
    if len(columns) >= 2:
        return columns[0], columns[1]
    if rows and len(rows[0]) >= 2:
        ordered = list(rows[0].keys())
        return ordered[0], ordered[1]
    raise ValueError("Could not infer x and y columns from the input table.")


def svg_text(parts: list[str], x: float, y: float, text: str, size: int = 14, bold: bool = False, fill: str = "#111827") -> None:
    weight = ' font-weight="bold"' if bold else ""
    parts.append(
        f'<text x="{x}" y="{y}" font-size="{size}"{weight} font-family="Helvetica, Arial, sans-serif" fill="{fill}">{html.escape(text)}</text>'
    )


def build_series(rows: list[dict[str, str]], parameters: dict) -> dict[str, object]:
    if not rows:
        raise ValueError("Input table is empty.")

    plot_kind = parameters.get("plot_kind", "auto")
    if plot_kind == "auto":
        plot_kind = "scatter"

    if plot_kind == "heatmap":
        numeric = numeric_columns(rows)
        if not numeric:
            raise ValueError("Heatmap rendering requires numeric columns.")
        columns = list(rows[0].keys())
        row_label_column = next((column for column in columns if column not in numeric), None)
        matrix = []
        row_labels = []
        for row in rows:
            matrix.append([coerce_float(row.get(column)) or 0.0 for column in numeric])
            if row_label_column:
                row_labels.append(str(row.get(row_label_column, "")))
        return {
            "plot_kind": plot_kind,
            "matrix": matrix,
            "x_labels": numeric,
            "row_labels": row_labels,
        }

    x_column, y_column = choose_xy(rows, parameters)
    group_column = parameters.get("group")
    label_column = parameters.get("label")
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    if group_column and group_column in rows[0]:
        for row in rows:
            grouped[str(row.get(group_column, "default"))].append(row)
    else:
        grouped["series"] = rows

    series = []
    all_y = []
    numeric_x = True
    category_labels: list[str] = []
    for name, bucket in grouped.items():
        x_raw = [str(row.get(x_column, "")) for row in bucket]
        y_values = [coerce_float(row.get(y_column)) or 0.0 for row in bucket]
        x_numeric = [coerce_float(value) for value in x_raw]
        if all(value is not None for value in x_numeric) and plot_kind in {"scatter", "line"}:
            x_values = [float(value) for value in x_numeric if value is not None]
        else:
            numeric_x = False
            x_values = list(range(len(bucket)))
            if not category_labels:
                category_labels = x_raw
        labels = [str(row.get(label_column, "")) for row in bucket] if label_column else []
        series.append({"name": name, "x": x_values, "x_raw": x_raw, "y": y_values, "labels": labels})
        all_y.extend(y_values)

    y_min = min(all_y) if all_y else 0.0
    y_max = max(all_y) if all_y else 1.0
    if y_min == y_max:
        y_min -= 1.0
        y_max += 1.0

    return {
        "plot_kind": plot_kind,
        "x_column": x_column,
        "y_column": y_column,
        "series": series,
        "numeric_x": numeric_x,
        "category_labels": category_labels,
        "y_min": y_min,
        "y_max": y_max,
    }


def heatmap_color(value: float, low: float, high: float) -> str:
    if high <= low:
        ratio = 0.5
    else:
        ratio = (value - low) / (high - low)
    ratio = max(0.0, min(1.0, ratio))
    red = int(43 + ratio * 112)
    green = int(84 + ratio * 122)
    blue = int(135 + ratio * 80)
    return f"#{red:02x}{green:02x}{blue:02x}"


def scale_value(value: float, lower: float, upper: float, start: float, end: float) -> float:
    if upper <= lower:
        return start
    ratio = (value - lower) / (upper - lower)
    return start + ratio * (end - start)


def render_data_svg(spec: dict, spec_path: Path, payload: dict[str, object]) -> None:
    repo_root = repo_root_from_spec_path(spec, spec_path)
    svg_rel = spec["outputs"].get("svg")
    if not svg_rel:
        return

    width = 820
    height = 540
    left = 80
    right = width - 50
    top = 90
    bottom = height - 90
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#fbfaf7"/>',
    ]
    svg_text(parts, 40, 45, spec.get("title") or spec["figure_id"], size=24, bold=True, fill="#1f2933")

    if payload["plot_kind"] == "heatmap":
        matrix = payload["matrix"]
        x_labels = payload["x_labels"]
        row_labels = payload["row_labels"]
        values = [cell for row in matrix for cell in row]
        low = min(values) if values else 0.0
        high = max(values) if values else 1.0
        cell_width = max(35, int((right - left) / max(1, len(x_labels))))
        cell_height = max(28, int((bottom - top) / max(1, len(matrix))))
        for row_index, row in enumerate(matrix):
            for col_index, value in enumerate(row):
                fill = heatmap_color(value, low, high)
                x = left + col_index * cell_width
                y = top + row_index * cell_height
                parts.append(
                    f'<rect x="{x}" y="{y}" width="{cell_width}" height="{cell_height}" fill="{fill}" stroke="#ffffff" stroke-width="1"/>'
                )
            if row_labels:
                svg_text(parts, 18, top + row_index * cell_height + cell_height * 0.65, row_labels[row_index], size=12)
        for col_index, label in enumerate(x_labels):
            svg_text(parts, left + col_index * cell_width + 4, bottom + 28, label, size=12)
    else:
        parts.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" stroke="#334155" stroke-width="2"/>')
        parts.append(f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" stroke="#334155" stroke-width="2"/>')
        y_min = float(payload["y_min"])
        y_max = float(payload["y_max"])
        for tick_index in range(5):
            value = y_min + (y_max - y_min) * tick_index / 4
            y = scale_value(value, y_min, y_max, bottom, top)
            parts.append(f'<line x1="{left - 6}" y1="{y}" x2="{left}" y2="{y}" stroke="#334155" stroke-width="1"/>')
            svg_text(parts, 10, y + 4, f"{value:.2g}", size=11)

        series_list = payload["series"]
        numeric_x = bool(payload["numeric_x"])
        if numeric_x:
            x_values = [value for series in series_list for value in series["x"]]
            x_min = min(x_values) if x_values else 0.0
            x_max = max(x_values) if x_values else 1.0
        else:
            labels = payload["category_labels"] or series_list[0]["x_raw"]
            x_min = 0.0
            x_max = max(1.0, len(labels) - 1)
            for index, label in enumerate(labels):
                x = scale_value(index, x_min, x_max, left, right)
                svg_text(parts, x - 8, bottom + 28, str(label), size=11)

        for series_index, series in enumerate(series_list):
            color = PALETTE[series_index % len(PALETTE)]
            if payload["plot_kind"] == "bar":
                width_px = (right - left) / max(1, len(series["x"])) * 0.6
                for index, y_value in enumerate(series["y"]):
                    x = scale_value(index, 0.0, max(1.0, len(series["x"]) - 1), left, right)
                    y = scale_value(y_value, y_min, y_max, bottom, top)
                    parts.append(
                        f'<rect x="{x - width_px / 2}" y="{y}" width="{width_px}" height="{bottom - y}" fill="{color}" opacity="0.85"/>'
                    )
            else:
                points = []
                for index, (x_value, y_value) in enumerate(zip(series["x"], series["y"])):
                    mapped_x = scale_value(x_value, x_min, x_max, left, right) if numeric_x else scale_value(
                        index, 0.0, max(1.0, len(series["x"]) - 1), left, right
                    )
                    mapped_y = scale_value(y_value, y_min, y_max, bottom, top)
                    points.append((mapped_x, mapped_y))
                if payload["plot_kind"] == "line":
                    parts.append(
                        f'<polyline fill="none" stroke="{color}" stroke-width="3" points="{" ".join(f"{x},{y}" for x, y in points)}"/>'
                    )
                for point_index, (x, y) in enumerate(points):
                    parts.append(f'<circle cx="{x}" cy="{y}" r="5" fill="{color}"/>')
                    if series["labels"]:
                        svg_text(parts, x + 8, y - 8, series["labels"][point_index], size=10)
            if len(series_list) > 1:
                legend_y = top + series_index * 18
                parts.append(f'<rect x="{right - 130}" y="{legend_y - 10}" width="12" height="12" fill="{color}"/>')
                svg_text(parts, right - 110, legend_y, str(series["name"]), size=12)

        svg_text(parts, right - 50, bottom + 55, str(payload["x_column"]), size=13)
        svg_text(parts, 16, top - 18, str(payload["y_column"]), size=13)

    parts.append("</svg>")
    target = repo_root / svg_rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(parts) + "\n", encoding="utf-8")


def render_data_bitmap(spec: dict, spec_path: Path, payload: dict[str, object], fmt: str) -> None:
    repo_root = repo_root_from_spec_path(spec, spec_path)
    target = repo_root / spec["outputs"][fmt]
    target.parent.mkdir(parents=True, exist_ok=True)
    Image, ImageDraw, ImageFont = load_pillow()
    image = Image.new("RGB", (820, 540), "#fbfaf7")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    left, right, top, bottom = 80, 770, 90, 450
    draw.text((40, 24), spec.get("title") or spec["figure_id"], fill="#1f2933", font=font)

    if payload["plot_kind"] == "heatmap":
        matrix = payload["matrix"]
        x_labels = payload["x_labels"]
        row_labels = payload["row_labels"]
        values = [cell for row in matrix for cell in row]
        low = min(values) if values else 0.0
        high = max(values) if values else 1.0
        cell_width = max(35, int((right - left) / max(1, len(x_labels))))
        cell_height = max(28, int((bottom - top) / max(1, len(matrix))))
        for row_index, row in enumerate(matrix):
            for col_index, value in enumerate(row):
                fill = heatmap_color(value, low, high)
                x = left + col_index * cell_width
                y = top + row_index * cell_height
                draw.rectangle([x, y, x + cell_width, y + cell_height], fill=fill, outline="#ffffff")
            if row_labels:
                draw.text((10, top + row_index * cell_height + 6), row_labels[row_index], fill="#111827", font=font)
        for col_index, label in enumerate(x_labels):
            draw.text((left + col_index * cell_width + 4, bottom + 20), str(label), fill="#111827", font=font)
    else:
        draw.line((left, top, left, bottom), fill="#334155", width=2)
        draw.line((left, bottom, right, bottom), fill="#334155", width=2)
        y_min = float(payload["y_min"])
        y_max = float(payload["y_max"])
        for tick_index in range(5):
            value = y_min + (y_max - y_min) * tick_index / 4
            y = scale_value(value, y_min, y_max, bottom, top)
            draw.line((left - 6, y, left, y), fill="#334155", width=1)
            draw.text((8, y - 6), f"{value:.2g}", fill="#111827", font=font)

        series_list = payload["series"]
        numeric_x = bool(payload["numeric_x"])
        if numeric_x:
            x_values = [value for series in series_list for value in series["x"]]
            x_min = min(x_values) if x_values else 0.0
            x_max = max(x_values) if x_values else 1.0
        else:
            labels = payload["category_labels"] or series_list[0]["x_raw"]
            x_min = 0.0
            x_max = max(1.0, len(labels) - 1)
            for index, label in enumerate(labels):
                x = scale_value(index, x_min, x_max, left, right)
                draw.text((x - 8, bottom + 16), str(label), fill="#111827", font=font)

        for series_index, series in enumerate(series_list):
            color = PALETTE[series_index % len(PALETTE)]
            if payload["plot_kind"] == "bar":
                width_px = (right - left) / max(1, len(series["x"])) * 0.6
                for index, y_value in enumerate(series["y"]):
                    x = scale_value(index, 0.0, max(1.0, len(series["x"]) - 1), left, right)
                    y = scale_value(y_value, y_min, y_max, bottom, top)
                    draw.rectangle([x - width_px / 2, y, x + width_px / 2, bottom], fill=color, outline=color)
            else:
                points = []
                for index, (x_value, y_value) in enumerate(zip(series["x"], series["y"])):
                    mapped_x = scale_value(x_value, x_min, x_max, left, right) if numeric_x else scale_value(
                        index, 0.0, max(1.0, len(series["x"]) - 1), left, right
                    )
                    mapped_y = scale_value(y_value, y_min, y_max, bottom, top)
                    points.append((mapped_x, mapped_y))
                if payload["plot_kind"] == "line":
                    draw.line(points, fill=color, width=3)
                for point_index, (x, y) in enumerate(points):
                    draw.ellipse([x - 4, y - 4, x + 4, y + 4], fill=color, outline=color)
                    if series["labels"]:
                        draw.text((x + 6, y - 10), series["labels"][point_index], fill="#111827", font=font)
            if len(series_list) > 1:
                legend_y = top + series_index * 16
                draw.rectangle([right - 130, legend_y - 8, right - 118, legend_y + 4], fill=color, outline=color)
                draw.text((right - 110, legend_y - 10), str(series["name"]), fill="#111827", font=font)

    if fmt == "pdf":
        image.convert("RGB").save(target, "PDF")
    else:
        image.save(target)


def render_data_figure(spec: dict, spec_path: Path) -> None:
    repo_root = repo_root_from_spec_path(spec, spec_path)
    input_entry = spec["inputs"][0]
    input_path = (repo_root / input_entry["path"]).resolve()
    rows = read_table(input_path, delimiter=spec.get("parameters", {}).get("delimiter"))
    payload = build_series(rows, spec.get("parameters", {}))
    render_data_svg(spec, spec_path, payload)
    for fmt in spec["outputs"]:
        if fmt == "svg":
            continue
        render_data_bitmap(spec, spec_path, payload, fmt)


def layout_nodes(spec: dict) -> tuple[list[dict[str, object]], int, int]:
    nodes = spec.get("parameters", {}).get("nodes") or [{"id": "panel-1", "label": spec.get("description") or spec["figure_id"]}]
    count = len(nodes)
    columns = min(3, max(1, count))
    rows = math.ceil(count / columns)
    laid_out = []
    for index, node in enumerate(nodes):
        column = index % columns
        row = index // columns
        laid_out.append(
            {
                "id": node["id"],
                "label": node["label"],
                "x": 40 + column * 250,
                "y": 80 + row * 130,
                "width": 190,
                "height": 70,
            }
        )
    return laid_out, columns, rows


def render_schematic_svg(spec: dict, spec_path: Path) -> None:
    repo_root = repo_root_from_spec_path(spec, spec_path)
    outputs = spec["outputs"]
    svg_rel = outputs.get("svg")
    if not svg_rel:
        return
    nodes, columns, rows = layout_nodes(spec)
    width = max(360, 70 + columns * 250)
    height = 120 + rows * 140
    emphasis = spec.get("parameters", {}).get("emphasis")
    panel_style = spec.get("parameters", {}).get("panel_labels", "letters")

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#2f5f8f"/></marker></defs>',
        '<rect width="100%" height="100%" fill="#fbfaf7"/>',
    ]
    svg_text(parts, 40, 40, spec.get("title") or spec["figure_id"], size=24, bold=True, fill="#1f2933")

    for index, node in enumerate(nodes):
        stroke = "#b45309" if node["label"] == emphasis else "#2f5f8f"
        fill = "#fff4d6" if node["label"] == emphasis else "#eef4fa"
        parts.append(
            f'<rect x="{node["x"]}" y="{node["y"]}" rx="16" ry="16" width="{node["width"]}" height="{node["height"]}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
        )
        if panel_style == "letters":
            panel_label = chr(ord("A") + index)
        elif panel_style == "numbers":
            panel_label = str(index + 1)
        else:
            panel_label = ""
        if panel_label:
            svg_text(parts, node["x"] + 14, node["y"] + 22, panel_label, size=16, bold=True, fill="#7c2d12")
        svg_text(parts, node["x"] + 18, node["y"] + 45, str(node["label"]), size=16)

    for left_node, right_node in zip(nodes, nodes[1:]):
        if left_node["y"] != right_node["y"]:
            continue
        start_x = left_node["x"] + left_node["width"]
        start_y = left_node["y"] + left_node["height"] / 2
        end_x = right_node["x"]
        end_y = right_node["y"] + right_node["height"] / 2
        parts.append(
            f'<line x1="{start_x}" y1="{start_y}" x2="{end_x}" y2="{end_y}" stroke="#2f5f8f" stroke-width="3" marker-end="url(#arrow)"/>'
        )

    parts.append("</svg>")
    target = repo_root / svg_rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(parts) + "\n", encoding="utf-8")


def render_schematic_bitmap(spec: dict, spec_path: Path, fmt: str) -> None:
    repo_root = repo_root_from_spec_path(spec, spec_path)
    target = repo_root / spec["outputs"][fmt]
    target.parent.mkdir(parents=True, exist_ok=True)
    Image, ImageDraw, ImageFont = load_pillow()
    nodes, columns, rows = layout_nodes(spec)
    image = Image.new("RGB", (max(380, 70 + columns * 250), 120 + rows * 140), "#fbfaf7")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    emphasis = spec.get("parameters", {}).get("emphasis")
    draw.text((40, 20), spec.get("title") or spec["figure_id"], fill="#1f2933", font=font)

    for node in nodes:
        edge = "#b45309" if node["label"] == emphasis else "#2f5f8f"
        fill = "#fff4d6" if node["label"] == emphasis else "#eef4fa"
        draw.rounded_rectangle(
            [node["x"], node["y"], node["x"] + node["width"], node["y"] + node["height"]],
            radius=16,
            fill=fill,
            outline=edge,
            width=2,
        )
        draw.text((node["x"] + 18, node["y"] + 28), str(node["label"]), fill="#111827", font=font)

    for left_node, right_node in zip(nodes, nodes[1:]):
        if left_node["y"] != right_node["y"]:
            continue
        draw.line(
            (
                left_node["x"] + left_node["width"],
                left_node["y"] + left_node["height"] / 2,
                right_node["x"],
                right_node["y"] + right_node["height"] / 2,
            ),
            fill="#2f5f8f",
            width=3,
        )

    if fmt == "pdf":
        image.convert("RGB").save(target, "PDF")
    else:
        image.save(target)


def render_schematic_figure(spec: dict, spec_path: Path) -> None:
    render_schematic_svg(spec, spec_path)
    for fmt in spec["outputs"]:
        if fmt == "svg":
            continue
        render_schematic_bitmap(spec, spec_path, fmt)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", help="Path to the figure spec JSON")
    parser.add_argument("--format", action="append", default=[], help="Override export formats")
    parser.add_argument("--pretty", action="store_true", help="Print the resolved spec after export")
    args = parser.parse_args()

    spec_path = Path(args.spec).resolve()
    spec = read_json(spec_path)
    if args.format:
        spec["export_formats"] = normalize_formats(args.format)
        spec["outputs"] = build_output_map(spec)
        if spec["mode"] == "schematic-figure":
            spec["source_editable"] = spec["outputs"].get("svg")
        write_json(spec_path, spec)

    if spec["mode"] == "data-figure":
        render_data_figure(spec, spec_path)
    elif spec["mode"] == "schematic-figure":
        render_schematic_figure(spec, spec_path)
    else:
        raise ValueError(f"Unsupported figure mode: {spec['mode']}")

    if args.pretty:
        print(json.dumps(spec, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
