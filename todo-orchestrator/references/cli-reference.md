# v2 CLI Reference

Invoke `python <skill-dir>/scripts/todo.py <command> --repo-root <repo> --json`.

Under `--json`, stdout contains exactly one JSON response envelope:

```json
{"schema_version": 2, "ok": true, "code": "success", "data": {}}
```

Failures use the same envelope with `ok: false`, a stable `code`, and `error.message`/`error.details`.

## Stable Exit Codes

| Code | Meaning |
|---:|---|
| 0 | success |
| 10 | no actionable work |
| 11 | transaction, lock, claim, or resource contention |
| 12 | blocked by a declared safety condition |
| 13 | invalid, stale, released, or mismatched token |
| 14 | gate/checkpoint validation failure |
| 15 | plan/schema/argument validation failure |
| 16 | consistency, projection, database, or unexpected internal failure |

## Commands

- Project: `bootstrap`, `init`, `status`, `doctor`, `export`, `cleanup`
- Plans: `plan validate|diff|apply|scaffold`
- Pickup: `continue`, `claim`, `ready`, `explain`, `context`, `changes`
- Claim lifecycle: `pulse`, `release`, `handoff`, `block`, `complete`
- Graph: `decision set|status`, `checkpoint reach|revoke|status`, `barrier status|explain`
- Contracts: `interface freeze|revise|status`
- Critical sections: `lock acquire|release|status`, `exec --lock ... -- <command>`
- Resources: `resource discover|list|acquire|release|explain`
- Evidence: `gate list|run|explain`; `gate run --required` runs all required gates for the current claim
- Safety: `guard`, `audit`, `reconcile`, `recover inspect|release|adopt`
- Compatibility: `migrate markdown --dry-run|--apply`

`resource discover` is an optional NVIDIA inventory provider. The scheduling tables and commands remain generic.
