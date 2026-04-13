# Component Breakdown

Use this reference when overall timing differs and you need to explain which phase or subsystem caused the gap.

## Core Rule

Do not stop at total runtime.

Each implementation should expose stable phases or components so the comparison can say:

- which phase dominated on side A
- which phase dominated on side B
- which phase explains the largest delta

## Good Component Labels

Good labels are:

- stable across both implementations
- specific enough to explain the gap
- not so fine-grained that the comparison becomes noisy

Examples:

- parse
- preprocess
- transfer
- steady_state_compute
- reduce
- materialize

## Comparison Output

The diff should identify:

- the largest absolute delta
- the largest relative delta
- whether the gap is concentrated or spread across many phases

Use `scripts/diff_component_breakdown.py` to make this concise.
