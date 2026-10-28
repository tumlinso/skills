"""CPU-only ABI and physical mapping checks; no CUDA initialization or allocation."""
import ctypes
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import qualify_observer_residency as qualification

FIRST = 'GPU-cf22c41f-5b58-77b1-3535-8fadd1ca6505'
SECOND = 'GPU-6c1cac7f-a360-0aef-ba98-2828bfd1db1a'
ROWS = [dict(uuid=FIRST, pci_bus_id='00000000:03:00.0', index=1, mig_mode='[N/A]'),
        dict(uuid=SECOND, pci_bus_id='00000000:84:00.0', index=3, mig_mode='Disabled')]


class QualificationMappingTests(unittest.TestCase):
    def test_hex_normalization_and_exact_logical_order(self):
        self.assertEqual(qualification.normalize_pci_bus_id('0000:0A:1f.7'), '00000000:0a:1f.7')
        self.assertEqual(qualification.map_runtime_devices(['0000:03:00.0', '0000:84:00.0'], ROWS,
                         [FIRST, SECOND], ['1', '3']), [FIRST, SECOND])

    def test_malformed_pci_rejected(self):
        for value in ('03:00.0', '0000:03:00', '0000:03:20.0', '0000:03:00.8', '0000:gg:00.0', ' 0000:03:00.0'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                qualification.normalize_pci_bus_id(value)

    def test_ambiguous_duplicate_pci_or_uuid_rejected(self):
        for extra in (dict(ROWS[0]), dict(ROWS[1], pci_bus_id=ROWS[0]['pci_bus_id'])):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                qualification.map_runtime_devices(['0000:03:00.0', '0000:84:00.0'], ROWS + [extra],
                                                  [FIRST, SECOND], ['1', '3'])

    def test_foreign_order_visible_order_and_mig_rejected(self):
        cases = [(ROWS, [SECOND, FIRST], ['1', '3']), (ROWS, [FIRST, SECOND], ['3', '1']),
                 ([dict(ROWS[0], uuid='GPU-11111111-1111-1111-1111-111111111111'), ROWS[1]], [FIRST, SECOND], ['1', '3']),
                 ([dict(ROWS[0], mig_mode='Enabled'), ROWS[1]], [FIRST, SECOND], ['1', '3']),
                 ([dict(ROWS[0], uuid='MIG-' + FIRST), ROWS[1]], [FIRST, SECOND], ['1', '3'])]
        for rows, expected, visible in cases:
            with self.subTest(rows=rows, expected=expected, visible=visible), self.assertRaises(ValueError):
                qualification.map_runtime_devices(['0000:03:00.0', '0000:84:00.0'], rows, expected, visible)

    def test_required_installed_symbols_bind_without_any_cuda_call(self):
        library = qualification.bind_cuda_runtime(ctypes.CDLL('/usr/lib/x86_64-linux-gnu/libcudart.so.12.0.146'))
        self.assertEqual(library.cudaDeviceGetPCIBusId.argtypes,
                         [ctypes.POINTER(ctypes.c_char), ctypes.c_int, ctypes.c_int])
        self.assertIs(library.cudaDeviceGetPCIBusId.restype, ctypes.c_int)

    def test_missing_symbol_fails_without_runtime_call(self):
        library = Mock()
        del library.cudaDeviceGetPCIBusId
        with self.assertRaises(AttributeError):
            qualification.bind_cuda_runtime(library)
        library.cudaRuntimeGetVersion.assert_not_called()

    def test_invalid_mapping_fails_before_allocation(self):
        import local_worker.residency
        library = Mock()
        library.cudaRuntimeGetVersion.side_effect = lambda p: (setattr(p._obj, 'value', 12000) or 0)
        library.cudaGetDeviceCount.side_effect = lambda p: (setattr(p._obj, 'value', 2) or 0)
        library.cudaDeviceGetPCIBusId.side_effect = lambda p, length, device: (setattr(p, 'value',
                          [b'0000:03:00.0', b'0000:84:00.0'][device]) or 0)
        bad_rows = 'GPU-11111111-1111-1111-1111-111111111111, 00000000:03:00.0, 1, Disabled\n' + SECOND + ', 00000000:84:00.0, 3, Disabled\n'
        with tempfile.TemporaryDirectory() as directory:
            receipt = Path(directory) / 'lease.json'
            receipt.write_text(json.dumps({'resource_ids': ['accelerator:' + FIRST, 'accelerator:' + SECOND]}))
            environment = {'CUDA_VISIBLE_DEVICES': '1,3', 'TODO_GPU_LEASE_RECEIPT': str(receipt),
                           'CUDA_RUNTIME_LIBRARY': __file__, 'CUDA_RUNTIME_LIBRARY_SHA256': qualification.digest(__file__)}
            with patch.dict(os.environ, environment), patch.object(qualification.ctypes, 'CDLL', return_value=library), \
                 patch.object(local_worker.residency, 'observe_residency', return_value={'available': True}), \
                 patch.object(qualification.subprocess, 'run', return_value=Mock(stdout=bad_rows)), \
                 self.assertRaises(ValueError):
                qualification.foreground_check()
        library.cudaMalloc.assert_not_called()
        library.cudaSetDevice.assert_not_called()

    def test_pci_api_error_fails_before_allocation(self):
        import local_worker.residency
        library = Mock()
        library.cudaRuntimeGetVersion.side_effect = lambda p: (setattr(p._obj, 'value', 12000) or 0)
        library.cudaGetDeviceCount.side_effect = lambda p: (setattr(p._obj, 'value', 2) or 0)
        library.cudaDeviceGetPCIBusId.return_value = 10
        with tempfile.TemporaryDirectory() as directory:
            receipt = Path(directory) / 'lease.json'
            receipt.write_text(json.dumps({'resource_ids': ['accelerator:' + FIRST, 'accelerator:' + SECOND]}))
            with patch.dict(os.environ, {'CUDA_VISIBLE_DEVICES': '1,3', 'TODO_GPU_LEASE_RECEIPT': str(receipt),
                     'CUDA_RUNTIME_LIBRARY': __file__, 'CUDA_RUNTIME_LIBRARY_SHA256': qualification.digest(__file__)}), \
                 patch.object(qualification.ctypes, 'CDLL', return_value=library), \
                 patch.object(local_worker.residency, 'observe_residency', return_value={'available': True}), \
                 self.assertRaises(AssertionError):
                qualification.foreground_check()
        library.cudaMalloc.assert_not_called()


if __name__ == '__main__':
    unittest.main()
