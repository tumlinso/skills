# S40 — Nouveau GV100 FIFO

**Version:** Linuxv6.12

**Locator:** GV100 implementation

**Evidence type:** original implementation

**Source:** https://raw.githubusercontent.com/torvalds/linux/v6.12/drivers/gpu/drm/nouveau/nvkm/engine/fifo/gv100.c

Channels, runlists, preemption and engine faults sit below streams; their contract is required for safe command work.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.
