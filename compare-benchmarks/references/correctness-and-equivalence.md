# Correctness And Equivalence

Use this reference whenever a comparison might confuse “faster” with “different.”

## Core Rule

Do not declare a winner if the outputs are not equivalent enough for the intended use case.

## Required Checks

Every comparison should record:

- whether correctness passed
- what equivalence policy was used
- whether the policy is exact, tolerant, or structural

## Typical Equivalence Modes

- exact match
- floating-point tolerance
- structural equality with metric tolerance
- checksum or invariant validation

## Output Rule

The summary must say explicitly when:

- correctness failed
- correctness was only partial
- the comparison needs rerun with better validation
