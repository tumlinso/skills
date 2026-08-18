# Hopper Memory And Topology

Use this route for memory fit, multi-GPU placement, and H100 scaling questions.

## Do First

1. Separate pure memory-fit trouble from collective or topology trouble.
2. Measure the actual interconnect before locking a rank layout.
3. Keep collective experiments minimal until the topology hypothesis is clear.

## Hopper Notes

- larger memory does not remove the need to budget persistent activation or
  staging buffers
- NVLink and NVSwitch behavior depend on the actual machine, not the family name
