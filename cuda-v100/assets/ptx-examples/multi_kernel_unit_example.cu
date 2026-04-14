#include <cuda_runtime.h>

__device__ __forceinline__ float shared_mix(float x, float y) {
  return x * y + x;
}

extern "C" __global__ void kernel_alpha(
    const float* x,
    const float* y,
    float* out,
    int count) {
  unsigned int idx = blockIdx.x * blockDim.x + threadIdx.x;
  if (idx >= static_cast<unsigned int>(count)) {
    return;
  }
  out[idx] = shared_mix(x[idx], y[idx]);
}

namespace split_demo {

__device__ __forceinline__ float beta_only(float v) {
  return v + 1.0f;
}

}  // namespace split_demo

__global__ void kernel_beta(
    const float* x,
    const float* y,
    float* out,
    int count) {
  unsigned int idx = blockIdx.x * blockDim.x + threadIdx.x;
  if (idx >= static_cast<unsigned int>(count)) {
    return;
  }
  float mixed = shared_mix(x[idx], y[idx]);
  out[idx] = split_demo::beta_only(mixed);
}
