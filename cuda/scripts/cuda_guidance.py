#!/usr/bin/env python3
"""Deterministic section retrieval over the preserved CUDA Markdown corpus."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
from pathlib import Path


TOKEN_RE = re.compile(r"[A-Za-z0-9_.+-]+")
TAG_WORDS = {
    "volta", "ampere", "hopper", "blackwell", "native-v100", "gb200",
    "fusion", "occupancy", "registers", "memory", "shared-memory", "launch",
    "streams", "graphs", "tensor-core", "libraries", "profiling", "roofline",
    "benchmarking", "crash", "sanitizer", "cuda-gdb", "ptx", "sass", "torch",
    "cpu-porting", "nvhpc", "sparse", "bio", "pipeline", "topology", "multi-gpu",
}


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def corpus_files(skill_root: Path) -> list[Path]:
    return sorted(path for path in (skill_root / "references").rglob("*.md") if path.is_file())


def corpus_identity(skill_root: Path) -> str:
    payload = [(path.relative_to(skill_root).as_posix(), sha256(path)) for path in corpus_files(skill_root)]
    return hashlib.sha256(json.dumps(payload, separators=(",", ":")).encode()).hexdigest()


def manifest(skill_root: Path) -> dict[str, object]:
    files = []
    for path in [skill_root / "SKILL.md", *corpus_files(skill_root)]:
        files.append({
            "path": path.relative_to(skill_root).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        })
    return {"schema_version": 1, "files": files}


def validate_manifest(skill_root: Path, payload: dict[str, object]) -> list[str]:
    problems = []
    for item in payload.get("files", []):
        path = skill_root / str(item["path"])
        if not path.exists():
            problems.append(f"missing:{item['path']}")
        elif sha256(path) != item["sha256"]:
            problems.append(f"hash:{item['path']}")
    return problems


def _tags(path: str, heading: str) -> str:
    value = (path + " " + heading).lower().replace("_", "-")
    aliases = {
        "v100": "volta native-v100", "a100": "ampere", "h100": "hopper",
        "b100": "blackwell", "b200": "blackwell", "gb200": "blackwell gb200",
        "tensor core": "tensor-core", "multi gpu": "multi-gpu", "benchmark": "benchmarking",
        "shared memory": "shared-memory", "cpu": "cpu-porting",
    }
    expanded = value + " " + " ".join(tag for needle, tag in aliases.items() if needle in value)
    return " ".join(sorted(tag for tag in TAG_WORDS if tag in expanded))


def sections(path: Path, skill_root: Path):
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    headings: list[tuple[int, int, str]] = []
    fenced = False
    for index, line in enumerate(lines, start=1):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if match:
            headings.append((index, len(match.group(1)), match.group(2)))
    if not headings:
        headings = [(1, 1, path.stem)]
    chain: list[tuple[int, str]] = []
    for position, (start, level, title) in enumerate(headings):
        while chain and chain[-1][0] >= level:
            chain.pop()
        chain.append((level, title))
        end = headings[position + 1][0] - 1 if position + 1 < len(headings) else len(lines)
        text = "".join(lines[start - 1:end])
        relative = path.relative_to(skill_root).as_posix()
        heading_chain = " > ".join(value for _, value in chain)
        yield {
            "path": relative, "heading": heading_chain, "line_start": start, "line_end": end,
            "tags": _tags(relative, heading_chain), "content_hash": hashlib.sha256(text.encode()).hexdigest(), "text": text,
        }


def index_path(skill_root: Path) -> Path:
    cache = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "codex-cuda-guidance"
    cache.mkdir(parents=True, exist_ok=True)
    return cache / f"sections-{corpus_identity(skill_root)}.sqlite3"


def ensure_index(skill_root: Path) -> Path:
    target = index_path(skill_root)
    if target.exists():
        return target
    connection = sqlite3.connect(target)
    try:
        connection.execute("CREATE TABLE sections(id INTEGER PRIMARY KEY,path TEXT,heading TEXT,line_start INTEGER,line_end INTEGER,tags TEXT,content_hash TEXT,text TEXT)")
        connection.execute("CREATE VIRTUAL TABLE sections_fts USING fts5(path,heading,tags,text,content='sections',content_rowid='id')")
        for source in corpus_files(skill_root):
            for item in sections(source, skill_root):
                cursor = connection.execute("INSERT INTO sections(path,heading,line_start,line_end,tags,content_hash,text) VALUES(?,?,?,?,?,?,?)",
                                            (item["path"], item["heading"], item["line_start"], item["line_end"], item["tags"], item["content_hash"], item["text"]))
                connection.execute("INSERT INTO sections_fts(rowid,path,heading,tags,text) VALUES(?,?,?,?,?)",
                                   (cursor.lastrowid, item["path"], item["heading"], item["tags"], item["text"]))
        connection.commit()
    except Exception:
        connection.close()
        target.unlink(missing_ok=True)
        raise
    connection.close()
    return target


def retrieve(skill_root: Path, query: str, *, limit: int = 3, token_budget: int = 900) -> dict[str, object]:
    if query.startswith("full:"):
        relative = query[5:].strip()
        path = (skill_root / relative).resolve()
        path.relative_to(skill_root.resolve())
        text = path.read_text(encoding="utf-8")
        return {"kind": "collected-guidance", "query": query, "sections": [{
            "path": relative, "heading": "<full-document>", "line_start": 1,
            "line_end": len(text.splitlines()), "content_hash": sha256(path), "text": text,
        }]}
    terms = [term.lower() for term in TOKEN_RE.findall(query) if len(term) > 1]
    if not terms:
        return {"kind": "collected-guidance", "query": query, "sections": []}
    expression = " OR ".join('"' + term.replace('"', '""') + '"' for term in terms[:16])
    connection = sqlite3.connect(ensure_index(skill_root))
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            "SELECT s.*,bm25(sections_fts,3.0,2.0,4.0,1.0) AS score FROM sections_fts JOIN sections s ON s.id=sections_fts.rowid WHERE sections_fts MATCH ? ORDER BY score LIMIT 30",
            (expression,),
        ).fetchall()
    finally:
        connection.close()
    architecture = next((name for name in ("volta", "ampere", "hopper", "blackwell") if name in terms), None)
    ranked = sorted(rows, key=lambda row: (0 if architecture and architecture in row["tags"] else 1, row["score"], row["path"], row["line_start"]))
    selected = []
    used = 0
    seen = set()
    for row in ranked:
        key = (row["path"], row["heading"])
        estimate = max(1, len(row["text"]) // 4)
        if key in seen or selected and used + estimate > token_budget:
            continue
        item = {key: row[key] for key in ("path", "heading", "line_start", "line_end", "tags", "content_hash", "text")}
        item["token_estimate"] = estimate
        selected.append(item)
        seen.add(key)
        used += estimate
        if len(selected) >= limit:
            break
    return {"kind": "collected-guidance", "query": query, "token_estimate": used, "sections": selected}
