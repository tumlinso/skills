# SRA Notes

Use official SRA programmatic access and preserve study and run metadata separately.

## Discovery

- Query SRA through NCBI E-utilities.
- Resolve study metadata from runinfo-style tables when that yields clearer study or sample or run linkage than free-text summaries.
- Preserve run metadata as a separate table even when producing a study-level summary.

## Fetch Policy

- `metadata` scope means runinfo and study summary capture only.
- `raw` scope means explicit SRA Toolkit-backed raw acquisition.
- `all-public` means metadata plus raw in v1.
- Do not default to raw.

## Raw Acquisition Guardrails

- Use `prefetch` for raw SRA materialization.
- Use `fasterq-dump` only when explicitly requested or operationally necessary.
- Fail clearly if SRA Toolkit is missing.
- Keep raw files and any optional FASTQ materialization linked back to the study and run manifests.
