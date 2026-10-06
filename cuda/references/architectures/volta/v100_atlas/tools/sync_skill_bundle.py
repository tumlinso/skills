#!/usr/bin/env python3
"""Build or validate the preserved V100 atlas bundle inside the CUDA skill."""
from __future__ import annotations

import argparse
import hashlib
from collections import Counter
import json
import re
import shutil
import subprocess
import os
import sys
import unicodedata
import zipfile
from pathlib import Path
from urllib.parse import urlsplit

SOURCE_COMMIT = "5b5629b001da4a42d6f41a84d94f73c07a29d478"
CAMPAIGN_SOURCE_COMMIT = "f223c51dcfacab602e9bc68b3e65cc75730dc7f8"
ARCHIVE_COMMIT = "5c1f805db80a81f7476ede8292abba69821d104f"
CORPUS_BASELINE_COMMIT = "9cafc699539c84c3aa2155513da38711f97fd807"
PINNED_SOURCE_SUMS_SHA256 = "23434ed437c2d8ceec440bb4cb7cda280fc61f2e06e78d2b839899884682016f"
PINNED_ZIP_SHA256 = "f592a89480cd90df3451b79601fa5492f588f13579acae6b511a7ae3619c2345"
PINNED_COMPENDIUM_SHA256 = "9a6acb6a7d9e22422585265972ba29a138212eac9c537ebb0d73a5b001249c61"
ATLAS_REL = Path("references/architectures/volta/v100_atlas")
PREFIX_COUNTS = {"reference": ("R", 16), "mechanisms": ("M", 52), "compositions": ("C", 40), "experiments": ("E", 40), "sources": ("S", 42)}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def protocol_body_sha256(text: str) -> str | None:
    start = re.search(r"(?m)^\*\*Question:\*\*.*(?:\n|$)", text)
    if start is None:
        return None
    end = re.search(r"(?m)^\*\*Record:\*\*.*(?:\n|$)", text[start.start():])
    if end is None:
        return None
    body = text[start.start():start.start() + end.end()]
    return sha256(body.encode("utf-8"))


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def slug(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-")


def document_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            return re.sub(rf"^{re.escape(fallback)}\s*[—–-]\s*", "", title)
    return fallback


def pinned_source_bytes(source: Path, relative: str | Path, revision: str | None = None) -> bytes:
    revision = revision or SOURCE_COMMIT
    rel = Path(relative).as_posix()
    try:
        return subprocess.check_output(["git", "-C", str(source), "show", f"{revision}:{rel}"])
    except subprocess.CalledProcessError as exc:
        raise ValueError(f"source path is not present at pinned commit {revision}: {rel}") from exc


def source_checksums(source: Path) -> tuple[bytes, dict[str, str]]:
    content = pinned_source_bytes(source, "SHA256SUMS")
    actual = sha256(content)
    if actual != PINNED_SOURCE_SUMS_SHA256:
        raise ValueError(f"pinned SHA256SUMS mismatch: {actual}")
    checksums = {}
    for line in content.decode("utf-8").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if match:
            checksums[match.group(2)] = match.group(1)
    if not checksums:
        raise ValueError("pinned SHA256SUMS has no valid entries")
    return content, checksums


def verified_pinned_bytes(source: Path, relative: str | Path, checksums: dict[str, str], revision: str | None = None) -> bytes:
    rel = Path(relative).as_posix()
    data = pinned_source_bytes(source, rel, revision)
    expected = checksums.get(rel)
    if expected is None or sha256(data) != expected:
        raise ValueError(f"pinned source checksum is missing or mismatched: {rel}")
    return data


def snapshot_path(source_rel: str) -> str:
    path = Path(source_rel)
    return f"archive/source-snapshot/{path.as_posix()}.source.txt" if path.suffix.lower() == ".md" else f"archive/source-snapshot/{path.as_posix()}"


def tracked_source_paths(source: Path) -> list[Path]:
    paths = [Path(x) for x in subprocess.check_output(["git", "-C", str(source), "ls-tree", "-r", "--name-only", SOURCE_COMMIT], text=True).splitlines()]
    wanted = []
    for rel in paths:
        if rel.parts[0] in {"reference", "mechanisms", "compositions", "experiments", "sources", "ledger"}:
            if rel.parts[0] == "experiments" and rel.parts[1:2] == ("evidence",):
                wanted.append(rel)
            elif rel.suffix in {".md", ".json", ".jsonl", ".tsv"}:
                wanted.append(rel)
        elif rel.as_posix() in {"README.md", "START_HERE.md", "NEED_INDEX.md", "FIELD_GUIDE.md", "manifest.json", "SHA256SUMS", "benchmarks/README.md"}:
            wanted.append(rel)
        elif rel.parts[0] in {"tools", "scripts", "benchmarks"}:
            wanted.append(rel)
    return sorted(set(wanted), key=lambda p: p.as_posix())


def portable_evidence_paths(source: Path) -> list[Path]:
    campaign = Path("benchmark_runs/v100-20261006T145155Z-4bd01216")
    paths = [campaign / "REPORT.md", campaign / "build.json", campaign / "results.json", campaign / "run_config.json", campaign / "summary.json", campaign / "offline/final-acceptance.json", campaign / "offline/measurement-audit.json"]
    return [path for path in paths if path in set(tracked_source_paths(source)) or (source / path).is_file()]


def verified_campaign_bytes(source: Path, relative: str | Path, provenance: dict) -> bytes:
    rel = Path(relative).as_posix()
    if rel.endswith("/REPORT.md"):
        expected = provenance.get("analysis_sources", {}).get("campaign_report_sha256")
    else:
        parts = Path(rel).parts
        campaign_rel = "/".join(parts[2:]) if len(parts) > 2 and parts[0] == "benchmark_runs" else Path(rel).name
        expected = provenance.get("campaign_input_sha256", {}).get(campaign_rel, provenance.get("campaign_input_sha256", {}).get(Path(rel).name))
    if not expected:
        raise ValueError(f"portable campaign file has no pinned provenance hash: {rel}")
    data = (source / rel).read_bytes()
    if sha256(data) != expected:
        raise ValueError(f"portable campaign file differs from its pinned provenance hash: {rel}")
    return data


def source_path_map(source: Path) -> tuple[dict[str, str], dict[str, dict[str, str]]]:
    id_map: dict[str, str] = {"A00": "START_HERE.md", "A01": "NEED_INDEX.md", "A02": "FIELD_GUIDE.md"}
    card_map: dict[str, dict[str, str]] = {}
    for directory, (prefix, count) in PREFIX_COUNTS.items():
        for index in range(1 if prefix == "S" else 0, count + (1 if prefix != "S" else 1)):
            # S01..S42; the other families use zero-based identifiers except R00.
            identifier = f"{prefix}{index:02d}"
            source_file = source / directory / f"{identifier}.md"
            if not source_file.is_file():
                continue
            title = document_title(pinned_source_bytes(source, source_file.relative_to(source)).decode("utf-8"), identifier)
            destination = f"{directory}/{identifier}-{slug(title)}.md"
            id_map[identifier] = destination
            card_map[identifier] = {"source_path": source_file.relative_to(source).as_posix(), "path": destination, "title": title}
    return id_map, card_map


def all_link_destinations(text: str):
    pattern = re.compile(r"(?P<open>!?\[[^\]]*\]\()(?P<target><[^>]+>|[^)\s]+)(?P<tail>[^)]*\))")
    for match in pattern.finditer(text):
        yield match


def rewrite_local_links(text: str, source_file: Path, target_file: Path, source_root: Path, path_map: dict[str, str]) -> str:
    pattern = re.compile(r"(?P<open>!?\[[^\]]*\]\()(?P<target><[^>]+>|[^)\s]+)(?P<tail>[^)]*\))")
    def replace(match: re.Match[str]) -> str:
        raw = match.group("target")
        wrapped = raw.startswith("<") and raw.endswith(">")
        url = raw[1:-1] if wrapped else raw
        parsed = urlsplit(url)
        if parsed.scheme or parsed.netloc or not parsed.path:
            return match.group(0)
        resolved = (source_file.parent / parsed.path).resolve(strict=False)
        try:
            rel_source = resolved.relative_to(source_root.resolve()).as_posix()
        except ValueError:
            return match.group(0)
        mapped = path_map.get(rel_source)
        if mapped is None:
            return match.group(0)
        rel_target = Path(mapped)
        new_path = Path(__import__("os").path.relpath(rel_target.as_posix(), target_file.parent.as_posix())).as_posix()
        updated = new_path + (f"#{parsed.fragment}" if parsed.fragment else "")
        return match.group("open") + (f"<{updated}>" if wrapped else updated) + match.group("tail")
    return pattern.sub(replace, text)


def source_file_map(source: Path, id_map: dict[str, str], card_map: dict[str, dict[str, str]]) -> dict[str, str]:
    mapping = {p.as_posix(): p.as_posix() for p in tracked_source_paths(source)}
    for key in list(mapping):
        if key.startswith("tools/"):
            mapping[key] = "source-tools/" + Path(key).name
    mapping.update({"V100_ATLAS_FULL.md": "archive/V100_ATLAS_FULL.source.txt"})
    for path in portable_evidence_paths(source):
        key = path.as_posix()
        mapping[key] = "archive/campaign/REPORT.source.txt" if key.endswith("/REPORT.md") else key
    campaign = "benchmark_runs/v100-20261006T145155Z-4bd01216/host/host/"
    for name, wrapper in {
        "E33/serial/resident_run.json": "experiments/evidence/v100-20261006/E33-raw-host-records.md",
        "E33/interleaved/resident_run.json": "experiments/evidence/v100-20261006/E33-raw-host-records.md",
        "E34_readonly_ras.json": "experiments/evidence/v100-20261006/E34-raw-host-records.md",
        "E35_platform_evidence.json": "experiments/evidence/v100-20261006/E35-raw-host-records.md",
        "E36_toolchain.json": "experiments/evidence/v100-20261006/E36-raw-host-records.md",
        "E38_falsifiers.json": "experiments/evidence/v100-20261006/E38-raw-host-records.md",
    }.items():
        mapping[campaign + name] = wrapper
    for identifier, info in card_map.items():
        mapping[info["source_path"]] = info["path"]
    # Main navigation aliases also appear with references to their original top-level paths.
    for identifier, target in id_map.items():
        if identifier in {"A00", "A01", "A02"}:
            mapping[target] = target
    return mapping


def resource_title(identifier: str, path: str, text: str) -> str:
    return document_title(text, Path(path).stem)



def load_owned_files(atlas: Path) -> dict[str, str]:
    map_path = atlas / "import-map.json"
    sidecar = atlas / "import-map.sha256"
    assert_safe_destination(atlas, map_path)
    assert_safe_destination(atlas, sidecar)
    if not map_path.is_file():
        return {}
    current_digest = sha256(map_path.read_bytes())
    if sidecar.is_file():
        if sidecar.read_text(encoding="ascii").strip() != current_digest:
            raise ValueError("import-map.json changed without its integrity sidecar")
        inventory = json.loads(map_path.read_text(encoding="utf-8"))
        return dict(inventory.get("owned_files", {}))
    # Prior maps did not record trusted content hashes for every generated file.
    # Do not infer ownership from the files' current bytes: preserve that tree and
    # require a separately verified copy to a fresh destination for migration.
    raise ValueError("legacy import map has no owned-file hash manifest; refusing automatic migration")


def assert_safe_destination(atlas: Path, path: Path) -> None:
    """Reject symlinks and destinations that resolve outside the atlas root."""
    atlas_abs = atlas.absolute()
    path_abs = path.absolute()
    try:
        relative = path_abs.relative_to(atlas_abs)
    except ValueError as exc:
        raise ValueError(f"output path is outside atlas root: {path}") from exc
    if atlas.is_symlink():
        raise ValueError(f"atlas root must not be a symlink: {atlas}")
    cursor = atlas_abs
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError(f"symlink in atlas output path: {cursor}")
    try:
        path_abs.resolve(strict=False).relative_to(atlas.resolve(strict=True))
    except ValueError as exc:
        raise ValueError(f"output path resolves outside atlas root: {path}") from exc


def assert_safe_repo_path(repo_root: Path, path: Path) -> None:
    """Reject symlink components below the resolved repository root."""
    root_abs = repo_root.absolute()
    destination_abs = path.absolute()
    try:
        relative = destination_abs.relative_to(root_abs)
    except ValueError as exc:
        raise ValueError(f"path is outside repository root: {path}") from exc
    cursor = repo_root.resolve(strict=True)
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError(f"symlink in repository output path: {cursor}")
    try:
        destination_abs.resolve(strict=False).relative_to(repo_root.resolve(strict=True))
    except ValueError as exc:
        raise ValueError(f"path resolves outside repository root: {path}") from exc


def write_imported(atlas: Path, path: Path, data: bytes, owned: dict[str, str]) -> None:
    assert_safe_destination(atlas, path)
    rel = path.relative_to(atlas).as_posix()
    if path.exists():
        actual = sha256(path.read_bytes())
        expected = owned.get(rel)
        if actual != sha256(data) and (expected is None or actual != expected):
            raise ValueError(f"refusing to overwrite modified or unowned import path: {rel}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    owned[rel] = sha256(data)


def write_import_map(atlas: Path, inventory: dict, owned: dict[str, str]) -> None:
    path = atlas / "import-map.json"
    sidecar = atlas / "import-map.sha256"
    assert_safe_destination(atlas, path)
    assert_safe_destination(atlas, sidecar)
    if path.exists():
        old_digest = sha256(path.read_bytes())
        if sidecar.is_file() and sidecar.read_text(encoding="ascii").strip() != old_digest:
            raise ValueError("refusing to overwrite changed import-map.json")
        if not sidecar.exists():
            old_inventory = json.loads(path.read_text(encoding="utf-8"))
            if old_inventory.get("source", {}).get("commit") != SOURCE_COMMIT:
                raise ValueError("refusing to migrate unrecognized import-map.json")
    inventory["owned_files"] = dict(sorted(owned.items()))
    payload = json_bytes(inventory)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    sidecar.write_text(sha256(payload) + "\n", encoding="ascii")

def build(source: Path, archive: Path, skill_root: Path) -> None:
    atlas = skill_root / "cuda" / ATLAS_REL
    assert_safe_repo_path(skill_root, atlas)
    atlas.mkdir(parents=True, exist_ok=True)
    checksums_bytes, checksums = source_checksums(source)
    id_map, cards = source_path_map(source)
    mapping = source_file_map(source, id_map, cards)
    provenance = json.loads(verified_pinned_bytes(source, "experiments/evidence/v100-20261006/provenance.json", checksums))
    if provenance.get("source_commit") != CAMPAIGN_SOURCE_COMMIT:
        raise ValueError("campaign provenance source commit does not match the recorded campaign commit")
    if provenance.get("original_protocol_archive_commit") != ARCHIVE_COMMIT:
        raise ValueError("original archive commit differs from the recorded archive lineage")
    owned = load_owned_files(atlas)
    prior_bytes = subprocess.check_output(["git", "-C", str(skill_root), "show", "9581834:cuda/references/architectures/volta/v100_atlas/.project-control-corpus.json"])
    baseline_corpus_bytes = subprocess.check_output(["git", "-C", str(skill_root), "show", f"{CORPUS_BASELINE_COMMIT}:cuda/.project-control-corpus.json"])
    baseline_corpus = json.loads(baseline_corpus_bytes)
    if len(baseline_corpus.get("resources", [])) != 110 or len(baseline_corpus.get("relationships", [])) != 298:
        raise ValueError("CUDA corpus baseline count differs from admitted workspace contract")
    # The historical corpus is archived as the exact prior source used for merge.
    prior_corpus = json.loads(prior_bytes)
    expected_zip = prior_corpus["source"]["sha256"]
    zip_bytes = archive.read_bytes()
    if expected_zip != PINNED_ZIP_SHA256 or sha256(zip_bytes) != PINNED_ZIP_SHA256:
        raise ValueError(f"archive ZIP SHA-256 mismatch: expected {expected_zip}, got {sha256(zip_bytes)}")

    source_snapshot = atlas / "archive/source-snapshot"
    assert_safe_destination(atlas, source_snapshot)
    source_snapshot.mkdir(parents=True, exist_ok=True)
    original_full = verified_pinned_bytes(source, "V100_ATLAS_FULL.md", checksums)
    if sha256(original_full) != PINNED_COMPENDIUM_SHA256:
        raise ValueError("pinned original compendium checksum mismatch")
    write_imported(atlas, atlas / "archive/V100_ATLAS_FULL.source.txt", original_full, owned)
    write_imported(atlas, atlas / "archive/source-SHA256SUMS.source.txt", checksums_bytes, owned)
    write_imported(atlas, atlas / "archive/V100_SXM2_Circuit_Bending_Atlas.zip", zip_bytes, owned)
    write_imported(atlas, atlas / "archive/prior-corpus-9581834.source.json", prior_bytes, owned)
    write_imported(atlas, atlas / "archive/cuda-corpus-baseline-9cafc69.source.json", baseline_corpus_bytes, owned)
    status = make_status(source, provenance, checksums)
    write_imported(atlas, atlas / "CURRENT_STATUS.md", status.encode(), owned)
    maintenance = (
        "# Import maintenance and migration\n\n"
        "The bundle importer updates files only when the `import-map.json` integrity sidecar and per-file hashes in `owned_files` verify. It refuses unknown collisions and edits to files it previously owned.\n\n"
        "Legacy bundles that have an import map but no owned-file hash manifest are preserved and fail closed; the importer will not infer ownership from current bytes on disk. Manual migration requires either preserving the legacy bundle and importing into a new destination, or using a separate externally verified procedure that checks each payload against pinned Git source, campaign provenance, or exact generated output before establishing ownership. Do not add a broad overwrite bypass or bless hashes sampled only from the legacy destination.\n\n"
        "Use `python -B tools/sync_skill_bundle.py --validate` for source-less integrity checks. Validation checks the sidecar, owned-file hashes, corpus content hashes, pinned archive anchors, original protocol identities, and local links.\n"
    )
    write_imported(atlas, atlas / "IMPORT_MAINTENANCE.md", maintenance.encode(), owned)
    write_imported(atlas, atlas / "reference/R00-current-status-context.md", (
        "# R00 source-date context\n\n"
        "> Dated 2026-10-06. The R00 card below is preserved byte-for-byte apart from documented relative-link relocation.\n\n"
        "R00's statement that the research did not execute on the user's V100 describes the original 2026-10-03 source-backed synthesis. It remains the right description of that source work. The later campaign is a separate, bounded 2026-10-06 evidence packet; see [the preserved R00 card](R00-reading-and-evidence-contract.md), [current measured status](../CURRENT_STATUS.md), and [campaign provenance](../experiments/evidence/v100-20261006/provenance.json). Its GPU_RUN records cover only the implemented measured subset, while CPU_ONLY and NOT_RUN records retain their own status.\n"
    ).encode(), owned)
    for eid in ("E33", "E34", "E35", "E36", "E38"):
        summary = atlas / f"experiments/evidence/v100-20261006/{eid}.json"
        wrapper = (
            f"# {eid} raw host record availability\n\n"
            "> Dated 2026-10-06 portable-bundle note. The raw host JSON capture is not included in this skill bundle.\n\n"
            f"The original source card points to a raw host record under the campaign host directory. That path is retained in the card as provenance, but the file was not tracked in the pinned source commit and is not represented here as a raw capture. Use the [portable {eid} campaign summary]({eid}.json) for the bounded evidence available in this bundle; it is a summary, not the original host JSON. See [campaign provenance](provenance.json) for source identity and artifact boundaries.\n"
        )
        write_imported(atlas, atlas / f"experiments/evidence/v100-20261006/{eid}-raw-host-records.md", wrapper.encode(), owned)

    tracked_paths = set(tracked_source_paths(source))
    source_paths = sorted(tracked_paths.union(portable_evidence_paths(source)), key=lambda p: p.as_posix())
    for rel in source_paths:
        rel_text = rel.as_posix()
        if rel in tracked_paths:
            raw = checksums_bytes if rel_text == "SHA256SUMS" else verified_pinned_bytes(source, rel, checksums)
        else:
            raw = verified_campaign_bytes(source, rel, provenance)
        snap_path = atlas / snapshot_path(rel_text)
        if rel.suffix.lower() == ".md":
            stale_md = atlas / "archive/source-snapshot" / rel
            assert_safe_destination(atlas, stale_md)
            if stale_md.is_file():
                stale_rel = stale_md.relative_to(atlas).as_posix()
                # The exact byte comparison against a checksum-verified pinned Git
                # object (or provenance-pinned report) establishes this migration.
                if sha256(stale_md.read_bytes()) != sha256(raw):
                    raise ValueError(f"refusing to migrate changed or unowned archived Markdown source: {rel_text}")
                stale_md.unlink()
                owned.pop(stale_rel, None)
        write_imported(atlas, snap_path, raw, owned)
        if rel_text == "V100_ATLAS_FULL.md":
            continue
        if rel_text.endswith("/REPORT.md"):
            write_imported(atlas, atlas / "archive/campaign/REPORT.source.txt", raw, owned)
            continue
        out_rel = mapping.get(rel.as_posix(), rel.as_posix())
        out = atlas / out_rel
        src = source / rel
        if out.suffix == ".md":
            original = raw.decode("utf-8")
            out_text = rewrite_local_links(original, src, Path(out_rel), source, mapping)
            raw = out_text.encode("utf-8")
        write_imported(atlas, out, raw, owned)

    # Ensure the navigation, JSON ledgers, evidence packet, and source tools named by the import contract exist.
    required = ["START_HERE.md", "NEED_INDEX.md", "FIELD_GUIDE.md", "IMPORT_MAINTENANCE.md", "ledger/CORRECTIONS.md", "ledger/OPEN_QUESTIONS.md", "ledger/claims.jsonl", "ledger/scope.tsv", "experiments/evidence/v100-20261006/provenance.json", "source-tools/read_atlas.py"]
    missing = [name for name in required if not (atlas / name).is_file()]
    if missing:
        raise ValueError(f"source import is incomplete: {missing}")

    catalog_lines = ["# Complete atlas card and resource catalog", "", "> Generated index of the preserved source cards. Open only the entries relevant to the current question.", ""]
    for family, prefix, count, start in (("reference", "R", 16, 0), ("mechanisms", "M", 52, 1), ("compositions", "C", 40, 0), ("experiments", "E", 40, 0), ("sources", "S", 42, 1)):
        catalog_lines.extend([f"## {family.title()} cards", ""])
        for i in range(start, count + (1 if start == 0 else 1)):
            identifier = f"{prefix}{i:02d}"
            info = cards.get(identifier)
            if info:
                catalog_lines.append(f"- [{identifier}: {info['title']}]({info['path']})")
        catalog_lines.append("")
    support_docs = ["README.md", "CURRENT_STATUS.md", "IMPORT_MAINTENANCE.md", "benchmarks/README.md", "experiments/README.md", "ledger/OPEN_QUESTIONS.md", "ledger/SESSION.md", "ledger/MAINTENANCE.md", "ledger/LEGACY_SCOPE.md", "ledger/SCOPE.md", "ledger/CORRECTIONS.md", "sources/SOURCES.md", "reference/R00-current-status-context.md"]
    catalog_lines.extend(["## Supporting documentation", ""])
    for rel in support_docs:
        if (atlas / rel).is_file():
            title = document_title((atlas / rel).read_text(encoding="utf-8"), Path(rel).stem.replace("_", " "))
            catalog_lines.append(f"- [{title}]({rel})")
    catalog_lines.append("")
    catalog_payload = "\n".join(catalog_lines).rstrip("\n") + "\n"
    write_imported(atlas, atlas / "CARD_CATALOG.md", catalog_payload.encode(), owned)
    start_path = atlas / "START_HERE.md"
    start = start_path.read_text(encoding="utf-8")
    marker = "## Evidence and access"
    addition = "## Complete card catalog\n\nOpen the [complete card and resource catalog](CARD_CATALOG.md) to locate any preserved card without reading the whole corpus.\n\n"
    if "[complete card and resource catalog]" not in start:
        start = start.replace(marker, addition + marker)
        write_imported(atlas, start_path, start.encode(), owned)
    need_path = atlas / "NEED_INDEX.md"
    need = need_path.read_text(encoding="utf-8")
    if "[complete card and resource catalog]" not in need:
        need += "\n## Full card catalog\n\nUse the [complete card and resource catalog](CARD_CATALOG.md) when a direct card ID is already known.\n"
        write_imported(atlas, need_path, need.encode(), owned)

    current_corpus_path = skill_root / "cuda/.project-control-corpus.json"
    assert_safe_repo_path(skill_root, current_corpus_path)
    current = json.loads(current_corpus_path.read_text(encoding="utf-8"))
    if len(current.get("resources", [])) < 110 or len(current.get("relationships", [])) < 298:
        raise ValueError("existing CUDA corpus is smaller than its expected preservation baseline")
    existing_resources = {item["id"]: item for item in current["resources"]}
    # Preserve baseline records exactly except for a refreshed content hash when
    # their existing Markdown target was actually modified in this integration.
    for item in baseline_corpus["resources"]:
        present = existing_resources.get(item["id"])
        if present is None:
            current["resources"].append(dict(item))
            present = current["resources"][-1]
            existing_resources[item["id"]] = present
        refreshed = dict(item)
        resource_path = skill_root / "cuda" / item.get("path", "")
        if resource_path.exists():
            assert_safe_repo_path(skill_root, resource_path)
        if "sha256" in item and resource_path.is_file():
            actual_hash = sha256(resource_path.read_bytes())
            if actual_hash != item["sha256"]:
                refreshed["sha256"] = actual_hash
        if present != refreshed:
            if {k: v for k, v in present.items() if k != "sha256"} != {k: v for k, v in refreshed.items() if k != "sha256"}:
                raise ValueError(f"pre-existing CUDA resource has unexpected edits: {item['id']}")
            present.clear()
            present.update(refreshed)
    old_resources = {item["id"]: item for item in prior_corpus["resources"]}
    target_prefix = "references/architectures/volta/v100_atlas/"
    for record in prior_corpus["resources"]:
        updated = dict(record)
        source_rel = record.get("path", "")
        if source_rel.startswith(target_prefix):
            source_rel = source_rel[len(target_prefix):]
        updated["path"] = target_prefix + mapping.get(source_rel, source_rel)
        mapped_target = skill_root / "cuda" / updated["path"]
        if mapped_target.exists():
            assert_safe_repo_path(skill_root, mapped_target)
        if mapped_target.is_file() and "sha256" in updated:
            updated["sha256"] = sha256(mapped_target.read_bytes())
        if updated["id"] in existing_resources:
            # These IDs belong to the archived atlas graph; refresh their relocated path/hash
            # while preserving any fields already added by the current CUDA corpus.
            existing_resources[updated["id"]].update(updated)
        else:
            current["resources"].append(updated)
            existing_resources[updated["id"]] = updated
    seen_edges = {(x["from"], x["to"], x["type"]) for x in current.get("relationships", [])}
    for edge in prior_corpus["relationships"]:
        key = (edge["from"], edge["to"], edge["type"])
        if key not in seen_edges:
            current["relationships"].append(edge)
            seen_edges.add(key)

    # Add stable identities for the measured packet and its bounded interpretation/claim limits.
    add_resource(current, existing_resources, {"id": "atlas-current-status", "title": "Current measured status", "path": target_prefix + "CURRENT_STATUS.md", "role": "deep_reference", "aliases": ["V100 atlas current status"], "sha256": sha256((atlas / "CURRENT_STATUS.md").read_bytes())})
    add_resource(current, existing_resources, {"id": "atlas-campaign-provenance", "title": "Measured campaign provenance", "path": target_prefix + "experiments/evidence/v100-20261006/provenance.json", "role": "evidence", "aliases": ["V100 campaign provenance"], "sha256": sha256((atlas / "experiments/evidence/v100-20261006/provenance.json").read_bytes())})
    evidence_statuses = {f"E{i:02d}": json.loads((atlas / f"experiments/evidence/v100-20261006/E{i:02d}.json").read_text()).get("status", "UNKNOWN") for i in range(40)}
    # Remove only generated identities from an earlier importer revision that mislabeled
    # CPU_ONLY and NOT_RUN records as measured GPU evidence.
    invalid_measured = {f"atlas-measured-{identifier}" for identifier, status in evidence_statuses.items() if status != "GPU_RUN"}
    current["resources"] = [item for item in current["resources"] if item.get("id") not in invalid_measured]
    current["relationships"] = [item for item in current.get("relationships", []) if item.get("from") not in invalid_measured and item.get("to") not in invalid_measured]
    existing_resources = {item["id"]: item for item in current["resources"]}
    for identifier, status in evidence_statuses.items():
        evidence_rel = f"experiments/evidence/v100-20261006/{identifier}.json"
        evidence_path = atlas / evidence_rel
        if evidence_path.is_file():
            result_id = f"atlas-result-{identifier}"
            add_resource(current, existing_resources, {"id": result_id, "title": f"Portable campaign result {identifier} ({status})", "path": target_prefix + evidence_rel, "role": "evidence", "aliases": [f"V100 campaign record {identifier}"], "metadata": {"status": status}, "sha256": sha256(evidence_path.read_bytes())})
            append_edge(current, {"from": identifier, "to": result_id, "type": f"experiment_result_{status.lower()}"})
            append_edge(current, {"from": result_id, "to": "atlas-campaign-provenance", "type": "campaign_provenance"})
            if status == "GPU_RUN":
                measured_id = f"atlas-measured-{identifier}"
                add_resource(current, existing_resources, {"id": measured_id, "title": f"GPU measured evidence {identifier} (implemented subset)", "path": target_prefix + evidence_rel, "role": "evidence", "aliases": [f"V100 measured evidence {identifier}"], "metadata": {"status": status, "scope": "implemented measured subset only"}, "sha256": sha256(evidence_path.read_bytes())})
                append_edge(current, {"from": identifier, "to": measured_id, "type": "measured_evidence"})
                append_edge(current, {"from": measured_id, "to": "atlas-campaign-provenance", "type": "campaign_provenance"})
    for identifier, title, rel in [
        ("atlas-claim-limits", "Atlas claim limits", "experiments/CLAIM_LIMITS.md"),
        ("atlas-interpretation", "Interpreting results", "experiments/INTERPRETING_RESULTS.md"),
        ("atlas-scope", "Atlas scope", "ledger/SCOPE.md"),
        ("atlas-corrections", "Atlas corrections", "ledger/CORRECTIONS.md"),
        ("atlas-open-questions", "Atlas open questions", "ledger/OPEN_QUESTIONS.md"),
    ]:
        target = atlas / rel
        if target.is_file():
            add_resource(current, existing_resources, {"id": identifier, "title": title, "path": target_prefix + rel, "role": "deep_reference", "aliases": [title], "sha256": sha256(target.read_bytes())})
    for identifier, source_id in [("atlas-claim-limits", "E00"), ("atlas-interpretation", "E00"), ("atlas-scope", "E00"), ("atlas-corrections", "E00"), ("atlas-open-questions", "E00")]:
        if identifier in existing_resources:
            append_edge(current, {"from": "atlas-campaign-provenance", "to": identifier, "type": "interpretation_limits"})
    machine_path = "references/common/machine-aligned-design.md"
    machine_file = skill_root / "cuda" / machine_path
    if machine_file.is_file():
        assert_safe_repo_path(skill_root, machine_file)
        add_resource(current, existing_resources, {"id": "cuda-machine-aligned-design", "title": "Machine-aligned design", "path": machine_path, "role": "deep_reference", "aliases": ["machine aligned design", "representation and hardware mapping"], "sha256": sha256(machine_file.read_bytes())})
        append_edge(current, {"from": "cuda-machine-aligned-design", "to": "atlas-current-status", "type": "hardware_evidence_context"})
        append_edge(current, {"from": "cuda-machine-aligned-design", "to": "atlas-interpretation", "type": "representation_guidance"})
        append_edge(current, {"from": "cuda-machine-aligned-design", "to": "atlas-claim-limits", "type": "claim_scope"})
        for identifier in ("R00", "R05", "R06", "R15", "C39"):
            append_edge(current, {"from": "cuda-machine-aligned-design", "to": identifier, "type": "architecture_route"})
    assert_safe_repo_path(skill_root, current_corpus_path)
    current_corpus_path.write_bytes(json_bytes(current))

    evidence_status_counts = Counter(json.loads(verified_pinned_bytes(source, f"experiments/evidence/v100-20261006/E{i:02d}.json", checksums)).get("status", "UNKNOWN") for i in range(40))
    inventory = {
        "schema_version": 1,
        "source": {"repository": "gpu_circuit_bending_atlas", "commit": SOURCE_COMMIT, "campaign_source_commit": CAMPAIGN_SOURCE_COMMIT, "archive_commit": ARCHIVE_COMMIT},
        "workspace_baseline": {"commit": CORPUS_BASELINE_COMMIT, "resources": len(baseline_corpus["resources"]), "relationships": len(baseline_corpus["relationships"]), "archive": "archive/cuda-corpus-baseline-9cafc69.source.json"},
        "counts": {"references": 16, "mechanisms": 52, "compositions": 40, "experiments": 40, "sources": 42, "cards": len(cards), "source_snapshot_files": len(source_paths), "campaign_evidence_status": dict(sorted(evidence_status_counts.items()))},
        "cards": cards,
        "entrypoints": {"A00": "START_HERE.md", "A01": "NEED_INDEX.md", "A02": "FIELD_GUIDE.md"},
        "archive": {"compendium": "archive/V100_ATLAS_FULL.source.txt", "compendium_sha256": sha256(original_full), "zip": "archive/V100_SXM2_Circuit_Bending_Atlas.zip", "zip_sha256": sha256(zip_bytes), "prior_corpus": "archive/prior-corpus-9581834.source.json", "prior_resource_count": len(prior_corpus["resources"]), "prior_relationship_count": len(prior_corpus["relationships"])},
        "mapping": {"source_to_bundle": mapping},
        "source_checksums": {"source_path": "archive/source-SHA256SUMS.source.txt", "sha256": PINNED_SOURCE_SUMS_SHA256},
        "portable_campaign_evidence": {rel.as_posix(): {"bundle_path": mapping[rel.as_posix()], "sha256": sha256(verified_campaign_bytes(source, rel, provenance))} for rel in portable_evidence_paths(source)},
    }
    write_import_map(atlas, inventory, owned)



def add_resource(corpus: dict, resources: dict, record: dict) -> None:
    if record["id"] in resources:
        if resources[record["id"]].get("path") != record.get("path"):
            raise ValueError(f"corpus ID collision: {record['id']}")
        if "sha256" in record:
            resources[record["id"]]["sha256"] = record["sha256"]
        return
    corpus["resources"].append(record)
    resources[record["id"]] = record


def append_edge(corpus: dict, edge: dict) -> None:
    edges = corpus.setdefault("relationships", [])
    if not any(x.get("from") == edge["from"] and x.get("to") == edge["to"] and x.get("type") == edge["type"] for x in edges):
        edges.append(edge)


def make_status(source: Path, provenance: dict, checksums: dict[str, str]) -> str:
    statuses = Counter(json.loads(verified_pinned_bytes(source, f"experiments/evidence/v100-20261006/E{i:02d}.json", checksums)).get("status", "UNKNOWN") for i in range(40))
    gpu_ids = [f"E{i:02d}" for i in range(40) if json.loads(verified_pinned_bytes(source, f"experiments/evidence/v100-20261006/E{i:02d}.json", checksums)).get("status") == "GPU_RUN"]
    status_text = ", ".join(f"{key}={value}" for key, value in sorted(statuses.items()))
    return (
        "# Current evidence status\n\n"
        "> Dated 2026-10-06 from the portable evidence packet at source commit `5b5629b001da4a42d6f41a84d94f73c07a29d478`. The original navigation, protocols, and full compendium remain preserved separately.\n\n"
        f"The portable campaign evidence contains 40 experiment records with these overall statuses: {status_text}. GPU-run records are {', '.join(gpu_ids)}. "
        "A GPU_RUN status covers only the implemented and measured subset recorded for that experiment; it does not complete the original protocol. CPU_ONLY and NOT_RUN results retain their distinct scope. "
        "COMPILED_ONLY remains an individual subcase where the source card records one (including E36's compiled-image inspection); it is not promoted to a whole-experiment status. The records do not establish biological validation or blanket composition speedups.\n\n"
        "Read the [dated context for R00](reference/R00-current-status-context.md), [claim limits](experiments/CLAIM_LIMITS.md), and [result interpretation](experiments/INTERPRETING_RESULTS.md) before using measurements to support a broader claim. Campaign and source identities are recorded in [provenance](experiments/evidence/v100-20261006/provenance.json).\n"
    )




def validate(skill_root: Path) -> list[str]:
    atlas = skill_root / "cuda" / ATLAS_REL
    failures: list[str] = []
    try:
        assert_safe_repo_path(skill_root, atlas)
    except ValueError as exc:
        return [f"unsafe atlas path: {exc}"]
    inventory_path = atlas / "import-map.json"
    if not atlas.is_dir():
        return ["cannot read import map: atlas bundle directory missing"]
    try:
        assert_safe_destination(atlas, inventory_path)
        assert_safe_destination(atlas, atlas / "import-map.sha256")
    except ValueError as exc:
        return [f"unsafe atlas import metadata path: {exc}"]
    try:
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"cannot read import map: {exc}"]
    sidecar = atlas / "import-map.sha256"
    inventory_digest = sha256(inventory_path.read_bytes())
    if not sidecar.is_file() or sidecar.read_text(encoding="ascii").strip() != inventory_digest:
        failures.append("import-map integrity sidecar missing or mismatched")
    owned_files = inventory.get("owned_files")
    if not isinstance(owned_files, dict) or not owned_files:
        failures.append("import map has no owned-file hash manifest")
    else:
        for relative, expected_hash in owned_files.items():
            path = (atlas / relative).resolve(strict=False)
            try:
                assert_safe_destination(atlas, atlas / relative)
                path.relative_to(atlas.resolve())
            except ValueError:
                failures.append(f"owned-file path escapes atlas bundle: {relative}")
                continue
            if not path.is_file():
                failures.append(f"owned import file missing: {relative}")
            elif sha256(path.read_bytes()) != expected_hash:
                failures.append(f"owned import file hash mismatch: {relative}")
    if inventory.get("source", {}).get("commit") != SOURCE_COMMIT:
        failures.append("import map source commit mismatch")
    expected_counts = {"references": 16, "mechanisms": 52, "compositions": 40, "experiments": 40, "sources": 42}
    for key, count in expected_counts.items():
        if inventory.get("counts", {}).get(key) != count:
            failures.append(f"import map count {key} is not {count}")
    cards = inventory.get("cards", {})
    if len(cards) != 190:
        failures.append(f"expected 190 card mappings, found {len(cards)}")

    # All source Markdown is kept byte-exact under source-snapshot. The imported cards may
    # differ only in local link destinations that map to preserved bundle files.
    mapping = inventory.get("mapping", {}).get("source_to_bundle", {})
    source_snapshot = atlas / "archive/source-snapshot"
    checksum_file = atlas / inventory.get("source_checksums", {}).get("source_path", "")
    if not checksum_file.is_file() or sha256(checksum_file.read_bytes()) != PINNED_SOURCE_SUMS_SHA256 or inventory.get("source_checksums", {}).get("sha256") != PINNED_SOURCE_SUMS_SHA256:
        failures.append("pinned source checksum anchor missing or mismatch")
    checksum_map = {}
    if checksum_file.is_file():
        for line in checksum_file.read_text(encoding="utf-8").splitlines():
            match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
            if match:
                checksum_map[match.group(2)] = match.group(1)
    for source_rel, bundle_rel in mapping.items():
        if source_rel == "V100_ATLAS_FULL.md" or source_rel.endswith("/REPORT.md"):
            continue
        if source_rel not in checksum_map:
            # External portable summaries and qualified raw-host wrappers have
            # their own evidence/provenance checks; they are not pinned source files.
            continue
        snapshot = atlas / snapshot_path(source_rel)
        target = atlas / bundle_rel
        if not snapshot.is_file() or not target.is_file():
            failures.append(f"missing source/target payload pair: {source_rel} -> {bundle_rel}")
            continue
        if source_rel in checksum_map and sha256(snapshot.read_bytes()) != checksum_map[source_rel]:
            failures.append(f"pinned source snapshot hash mismatch: {source_rel}")
        if source_rel.endswith(".md"):
            source_text = snapshot.read_text(encoding="utf-8")
            target_text = target.read_text(encoding="utf-8")
            expected = rewrite_local_links(source_text, Path("/source") / source_rel, Path(bundle_rel), Path("/source"), mapping)
            if source_rel == "START_HERE.md":
                expected = expected.replace("## Evidence and access", "## Complete card catalog\n\nOpen the [complete card and resource catalog](CARD_CATALOG.md) to locate any preserved card without reading the whole corpus.\n\n## Evidence and access")
            elif source_rel == "NEED_INDEX.md":
                expected += "\n## Full card catalog\n\nUse the [complete card and resource catalog](CARD_CATALOG.md) when a direct card ID is already known.\n"
            if target_text != expected:
                failures.append(f"content or non-link wording changed: {source_rel}")
        elif snapshot.read_bytes() != target.read_bytes():
            failures.append(f"non-Markdown payload changed: {source_rel}")
    for source_rel, record in inventory.get("portable_campaign_evidence", {}).items():
        target = atlas / record["bundle_path"]
        if not target.is_file() or sha256(target.read_bytes()) != record["sha256"]:
            failures.append(f"portable campaign evidence missing or hash mismatch: {source_rel}")
    for identifier, info in cards.items():
        source = atlas / snapshot_path(info["source_path"])
        target = atlas / info["path"]
        if not source.is_file() or not target.is_file():
            failures.append(f"missing card {identifier}")
    if any(source_snapshot.rglob("*.md")):
        failures.append("raw source snapshot still contains Markdown files; archived originals must use non-Markdown suffixes")
    compendium = atlas / "archive/V100_ATLAS_FULL.source.txt"
    if not compendium.is_file() or inventory.get("archive", {}).get("compendium_sha256") != PINNED_COMPENDIUM_SHA256 or sha256(compendium.read_bytes()) != PINNED_COMPENDIUM_SHA256:
        failures.append("original full compendium missing or hash mismatch")
    zip_path = atlas / "archive/V100_SXM2_Circuit_Bending_Atlas.zip"
    if not zip_path.is_file() or inventory.get("archive", {}).get("zip_sha256") != PINNED_ZIP_SHA256 or sha256(zip_path.read_bytes()) != PINNED_ZIP_SHA256:
        failures.append("original ZIP missing or hash mismatch")
    else:
        try:
            with zipfile.ZipFile(zip_path) as archive:
                provenance = json.loads((atlas / "experiments/evidence/v100-20261006/provenance.json").read_text(encoding="utf-8"))
                original_cards = provenance.get("original_card_sha256", {})
                original_bodies = provenance.get("original_protocol_body_sha256", {})
                for identifier in (f"E{i:02d}" for i in range(40)):
                    member = f"v100_atlas/experiments/{identifier}.md"
                    original = archive.read(member)
                    if sha256(original) != original_cards.get(identifier):
                        failures.append(f"original archived card hash mismatch: {identifier}")
                    if protocol_body_sha256(original.decode("utf-8")) != original_bodies.get(identifier):
                        failures.append(f"original archived protocol body hash mismatch: {identifier}")
        except (KeyError, OSError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
            failures.append(f"original archive protocol verification failed: {exc}")
    prior_path = atlas / inventory.get("archive", {}).get("prior_corpus", "")
    try:
        prior = json.loads(prior_path.read_text(encoding="utf-8"))
        corpus_path = skill_root / "cuda/.project-control-corpus.json"
        assert_safe_repo_path(skill_root, corpus_path)
        current = json.loads(corpus_path.read_text(encoding="utf-8"))
        current_ids = {x["id"] for x in current.get("resources", [])}
        current_edges = {(x["from"], x["to"], x["type"]) for x in current.get("relationships", [])}
        missing_ids = {x["id"] for x in prior["resources"]} - current_ids
        missing_edges = {(x["from"], x["to"], x["type"]) for x in prior["relationships"]} - current_edges
        if missing_ids:
            failures.append(f"prior corpus resource IDs missing: {len(missing_ids)}")
        if missing_edges:
            failures.append(f"prior corpus relationships missing: {len(missing_edges)}")
        if len(current.get("resources", [])) < 110 + len(prior["resources"]):
            failures.append("pre-existing CUDA corpus resources were not preserved additively")
        if len(current.get("relationships", [])) < 298 + len(prior["relationships"]):
            failures.append("pre-existing CUDA corpus relationships were not preserved additively")
        baseline_path = atlas / inventory.get("workspace_baseline", {}).get("archive", "")
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        current_by_id = {item["id"]: item for item in current.get("resources", [])}
        for item in baseline.get("resources", []):
            actual = current_by_id.get(item["id"])
            if actual is None or {k: v for k, v in actual.items() if k != "sha256"} != {k: v for k, v in item.items() if k != "sha256"}:
                failures.append(f"pre-existing CUDA resource changed: {item['id']}")
            elif actual.get("sha256") != item.get("sha256"):
                target = skill_root / "cuda" / item.get("path", "")
                if not item.get("sha256") or not target.is_file() or sha256(target.read_bytes()) != actual.get("sha256"):
                    failures.append(f"pre-existing CUDA resource hash changed without matching content: {item['id']}")
        current_edge_set = {(item["from"], item["to"], item["type"]) for item in current.get("relationships", [])}
        baseline_edge_set = {(item["from"], item["to"], item["type"]) for item in baseline.get("relationships", [])}
        if not baseline_edge_set.issubset(current_edge_set):
            failures.append("pre-existing CUDA relationships changed")
        for record in current.get("resources", []):
            path = record.get("path")
            if path and path.startswith("references/architectures/volta/v100_atlas/"):
                target = skill_root / "cuda" / path
                if not target.is_file():
                    failures.append(f"corpus path does not resolve: {record['id']} -> {path}")
                else:
                    try:
                        assert_safe_destination(atlas, target)
                    except ValueError:
                        failures.append(f"unsafe corpus path: {record['id']} -> {path}")
                        continue
                    if record.get("sha256") and sha256(target.read_bytes()) != record["sha256"]:
                        failures.append(f"corpus content hash mismatch: {record['id']} -> {path}")
    except Exception as exc:
        failures.append(f"corpus integrity check failed: {exc}")
    required = ["CURRENT_STATUS.md", "IMPORT_MAINTENANCE.md", "experiments/CLAIM_LIMITS.md", "experiments/INTERPRETING_RESULTS.md", "ledger/CORRECTIONS.md", "ledger/OPEN_QUESTIONS.md", "ledger/claims.jsonl", "ledger/scope.tsv", "experiments/evidence/v100-20261006/provenance.json", "source-tools/read_atlas.py"]
    for rel in required:
        if not (atlas / rel).is_file():
            failures.append(f"required preserved artifact missing: {rel}")
    for document in atlas.rglob("*.md"):
        if "archive" in document.relative_to(atlas).parts:
            continue
        for match in all_link_destinations(document.read_text(encoding="utf-8")):
            raw = match.group("target")
            url = raw[1:-1] if raw.startswith("<") and raw.endswith(">") else raw
            parsed = urlsplit(url)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            target = (document.parent / parsed.path).resolve(strict=False)
            try:
                target.relative_to(atlas.resolve())
            except ValueError:
                failures.append(f"local Markdown link escapes atlas bundle: {document.relative_to(atlas)} -> {url}")
                continue
            if not target.is_file() and not target.is_dir():
                failures.append(f"local Markdown link target missing: {document.relative_to(atlas)} -> {url}")
    try:
        provenance = json.loads((atlas / "experiments/evidence/v100-20261006/provenance.json").read_text())
        if provenance.get("source_commit") != CAMPAIGN_SOURCE_COMMIT or provenance.get("original_protocol_archive_commit") != ARCHIVE_COMMIT:
            failures.append("campaign/source/archive provenance identity mismatch")
        statuses = {f"E{i:02d}": json.loads((atlas / f"experiments/evidence/v100-20261006/E{i:02d}.json").read_text()).get("status", "UNKNOWN") for i in range(40)}
        counts = dict(sorted(Counter(statuses.values()).items()))
        if inventory.get("counts", {}).get("campaign_evidence_status") != counts:
            failures.append("campaign status counts differ from portable evidence")
        corpus = json.loads((skill_root / "cuda/.project-control-corpus.json").read_text())
        ids = {item["id"] for item in corpus.get("resources", [])}
        edges = {(item["from"], item["to"], item["type"]) for item in corpus.get("relationships", [])}
        for identifier, status in statuses.items():
            result_id = f"atlas-result-{identifier}"
            if result_id not in ids or (identifier, result_id, f"experiment_result_{status.lower()}") not in edges:
                failures.append(f"campaign result identity/scope missing: {identifier} ({status})")
            measured_id = f"atlas-measured-{identifier}"
            if status == "GPU_RUN" and (measured_id not in ids or (identifier, measured_id, "measured_evidence") not in edges):
                failures.append(f"GPU measured subset identity missing: {identifier}")
            if status != "GPU_RUN" and measured_id in ids:
                failures.append(f"non-GPU result mislabeled as measured evidence: {identifier}")
    except Exception as exc:
        failures.append(f"portable evidence identity validation failed: {exc}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, help="read-only atlas checkout at the recorded source commit")
    parser.add_argument("--archive", type=Path, help="original atlas ZIP whose SHA matches the historical corpus")
    parser.add_argument("--skill-root", type=Path, default=Path(__file__).resolve().parents[6], help="repository root containing cuda/")
    parser.add_argument("--validate", action="store_true", help="validate an existing deployed bundle without the source checkout")
    args = parser.parse_args()
    try:
        if args.validate:
            failures = validate(args.skill_root)
            for item in failures:
                print(f"FAIL: {item}", file=sys.stderr)
            if failures:
                return 1
            print("PASS: atlas bundle integrity")
            return 0
        if not args.source or not args.archive:
            parser.error("--source and --archive are required for import; use --validate for source-less validation")
        build(args.source.resolve(), args.archive.resolve(), args.skill_root.resolve())
        failures = validate(args.skill_root.resolve())
        if failures:
            for item in failures:
                print(f"FAIL: {item}", file=sys.stderr)
            return 1
        print("PASS: imported and validated atlas bundle")
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
