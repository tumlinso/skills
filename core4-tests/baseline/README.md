# CORE4 compatibility baseline

This directory captures the public command surfaces and representative JSON
outputs at Git commit `a7c0060eab831871dfe4343d0185cc77dc6ddbbd`, before CORE4 semantic changes.
Absolute paths and live todo revision/task data are explicitly marked volatile.

The three declared baseline suites were each run once through todo-orchestrator:

- todo-orchestrator: 66 tests passed; evidence `bc7dd482-be86-4039-bfe5-8b6ec9d1881d`.
- cuda: 19 tests passed; evidence `c87b3e67-d59a-47ef-a069-5bd9e660cb22`.
- cpp-context-compiler: 48 tests passed; evidence `387e49d4-fbca-4d25-882e-76e7b3b0832f`.

The initial ctxpp baseline failure was
`IntegrationTests.test_new_symbol_in_previously_empty_included_header_routes_via_targeted_refresh`.
The lexical overlay returned the degraded `demo` namespace rather than
`demo::newly_added_api` while reporting `incomplete=false`. CORE4-02A preserved
lexical-only routing for orphaned files but restored one targeted semantic TU
refresh for indexed dependencies. Its focused test and the full 48-test suite
passed; focused evidence is `8e98500b-2ebb-493f-a769-20a5d3604034`.

Help captures can be reproduced without changing repository state:

```bash
python todo-orchestrator/scripts/todo.py --help
cpp-context-compiler/scripts/ctxpp --help
python cuda/scripts/cuda_controller.py --help
```

No GPU, model assets, package installation, or downloads are required by this
baseline.
