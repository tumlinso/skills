from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SKILLS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SKILLS / "todo-orchestrator"))

from todo_orchestrator.runtime import RuntimeFacade, discover_gpu_topology


class Core4TopologyTests(unittest.TestCase):
    def test_discovery_records_optional_pcie_and_live_capacity_facts(self) -> None:
        outputs = iter([
            "0, GPU-a, 00000000:02:00.0, 3, 8, 15000, 2\n1, GPU-b, 00000000:03:00.0, 3, 8, 14000, 4\n",
            "\tGPU0\tGPU1\tCPU Affinity\tNUMA Affinity\tGPU NUMA ID\n"
            "GPU0\tX\tNV6\t0-19\t0\tN/A\nGPU1\tNV6\tX\t0-19\t0\tN/A\n",
        ])
        resources = discover_gpu_topology(lambda argv: next(outputs))
        tags = resources[0]["tags"]
        self.assertEqual((tags["pcie_generation_current"], tags["pcie_link_width_current"]), ("3", "8"))
        self.assertEqual((tags["memory_free_mib"], tags["utilization_percent"]), ("15000", "2"))

    def test_bundle_order_prefers_numa_local_then_capacity_without_indices(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            facade = RuntimeFacade(temporary)
            facade.host.upsert([
                {"id": "accelerator:GPU-a", "tags": {"nvlink_domain": "island-a", "pcie_root": "r0", "numa_node": "0", "memory_free_mib": "12000", "utilization_percent": "2"}},
                {"id": "accelerator:GPU-b", "tags": {"nvlink_domain": "island-a", "pcie_root": "r0", "numa_node": "0", "memory_free_mib": "12000", "utilization_percent": "2"}},
                {"id": "accelerator:GPU-c", "tags": {"nvlink_domain": "island-b", "pcie_root": "r1", "numa_node": "1", "memory_free_mib": "8000", "utilization_percent": "0"}},
                {"id": "accelerator:GPU-d", "tags": {"nvlink_domain": "island-b", "pcie_root": "r1", "numa_node": "1", "memory_free_mib": "8000", "utilization_percent": "0"}},
            ])
            bundles = facade.host.compound_gpu_bundles(2)
            self.assertEqual(bundles[0]["resource_ids"], ["accelerator:GPU-a", "accelerator:GPU-b"])
            self.assertTrue(bundles[0]["selection"]["numa_local"])


if __name__ == "__main__":
    unittest.main()
