#include <cuda_runtime.h>

#include "inline_hot_path.cuh"

extern "C" __global__ void inline_hot_path_kernel(
    const float* x,
    const float* y,
    float* out,
    int groups) {
  unsigned int idx = blockIdx.x * blockDim.x + threadIdx.x;
  if (idx >= static_cast<unsigned int>(groups)) {
    return;
  }

  const float* px = x + idx * 4;
  const float* py = y + idx * 4;

  float acc0 = 0.0f;
  float acc1 = 0.0f;
  float acc2 = 0.0f;
  float acc3 = 0.0f;

  inline_hot_fma4(px, py, acc0, acc1, acc2, acc3);

  out[idx] = acc0 + acc1 + acc2 + acc3;
}
