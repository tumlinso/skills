# S30 — CUDA C++ Programming Guide

**Version:** CUDA 12.9.1

**Locator:** memory model; texture; cooperative launch; CDP; feature tables

**Evidence type:** primary

**Source:** https://docs.nvidia.com/cuda/archive/12.9.1/cuda-c-programming-guide/index.html

Participation, ordering and progress are separate requirements. Streams need not run concurrently. Legacy atomics are not general acquire/release fences. Later cp.async, ldmatrix, mbarrier, clusters, TMA, DPX, TF32/BF16 tensor modes and L2-persistence controls must not be imported into ordinary sm70 designs.

This is a short evidence capsule, not a redistributed source. Source behavior does not automatically establish local performance or a public interface. Accessed 2026-10-03.
