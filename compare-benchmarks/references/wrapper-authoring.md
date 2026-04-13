# Wrapper Authoring

Use this reference when implementations A and B do not already expose comparable benchmark entrypoints.

## Wrapper Rule

Wrappers should normalize:

- scenario inputs
- warmup/repeat policy
- correctness checking
- output directory layout
- phase naming

They should not add avoidable work that changes the comparison.

## Wrapper Types

### CLI Wrapper

Use when the implementation is already exposed as a benchmark binary or command-line tool.

Use:

- `scripts/init_cli_wrapper.py`

### Python Wrapper

Use when the implementation is called through Python and needs a thin benchmark harness.

Use:

- `scripts/init_python_wrapper.py`

## Required Wrapper Outputs

Each wrapper should emit:

- `run_config.json`
- `results.json`

Preferred fields:

- implementation name
- scenario id
- warmup/repeats
- correctness status
- stable phase names
- raw metrics and counters

## Phase Naming

Use stable phase names whenever possible:

- `load_or_generate`
- `setup_or_prepare`
- `steady_state_compute`
- `collect_or_finalize`
- `end_to_end`
