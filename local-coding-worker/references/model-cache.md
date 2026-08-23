# Persistent model cache

Cold canonical assets remain under `/mnt/block/core4-models`. Production uses
the persistent SSD cache at `/home/tumlinson/.local/share/core4/models`:

```text
<candidate-id>/<payload-sha256>/
  model.gguf
  asset-manifest.json
  READY
active-profile.json
```

`local-worker model-cache inspect|list|install|verify|activate|remove` is the
public surface. Install holds a cache lock, checks the pinned source manifest
and free-space margin, copies into a same-filesystem partial directory, hashes
the copied payload, fsyncs durable files, and atomically renames it. Models are
not deleted after tasks.

Ordinary use performs quick READY, schema, size, immutable-path, GGUF-header,
inode, and mtime checks. Install, explicit `verify --full`, and metadata change
perform full SHA-256 verification. The active-profile pointer is atomic and
outside payload directories. Removal refuses active or leased payloads.
