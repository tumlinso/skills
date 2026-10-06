"""Offline contract tests for campaign aggregation and resume safety."""

from __future__ import annotations

import importlib.util
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

RUNNER = Path(__file__).resolve().parents[1] / "benchmarks" / "run_suite.py"
SPEC = importlib.util.spec_from_file_location("atlas_suite_runner", RUNNER)
assert SPEC and SPEC.loader
suite = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(suite)


class SuiteContractTests(unittest.TestCase):
    def test_executed_invalid_case_fails_but_unsupported_skip_does_not(self) -> None:
        failed = {"cases": [{"experiment": "E06", "status": "GPU_RUN",
                             "checks": {"valid": False}}]}
        cases, valid = suite.normalize_cases(failed, "E06")
        self.assertEqual(len(cases), 1)
        self.assertFalse(valid)
        skipped = {"cases": [{"experiment": "E06", "status": "NOT_RUN",
                              "checks": {"valid": False}, "limitations": ["unsupported"]}]}
        _, valid = suite.normalize_cases(skipped, "E06")
        self.assertTrue(valid)

    def test_runner_p95_uses_nearest_rank(self) -> None:
        self.assertEqual(suite.percentile95(list(range(1, 31))), 29)
        self.assertEqual(suite.percentile95([7.5]), 7.5)

    def test_resume_requires_exact_campaign_key(self) -> None:
        previous = {"campaign_key": "source-binary-config-machine-A"}
        self.assertTrue(suite.resume_compatible(previous, "source-binary-config-machine-A"))
        self.assertFalse(suite.resume_compatible(previous, "source-binary-config-machine-B"))
        self.assertFalse(suite.resume_compatible(previous, "source-changed"))

    def test_resume_reuses_only_correctness_qualified_completed_dispositions(self) -> None:
        entry = {"nsys_eligible": False}
        valid_gpu = {"status": "GPU_RUN", "correctness": {"valid": True}}
        self.assertTrue(suite.result_complete_for_resume(valid_gpu, entry, "focused"))
        for status in ("INCONCLUSIVE", "NOT_RUN", "REJECTED", "COMPILED_ONLY"):
            self.assertFalse(suite.result_complete_for_resume(
                {"status": status, "correctness": {"valid": True}}, entry, "focused"))
        self.assertFalse(suite.result_complete_for_resume(
            {"status": "GPU_RUN", "correctness": {"valid": None}}, entry, "focused"))

    def test_dependency_failure_includes_cpu_reference_failure(self) -> None:
        matrix = {"experiments": {"E39": {"depends_on": ["E01"]}}}
        results = {"E01": {"status": "CPU_ONLY", "samples": [
            {"status": "CPU_ONLY", "checks": {"valid": False}}]}}
        self.assertEqual(suite.dependency_failures("E39", results, matrix), ["E01"])
        results["E01"]["samples"][0]["checks"]["valid"] = True
        self.assertEqual(suite.dependency_failures("E39", results, matrix), [])

    def test_timeout_or_missing_stdout_is_not_a_pass(self) -> None:
        self.assertIn("timed out", suite.capture_problem({"ok": False, "timeout": True}, None))
        self.assertIn("missing", suite.capture_problem({"ok": True}, None))
        self.assertIsNone(suite.capture_problem({"ok": True}, {"cases": [{"experiment": "E02"}]}))

    def test_partial_profiler_failure_marks_result_inconclusive(self) -> None:
        status, reason = suite.profile_failure("GPU_RUN", {"ok": False, "code": "permission_denied"}, "nsys")
        self.assertEqual(status, "INCONCLUSIVE")
        self.assertIn("nsys", reason)
        self.assertEqual(suite.profile_failure("GPU_RUN", {"ok": True}, "ncu"), ("GPU_RUN", None))

    def test_profiler_success_requires_nonempty_report_and_validated_summary(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            stdout = root / "stdout.txt"
            stdout.write_text("wrapper output", encoding="utf-8")
            nsys = root / "nsys/run"
            nsys.mkdir(parents=True)
            (nsys / "report.nsys-rep").write_bytes(b"timeline")
            db = sqlite3.connect(nsys / "report.sqlite")
            db.execute("CREATE TABLE CUPTI_ACTIVITY_KIND_KERNEL (start INTEGER)")
            db.execute("INSERT INTO CUPTI_ACTIVITY_KIND_KERNEL VALUES (1)")
            db.commit(); db.close()
            (nsys / "summary.json").write_text(json.dumps({"status": "partial", "trace_valid": True}))
            valid, evidence = suite.validate_profile_artifacts("nsys", {"ok": True, "stdout_path": str(stdout)})
            self.assertTrue(valid)
            self.assertTrue(evidence["trace_has_gpu_work"])
            ncu = root / "ncu/run"
            ncu.mkdir(parents=True)
            (ncu / "report.ncu-rep").write_bytes(b"counters")
            (ncu / "raw.csv").write_text("Kernel Name,Instances\nkernel,12\n", encoding="utf-8")
            (ncu / "summary.json").write_text(json.dumps({"status": "partial", "counter_valid": True,
                                                           "timing_valid": False}))
            valid, evidence = suite.validate_profile_artifacts("ncu", {"ok": True, "stdout_path": str(stdout)})
            self.assertTrue(valid)
            self.assertTrue(evidence["counter_valid"])
            (ncu / "raw.csv").write_text("", encoding="utf-8")
            self.assertFalse(suite.validate_profile_artifacts("ncu", {"ok": True, "stdout_path": str(stdout)})[0])

    def test_profile_report_validity_uses_receipt_flags_not_display_text(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "results.json").write_text("{}", encoding="utf-8")
            results = {"E20": {"samples": [
                {"variant": "copy-only", "profiles": {"nsys": {
                    "trace_has_gpu_work": True,
                    "summary": {"trace_valid": False, "status": "rerun", "measurement_scope": "timeline only"},
                    "sqlite_activity_counts": {"kernels": 0, "memcpy": 110, "memset": 0}}}},
                {"variant": "no-gpu-work", "profiles": {"nsys": {
                    "trace_has_gpu_work": False,
                    "summary": {"trace_valid": True, "status": "partial"},
                    "sqlite_activity_counts": {"kernels": 0, "memcpy": 0, "memset": 0}}}}]},
                "E09": {"samples": [{"variant": "empty-counters", "profiles": {"ncu": {
                    "counter_valid": False, "summary": {"counter_valid": True, "status": "partial"}}}}]}}
            lines, records = suite.atlas_report.profile_rows(results, root)
            validity = {(r["experiment"], r["variant"]): r["valid"] for r in records}
            self.assertTrue(validity[("E20", "copy-only")])
            self.assertFalse(validity[("E20", "no-gpu-work")])
            self.assertFalse(validity[("E09", "empty-counters")])
            self.assertTrue(any("memcpy rows=110" in line for line in lines))

    def test_report_dispositions_link_to_preserved_protocol_writeups(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run = Path(td)
            results = {f"E{i:02d}": suite.disposition(f"E{i:02d}", "NOT_RUN") for i in range(40)}
            (run / "results.json").write_text(json.dumps(results), encoding="utf-8")
            (run / "run_config.json").write_text(json.dumps({"campaign_key": "fixture", "experiments": []}), encoding="utf-8")
            (run / "summary.json").write_text(json.dumps({"complete": False, "selected_complete": False}), encoding="utf-8")
            (run / "build.json").write_text(json.dumps({"build": {"returncode": 0}}), encoding="utf-8")
            markdown, _ = suite.atlas_report.render(run)
            for i in range(40):
                experiment = f"E{i:02d}"
                self.assertIn(f"[{experiment}](../../experiments/{experiment}.md)", markdown)
            self.assertIn("preserve their authoring provenance", markdown)

    def test_result_schema_matches_all_forty_dispositions(self) -> None:
        results = {f"E{i:02d}": suite.disposition(f"E{i:02d}", "NOT_RUN") for i in range(40)}
        suite.validate_result_records(results)
        results["E02"]["unexpected"] = True
        with self.assertRaises(ValueError):
            suite.validate_result_records(results)

    def test_unknown_case_status_is_rejected(self) -> None:
        payload = {"cases": [{"experiment": "E02", "status": "PASSED"}]}
        with self.assertRaises(ValueError):
            suite.normalize_cases(payload, "E02")

    def test_full_e39_matrix_covers_reuse_and_boundary_oracles(self) -> None:
        matrix = suite.load_matrix()
        cases = matrix["experiments"]["E39"]["cases"]
        self.assertEqual({case["iterations"] for case in cases}, {1, 8, 64})
        self.assertTrue({1, 31, 32, 33, 1023, 1024, 65536, 1048576}.issubset(
            {case["size"] for case in cases}))
        self.assertIn("carry-heavy", {case["pattern"] for case in cases})

    def test_focused_capture_matrix_avoids_boundary_only_and_covers_peer_routes(self) -> None:
        matrix = suite.load_matrix()["experiments"]
        e20 = suite.focused_profile_indices("E20", matrix["E20"], matrix["E20"]["cases"])
        self.assertEqual(e20, {0, 1})
        e39_cases = matrix["E39"]["cases"]
        e39 = suite.focused_profile_indices("E39", matrix["E39"], e39_cases)
        self.assertEqual(e39, {20})
        self.assertGreater(e39_cases[next(iter(e39))]["size"], 1)

    def test_full_mode_requires_thirty_unprofiled_timing_samples(self) -> None:
        self.assertIn("fewer than 30", suite.full_timing_sample_problem(
            {"samples": {"event_ms": [1.0] * 29}}))
        self.assertIsNone(suite.full_timing_sample_problem(
            {"samples": {"event_ms": [1.0] * 30}}))

    def test_e32_uses_distinct_cdp_binary_and_records_sanitizer_scope(self) -> None:
        entry = suite.load_matrix()["experiments"]["E32"]
        cdp = next(case for case in entry["cases"] if case.get("sanitizer") == "cdp")
        argv = suite.child_argv(entry, "E32", verify=True, size=cdp["size"],
                                iterations=cdp["iterations"], warmup=0, repeats=1,
                                variant=cdp["variant"], target=cdp["target"])
        self.assertEqual(argv[0], str(suite.BUILD / "bin" / "atlas_transport_cdp"))
        self.assertIn("device_side_child_launch_pipeline", argv)
        self.assertEqual(entry["cases"][0].get("target"), None)

    def test_e20_all_twelve_directed_peers_reach_child_argv(self) -> None:
        entry = suite.load_matrix()["experiments"]["E20"]
        pairs = set()
        for case in entry["cases"]:
            device, peer = suite.lease_ordinals(case, "all", 4)
            argv = suite.child_argv(entry, "E20", verify=True, size=case["size"],
                                    iterations=case["iterations"], warmup=0, repeats=1,
                                    device=device, peer=peer)
            self.assertEqual(int(argv[argv.index("--device") + 1]), device)
            self.assertEqual(int(argv[argv.index("--peer") + 1]), peer)
            pairs.add((device, peer))
        self.assertEqual(len(entry["cases"]), 12)
        self.assertEqual(pairs, {(src, dst) for src in range(4) for dst in range(4) if src != dst})
        with self.assertRaises(ValueError):
            suite.lease_ordinals({"device": 3, "peer": 4}, "all", 4)

    def test_sanitizer_gate_rejects_success_exit_with_reported_errors(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "sanitizer/run").mkdir(parents=True)
            stdout = root / "foreground.stdout.txt"
            stdout.write_text("Compute Sanitizer summary: sanitizer/run/summary.txt\n", encoding="utf-8")
            summary = root / "sanitizer/run/summary.txt"
            summary.write_text("tool: compute-sanitizer\nstatus: partial\nconclusive: no\nerror_count: 0\n", encoding="utf-8")
            raw = root / "sanitizer/run/raw.log"
            raw.write_text("========= COMPUTE-SANITIZER\n========= ERROR SUMMARY: 0 errors\n", encoding="utf-8")
            passed, evidence = suite.validate_sanitizer_outcome(
                {"ok": True, "returncode": 0, "stdout_path": str(stdout)}, "memcheck", child_valid=True)
            self.assertTrue(passed, evidence)
            raw.write_text("========= COMPUTE-SANITIZER\n========= ERROR SUMMARY: 4 errors\n", encoding="utf-8")
            summary.write_text("tool: compute-sanitizer\nstatus: ok\nconclusive: yes\nerror_count: 4\n", encoding="utf-8")
            passed, evidence = suite.validate_sanitizer_outcome(
                {"ok": True, "returncode": 0, "stdout_path": str(stdout)}, "memcheck", child_valid=True)
            self.assertFalse(passed)
            self.assertEqual(evidence["error_counts"], [4])
            raw.write_text("========= COMPUTE-SANITIZER\n========= WARNING: tool warning\n========= ERROR SUMMARY: 0 errors\n", encoding="utf-8")
            passed, _ = suite.validate_sanitizer_outcome(
                {"ok": True, "returncode": 0, "stdout_path": str(stdout)}, "memcheck", child_valid=True)
            self.assertFalse(passed)
            raw.write_text("========= ERROR SUMMARY: 0 errors\n", encoding="utf-8")
            passed, _ = suite.validate_sanitizer_outcome(
                {"ok": True, "returncode": 0, "stdout_path": str(stdout)}, "memcheck", child_valid=False)
            self.assertFalse(passed)

    def test_capability_not_run_is_preserved_without_becoming_a_failed_oracle(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            stdout = Path(td) / "child.json"
            stdout.write_text(json.dumps({"experiment": "E02", "cases": [
                {"experiment": "E02", "status": "GPU_RUN", "checks": {"valid": True}}]}), encoding="utf-8")
            passed, evidence = suite.validate_child_correctness(
                {"ok": True, "stdout_path": str(stdout)}, "E02")
            self.assertTrue(passed, evidence)
            stdout.write_text(json.dumps({"experiment": "E02", "cases": [
                {"experiment": "E02", "status": "NOT_RUN", "checks": {"valid": False},
                 "limitations": ["peer access unsupported"]}]}), encoding="utf-8")
            passed, evidence = suite.validate_child_correctness(
                {"ok": True, "stdout_path": str(stdout)}, "E02")
            self.assertTrue(passed, evidence)
            self.assertTrue(evidence["unsupported_only"])
            self.assertTrue(evidence["unsupported_reason_valid"])
            self.assertTrue(suite.has_required_profiles({"status": "NOT_RUN", "samples": evidence["normalized_cases"]},
                                                        {"nsys_eligible": True}, "focused"))
            stdout.write_text(json.dumps({"experiment": "E02", "cases": [
                {"experiment": "E02", "status": "NOT_RUN", "checks": {"valid": False},
                 "limitations": []}]}), encoding="utf-8")
            passed, evidence = suite.validate_child_correctness(
                {"ok": True, "stdout_path": str(stdout)}, "E02")
            self.assertFalse(passed)
            self.assertFalse(evidence["unsupported_reason_valid"])
            stdout.write_text(json.dumps({"experiment": "E02", "cases": [
                {"experiment": "E02", "status": "INCONCLUSIVE", "checks": {"valid": False}}]}), encoding="utf-8")
            passed, _ = suite.validate_child_correctness(
                {"ok": True, "stdout_path": str(stdout)}, "E02")
            self.assertFalse(passed)
            stdout.write_text(json.dumps({"experiment": "E02", "cases": [
                {"experiment": "E02", "status": "NOT_RUN", "checks": {"valid": False},
                 "limitations": ["capability unsupported"]},
                {"experiment": "E02", "status": "GPU_RUN", "checks": {"valid": True}}]}), encoding="utf-8")
            passed, evidence = suite.validate_child_correctness(
                {"ok": True, "stdout_path": str(stdout)}, "E02")
            self.assertTrue(passed, evidence)
            self.assertFalse(evidence["unsupported_only"])

    def test_native_result_status_preserves_supported_and_all_unsupported_cases(self) -> None:
        mixed, reason = suite.finalize_native_status("GPU_RUN", [
            {"status": "GPU_RUN"}, {"status": "NOT_RUN"}])
        self.assertEqual((mixed, reason), ("GPU_RUN", None))
        unsupported, reason = suite.finalize_native_status("GPU_RUN", [
            {"status": "NOT_RUN"}, {"status": "NOT_RUN"}])
        self.assertEqual(unsupported, "NOT_RUN")
        self.assertIn("unsupported", reason)

    def test_nsys_copy_only_trace_is_validated_from_sqlite_activity(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            stdout = root / "foreground.stdout.txt"
            stdout.write_text("", encoding="utf-8")
            run = root / "nsys/run"
            run.mkdir(parents=True)
            (run / "report.nsys-rep").write_bytes(b"report")
            (run / "summary.json").write_text(json.dumps({"status": "rerun", "trace_valid": False,
                                                             "reasons": ["classifier expected kernel rows"]}),
                                               encoding="utf-8")
            db = sqlite3.connect(run / "report.sqlite")
            db.execute("CREATE TABLE CUPTI_ACTIVITY_KIND_MEMCPY (start INTEGER)")
            db.executemany("INSERT INTO CUPTI_ACTIVITY_KIND_MEMCPY VALUES (?)", [(1,), (2,)])
            db.execute("CREATE TABLE CUPTI_ACTIVITY_KIND_MEMSET (start INTEGER)")
            db.execute("INSERT INTO CUPTI_ACTIVITY_KIND_MEMSET VALUES (3)")
            db.commit(); db.close()
            valid, evidence = suite.validate_profile_artifacts("nsys", {"ok": True, "stdout_path": str(stdout)})
            self.assertTrue(valid, evidence)
            self.assertFalse(evidence["summary"]["trace_valid"])
            self.assertEqual(evidence["sqlite_activity_counts"], {"kernels": 0, "memcpy": 2, "memset": 1})
            db = sqlite3.connect(run / "report.sqlite")
            db.execute("DELETE FROM CUPTI_ACTIVITY_KIND_MEMCPY")
            db.execute("DELETE FROM CUPTI_ACTIVITY_KIND_MEMSET")
            db.commit(); db.close()
            valid, evidence = suite.validate_profile_artifacts("nsys", {"ok": True, "stdout_path": str(stdout)})
            self.assertFalse(valid)
            self.assertEqual(evidence["sqlite_activity_rows"], 0)

    def test_racecheck_uses_hazard_error_warning_summary(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            stdout = Path(td) / "racecheck.stdout.txt"
            outcome = {"ok": True, "returncode": 0, "stdout_path": str(stdout)}
            stdout.write_text("========= COMPUTE-SANITIZER\n========= RACECHECK SUMMARY: 0 hazards displayed (0 errors, 0 warnings)\n", encoding="utf-8")
            passed, evidence = suite.validate_sanitizer_outcome(outcome, "racecheck", child_valid=True)
            self.assertTrue(passed, evidence)
            self.assertEqual(evidence["racecheck_summaries"], [(0, 0, 0)])
            for report in (
                "========= RACECHECK SUMMARY: 1 hazard displayed (1 errors, 0 warnings)\n",
                "========= RACECHECK SUMMARY: 0 hazards displayed (0 errors, 1 warnings)\n",
                "========= RACECHECK SUMMARY: 0 hazards displayed (1 errors, 0 warnings)\n",
                "========= RACECHECK SUMMARY: 0 hazards displayed (0 errors, 0 warnings)\n========= WARNING: tool warning\n",
            ):
                stdout.write_text("========= COMPUTE-SANITIZER\n" + report, encoding="utf-8")
                passed, _ = suite.validate_sanitizer_outcome(outcome, "racecheck", child_valid=True)
                self.assertFalse(passed, report)

    def test_e33_profile_command_is_marked_diagnostic_and_separate_mode(self) -> None:
        entry = {"runner": "host"}
        argv = suite.child_argv(entry, "E33", verify=False, size=0, iterations=0,
                                warmup=1, repeats=1, output_dir=Path("/tmp/atlas-profile"),
                                profile=True)
        self.assertIn("--mode", argv)
        self.assertEqual(argv[argv.index("--mode") + 1], "smoke")
        self.assertIn("--profile-diagnostic", argv)
        smoke_argv = suite.child_argv(entry, "E33", verify=False, size=0, iterations=0,
                                      warmup=0, repeats=1, mode="smoke")
        self.assertEqual(smoke_argv[smoke_argv.index("--mode") + 1], "smoke")

    def test_archives_controller_artifact_directory(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            artifact_dir = root / "private" / "run"
            artifact_dir.mkdir(parents=True)
            stdout = artifact_dir / "stdout.txt"
            stdout.write_text("case output", encoding="utf-8")
            profile = artifact_dir / "nsys" / "report.nsys-rep"
            profile.parent.mkdir()
            profile.write_bytes(b"capture")
            run_dir = root / "result"
            run_dir.mkdir()
            copied = suite.archive_controller_files({"stdout_path": str(stdout)}, run_dir, "E02")
            self.assertTrue(copied)
            self.assertEqual((run_dir / "controller/E02/artifacts/nsys/report.nsys-rep").read_bytes(), b"capture")


if __name__ == "__main__":
    unittest.main()
