from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "common"))

from cuda_guidance import retrieve, validate_manifest  # noqa: E402
from recommend_cuda_route import main as recommend_main  # noqa: E402
from recommend_cuda_route import pick_route, summarize_evidence  # noqa: E402


LINK_RE = re.compile(r"\[[^\]]*\]\((?:<([^>]+)>|([^\s)]+))(?:\s+[^)]*)?\)")


def markdown_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.md") if path.is_file())


def local_links(path: Path):
    text = path.read_text(encoding="utf-8")
    for match in LINK_RE.finditer(text):
        target = unquote(match.group(1) or match.group(2)).split("#", 1)[0]
        if not target:
            continue
        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc:
            continue
        yield path.parent / parsed.path


class GuidanceTests(unittest.TestCase):
    def test_manifest_preserves_entire_markdown_corpus(self) -> None:
        payload = json.loads((ROOT / "assets" / "cuda-markdown-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(validate_manifest(ROOT, payload), [])
        expected = {"SKILL.md", *{path.relative_to(ROOT).as_posix() for path in (ROOT / "references").rglob("*.md")}}
        self.assertEqual({item["path"] for item in payload["files"]}, expected)

    def test_all_local_markdown_links_resolve_and_all_references_are_reachable(self) -> None:
        documents = markdown_files(ROOT)
        failures = []
        graph: dict[Path, set[Path]] = {}
        for source in documents:
            targets = set()
            for target in local_links(source):
                if target.suffix.lower() != ".md":
                    continue
                if not target.is_file():
                    failures.append(f"{source.relative_to(ROOT)} -> {target}")
                elif target.resolve().is_relative_to(ROOT.resolve()):
                    targets.add(target.resolve())
            graph[source.resolve()] = targets
        self.assertEqual(failures, [])

        entry = (ROOT / "SKILL.md").resolve()
        visited = set()
        pending = [entry]
        while pending:
            current = pending.pop()
            if current in visited:
                continue
            visited.add(current)
            pending.extend(graph.get(current, set()) - visited)
        unreachable = [
            path.relative_to(ROOT).as_posix()
            for path in (ROOT / "references").rglob("*.md")
            if path.resolve() not in visited
        ]
        self.assertEqual(unreachable, [])

    def test_natural_queries_return_same_authored_navigation_without_indexing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "references").mkdir()
            (root / "SKILL.md").write_text("# Test skill\n\n[Route](references/route.md)\n", encoding="utf-8")
            (root / "references" / "route.md").write_text("# Authored route\n", encoding="utf-8")
            cache = root / "cache"
            with patch.dict(os.environ, {"XDG_CACHE_HOME": str(cache)}):
                results = [
                    retrieve(root, "tensor core throughput", limit=1, token_budget=5),
                    retrieve(root, "how do I debug a race?", limit=8, token_budget=9000),
                    retrieve(root, "completely unrelated words"),
                ]

            self.assertEqual(
                [{key: value for key, value in item.items() if key != "query"} for item in results],
                [{key: value for key, value in results[0].items() if key != "query"}] * len(results),
            )
            self.assertEqual(results[0]["kind"], "collected-guidance")
            self.assertEqual(results[0]["navigation_mode"], "authored-entrypoint")
            self.assertEqual(results[0]["authority_model"], "agent-semantic-router")
            self.assertEqual(results[0]["navigation_pointer"], "SKILL.md")
            self.assertEqual(results[0]["sections"], [])
            self.assertFalse(cache.exists())

    def test_full_read_is_exact_and_limited_to_instruction_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "references").mkdir()
            (root / "scripts").mkdir()
            (root / "SKILL.md").write_text("# Entrypoint\n", encoding="utf-8")
            (root / "references" / "route.md").write_text("# Exact guide\n\nKeep this text.\n", encoding="utf-8")
            (root / "scripts" / "secret.py").write_text("secret", encoding="utf-8")

            result = retrieve(root, "full:references/route.md")
            section = result["sections"][0]
            self.assertEqual(section["text"], (root / section["path"]).read_text(encoding="utf-8"))
            self.assertEqual(section["heading"], "<full-document>")
            with self.assertRaises(ValueError):
                retrieve(root, "full:scripts/secret.py")
            with self.assertRaises(ValueError):
                retrieve(root, "full:../outside.md")

    def test_architecture_cli_adapter_never_uses_summary_routes_as_authority(self) -> None:
        benchmark = {"status": "ok", "workload_balance": "transfer-dominant", "recommended_route": "pipeline"}
        nsys = {"status": "ok", "recommended_route": "graphs", "reasons": ["timeline clue"]}
        ncu = {"status": "ok", "recommended_route": "tensor", "notes": ["counter clue"]}

        route, reason = pick_route(benchmark, nsys, ncu)
        evidence = summarize_evidence(benchmark, nsys, ncu)

        self.assertEqual(route, "agent-review")
        self.assertIn("authored architecture router", reason)
        self.assertEqual([item["source"] for item in evidence], ["benchmark", "nsys", "ncu"])
        self.assertEqual(evidence[1]["reasons"], ["timeline clue"])
        self.assertNotIn("recommended_route", json.dumps(evidence))

    def test_architecture_cli_preserves_output_keys_and_routes_by_explicit_arch(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            summary = root / "nsys.json"
            output = root / "route.json"
            summary.write_text(
                json.dumps({"status": "ok", "recommended_route": "graphs", "reasons": ["timeline clue"]}),
                encoding="utf-8",
            )
            with patch(
                "sys.argv",
                ["recommend_cuda_route.py", "--arch", "hopper", "--nsys", str(summary), "--json-out", str(output)],
            ):
                with patch("builtins.print") as print_mock:
                    self.assertEqual(recommend_main(), 0)

            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(
                set(payload),
                {"arch", "recommended_route", "recommended_reference", "reason", "evidence"},
            )
            self.assertEqual(payload["recommended_route"], "agent-review")
            self.assertEqual(payload["recommended_reference"], "references/architectures/hopper/router.md")
            self.assertIn("timeline clue", print_mock.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
