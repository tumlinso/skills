# S01 — NVIDIA Volta Tuning Guide

**Version:** retrieved13.4, 2026-10-03

**Locator:** §1.4.1–1.4.6

**Evidence type:** primary

**Source:** https://docs.nvidia.com/cuda/volta-tuning-guide/index.html

Four static warp-scheduler sets per SM;64 FP32,32 FP64,64 INT32,8 tensor units. Core FMA dependence latency4 cycles. Limits:64 warps,64 K 32-bit registers,255 registers/thread,32 CTAs,96 KB shared per SM. Combined shared/L1/texture128 KB. Independent-thread scheduling needs explicit synchronization. MPS supports separate VAs but not fatal-fault isolation. INT/FP overlap does not imply all resource peaks add.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.
