#pragma once

__device__ __forceinline__ void inline_hot_fma4(
    const float* px,
    const float* py,
    float& acc0,
    float& acc1,
    float& acc2,
    float& acc3) {
  float x0 = px[0];
  float x1 = px[1];
  float x2 = px[2];
  float x3 = px[3];
  float y0 = py[0];
  float y1 = py[1];
  float y2 = py[2];
  float y3 = py[3];

  asm volatile(
      "{\n\t"
      "fma.rn.f32 %0, %4, %8, %0;\n\t"
      "fma.rn.f32 %1, %5, %9, %1;\n\t"
      "fma.rn.f32 %2, %6, %10, %2;\n\t"
      "fma.rn.f32 %3, %7, %11, %3;\n\t"
      "}\n"
      : "+f"(acc0), "+f"(acc1), "+f"(acc2), "+f"(acc3)
      : "f"(x0), "f"(x1), "f"(x2), "f"(x3), "f"(y0), "f"(y1), "f"(y2), "f"(y3));
}
