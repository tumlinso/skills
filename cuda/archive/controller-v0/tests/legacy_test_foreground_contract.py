"""Foreground execution rejects stale-build specs before acquiring resources."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import cuda_controller as controller
from cuda_toolchain import resolve_toolchain

class ForegroundContractTests(unittest.TestCase):
    def test_top_level_build_is_rejected_before_resource_access(self):
        with patch.object(controller, 'probe_gpus') as probe:
            with self.assertRaisesRegex(ValueError, 'benchmark.build_argv'):
                controller.foreground_run({'argv':['true'], 'build_argv':['false']})
            probe.assert_not_called()

    def test_failed_build_never_acquires_gpu(self):
        with tempfile.TemporaryDirectory() as directory:
            subprocess.run(['git','init','-q',directory],check=True)
            with patch.object(controller, 'probe_gpus') as probe:
                result=controller.foreground_run({'project_root':directory,'argv':['true'],
                    'benchmark':{'build_argv':[sys.executable,'-c','raise SystemExit(7)']}})
            self.assertFalse(result['ok']); self.assertEqual(result['build']['returncode'],7)
            probe.assert_not_called()

    def test_explicit_bad_toolkit_cannot_silently_fall_back(self):
        with patch.dict(os.environ,{'CUDACXX':'/missing/toolkit/bin/nvcc'},clear=True):
            with self.assertRaisesRegex(ValueError,'No usable CUDA toolkit'):
                resolve_toolchain()

    def test_compiler_and_sanitizer_share_validated_toolkit(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'bin').mkdir()
            for name,text in [('nvcc','Cuda compilation tools, release 12.9'),('compute-sanitizer','version 12.9')]:
                path=root/'bin'/name;path.write_text('#!/bin/sh\necho '+repr(text)+'\n');path.chmod(0o755)
            result=resolve_toolchain(str(root),require_sanitizer=True)
            self.assertEqual(result['version'],'12.9')
            self.assertEqual(Path(result['sanitizer']).parent,Path(result['nvcc']).parent)
