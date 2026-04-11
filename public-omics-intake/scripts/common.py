#!/usr/bin/env python3
from __future__ import annotations

import csv
import ftplib
import json
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

NCBI_EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
GEO_FTP_HOST = "ftp.ncbi.nlm.nih.gov"
GEO_HTTPS_BASE = "https://ftp.ncbi.nlm.nih.gov"
DEFAULT_TIMEOUT = 60
USER_AGENT = "public-omics-intake/1.0"

ACCESSION_PREFIXES = {
    "GSE": "geo-series",
    "GSM": "geo-sample",
    "GPL": "geo-platform",
    "GDS": "geo-dataset",
    "SRP": "sra-project",
    "SRS": "sra-sample",
    "SRX": "sra-experiment",
    "SRR": "sra-run",
    "PRJNA": "bioproject",
    "PRJEB": "bioproject",
    "PRJDB": "bioproject",
    "SAMN": "biosample",
    "SAMEA": "biosample",
    "SAMD": "biosample",
}

ORGANISM_PATTERNS = {
    "human": ["human", "homo sapiens"],
    "mouse": ["mouse", "mus musculus", "murine"],
    "rat": ["rat", "rattus norvegicus"],
    "zebrafish": ["zebrafish", "danio rerio"],
    "fruit-fly": ["drosophila", "fruit fly", "d. melanogaster"],
    "nematode": ["c. elegans", "caenorhabditis elegans"],
}

MODALITY_PATTERNS = {
    "scrna-seq": ["scrna", "single-cell rna", "single cell rna", "sc-rna", "10x gene expression"],
    "snrna-seq": ["snrna", "single-nucleus rna", "single nucleus rna"],
    "bulk-rna-seq": ["bulk rna", "rna-seq", "rnaseq", "transcriptome"],
    "scatac-seq": ["scatac", "single-cell atac", "single cell atac", "atac-seq", "atac seq"],
    "multiome": ["multiome", "paired atac", "paired rna", "joint atac", "multi-omic"],
    "cite-seq": ["cite-seq", "citeseq", "adt"],
    "spatial-transcriptomics": ["spatial", "visium", "merfish", "seqfish", "slide-seq"],
}

LIKELY_TISSUES = [
    "brain",
    "cortex",
    "heart",
    "lung",
    "liver",
    "kidney",
    "blood",
    "bone marrow",
    "skin",
    "tumor",
    "retina",
    "intestine",
    "colon",
    "pancreas",
    "embryo",
]

LIKELY_STAGES = [
    "embryonic",
    "fetal",
    "neonatal",
    "adult",
    "aged",
    "developmental",
]


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower())
    value = re.sub(r"-{2,}", "-", value)
    return value.strip("-") or "project"


def parse_bool(text: str | None, default: bool = False) -> bool:
    if text is None:
        return default
    lowered = text.strip().lower()
    if lowered in {"1", "true", "yes", "y", "on"}:
        return True
    if lowered in {"0", "false", "no", "n", "off"}:
        return False
    return default


def accession_type(accession: str) -> str | None:
    normalized = accession.strip().upper()
    for prefix, kind in ACCESSION_PREFIXES.items():
        if normalized.startswith(prefix):
            return kind
    return None


def normalize_accession(accession: str) -> str:
    normalized = accession.strip().upper()
    if not accession_type(normalized):
        raise ValueError(f"Unsupported accession: {accession}")
    return normalized


def geo_bucket(accession: str) -> str:
    accession = normalize_accession(accession)
    prefix = accession[:3]
    digits = accession[3:]
    if len(digits) <= 3:
        return f"{prefix}nnn"
    return f"{prefix}{digits[:-3]}nnn"


def geo_series_root(accession: str) -> str:
    accession = normalize_accession(accession)
    kind = accession_type(accession)
    bucket = geo_bucket(accession)
    if kind == "geo-series":
        branch = "series"
    elif kind == "geo-sample":
        branch = "samples"
    elif kind == "geo-platform":
        branch = "platforms"
    elif kind == "geo-dataset":
        branch = "datasets"
    else:
        raise ValueError(f"Unsupported GEO accession: {accession}")
    return f"/geo/{branch}/{bucket}/{accession}"


def build_geo_download_plan(accession: str) -> dict[str, Any]:
    accession = normalize_accession(accession)
    root = geo_series_root(accession)
    base_url = f"{GEO_HTTPS_BASE}{root}"
    plan = {
        "accession": accession,
        "source": "geo",
        "root_url": base_url,
        "root_ftp_path": root,
        "local_root": f"sources/geo/{accession}",
        "metadata_dir": f"sources/geo/{accession}/metadata",
        "soft_dir": f"sources/geo/{accession}/soft",
        "miniml_dir": f"sources/geo/{accession}/miniml",
        "matrix_dir": f"sources/geo/{accession}/matrix",
        "suppl_dir": f"sources/geo/{accession}/suppl",
        "download_candidates": [],
    }
    if accession.startswith("GSE"):
        plan["download_candidates"] = [
            {
                "scope": "metadata",
                "label": "soft",
                "url": f"{base_url}/soft/{accession}_family.soft.gz",
                "ftp_dir": f"{root}/soft",
                "filename": f"{accession}_family.soft.gz",
                "local_dir": plan["soft_dir"],
            },
            {
                "scope": "metadata",
                "label": "miniml",
                "url": f"{base_url}/miniml/{accession}_family.xml.tgz",
                "ftp_dir": f"{root}/miniml",
                "filename": f"{accession}_family.xml.tgz",
                "local_dir": plan["miniml_dir"],
            },
            {
                "scope": "processed",
                "label": "matrix",
                "url": f"{base_url}/matrix/",
                "ftp_dir": f"{root}/matrix",
                "filename": None,
                "local_dir": plan["matrix_dir"],
            },
            {
                "scope": "processed",
                "label": "suppl",
                "url": f"{base_url}/suppl/",
                "ftp_dir": f"{root}/suppl",
                "filename": None,
                "local_dir": plan["suppl_dir"],
            },
        ]
    else:
        plan["download_candidates"] = [
            {
                "scope": "processed",
                "label": "suppl",
                "url": f"{base_url}/suppl/",
                "ftp_dir": f"{root}/suppl",
                "filename": None,
                "local_dir": plan["suppl_dir"],
            }
        ]
    return plan


def build_sra_local_root(study_accession: str) -> str:
    return f"sources/sra/{normalize_accession(study_accession)}"


def request_json(endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
    query = urlencode({key: value for key, value in params.items() if value is not None}, doseq=True)
    url = f"{NCBI_EUTILS_BASE}/{endpoint}?{query}"
    request = Request(url, headers={"User-Agent": USER_AGENT})
    retries = 3
    for attempt in range(retries):
        try:
            with urlopen(request, timeout=DEFAULT_TIMEOUT) as response:
                return json.load(response)
        except HTTPError as exc:
            if exc.code in {429, 500, 502, 503, 504} and attempt + 1 < retries:
                time.sleep(1.0 + attempt)
                continue
            raise RuntimeError(f"HTTP error for {url}: {exc.code}") from exc
        except URLError as exc:
            if attempt + 1 < retries:
                time.sleep(1.0 + attempt)
                continue
            raise RuntimeError(f"Network error for {url}: {exc.reason}") from exc
    raise RuntimeError(f"Failed to retrieve {url}")


def request_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    retries = 3
    for attempt in range(retries):
        try:
            with urlopen(request, timeout=DEFAULT_TIMEOUT) as response:
                return response.read().decode("utf-8")
        except HTTPError as exc:
            if exc.code in {429, 500, 502, 503, 504} and attempt + 1 < retries:
                time.sleep(1.0 + attempt)
                continue
            raise RuntimeError(f"HTTP error for {url}: {exc.code}") from exc
        except URLError as exc:
            if attempt + 1 < retries:
                time.sleep(1.0 + attempt)
                continue
            raise RuntimeError(f"Network error for {url}: {exc.reason}") from exc
    raise RuntimeError(f"Failed to retrieve {url}")


def download_url(url: str, target_path: str | Path) -> Path:
    target = ensure_parent(target_path)
    request = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=DEFAULT_TIMEOUT) as response:
            target.write_bytes(response.read())
    except HTTPError as exc:
        raise RuntimeError(f"HTTP error for {url}: {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"Network error for {url}: {exc.reason}") from exc
    return target


def list_ftp_files(ftp_dir: str) -> list[str]:
    entries: list[str] = []
    with ftplib.FTP(GEO_FTP_HOST, timeout=DEFAULT_TIMEOUT) as ftp:
        ftp.login()
        try:
            entries = ftp.nlst(ftp_dir)
        except ftplib.error_perm as exc:
            if str(exc).startswith("550"):
                return []
            raise
    names = [entry.rsplit("/", 1)[-1] for entry in entries]
    return [name for name in names if name not in {".", ".."}]


def read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text())


def ensure_parent(path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def write_json(path: str | Path, payload: Any) -> Path:
    target = ensure_parent(path)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return target


def write_jsonl(path: str | Path, rows: Iterable[dict[str, Any]]) -> Path:
    target = ensure_parent(path)
    with target.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    return target


def write_tsv(path: str | Path, rows: Iterable[dict[str, Any]], fieldnames: list[str] | None = None) -> Path:
    rows = list(rows)
    target = ensure_parent(path)
    if fieldnames is None:
        fieldnames = sorted({key for row in rows for key in row.keys()}) if rows else []
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _stringify_cell(row.get(key)) for key in fieldnames})
    return target


def read_tsv(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _stringify_cell(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True)
    return str(value)


def emit_provenance_event(
    script_name: str,
    arguments: dict[str, Any],
    inputs: list[str],
    outputs: list[str],
    warnings: list[str] | None = None,
    endpoint_category: str | None = None,
) -> dict[str, Any]:
    return {
        "timestamp": now_utc_iso(),
        "script": script_name,
        "arguments": arguments,
        "inputs": inputs,
        "outputs": outputs,
        "warnings": warnings or [],
        "endpoint_category": endpoint_category,
    }


def append_provenance(root: str | Path, event: dict[str, Any]) -> Path:
    target = Path(root) / "registry" / "provenance" / "provenance_log.jsonl"
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")
    return target


def parse_request_description(
    description: str,
    preferred_modalities: list[str] | None = None,
    required_modalities: list[str] | None = None,
    organisms: list[str] | None = None,
) -> dict[str, Any]:
    lowered = description.lower()
    inferred_organisms = organisms[:] if organisms else []
    for canonical, variants in ORGANISM_PATTERNS.items():
        if canonical in inferred_organisms:
            continue
        if any(variant in lowered for variant in variants):
            inferred_organisms.append(canonical)

    inferred_modalities = preferred_modalities[:] if preferred_modalities else []
    for canonical, variants in MODALITY_PATTERNS.items():
        if canonical in inferred_modalities:
            continue
        if any(variant in lowered for variant in variants):
            inferred_modalities.append(canonical)

    stages = [stage for stage in LIKELY_STAGES if stage in lowered]
    tissues = [tissue for tissue in LIKELY_TISSUES if tissue in lowered]
    raw_required = "raw only" in lowered or "require raw" in lowered or "raw sra" in lowered
    processed_acceptable = not raw_required
    public_only = "private" not in lowered

    cell_type = None
    cell_match = re.search(r"(?:cell type|cells?)\s+(?:of|from|in)?\s*([a-z0-9 _-]{3,40})", lowered)
    if cell_match:
        cell_type = cell_match.group(1).strip(" -_")

    perturbation = None
    perturb_match = re.search(r"(?:perturbation|treated with|knockout|ko|stimulated with)\s+([a-z0-9 _-]{3,50})", lowered)
    if perturb_match:
        perturbation = perturb_match.group(1).strip(" -_")

    disease_state = None
    disease_match = re.search(r"(?:disease|cancer|tumor|fibrosis|infection)\s+([a-z0-9 _-]{0,50})", lowered)
    if disease_match and disease_match.group(0).strip():
        disease_state = disease_match.group(0).strip()

    intended_use = None
    use_match = re.search(r"(?:for|to support|to build)\s+([a-z0-9 ,/_-]{5,80})", lowered)
    if use_match:
        intended_use = use_match.group(1).strip(" -_,")

    return {
        "description": description,
        "biological_system": description,
        "organisms": inferred_organisms,
        "developmental_stages": stages,
        "disease_state": disease_state,
        "tissues": tissues,
        "cell_type": cell_type,
        "preferred_modalities": inferred_modalities,
        "required_modalities": required_modalities or [],
        "processed_files_acceptable": processed_acceptable,
        "raw_files_required": raw_required,
        "public_only_required": public_only,
        "intended_use": intended_use,
        "perturbation": perturbation,
    }


def list_field(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str):
        if not value.strip():
            return []
        if "|" in value:
            return [chunk.strip() for chunk in value.split("|") if chunk.strip()]
        if "," in value:
            return [chunk.strip() for chunk in value.split(",") if chunk.strip()]
        return [value.strip()]
    return [str(value)]


def unique_sorted(values: Iterable[str]) -> list[str]:
    return sorted({value for value in values if value})


def metadata_richness(record: dict[str, Any]) -> float:
    fields = [
        "title",
        "summary",
        "species",
        "modality",
        "assay",
        "chemistry",
        "stage",
        "tissue",
        "cell_type",
        "perturbation",
        "pubmed_ids",
    ]
    filled = 0
    for field in fields:
        value = record.get(field)
        if isinstance(value, list) and value:
            filled += 1
        elif isinstance(value, str) and value.strip():
            filled += 1
        elif value not in (None, "", []):
            filled += 1
    return round(filled / len(fields), 4)


def linked_accession_completeness(record: dict[str, Any]) -> float:
    fields = ["primary_accession", "study_accessions", "sample_accessions", "run_accessions"]
    filled = 0
    for field in fields:
        value = record.get(field)
        if field == "primary_accession" and value:
            filled += 1
        elif list_field(value):
            filled += 1
    return round(filled / len(fields), 4)


def identifier_consistency(record: dict[str, Any]) -> float:
    accession_sets = [
        len(unique_sorted(list_field(record.get("study_accessions")))),
        len(unique_sorted(list_field(record.get("sample_accessions")))),
        len(unique_sorted(list_field(record.get("run_accessions")))),
    ]
    non_zero = [count for count in accession_sets if count > 0]
    if not non_zero:
        return 0.25
    max_count = max(non_zero)
    min_count = min(non_zero)
    if max_count == 0:
        return 0.25
    return round(min_count / max_count, 4)


def compute_file_types(record: dict[str, Any]) -> list[str]:
    explicit = unique_sorted(list_field(record.get("file_types_available")))
    if explicit:
        return explicit
    file_types: list[str] = []
    if record.get("processed_available"):
        file_types.append("processed")
    if record.get("raw_available"):
        file_types.append("raw")
    if record.get("source") == "geo":
        file_types.extend(["soft", "miniml"])
    if record.get("source") == "sra":
        file_types.append("runinfo")
    return unique_sorted(file_types)


def load_records(path: str | Path) -> list[dict[str, Any]]:
    payload = read_json(path)
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("records", "candidates", "datasets", "selected_datasets"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
    raise ValueError(f"Could not find a record list in {path}")


def dump_yaml_like(path: str | Path, payload: dict[str, Any]) -> Path:
    target = ensure_parent(path)
    lines: list[str] = []
    for key, value in payload.items():
        lines.extend(_yaml_lines(key, value, indent=0))
    target.write_text("\n".join(lines) + "\n")
    return target


def _yaml_lines(key: str, value: Any, indent: int) -> list[str]:
    prefix = " " * indent
    if isinstance(value, dict):
        lines = [f"{prefix}{key}:"]
        for child_key, child_value in value.items():
            lines.extend(_yaml_lines(str(child_key), child_value, indent + 2))
        return lines
    if isinstance(value, list):
        lines = [f"{prefix}{key}:"]
        for item in value:
            if isinstance(item, dict):
                lines.append(f"{prefix}  -")
                for child_key, child_value in item.items():
                    lines.extend(_yaml_lines(str(child_key), child_value, indent + 4))
            else:
                lines.append(f"{prefix}  - {json.dumps(item)}")
        return lines
    return [f"{prefix}{key}: {json.dumps(value)}"]


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=False, capture_output=True, text=True)
