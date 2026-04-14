#!/usr/bin/env python3
"""Split a multi-kernel CUDA translation unit into one focused source file."""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


DEFAULT_LIBCLANG_CANDIDATES = (
    os.environ.get("LIBCLANG_PATH", ""),
    "/usr/lib/llvm-18/lib/libclang.so.1",
    "/usr/lib/llvm-17/lib/libclang.so.1",
    "/usr/lib/llvm-16/lib/libclang.so.1",
)

SUPPORTED_DECL_KINDS = {
    "FunctionDecl",
    "FunctionTemplate",
    "VarDecl",
    "TypedefDecl",
    "TypeAliasDecl",
    "StructDecl",
    "ClassDecl",
    "UnionDecl",
    "EnumDecl",
}


class CXString(ctypes.Structure):
    _fields_ = [("data", ctypes.c_void_p), ("private_flags", ctypes.c_uint)]


class CXCursor(ctypes.Structure):
    _fields_ = [
        ("kind", ctypes.c_int),
        ("xdata", ctypes.c_int),
        ("data", ctypes.c_void_p * 3),
    ]


class CXSourceLocation(ctypes.Structure):
    _fields_ = [("ptr_data", ctypes.c_void_p * 2), ("int_data", ctypes.c_uint)]


class CXSourceRange(ctypes.Structure):
    _fields_ = [
        ("ptr_data", ctypes.c_void_p * 2),
        ("begin_int_data", ctypes.c_uint),
        ("end_int_data", ctypes.c_uint),
    ]


@dataclass
class DeclNode:
    usr: str
    spelling: str
    kind: str
    file_path: str
    start_offset: int
    end_offset: int
    start_line: int
    end_line: int
    scope_chain: list[tuple[str, str]]
    is_kernel: bool
    cursor: CXCursor

    def manifest_dict(self) -> dict[str, object]:
        return {
            "usr": self.usr,
            "spelling": self.spelling,
            "kind": self.kind,
            "file_path": self.file_path,
            "start_offset": self.start_offset,
            "end_offset": self.end_offset,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "scope_chain": [
                {"kind": kind, "value": value} for kind, value in self.scope_chain
            ],
            "is_kernel": self.is_kernel,
        }


class LibClang:
    def __init__(self, path: str | None = None) -> None:
        self.path = self._resolve_path(path)
        self.lib = ctypes.CDLL(self.path)
        self._configure()

    @staticmethod
    def _resolve_path(path: str | None) -> str:
        candidates = []
        if path:
            candidates.append(path)
        candidates.extend(candidate for candidate in DEFAULT_LIBCLANG_CANDIDATES if candidate)
        for candidate in candidates:
            if Path(candidate).exists():
                return candidate
        raise FileNotFoundError("Could not locate libclang.so. Set LIBCLANG_PATH.")

    def _configure(self) -> None:
        lib = self.lib
        lib.clang_createIndex.argtypes = [ctypes.c_int, ctypes.c_int]
        lib.clang_createIndex.restype = ctypes.c_void_p
        lib.clang_disposeIndex.argtypes = [ctypes.c_void_p]
        lib.clang_parseTranslationUnit2.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.POINTER(ctypes.c_char_p),
            ctypes.c_int,
            ctypes.c_void_p,
            ctypes.c_uint,
            ctypes.c_uint,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        lib.clang_parseTranslationUnit2.restype = ctypes.c_int
        lib.clang_disposeTranslationUnit.argtypes = [ctypes.c_void_p]
        lib.clang_getTranslationUnitCursor.argtypes = [ctypes.c_void_p]
        lib.clang_getTranslationUnitCursor.restype = CXCursor
        lib.clang_getCursorSpelling.argtypes = [CXCursor]
        lib.clang_getCursorSpelling.restype = CXString
        lib.clang_getCursorKindSpelling.argtypes = [ctypes.c_uint]
        lib.clang_getCursorKindSpelling.restype = CXString
        lib.clang_getCursorUSR.argtypes = [CXCursor]
        lib.clang_getCursorUSR.restype = CXString
        lib.clang_getCursorLocation.argtypes = [CXCursor]
        lib.clang_getCursorLocation.restype = CXSourceLocation
        lib.clang_getCursorExtent.argtypes = [CXCursor]
        lib.clang_getCursorExtent.restype = CXSourceRange
        lib.clang_getRangeStart.argtypes = [CXSourceRange]
        lib.clang_getRangeStart.restype = CXSourceLocation
        lib.clang_getRangeEnd.argtypes = [CXSourceRange]
        lib.clang_getRangeEnd.restype = CXSourceLocation
        lib.clang_getExpansionLocation.argtypes = [
            CXSourceLocation,
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.POINTER(ctypes.c_uint),
            ctypes.POINTER(ctypes.c_uint),
            ctypes.POINTER(ctypes.c_uint),
        ]
        lib.clang_getFileName.argtypes = [ctypes.c_void_p]
        lib.clang_getFileName.restype = CXString
        lib.clang_getCursorReferenced.argtypes = [CXCursor]
        lib.clang_getCursorReferenced.restype = CXCursor
        lib.clang_getCursorDefinition.argtypes = [CXCursor]
        lib.clang_getCursorDefinition.restype = CXCursor
        lib.clang_getCursorSemanticParent.argtypes = [CXCursor]
        lib.clang_getCursorSemanticParent.restype = CXCursor
        lib.clang_getCursorLexicalParent.argtypes = [CXCursor]
        lib.clang_getCursorLexicalParent.restype = CXCursor
        lib.clang_isCursorDefinition.argtypes = [CXCursor]
        lib.clang_isCursorDefinition.restype = ctypes.c_uint
        lib.clang_visitChildren.argtypes = [
            CXCursor,
            ctypes.CFUNCTYPE(ctypes.c_uint, CXCursor, CXCursor, ctypes.c_void_p),
            ctypes.c_void_p,
        ]
        lib.clang_visitChildren.restype = ctypes.c_uint
        lib.clang_getCString.argtypes = [CXString]
        lib.clang_getCString.restype = ctypes.c_char_p
        lib.clang_disposeString.argtypes = [CXString]

    def cxstring_to_str(self, value: CXString) -> str:
        raw = self.lib.clang_getCString(value)
        text = raw.decode() if raw else ""
        self.lib.clang_disposeString(value)
        return text

    def kind_name(self, cursor: CXCursor) -> str:
        return self.cxstring_to_str(self.lib.clang_getCursorKindSpelling(cursor.kind))

    def spelling(self, cursor: CXCursor) -> str:
        return self.cxstring_to_str(self.lib.clang_getCursorSpelling(cursor))

    def usr(self, cursor: CXCursor) -> str:
        return self.cxstring_to_str(self.lib.clang_getCursorUSR(cursor))

    def location_info(self, location: CXSourceLocation) -> tuple[str, int, int, int]:
        file_ptr = ctypes.c_void_p()
        line = ctypes.c_uint()
        column = ctypes.c_uint()
        offset = ctypes.c_uint()
        self.lib.clang_getExpansionLocation(
            location,
            ctypes.byref(file_ptr),
            ctypes.byref(line),
            ctypes.byref(column),
            ctypes.byref(offset),
        )
        file_path = self.cxstring_to_str(self.lib.clang_getFileName(file_ptr)) if file_ptr.value else ""
        return file_path, line.value, column.value, offset.value

    def cursor_file_path(self, cursor: CXCursor) -> str:
        location = self.lib.clang_getCursorLocation(cursor)
        return self.location_info(location)[0]

    def extent_info(self, cursor: CXCursor) -> tuple[str, int, int, int, int]:
        extent = self.lib.clang_getCursorExtent(cursor)
        start = self.lib.clang_getRangeStart(extent)
        end = self.lib.clang_getRangeEnd(extent)
        start_file, start_line, _, start_offset = self.location_info(start)
        end_file, end_line, _, end_offset = self.location_info(end)
        file_path = start_file or end_file
        return file_path, start_offset, end_offset, start_line, end_line

    def is_definition(self, cursor: CXCursor) -> bool:
        return bool(self.lib.clang_isCursorDefinition(cursor))

    def semantic_parent(self, cursor: CXCursor) -> CXCursor:
        return self.lib.clang_getCursorSemanticParent(cursor)

    def lexical_parent(self, cursor: CXCursor) -> CXCursor:
        return self.lib.clang_getCursorLexicalParent(cursor)

    def referenced(self, cursor: CXCursor) -> CXCursor:
        return self.lib.clang_getCursorReferenced(cursor)

    def definition(self, cursor: CXCursor) -> CXCursor:
        return self.lib.clang_getCursorDefinition(cursor)

    def visit_children(self, cursor: CXCursor, fn) -> None:
        visitor_type = ctypes.CFUNCTYPE(ctypes.c_uint, CXCursor, CXCursor, ctypes.c_void_p)
        callback = visitor_type(fn)
        self.lib.clang_visitChildren(cursor, callback, None)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="Input CUDA translation unit")
    parser.add_argument("--symbol", default="", help="Kernel or declaration spelling to extract")
    parser.add_argument("--out-dir", type=Path, default=Path("./split_out"))
    parser.add_argument("--label", default="", help="Run label. Default: source stem plus symbol")
    parser.add_argument("--arch", default="sm_70")
    parser.add_argument("--clang-arg", action="append", default=[], help="Extra clang parse argument")
    parser.add_argument("--libclang", default="", help="Explicit libclang shared library path")
    parser.add_argument("--list-kernels", action="store_true", help="List kernel candidates and exit")
    parser.add_argument("--json-out", type=Path, default=None, help="Optional manifest JSON output path")
    return parser.parse_args()


def resolve_nvcc_include() -> str | None:
    nvcc = shutil.which("nvcc")
    if not nvcc:
        fallback = Path("/opt/nvidia/hpc_sdk/Linux_x86_64/26.1/cuda/12.9/bin/nvcc")
        nvcc = str(fallback) if fallback.exists() else ""
    if not nvcc:
        return None
    include_dir = Path(nvcc).resolve().parent.parent / "include"
    return str(include_dir) if include_dir.exists() else None


def default_clang_args(source: Path, arch: str, extra_args: list[str]) -> list[str]:
    args = ["-x", "cuda", f"--cuda-gpu-arch={arch}", "-std=c++17", f"-I{source.parent}"]
    include_dir = resolve_nvcc_include()
    if include_dir:
        args.append(f"-I{include_dir}")
    args.extend(extra_args)
    return args


def parse_translation_unit(libclang: LibClang, source: Path, args: list[str]):
    index = libclang.lib.clang_createIndex(0, 0)
    translation_unit = ctypes.c_void_p()
    encoded_args = (ctypes.c_char_p * len(args))(*(arg.encode() for arg in args))
    error = libclang.lib.clang_parseTranslationUnit2(
        index,
        str(source).encode(),
        encoded_args,
        len(args),
        None,
        0,
        0,
        ctypes.byref(translation_unit),
    )
    if error != 0 or not translation_unit.value:
        libclang.lib.clang_disposeIndex(index)
        raise RuntimeError(f"libclang failed to parse {source} (error {error}).")
    return index, translation_unit


def scope_chain(libclang: LibClang, cursor: CXCursor) -> list[tuple[str, str]]:
    chain: list[tuple[str, str]] = []
    current = libclang.lexical_parent(cursor)
    while True:
        kind = libclang.kind_name(current)
        if kind == "TranslationUnit":
            break
        if kind == "Namespace":
            chain.append(("Namespace", libclang.spelling(current)))
        elif kind == "LinkageSpec":
            chain.append(("LinkageSpec", "C"))
        else:
            return []
        current = libclang.lexical_parent(current)
    chain.reverse()
    return chain


def is_extractable_scope(libclang: LibClang, cursor: CXCursor) -> bool:
    chain = scope_chain(libclang, cursor)
    if chain:
        return True
    return libclang.kind_name(libclang.lexical_parent(cursor)) == "TranslationUnit"


def supports_kind(kind: str) -> bool:
    return kind in SUPPORTED_DECL_KINDS


def snippet_text(source_text: str, start: int, end: int) -> str:
    return source_text[start:end]


def detect_kernel(libclang: LibClang, cursor: CXCursor, source_text: str) -> bool:
    kind = libclang.kind_name(cursor)
    if kind not in {"FunctionDecl", "FunctionTemplate"}:
        return False
    _, start, end, _, _ = libclang.extent_info(cursor)
    line_start = source_text.rfind("\n", 0, start) + 1
    head = source_text[line_start : min(end, line_start + 256)]
    return "__global__" in head


def collect_decl_nodes(
    libclang: LibClang, tu_cursor: CXCursor, source: Path, source_text: str
) -> dict[str, DeclNode]:
    nodes: dict[str, DeclNode] = {}
    source_path = str(source.resolve())

    def visit(cursor: CXCursor, parent: CXCursor, _data) -> int:
        file_path = libclang.cursor_file_path(cursor)
        if file_path and str(Path(file_path).resolve()) != source_path:
            return 1
        kind = libclang.kind_name(cursor)
        if kind in {"Namespace", "LinkageSpec", "TranslationUnit"}:
            return 2
        if not supports_kind(kind):
            return 1
        if kind in {"FunctionDecl", "FunctionTemplate", "StructDecl", "ClassDecl", "UnionDecl", "EnumDecl", "VarDecl"}:
            if not libclang.is_definition(cursor):
                return 1
        usr = libclang.usr(cursor)
        if not usr:
            return 1
        file_name, start, end, start_line, end_line = libclang.extent_info(cursor)
        if str(Path(file_name).resolve()) != source_path:
            return 1
        line_start = source_text.rfind("\n", 0, start) + 1
        chain = scope_chain(libclang, cursor)
        if not is_extractable_scope(libclang, cursor):
            return 1
        node = DeclNode(
            usr=usr,
            spelling=libclang.spelling(cursor),
            kind=kind,
            file_path=file_name,
            start_offset=line_start,
            end_offset=end,
            start_line=start_line,
            end_line=end_line,
            scope_chain=chain,
            is_kernel=detect_kernel(libclang, cursor, source_text),
            cursor=cursor,
        )
        existing = nodes.get(usr)
        if existing is None or (node.end_offset - node.start_offset) > (existing.end_offset - existing.start_offset):
            nodes[usr] = node
        return 1

    libclang.visit_children(tu_cursor, visit)
    return nodes


def resolve_decl_usr(libclang: LibClang, cursor: CXCursor, nodes: dict[str, DeclNode]) -> str:
    current = cursor
    for _ in range(16):
        usr = libclang.usr(current)
        if usr in nodes:
            return usr
        parent = libclang.semantic_parent(current)
        if libclang.kind_name(parent) == "TranslationUnit":
            break
        current = parent
    current = cursor
    for _ in range(16):
        usr = libclang.usr(current)
        if usr in nodes:
            return usr
        parent = libclang.lexical_parent(current)
        if libclang.kind_name(parent) == "TranslationUnit":
            break
        current = parent
    return ""


def collect_same_file_dependencies(
    libclang: LibClang,
    root_node: DeclNode,
    nodes: dict[str, DeclNode],
    source: Path,
) -> tuple[set[str], list[dict[str, str]]]:
    source_path = str(source.resolve())
    dependencies: set[str] = set()
    unresolved: dict[tuple[str, str, str], dict[str, str]] = {}

    def visit(cursor: CXCursor, parent: CXCursor, _data) -> int:
        referenced = libclang.referenced(cursor)
        kind = libclang.kind_name(referenced)
        if kind and not kind.startswith("Invalid"):
            definition = libclang.definition(referenced)
            ref_cursor = definition if libclang.kind_name(definition) and not libclang.kind_name(definition).startswith("Invalid") else referenced
            ref_file = libclang.cursor_file_path(ref_cursor)
            if ref_file and str(Path(ref_file).resolve()) == source_path:
                enclosing_usr = resolve_decl_usr(libclang, ref_cursor, nodes)
                if enclosing_usr and enclosing_usr != root_node.usr:
                    dependencies.add(enclosing_usr)
                else:
                    unresolved_kind = libclang.kind_name(ref_cursor)
                    if unresolved_kind in SUPPORTED_DECL_KINDS and is_extractable_scope(libclang, ref_cursor):
                        unresolved_key = (
                            libclang.spelling(ref_cursor),
                            unresolved_kind,
                            ref_file,
                        )
                        unresolved[unresolved_key] = {
                            "spelling": unresolved_key[0],
                            "kind": unresolved_key[1],
                            "file_path": unresolved_key[2],
                        }
        return 2

    libclang.visit_children(root_node.cursor, visit)
    return dependencies, sorted(unresolved.values(), key=lambda item: (item["kind"], item["spelling"]))


def choose_target(nodes: dict[str, DeclNode], symbol: str) -> DeclNode:
    matches = [node for node in nodes.values() if node.spelling == symbol]
    if not matches:
        raise KeyError(f"Could not find a declaration named {symbol!r} in the main source file.")
    kernel_matches = [node for node in matches if node.is_kernel]
    if len(kernel_matches) == 1:
        return kernel_matches[0]
    if len(matches) == 1:
        return matches[0]
    raise KeyError(f"Multiple declarations named {symbol!r} were found. Narrow the symbol or source.")


def render_wrapped_declaration(text: str, chain: list[tuple[str, str]]) -> str:
    rendered = text.strip() + "\n"
    for kind, value in reversed(chain):
        if kind == "Namespace":
            if value:
                rendered = f"namespace {value} {{\n{rendered}}}  // namespace {value}\n"
            else:
                rendered = f"namespace {{\n{rendered}}}  // namespace\n"
        elif kind == "LinkageSpec":
            rendered = f'extern "C" {{\n{rendered}}}  // extern "C"\n'
    return rendered


def build_focused_source(
    source_text: str,
    selected_nodes: list[DeclNode],
    source: Path,
    symbol: str,
) -> str:
    first_decl_start = min(node.start_offset for node in selected_nodes)
    preamble = source_text[:first_decl_start].rstrip()
    chunks = []
    if preamble:
        chunks.append(preamble)
    chunks.append(f"// Generated from {source} for symbol {symbol}.")
    for node in selected_nodes:
        decl_text = snippet_text(source_text, node.start_offset, node.end_offset)
        chunks.append(render_wrapped_declaration(decl_text, node.scope_chain).rstrip())
    return "\n\n".join(chunk for chunk in chunks if chunk) + "\n"


def format_kernel_list(nodes: dict[str, DeclNode], source: Path) -> str:
    kernels = sorted(
        [node for node in nodes.values() if node.is_kernel],
        key=lambda item: item.start_offset,
    )
    lines = [
        "CUDA Kernel Candidates",
        "",
        f"source: {source}",
        f"kernels: {len(kernels)}",
        "",
    ]
    for node in kernels:
        lines.append(f"- {node.spelling} ({node.kind}, lines {node.start_line}-{node.end_line})")
    return "\n".join(lines) + "\n"


def format_summary(manifest: dict[str, object]) -> str:
    lines = [
        "CUDA Split Decision",
        "",
        f"status: {manifest['status']}",
        f"source: {manifest['source_path']}",
        f"symbol: {manifest['symbol']}",
        f"arch: {manifest['arch']}",
        f"generated_source: {manifest.get('generated_source', '')}",
        f"selected_declarations: {len(manifest.get('selected_declarations', []))}",
        f"same_file_unresolved: {len(manifest.get('unresolved_same_file_refs', []))}",
        "",
        "decision:",
    ]
    for reason in manifest.get("reasons", []):
        lines.append(f"- {reason}")
    if manifest.get("notes"):
        lines.extend(["", "notes:"])
        for note in manifest["notes"]:
            lines.append(f"- {note}")
    lines.extend(["", f"next_step: {manifest['next_step']}"])
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    source = args.source.resolve()
    if not source.exists():
        sys.stderr.write(f"Source file not found: {source}\n")
        return 2
    if source.suffix != ".cu":
        sys.stderr.write("split_cuda_translation_unit.py only supports .cu sources.\n")
        return 2

    libclang = LibClang(args.libclang or None)
    clang_args = default_clang_args(source, args.arch, args.clang_arg)
    source_text = source.read_text()

    index = None
    translation_unit = None
    try:
        index, translation_unit = parse_translation_unit(libclang, source, clang_args)
        tu_cursor = libclang.lib.clang_getTranslationUnitCursor(translation_unit)
        nodes = collect_decl_nodes(libclang, tu_cursor, source, source_text)

        if args.list_kernels:
            sys.stdout.write(format_kernel_list(nodes, source))
            return 0

        if not args.symbol:
            sys.stderr.write("Pass --symbol to extract a focused source, or use --list-kernels.\n")
            return 2

        target = choose_target(nodes, args.symbol)
        selected_usrs = {target.usr}
        unresolved_same_file_refs: dict[str, dict[str, str]] = {}
        queue = [target.usr]
        while queue:
            current_usr = queue.pop(0)
            current_node = nodes[current_usr]
            dependencies, unresolved = collect_same_file_dependencies(libclang, current_node, nodes, source)
            for dep in sorted(dependencies):
                if dep not in selected_usrs:
                    selected_usrs.add(dep)
                    queue.append(dep)
            for item in unresolved:
                key = f"{item['kind']}::{item['spelling']}::{item['file_path']}"
                unresolved_same_file_refs[key] = item

        selected_nodes = sorted(
            [nodes[usr] for usr in selected_usrs],
            key=lambda item: item.start_offset,
        )
        label = args.label or f"{source.stem}-{args.symbol}"
        out_dir = args.out_dir / label
        out_dir.mkdir(parents=True, exist_ok=True)
        generated_source = out_dir / "focused_source.cu"
        manifest_path = args.json_out or out_dir / "manifest.json"
        summary_path = out_dir / "summary.txt"

        focused_source = build_focused_source(source_text, selected_nodes, source, args.symbol)
        generated_source.write_text(focused_source)

        status = "ok"
        reasons = [
            f"Extracted {len(selected_nodes)} declarations for {args.symbol}.",
            "Preserved the file preamble before the first selected declaration.",
        ]
        notes: list[str] = []
        if unresolved_same_file_refs:
            status = "partial"
            reasons.append("Some same-file references could not be promoted to top-level extracted declarations.")
            notes.extend(
                f"unresolved same-file ref: {item['kind']} {item['spelling']}"
                for item in list(unresolved_same_file_refs.values())[:6]
            )
        manifest = {
            "tool": "cuda-tu-splitter",
            "status": status,
            "source_path": str(source),
            "symbol": args.symbol,
            "arch": args.arch,
            "clang_args": clang_args,
            "libclang_path": libclang.path,
            "generated_source": str(generated_source),
            "selected_declarations": [node.manifest_dict() for node in selected_nodes],
            "unresolved_same_file_refs": list(unresolved_same_file_refs.values()),
            "reasons": reasons,
            "notes": notes,
            "next_step": "Run dump_ptx_hotspot.sh on the generated focused source, then inspect summary.txt before opening raw PTX or SASS.",
        }
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
        summary_path.write_text(format_summary(manifest))
        sys.stdout.write(format_summary(manifest))
        return 0
    except Exception as exc:
        sys.stderr.write(f"Failed to split CUDA translation unit: {exc}\n")
        return 1
    finally:
        if translation_unit:
            libclang.lib.clang_disposeTranslationUnit(translation_unit)
        if index:
            libclang.lib.clang_disposeIndex(index)


if __name__ == "__main__":
    raise SystemExit(main())
