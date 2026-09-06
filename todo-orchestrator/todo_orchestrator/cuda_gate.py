"""Execute an explicitly GPU-bound gate through the canonical CUDA controller."""
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys


def run(argv: list[str], cwd: Path, environment: dict[str, str], config: dict, timeout: float = 3600) -> subprocess.CompletedProcess:
    skills = environment.get('PROJECT_CONTROL_SKILLS_ROOT')
    if not skills:
        raise ValueError('GPU gate requires the configured Project Control Skills runtime')
    controller = Path(skills) / 'cuda/scripts/cuda_controller.py'
    if not controller.is_file():
        raise ValueError('Canonical CUDA controller is unavailable')
    allowed = {'gpus', 'gpu_uuids', 'cpu_threads', 'isolate_pcie_root', 'isolate_nvlink_domain', 'toolchain', 'build_argv', 'binary_paths'}
    if set(config) - allowed:
        raise ValueError('Unsupported GPU gate fields: ' + ', '.join(sorted(set(config) - allowed)))
    if int(config.get('gpus', 1)) < 1:
        raise ValueError('GPU gates require at least one actual accelerator')
    spec = {'schema_version': 1, 'project_root': str(cwd), 'recipe': 'baseline',
            'campaign_id': 'workflow-required-gate', 'argv': argv, 'timeout': timeout, 'command_cwd': str(cwd),
            'resources': {k: v for k, v in config.items() if k not in {'toolchain', 'build_argv', 'binary_paths'}},
            'toolchain': config.get('toolchain', {'require_sanitizer': True})}
    spec['binary_paths'] = config.get('binary_paths', [])
    if 'build_argv' in config:
        spec['benchmark'] = {'build_argv': config['build_argv']}
    result = subprocess.run([sys.executable, str(controller), 'run', '--spec', '-', '--json'],
                            input=json.dumps(spec), cwd=cwd, env=environment, text=True, capture_output=True)
    try:
        receipt = json.loads(result.stdout)
    except ValueError:
        return subprocess.CompletedProcess(argv, 1, result.stdout, result.stderr + "\nInvalid CUDA controller receipt")
    stdout = Path(receipt['stdout_path']).read_text() if receipt.get('stdout_path') else result.stdout
    stderr = Path(receipt['stderr_path']).read_text() if receipt.get('stderr_path') else result.stderr
    stderr += '\nCUDA gate receipt: ' + json.dumps(receipt, sort_keys=True) + '\n'
    return subprocess.CompletedProcess(argv, 0 if receipt.get('ok') is True and result.returncode == 0 else 1, stdout, stderr)
