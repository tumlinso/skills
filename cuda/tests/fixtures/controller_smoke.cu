#include <cuda_runtime.h>

#include <cstdlib>
#include <iostream>

__global__ void wait_kernel(unsigned long long cycles) {
  const unsigned long long start = clock64();
  while (clock64() - start < cycles) {
  }
}

int main(int argc, char** argv) {
  const int milliseconds = argc > 1 ? std::atoi(argv[1]) : 20;
  cudaDeviceProp properties{};
  if (cudaGetDeviceProperties(&properties, 0) != cudaSuccess) return 2;
  const unsigned long long cycles =
      static_cast<unsigned long long>(properties.clockRate) * milliseconds;
  cudaEvent_t begin{}, end{};
  cudaEventCreate(&begin);
  cudaEventCreate(&end);
  cudaEventRecord(begin);
  wait_kernel<<<1, 1>>>(cycles);
  cudaEventRecord(end);
  if (cudaEventSynchronize(end) != cudaSuccess) return 3;
  float elapsed = 0.0f;
  cudaEventElapsedTime(&elapsed, begin, end);
  std::cout << "{\"latency_ms\":" << elapsed << "}\n";
  cudaEventDestroy(begin);
  cudaEventDestroy(end);
  return 0;
}
