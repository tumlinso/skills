from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

CUDA_ROOT = Path(__file__).resolve().parents[1]
for value in (CUDA_ROOT / "scripts",):
    if str(value) not in sys.path:
        sys.path.insert(0, str(value))

import cuda_controller as controller  # noqa: E402
from cuda_discovery import discover_campaigns  # noqa: E402
from cuda_registry import (RegistryError, campaign_probe_spec, campaign_watch_spec,
                           normalize_registry)  # noqa: E402


def metric(name: str = "latency_ms") -> dict[str, object]:
    return {
        "format": "CUDA-METRIC/1",
        "schema_version": 1,
        "name": name,
        "path": f"metrics.{name}",
        "direction": "minimize",
        "unit": "ms",
        "practical_regression_percent": 2.0,
        "target": None,
    }


def campaign(identifier: str, *, paths: list[str] | None = None,
             symbols: list[str] | None = None, targets: list[str] | None = None) -> dict[str, object]:
    return {
        "id": identifier,
        "description": identifier,
        "targets": targets or [],
        "paths": paths or [],
        "symbols": symbols or [],
        "task_ids": [],
        "task_prefixes": [],
        "build": {"argv": ["cmake", "--build", "build", "--target", identifier]},
        "correctness": {
            "argv": ["ctest", "--test-dir", "build", "-R", identifier],
            "repetitions": 3,
            "minimum_seconds": 0,
            "maximum_repetitions": 8,
            "class": "tolerance",
            "numerical_contract": {"rtol": 1e-5},
        },
        "benchmark": {"argv": [f"./build/{identifier}", "--json"], "warmups": 1, "repetitions": 5},
        "metric": metric(),
        "resources": {"gpu_count": 1, "architecture": "volta"},
        "policy": {"initial_characterization": False},
        "compatibility": {"workload": {"id": identifier}, "inputs": {"shape": "fixed"},
                          "build": {"configuration": "release"}, "toolchain": {"cuda": "12.x"}},
    }


def registry(*campaigns: dict[str, object], root: str = "/project") -> dict[str, object]:
    return {
        "format": "CUDA-BENCHMARK-REGISTRY/1",
        "schema_version": 1,
        "project_root": root,
        "campaigns": list(campaigns),
    }


class RegistryDiscoveryTests(unittest.TestCase):
    def test_registered_probe_uses_fixed_registry_private_storage_and_free_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "build").mkdir()
            (root / "build" / "probe").write_text("binary", encoding="utf-8")
            item = campaign("probe", paths=["src/probe.cu"])
            item["binary_paths"] = ["build/probe"]
            item["build"] = None
            (root / "cuda-benchmarks.json").write_text(json.dumps(registry(item, root=str(root))), encoding="utf-8")
            facts = [{"id": "accelerator:GPU-A", "kind": "accelerator", "tags": {
                "architecture": "volta", "physical_index": 1, "nvlink_domain": "pair-b", "pcie_bus_id": "0000:02:00.0",
            }}]
            class Store:
                def __init__(self, location): self.paths = type("Paths", (), {"artifacts": Path(location) / "artifacts"})()
                def upsert_resources(self, _): pass
                def result(self, _): return {"summary": {"provenance": {"source": {"commit": "abc"}}, "resource_samples": {"quiescence": {"state": "quiescent"}}}, "artifacts": [{"id": "artifact-1", "path": "/private/nope", "content_hash": "a" * 64, "kind": "stdout", "complete": True}]}
            class Host:
                def upsert(self, _): pass
                def replace(self, _kind, _resources): pass
                def compound_gpu_bundles(self, _): return [{"resource_ids": ["accelerator:GPU-A"]}]
                def conflicts(self, _): return []
            class Runtime:
                def __init__(self, *_args, **_kwargs): self.host = Host()
            captured = {}
            def foreground(spec):
                captured.update(spec)
                return {"ok": True, "evidence_id": "evidence-1"}
            with mock.patch.object(controller, "git_root", side_effect=lambda value: Path(value).resolve()), \
                 mock.patch.object(controller, "BackgroundStore", Store), \
                 mock.patch.object(controller, "RuntimeFacade", Runtime), \
                 mock.patch.object(controller, "probe_gpus", return_value=[]), \
                 mock.patch.object(controller, "resource_facts", return_value=facts), \
                 mock.patch.object(controller, "foreground_run", side_effect=foreground), \
                 mock.patch.dict("os.environ", {"PROJECT_CONTROL_PERFORMANCE_PROBE_STATE_DIR": str(root / "private")}, clear=False):
                result = controller.registered_foreground_probe(project_root=root, campaign_id="probe")
            self.assertTrue(result["registered"])
            self.assertEqual(captured["argv"], ["./build/probe", "--json"])
            self.assertEqual(captured["_priority_class"], "idle_model_residency")
            self.assertEqual(captured["preempt_grace_seconds"], 0)
            self.assertTrue(str(captured["_storage_root"]).startswith(str(root / "private")))
            self.assertEqual(result["probe"]["placement"]["gpu_uuids"], ["GPU-A"])
            self.assertEqual(result["probe"]["placement"]["nvlink_domains"], ["pair-b"])
            self.assertNotIn("path", result["probe"]["artifacts"][0])

    def test_probe_compiles_only_declared_typed_parameters_and_registered_binary(self) -> None:
        value = campaign("probe", paths=["src/probe.cu"])
        value.update({
            "binary_paths": ["build/probe-{parameter:size}"],
            "parameters": {
                "size": {"type": "integer", "minimum": 1, "maximum": 64, "default": 8},
                "tier": {"type": "enum", "values": {"small": "small", "large": "large"}, "default": "small"},
                "dataset": {"type": "dataset", "source": "fixture", "default": "tiny"},
            },
            "datasets": {"fixture": {"root": "data", "entries": {"tiny": "tiny.bin"}}},
        })
        value["benchmark"]["argv"] = ["./build/probe-{parameter:size}", "--tier={parameter:tier}", "--data={parameter:dataset}"]
        normalized = normalize_registry(registry(value))
        probe = campaign_probe_spec(normalized, "probe", mode="benchmark", parameters={"size": 16})
        self.assertEqual(probe["argv"], ["./build/probe-16", "--tier=small", "--data=data/tiny.bin"])
        self.assertEqual(probe["binary_paths"], ["build/probe-16"])
        self.assertEqual(probe["inputs"], ["data/tiny.bin"])
        self.assertFalse("benchmark" in probe)
        with self.assertRaisesRegex(RegistryError, "undeclared"):
            campaign_probe_spec(normalized, "probe", mode="benchmark", parameters={"other": 1})
        with self.assertRaisesRegex(RegistryError, "registered dataset"):
            broken = registry(campaign("broken", paths=["a.cu"]))
            broken["campaigns"][0]["parameters"] = {"data": {"type": "dataset", "source": "missing"}}
            normalize_registry(broken)

    def test_probe_requires_registered_binary_and_rebuild_is_opt_in(self) -> None:
        normalized = normalize_registry(registry(campaign("missing-binary", paths=["a.cu"])))
        with self.assertRaisesRegex(RegistryError, "binary_paths"):
            campaign_probe_spec(normalized, "missing-binary", mode="benchmark")
        value = campaign("built", paths=["a.cu"])
        value["binary_paths"] = ["build/built"]
        value["build"] = None
        normalized = normalize_registry(registry(value))
        with self.assertRaisesRegex(RegistryError, "no registered build"):
            campaign_probe_spec(normalized, "built", mode="benchmark", rebuild=True)

    def test_probe_stdin_contract_rejects_arbitrary_fields(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown fields"):
            controller.probe_request({"schema_version": 1, "project_root": "/project", "campaign": "x", "argv": ["sh"]})

    def test_deterministic_correctness_defaults_to_one_cheap_run(self) -> None:
        value = registry(campaign("deterministic-default", paths=["src/check.cu"]))
        value["campaigns"][0]["correctness"] = {
            "argv": ["./check"], "class": "deterministic",
        }
        normalized = normalize_registry(value)
        correctness = normalized["campaigns"][0]["correctness"]
        self.assertEqual((correctness["repetitions"], correctness["minimum_seconds"],
                          correctness["maximum_repetitions"]), (1, 0.0, 1))
    def test_registry_validates_and_compiles_to_legacy_watch_contract(self) -> None:
        normalized = normalize_registry(registry(campaign(
            "attention", paths=["src/attention/**/*.cu"], symbols=["c:@F@attention#"], targets=["attention"],
        )))
        watch = campaign_watch_spec(normalized, normalized["campaigns"][0])
        self.assertEqual(watch["schema_version"], 1)
        self.assertEqual(watch["watch"]["paths"], ["src/attention/**/*.cu"])
        self.assertEqual(watch["benchmark"]["metric"], "metrics.latency_ms")
        self.assertEqual(watch["benchmark"]["architecture"], "volta")
        self.assertEqual(watch["benchmark"]["build_argv"][-1], "attention")
        self.assertEqual(watch["benchmark"]["correctness_class"], "tolerance")
        controller.validate_watch_spec(watch)

    def test_registry_rejects_duplicate_ids_unsafe_paths_and_unknown_fields(self) -> None:
        with self.assertRaisesRegex(RegistryError, "ids must be unique"):
            normalize_registry(registry(campaign("same", paths=["a.cu"]), campaign("same", paths=["b.cu"])))
        unsafe = campaign("unsafe", paths=["../outside.cu"])
        with self.assertRaisesRegex(RegistryError, "safe repository-relative"):
            normalize_registry(registry(unsafe))
        unknown = campaign("unknown", paths=["kernel.cu"])
        unknown["guess"] = True
        with self.assertRaisesRegex(RegistryError, "unknown fields"):
            normalize_registry(registry(unknown))

    def test_all_supported_evidence_sources_match(self) -> None:
        symbol_id = "c:@N@demo@F@fused_attention#"
        value = registry(campaign(
            "attention", paths=["src/attention/**"], symbols=[symbol_id], targets=["attention-bench"],
        ))
        packet = {
            "format": "CTXPP-CONTEXT-PACKET/1",
            "readonly": True,
            "target": {"id": symbol_id, "name": "demo::fused_attention", "signature": "void()"},
        }
        result = discover_campaigns(value, {
            "schema_version": 1,
            "changed_paths": ["src/attention/kernel.cu"],
            "todo_scopes": ["src/attention"],
            "accepted_patches": [
                {"accepted": False, "changed_paths": ["ignored.cu"]},
                {"accepted": True, "changed_paths": ["src/attention/dispatch.cu"]},
            ],
            "context_packets": [packet],
            "targets": ["attention-bench"],
        })
        self.assertEqual(result["status"], "unambiguous")
        sources = {item["source"] for item in result["matches"][0]["reasons"]}
        self.assertEqual(sources, {"changed_path", "todo_scope", "accepted_patch", "ctxpp_symbol", "target"})
        self.assertNotIn("ignored.cu", json.dumps(result))

    def test_todo_glob_scope_overlaps_a_specific_campaign_path(self) -> None:
        result = discover_campaigns(
            registry(campaign("kernel", paths=["src/kernel.cu"])),
            {"todo_scopes": ["src/**"]},
        )
        self.assertEqual(result["status"], "unambiguous")
        self.assertEqual(result["matches"][0]["reasons"][0]["source"], "todo_scope")

    def test_discovery_is_deterministic_and_ambiguity_never_selects(self) -> None:
        value = registry(
            campaign("second", paths=["src/**/*.cu"]),
            campaign("first", paths=["src/kernel.cu"]),
        )
        forward = discover_campaigns(value, {"changed_paths": ["src/kernel.cu"]})
        reverse = discover_campaigns(value, {"changed_paths": ["src/kernel.cu"]})
        self.assertEqual(forward, reverse)
        self.assertEqual(forward["status"], "ambiguous")
        self.assertFalse(forward["auto_queue_safe"])
        self.assertNotIn("selected_campaign_id", forward)
        self.assertNotIn("watch_spec", forward)
        self.assertEqual([item["campaign_id"] for item in forward["matches"]], ["first", "second"])

    def test_controller_auto_queue_arms_only_one_unambiguous_campaign(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            registry_path = Path(temporary) / "registry.json"
            registry_path.write_text(json.dumps(registry(
                campaign("first", paths=["src/kernel.cu"]),
                campaign("second", paths=["src/**/*.cu"]),
            )), encoding="utf-8")
            with mock.patch.object(controller, "arm_background") as arm:
                ambiguous = controller.registry_discover(
                    str(registry_path), {"changed_paths": ["src/kernel.cu"]}, auto_queue=True,
                )
            arm.assert_not_called()
            self.assertEqual(ambiguous["auto_queue"], {"state": "not_queued", "reason": "ambiguous"})

            registry_path.write_text(json.dumps(registry(
                campaign("first", paths=["src/kernel.cu"]),
                campaign("second", paths=["other/**/*.cu"]),
            )), encoding="utf-8")
            with mock.patch.object(controller, "arm_background", return_value={
                "schema_version": 1, "watch_id": "watch", "state": "armed", "initial_jobs_queued": 2,
            }) as arm:
                selected = controller.registry_discover(
                    str(registry_path), {"changed_paths": ["src/kernel.cu"]}, auto_queue=True,
                )
            arm.assert_called_once()
            self.assertEqual(selected["selected_campaign_id"], "first")
            self.assertEqual(selected["auto_queue"]["state"], "queued")
            self.assertEqual(selected["auto_queue"]["controller"]["state"], "armed")
            self.assertEqual(selected["auto_queue"]["controller"]["watch_id"], "watch")

    def test_schemas_and_controller_subcommands_are_available(self) -> None:
        for name in ("benchmark-registry-v1.schema.json", "metric-v1.schema.json"):
            payload = json.loads((CUDA_ROOT / "schemas" / name).read_text(encoding="utf-8"))
            self.assertEqual(payload["$schema"], "https://json-schema.org/draft/2020-12/schema")
        validate = controller.parser().parse_args(["registry", "validate", "--registry", "registry.json", "--json"])
        discover = controller.parser().parse_args(["registry", "discover", "--file", "registry.json", "--auto-queue"])
        self.assertEqual(validate.registry_command, "validate")
        self.assertTrue(discover.auto_queue)


if __name__ == "__main__":
    unittest.main()
