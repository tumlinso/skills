# Ampere Memory And Topology

Use this route for memory fit, multi-GPU placement, and A100 scaling questions.

## Do First

1. Separate pure memory-fit trouble from communication trouble.
2. If the topology is not yet known, measure the actual machine before locking a
   rank layout.
3. Keep staging and steady-state traffic on the fastest links available.

## Ampere Notes

- larger memory and L2 do not remove the need to budget persistent buffers
- topology assumptions vary widely between PCIe A100, SXM A100, and NVSwitch
- structured sparsity or Tensor Core reformulation can reduce bytes moved, but
  only if the algorithm already matches the path
