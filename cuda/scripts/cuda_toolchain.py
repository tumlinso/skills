"""Resolve one usable toolkit without trusting a wrapper's selected version."""
from __future__ import annotations
import os
from pathlib import Path
import re
import shutil
import subprocess


def resolve_toolchain(root: str | None = None, *, require_sanitizer: bool = False) -> dict:
    explicit = root or os.environ.get('CUDAToolkit_ROOT') or os.environ.get('CUDA_HOME')
    if not explicit and os.environ.get('CUDACXX'):
        explicit = str(Path(os.environ['CUDACXX']).resolve().parent.parent)
    candidates = [Path(explicit)] if explicit else []
    if not explicit:
        nvcc = os.environ.get('CUDACXX') or shutil.which('nvcc')
        if nvcc:
            candidates.append(Path(nvcc).resolve().parent.parent)
        candidates.extend(sorted(Path('/opt/nvidia/hpc_sdk').glob('Linux_*/[0-9]*/cuda/[0-9]*'), reverse=True))
        candidates.extend([Path('/usr/local/cuda'), Path('/usr')])
    failures = []
    for candidate in dict.fromkeys(candidates):
        compiler = candidate / 'bin/nvcc'
        sanitizers = [candidate / 'bin/compute-sanitizer', candidate / 'compute-sanitizer/compute-sanitizer']
        sanitizer = next((p for p in sanitizers if p.is_file() and os.access(p, os.X_OK)), None)
        try:
            version = subprocess.run([str(compiler), '--version'], capture_output=True, text=True, timeout=10)
            match = re.search(r'release (\d+\.\d+)', version.stdout)
            if version.returncode or not match or (require_sanitizer and sanitizer is None):
                raise ValueError('compiler version or matching sanitizer unavailable')
            if sanitizer:
                check = subprocess.run([str(sanitizer), '--version'], capture_output=True, text=True, timeout=10)
                if check.returncode:
                    raise ValueError('sanitizer executable failed')
            directories = [str(compiler.parent)] + ([str(sanitizer.parent)] if sanitizer else [])
            return {'root': str(candidate.resolve()), 'version': match[1], 'nvcc': str(compiler),
                    'sanitizer': str(sanitizer) if sanitizer else None,
                    'environment': {'CUDACXX': str(compiler), 'CUDAToolkit_ROOT': str(candidate.resolve()),
                                    'PATH': os.pathsep.join(directories + [os.environ.get('PATH', '')])}}
        except (OSError, ValueError, subprocess.TimeoutExpired) as error:
            failures.append(f'{candidate}: {error}')
    raise ValueError('No usable CUDA toolkit: ' + '; '.join(failures))
