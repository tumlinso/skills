# Import maintenance and migration

The bundle importer updates files only when the `import-map.json` integrity sidecar and per-file hashes in `owned_files` verify. It refuses unknown collisions and edits to files it previously owned.

Legacy bundles that have an import map but no owned-file hash manifest are preserved and fail closed; the importer will not infer ownership from current bytes on disk. Manual migration requires either preserving the legacy bundle and importing into a new destination, or using a separate externally verified procedure that checks each payload against pinned Git source, campaign provenance, or exact generated output before establishing ownership. Do not add a broad overwrite bypass or bless hashes sampled only from the legacy destination.

Use `python -B tools/sync_skill_bundle.py --validate` for source-less integrity checks. Validation checks the sidecar, owned-file hashes, corpus content hashes, pinned archive anchors, original protocol identities, and local links.
