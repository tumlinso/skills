from __future__ import annotations

import csv
import json
from pathlib import Path

DEFAULT_EXPORT_FORMATS = ("svg", "png")
ALLOWED_EXPORT_FORMATS = ("svg", "png", "pdf")


def rel_path(path: Path, root: Path) -> str:
    return str(path.resolve().relative_to(root.resolve()))


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def normalize_formats(raw_formats: list[str] | tuple[str, ...] | None) -> list[str]:
    if not raw_formats:
        return list(DEFAULT_EXPORT_FORMATS)

    normalized: list[str] = []
    for item in raw_formats:
        for piece in str(item).split(","):
            fmt = piece.strip().lower().lstrip(".")
            if not fmt:
                continue
            if fmt not in ALLOWED_EXPORT_FORMATS:
                raise ValueError(f"Unsupported export format: {fmt}")
            if fmt not in normalized:
                normalized.append(fmt)
    return normalized or list(DEFAULT_EXPORT_FORMATS)


def output_dir_for_mode(spec: dict) -> str:
    layout = spec["figure_layout"]
    if spec["mode"] == "data-figure":
        return layout["data_dir"]
    if spec["mode"] == "schematic-figure":
        return layout["schematic_dir"]
    raise ValueError(f"Unsupported figure mode: {spec['mode']}")


def build_output_map(spec: dict, formats: list[str] | None = None) -> dict[str, str]:
    output_dir = Path(output_dir_for_mode(spec))
    figure_id = spec["figure_id"]
    outputs = {}
    for fmt in normalize_formats(formats or spec.get("export_formats")):
        outputs[fmt] = str(output_dir / f"{figure_id}.{fmt}")
    return outputs


def caption_stub_path(spec: dict) -> str | None:
    captions_dir = spec.get("figure_layout", {}).get("captions_dir")
    if not captions_dir:
        return None
    return str(Path(captions_dir) / f"{spec['figure_id']}.md")


def ensure_caption_stub(repo_root: Path, spec: dict) -> str | None:
    relative_path = caption_stub_path(spec)
    if not relative_path:
        return None
    caption_path = repo_root / relative_path
    if caption_path.exists():
        return relative_path

    title = spec.get("title") or spec["figure_id"]
    caption_path.parent.mkdir(parents=True, exist_ok=True)
    caption_path.write_text(
        f"# {title}\n\n"
        f"Short caption scaffold for `{spec['figure_id']}`.\n\n"
        "Describe the figure, key panels, and the main takeaway.\n",
        encoding="utf-8",
    )
    return relative_path


def infer_delimiter(path: Path) -> str:
    if path.suffix.lower() in {".tsv", ".tab"}:
        return "\t"
    return ","


def read_table(path: Path, delimiter: str | None = None) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter or infer_delimiter(path))
        return [dict(row) for row in reader]


def coerce_float(value: str | None) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def numeric_columns(rows: list[dict[str, str]]) -> list[str]:
    if not rows:
        return []
    columns: list[str] = []
    for column in rows[0]:
        numeric = 0
        total = 0
        for row in rows:
            total += 1
            if coerce_float(row.get(column)) is not None:
                numeric += 1
        if total and numeric >= max(1, int(total * 0.8)):
            columns.append(column)
    return columns


def repo_root_from_spec_path(spec: dict, spec_path: Path) -> Path:
    root_text = spec.get("repo_root")
    if root_text:
        return Path(root_text).resolve()
    return spec_path.resolve().parents[2]


def wrapper_script_text(helper_path: Path, spec_path: Path) -> str:
    return (
        "#!/usr/bin/env python3\n"
        "from __future__ import annotations\n\n"
        "import subprocess\n"
        "import sys\n"
        "from pathlib import Path\n\n"
        f"HELPER = Path({str(helper_path.resolve())!r})\n"
        f"SPEC = Path({str(spec_path.resolve())!r})\n\n"
        "if __name__ == '__main__':\n"
        "    subprocess.run([sys.executable, str(HELPER), str(SPEC)], check=True)\n"
    )
