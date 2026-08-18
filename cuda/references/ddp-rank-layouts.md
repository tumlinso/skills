# Rank Layouts

## Rank Order Rule

Prefer logical rank orders that make the fast pairs obvious.

Examples:

- logical `0,1` mapped to physical `0,2`
- logical `2,3` mapped to physical `1,3`

## CPU Affinity Rule

Because the NVLink pairs cross NUMA domains:

- one process per GPU is the safest default
- pin each process near its local GPU
- do not assume one process can be local to both members of an NVLink pair

## Communication Rule

- keep heavy collective or peer traffic inside the pair
- cross-pair traffic should be reduced and infrequent
- benchmark before fixing NCCL env vars permanently
