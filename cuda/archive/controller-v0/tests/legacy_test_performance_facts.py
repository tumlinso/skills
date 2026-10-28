from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest import mock

CUDA_ROOT = Path(__file__).resolve().parents[1]
TODO_ROOT = CUDA_ROOT.parent / "todo-orchestrator"
for value in (CUDA_ROOT / "scripts", TODO_ROOT):
    if str(value) not in sys.path:
        sys.path.insert(0, str(value))

import cuda_controller as controller  # noqa: E402
from cuda_baselines import (  # noqa: E402
    adaptive_correctness_target,
    compatibility_descriptor,
    compatible,
    machine_class,
    profiler_escalation,
    select_baseline,
)
from cuda_facts import FactError, PerformanceFactStore, build_performance_fact  # noqa: E402
from cuda_quiescence import prove_quiescence  # noqa: E402
from todo_orchestrator.background.store import BackgroundStore  # noqa: E402


class FakeMetaStore:
    def __init__(self) -> None:
        self.values: dict[str, object] = {}

    def get_meta(self, key: str, default: object = None) -> object:
        return self.values.get(key, default)

    def set_meta(self, key: str, value: object) -> None:
        self.values[key] = value


def device(identifier: str, index: int = 0) -> dict[str, object]:
    return {
        "uuid": identifier, "index": index, "name": "Tesla V100-SXM2-16GB",
        "compute_capability": "7.0", "memory_total_mib": 16160,
        "pci_bus_id": f"0000:{index + 1:02x}:00.0", "driver_version": "580.65",
    }


def benchmark(**overrides: object) -> dict[str, object]:
    return {
        "argv": ["./bench"], "metric": "latency_ms", "direction": "minimize",
        "warmups": 1, "repetitions": 5,
        "workload_identity": {"kernel": "gemm"}, "input_identity": {"shape": "4096x4096"},
        "build_identity": {"flags": ["-O3"]}, "toolchain_identity": {"nvcc": "12.9"},
        "compatibility": {"shape": "4096x4096", "precision": "fp32"},
        **overrides,
    }


def proof() -> dict[str, object]:
    return {
        "format": "CUDA-QUIESCENCE/1", "schema_version": 1, "state": "quiescent",
        "uncontaminated": True, "device_uuids": ["GPU-a"], "observations": [],
    }


class PerformanceFactsTests(unittest.TestCase):
    def test_incomplete_identity_is_explicitly_non_comparable(self) -> None:
        incomplete = compatibility_descriptor(
            campaign_id="gemm", benchmark={"metric": "latency", "direction": "minimize"},
            machine=machine_class([device("GPU-a")]),
        )
        self.assertFalse(incomplete["complete"])
        self.assertEqual(incomplete["key"], None)
        self.assertEqual(incomplete["missing_identity"], ["build", "inputs", "toolchain", "workload"])
        self.assertFalse(compatible(incomplete, incomplete))
    def test_compatibility_ignores_uuid_index_source_and_candidate_argv(self) -> None:
        first_machine = machine_class([device("GPU-a", 0)], {"GPU-a": {"nvlink_domain": "domain-0", "pcie_root": "0000:01"}})
        second_machine = machine_class([device("GPU-z", 7)], {"GPU-z": {"nvlink_domain": "domain-9", "pcie_root": "0000:ff"}})
        first = compatibility_descriptor(campaign_id="attention", benchmark=benchmark(argv=["./old"]), machine=first_machine)
        candidate = compatibility_descriptor(campaign_id="attention", benchmark=benchmark(argv=["./candidate"]), machine=second_machine)
        self.assertEqual(first["key"], candidate["key"])
        changed_metric = compatibility_descriptor(
            campaign_id="attention", benchmark=benchmark(metric="throughput", direction="maximize"), machine=second_machine,
        )
        self.assertNotEqual(first["key"], changed_metric["key"])

    def test_compatibility_covers_workload_inputs_build_numerics_and_toolchain(self) -> None:
        machine = machine_class([device("GPU-a")])
        base = benchmark(workload_identity={"kernel": "gemm"}, input_identity={"m": 4096},
                         build_identity={"flags": ["-O3"]}, numerical_contract={"rtol": 1e-5},
                         correctness_class="tolerance", toolchain_identity={"nvcc": "12.9"})
        original = compatibility_descriptor(campaign_id="gemm", benchmark=base, machine=machine)["key"]
        for field, value in (("workload_identity", {"kernel": "conv"}), ("input_identity", {"m": 8192}),
                             ("build_identity", {"flags": ["-O2"]}), ("numerical_contract", {"rtol": 1e-3}),
                             ("correctness_class", "statistical"), ("toolchain_identity", {"nvcc": "12.8"})):
            changed = {**base, field: value}
            self.assertNotEqual(original, compatibility_descriptor(campaign_id="gemm", benchmark=changed, machine=machine)["key"])

    def test_topology_shape_is_compatible_but_relationship_change_is_not(self) -> None:
        devices = [device("GPU-a", 0), device("GPU-b", 1)]
        linked = machine_class(devices, {
            "GPU-a": {"nvlink_domain": "one", "pcie_root": "root"},
            "GPU-b": {"nvlink_domain": "one", "pcie_root": "root"},
        })
        split = machine_class(devices, {
            "GPU-a": {"nvlink_domain": "one", "pcie_root": "root-a"},
            "GPU-b": {"nvlink_domain": "two", "pcie_root": "root-b"},
        })
        self.assertNotEqual(
            compatibility_descriptor(campaign_id="multi", benchmark=benchmark(), machine=linked)["key"],
            compatibility_descriptor(campaign_id="multi", benchmark=benchmark(), machine=split)["key"],
        )

    def test_baseline_precedence_and_explicit_acceptance_are_deterministic(self) -> None:
        compatibility = compatibility_descriptor(campaign_id="gemm", benchmark=benchmark(), machine=machine_class([device("GPU-a")]))
        facts = [
            {"fact_id": "historical", "role": "historical", "created_at": 30, "compatibility": compatibility},
            {"fact_id": "previous-new", "role": "previous", "created_at": 20, "compatibility": compatibility},
            {"fact_id": "previous-old", "role": "previous", "created_at": 10, "compatibility": compatibility},
            {"fact_id": "candidate", "role": "candidate", "created_at": 40, "compatibility": compatibility},
            {"fact_id": "accepted", "role": "accepted", "created_at": 1, "compatibility": compatibility},
        ]
        selected = select_baseline(facts, {"compatibility": compatibility})
        self.assertEqual((selected["relation"], selected["fact"]["fact_id"]), ("accepted", "accepted"))
        explicit = select_baseline(facts, {"compatibility": compatibility}, accepted_fact_id="previous-old")
        self.assertEqual((explicit["relation"], explicit["fact"]["fact_id"]), ("accepted", "previous-old"))
        missing = select_baseline(facts, {"compatibility": compatibility}, accepted_fact_id="missing")
        self.assertEqual(missing["status"], "no_compatible_baseline")

    def test_fact_store_preserves_hashed_raw_evidence_and_can_accept(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            stdout = root / "run.stdout.txt"
            stderr = root / "run.stderr.txt"
            stdout.write_text('{"latency_ms": 1.0}\n', encoding="utf-8")
            stderr.write_text("", encoding="utf-8")
            compatibility = compatibility_descriptor(campaign_id="gemm", benchmark=benchmark(), machine=machine_class([device("GPU-a")]))
            fact = build_performance_fact(
                campaign_id="gemm", role="previous", source={"fingerprint": "source", "commit": "abc", "dirty": False},
                compatibility=compatibility, metric="latency_ms", direction="minimize",
                statistics={"median": 1.0, "mad": 0.0, "values": [1.0]}, classification="healthy",
                records=[{"stdout": str(stdout), "stderr": str(stderr)}], quiescence=proof(), created_at=10,
            )
            store = PerformanceFactStore(FakeMetaStore(), "watch")
            stored = store.append(fact)
            self.assertEqual(len(stored["raw_evidence"]), 2)
            self.assertTrue(all(len(item["sha256"]) == 64 for item in stored["raw_evidence"]))
            accepted = store.accept(stored["fact_id"])
            self.assertEqual(accepted["role"], "accepted")
            self.assertEqual(accepted["fact_id"], stored["fact_id"])

    def test_contaminated_or_evidence_free_measurements_do_not_become_facts(self) -> None:
        compatibility = compatibility_descriptor(campaign_id="gemm", benchmark=benchmark(), machine=machine_class([device("GPU-a")]))
        with self.assertRaisesRegex(FactError, "uncontaminated"):
            build_performance_fact(
                campaign_id="gemm", role="previous", source={"fingerprint": "source"}, compatibility=compatibility,
                metric="latency_ms", direction="minimize", statistics={"median": 1.0, "mad": 0.0, "values": [1.0]},
                classification="healthy", records=[], quiescence={**proof(), "uncontaminated": False},
            )

    def test_controller_uses_previous_fact_for_candidate_regression(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = BackgroundStore(root)

            def outcome(value: float, label: str) -> dict[str, object]:
                output = root / f"{label}.stdout.txt"
                error = root / f"{label}.stderr.txt"
                output.write_text(json.dumps({"latency_ms": value}), encoding="utf-8")
                error.write_text("", encoding="utf-8")
                return {
                    "valid": True,
                    "records": [{"stdout": str(output), "stderr": str(error), "metric": value, "returncode": 0, "warmup": False}],
                    "statistics": {"median": value, "mad": 0.0, "values": [value], "included": [0], "excluded": []},
                }

            spec = {"registry_campaign_id": "gemm", "benchmark": benchmark(practical_regression_percent=2.0)}
            first = controller._classify_benchmark(
                store, "watch", spec, outcome(1.0, "first"), "source-a",
                snapshot={"fingerprint": "source-a", "commit": "a", "_fact_role": "previous"},
                devices=[device("GPU-a")], machine=machine_class([device("GPU-a")]), quiescence=proof(),
            )
            second_spec = {"registry_campaign_id": "gemm", "benchmark": benchmark(argv=["./candidate"], practical_regression_percent=2.0)}
            second = controller._classify_benchmark(
                store, "watch", second_spec, outcome(1.1, "second"), "source-b",
                snapshot={"fingerprint": "source-b", "commit": "b", "_fact_role": "candidate"},
                devices=[device("GPU-a")], machine=machine_class([device("GPU-a")]), quiescence=proof(),
            )
            self.assertEqual(first["baseline"]["status"], "absent")
            self.assertEqual(second["classification"], "material-regression")
            self.assertEqual(second["baseline"]["relation"], "previous")
            self.assertAlmostEqual(second["comparison_percent"], 10.0)
            self.assertEqual(second["performance_fact"]["role"], "candidate")

    def test_controller_queues_timeline_only_after_actionable_regression(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            store = BackgroundStore(root)
            watch_id = store.arm_watch({
                "schema_version": 1, "project_root": str(root), "watch": {},
                "benchmark": {**benchmark(practical_regression_percent=2.0), "correctness_argv": ["check"]},
                "policy": {"initial_characterization": False, "max_deep_profiles_per_revision": 2},
            })

            def measured(value: float, label: str) -> dict[str, object]:
                stdout = root / f"{label}.stdout.txt"
                stderr = root / f"{label}.stderr.txt"
                stdout.write_text(json.dumps({"latency_ms": value}), encoding="utf-8")
                stderr.write_text("", encoding="utf-8")
                return {
                    "valid": True,
                    "records": [{"stdout": str(stdout), "stderr": str(stderr), "metric": value, "returncode": 0, "warmup": False}],
                    "statistics": {"median": value, "mad": 0.0, "values": [value], "included": [0], "excluded": []},
                }

            idle = {"idle": True, "busy": False, "foreign_processes": False, "samples": []}
            snapshots = [
                {"safe": True, "source_root": str(source), "fingerprint": "first", "commit": "a"},
                {"safe": True, "source_root": str(source), "fingerprint": "second", "commit": "b"},
            ]
            with mock.patch.object(controller, "_benchmark", side_effect=[measured(1.0, "first"), measured(1.1, "second")]), \
                    mock.patch.object(controller, "_allocated_gpus", return_value=([], [])), \
                    mock.patch.object(controller, "measurement_machine", return_value=([], machine_class([]))), \
                    mock.patch.object(controller, "sample_devices", return_value=idle), \
                    mock.patch.object(controller, "probe_gpus", return_value=[]):
                first = controller.background_stage(root, watch_id, "benchmark", snapshots[0])
                second = controller.background_stage(root, watch_id, "benchmark", snapshots[1])
            self.assertEqual(first["profiler_decision"]["profile"], None)
            self.assertEqual(second["classification"], "material-regression")
            self.assertEqual(second["profiler_decision"]["profile"], "nsys")
            with closing(store.connect(readonly=True)) as connection:
                kinds = [row[0] for row in connection.execute("SELECT kind FROM background_jobs ORDER BY created_at")]
                self.assertEqual(kinds, ["nsys"])

    def test_incomplete_measurement_runs_but_creates_no_reusable_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = BackgroundStore(root)
            stdout = root / "run.stdout.txt"; stderr = root / "run.stderr.txt"
            stdout.write_text('{"latency_ms":1.0}', encoding="utf-8"); stderr.write_text("", encoding="utf-8")
            outcome = {"valid": True, "records": [{"stdout": str(stdout), "stderr": str(stderr),
                "metric": 1.0, "returncode": 0, "warmup": False}],
                "statistics": {"median": 1.0, "mad": 0.0, "values": [1.0], "included": [0], "excluded": []}}
            incomplete = {"registry_campaign_id": "gemm", "benchmark": {
                "argv": ["./bench"], "metric": "latency_ms", "direction": "minimize",
                "warmups": 0, "repetitions": 1,
            }}
            result = controller._classify_benchmark(
                store, "watch", incomplete, outcome, "source",
                snapshot={"fingerprint": "source", "commit": "a"}, devices=[device("GPU-a")],
                machine=machine_class([device("GPU-a")]), quiescence=proof(),
            )
            self.assertFalse(result["comparable"])
            self.assertEqual(result["baseline"]["status"], "non_comparable")
            self.assertNotIn("performance_fact", result)
            self.assertIsNone(store.get_meta("baseline:watch"))
            self.assertEqual(PerformanceFactStore(store, "watch").list(), [])

    def test_post_run_contamination_precedes_fact_baseline_and_profiler_persistence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); source = root / "source"; source.mkdir()
            store = BackgroundStore(root)
            watch_id = store.arm_watch({
                "schema_version": 1, "project_root": str(root), "watch": {},
                "benchmark": {**benchmark(target=0.5), "correctness_argv": ["check"]},
                "policy": {"initial_characterization": False, "max_deep_profiles_per_revision": 2},
            })
            stdout = root / "run.stdout.txt"; stderr = root / "run.stderr.txt"
            stdout.write_text('{"latency_ms": 1.0}', encoding="utf-8"); stderr.write_text("", encoding="utf-8")
            measured = {"valid": True, "records": [{"stdout": str(stdout), "stderr": str(stderr),
                        "metric": 1.0, "returncode": 0, "warmup": False}],
                        "statistics": {"median": 1.0, "mad": 0.0, "values": [1.0]}}
            clean = {**proof(), "observations": [{"idle": True, "busy": False, "foreign_processes": False, "samples": []}]}
            contaminated = {"idle": False, "busy": True, "foreign_processes": True, "samples": []}
            snapshot = {"safe": True, "source_root": str(source), "fingerprint": "source", "commit": "a"}
            with mock.patch.object(controller, "_allocated_gpus", return_value=(["GPU-a"], [0])), \
                    mock.patch.object(controller, "quiescence_proof", return_value=clean), \
                    mock.patch.object(controller, "_benchmark", return_value=measured), \
                    mock.patch.object(controller, "sample_devices", return_value=contaminated), \
                    mock.patch.object(controller, "measurement_machine") as machine_probe, \
                    mock.patch.object(controller, "probe_gpus", return_value=[]):
                result = controller.background_stage(root, watch_id, "benchmark", snapshot)
            self.assertEqual(result["classification"], "measurement-contaminated")
            self.assertNotIn("performance_fact", result)
            self.assertNotIn("profiler_decision", result)
            self.assertIsNone(store.get_meta(f"baseline:{watch_id}"))
            self.assertEqual(PerformanceFactStore(store, watch_id).list(), [])
            machine_probe.assert_not_called()
            with closing(store.connect(readonly=True)) as connection:
                self.assertEqual(connection.execute("SELECT count(*) FROM background_jobs").fetchone()[0], 0)

    def test_controller_refuses_measurement_without_quiescence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            store = BackgroundStore(root)
            watch_id = store.arm_watch({
                "schema_version": 1, "project_root": str(root), "watch": {},
                "benchmark": {**benchmark(), "correctness_argv": ["check"]},
                "policy": {"initial_characterization": False},
            })
            timeout = {
                "format": "CUDA-QUIESCENCE/1", "schema_version": 1, "state": "timeout",
                "uncontaminated": False, "device_uuids": ["GPU-a"],
                "observations": [{"idle": False, "busy": True, "foreign_processes": False, "samples": []}],
            }
            snapshot = {"safe": True, "source_root": str(source), "fingerprint": "source", "commit": "a"}
            with mock.patch.object(controller, "_allocated_gpus", return_value=(["GPU-a"], [0])), \
                    mock.patch.object(controller, "quiescence_proof", return_value=timeout), \
                    mock.patch.object(controller, "_benchmark") as measured:
                result = controller.background_stage(root, watch_id, "benchmark", snapshot)
            measured.assert_not_called()
            self.assertEqual(result["classification"], "gpu-not-quiescent")
            self.assertTrue(result["contaminated"])

    def test_backfill_labels_historical_and_explicitly_accepted_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
            source = root / "kernel.cu"
            source.write_text("// old\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "kernel.cu"], check=True)
            subprocess.run(["git", "-C", str(root), "-c", "user.name=test", "-c", "user.email=test@example.invalid", "commit", "-qm", "old"], check=True)
            old = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
            source.write_text("// new\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "kernel.cu"], check=True)
            subprocess.run(["git", "-C", str(root), "-c", "user.name=test", "-c", "user.email=test@example.invalid", "commit", "-qm", "new"], check=True)
            new = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
            store = BackgroundStore(root)
            watch_id = store.arm_watch({
                "schema_version": 1, "project_root": str(root), "watch": {"paths": ["kernel.cu"]},
                "benchmark": {**benchmark(), "correctness_argv": ["check"]},
                "policy": {"initial_characterization": False},
            })
            with mock.patch.object(controller, "wake_worker"):
                controller.enqueue_supplied_revisions({
                    "schema_version": 1, "project_root": str(root), "watch_id": watch_id,
                    "mappings": [
                        {"task_id": "OLD", "source_revision": old, "todo_revision": 1},
                        {"task_id": "NEW", "source_revision": new, "todo_revision": 2, "accepted_baseline": True},
                    ],
                }, backfill=True)
            with closing(store.connect(readonly=True)) as connection:
                snapshots = [json.loads(row[0]) for row in connection.execute(
                    "SELECT snapshot_json FROM background_jobs WHERE kind='benchmark' ORDER BY todo_revision"
                )]
            self.assertEqual([item["_fact_role"] for item in snapshots], ["historical", "accepted"])

    def test_adaptive_correctness_and_profiler_decisions_are_bounded(self) -> None:
        target = adaptive_correctness_target(
            configured_repetitions=3, minimum_seconds=1.0, maximum_repetitions=20,
            completed_records=[{"elapsed_seconds": 0.1}, {"elapsed_seconds": 0.1}],
        )
        self.assertEqual(target, 10)
        self.assertEqual(profiler_escalation("material-regression")["profile"], "nsys")
        self.assertIsNone(profiler_escalation("severe-variance")["profile"])
        self.assertEqual(
            profiler_escalation("material-regression", timeline_summary={"top_kernels": [{"name": "hot"}]})["profile"],
            "ncu",
        )
        self.assertIsNone(profiler_escalation("material-regression", timeline_summary={"top_kernels": []})["profile"])

    def test_quiescence_requires_consecutive_idle_samples_and_times_out(self) -> None:
        clock = [0.0]

        def monotonic() -> float:
            return clock[0]

        def sleep(value: float) -> None:
            clock[0] += value

        observations = iter([
            {"idle": False, "busy": True, "foreign_processes": False},
            {"idle": True, "busy": False, "foreign_processes": False},
            {"idle": True, "busy": False, "foreign_processes": False},
        ])
        result = prove_quiescence(
            ["GPU-b", "GPU-a"], lambda _: next(observations), timeout_seconds=2,
            consecutive_idle_samples=2, interval_seconds=0.1, monotonic=monotonic, sleep=sleep,
        )
        self.assertTrue(result["uncontaminated"])
        self.assertEqual(result["device_uuids"], ["GPU-a", "GPU-b"])
        self.assertEqual(len(result["observations"]), 3)

        clock[0] = 0
        timeout = prove_quiescence(
            ["GPU-a"], lambda _: {"idle": False, "busy": False, "foreign_processes": True},
            timeout_seconds=0.2, consecutive_idle_samples=2, interval_seconds=0.1,
            monotonic=monotonic, sleep=sleep,
        )
        self.assertEqual(timeout["state"], "timeout")
        self.assertFalse(timeout["uncontaminated"])

    def test_schema_is_present_and_strict(self) -> None:
        schema = json.loads((CUDA_ROOT / "schemas" / "performance-fact-v1.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["properties"]["format"]["const"], "CUDA-PERFORMANCE-FACT/1")
        self.assertFalse(schema["additionalProperties"])


if __name__ == "__main__":
    unittest.main()
