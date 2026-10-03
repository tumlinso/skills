# Benchmark entry points and status

`capability_probe.cpp` is a read-only host C++ CUDA Driver API inventory. It performs no allocations, kernel launches, peer enabling, resets or clock changes. It has **not been compiled or executed in this research session**. Attribute failures remain errors/nulls rather than false hardware facts.

With a CUDA 12.9-compatible development installation and a real installed NVIDIA driver library, a typical Linux build is:

```sh
c++ -std=c++17 -O2 capability_probe.cpp \
  -I"${CUDA_HOME:-/usr/local/cuda}/include" \
  -L"${CUDA_HOME:-/usr/local/cuda}/lib64" -lcuda -o capability_probe
./capability_probe > capability.json
```

Some systems resolve `libcuda` through the system driver path rather than toolkit `lib64`. Do not use a stub library as the runtime driver. Query failures are evidence to investigate. Driver initialization itself may initialize driver/device state; “read-only” means no intentional workload or configuration mutation.

Useful complementary read-only inventory, where installed and permitted:

```sh
nvidia-smi -q -x > nvidia-smi.xml
nvidia-smi topo -m > topology.txt
nvidia-smi nvlink --status > nvlink-status.txt
lspci -tv > pci-tree.txt
numactl --hardware > numa.txt
```

CLI options are version-dependent; retain errors. Do not add reset, ECC changes, clock locking or power-limit modifications as routine setup.

The forty `experiments/E*.md` files are **protocol specifications**, not forty runnable CUDA implementations. They define hypotheses, controlled variables, baselines, confounders and capability gates. Implement only the experiment needed by a design decision. K/F-level experiments are deliberately gated, with no raw pushbuffer/QMD/firmware writer supplied.

`tools/semantic_checks.py` is runnable without CUDA. Its successful results validate exact CPU algebra and coordinate identities only. They do not validate GPU instruction lowering, tensor rounding, memory ordering, progress or performance.
