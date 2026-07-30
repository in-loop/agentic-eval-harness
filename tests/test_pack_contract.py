"""Enforces the pack-boundary claim made in ``domain.py``'s docstring:

    "domains never collide. Adding a domain is additive — no engine edit
    required."

That sentence is a docstring, not a contract — nothing in the engine or in CI
stops one domain pack from importing another, or the engine from reaching into
domains/. This test makes the claim executable in both directions:

1. No domain pack imports another domain pack (only stdlib, third-party,
   `agentic_eval` core/engine modules, or its own pack are allowed).
2. The engine (`src/agentic_eval/` outside `domains/`) imports no domain pack.

Packs are discovered dynamically from the filesystem — this must hold for
pack N+1, not just the eleven that ship today. Every module in every pack is
AST-parsed (not just top-level statements) so function-local imports are
caught too — that's where the known approval_audit -> retail_ops violations
live.

KNOWN TO FAIL: approval_audit imports retail_ops six times across three
files (tools.py, compute.py, generate.py) by design (the pack's own
docstrings say so — it reuses retail_ops's gate/audit logic on purpose so
the safety spine can't fork). That reuse is real and probably fine, but it
directly contradicts the "domains never collide" docstring, and nothing
currently enforces or even flags it. This test is that flag. Do NOT
whitelist, xfail, or skip the violation to make this test pass — a green
result here should mean the boundary actually holds.
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
AGENTIC_EVAL = SRC / "agentic_eval"
DOMAINS = AGENTIC_EVAL / "domains"


@dataclass(frozen=True)
class Violation:
    file: Path
    line: int
    imported_pack: str

    def __str__(self) -> str:
        try:
            rel = self.file.relative_to(SRC)
        except ValueError:
            rel = self.file
        return f"{rel}:{self.line} -> {self.imported_pack}"


def _discover_packs() -> list[str]:
    """Every directory under domains/ that is an importable package."""
    packs = []
    for entry in sorted(DOMAINS.iterdir()):
        if not entry.is_dir():
            continue
        if entry.name == "__pycache__":
            continue
        if (entry / "__init__.py").exists():
            packs.append(entry.name)
    return packs


def _module_and_package(py_file: Path) -> tuple[str, str]:
    """Return (dotted module name, dotted __package__) for a source file.

    Mirrors how Python itself computes these, so relative-import resolution
    (``from . import x`` / ``from .. import x``) matches runtime behavior.
    """
    rel = py_file.relative_to(SRC).with_suffix("")
    parts = list(rel.parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
        module = ".".join(parts)
        package = module
    else:
        module = ".".join(parts)
        package = ".".join(parts[:-1])
    return module, package


def _resolve_relative(module: str | None, level: int, package: str) -> str:
    """Port of importlib._bootstrap._resolve_name: turn a relative import's
    (module, level, package) into an absolute dotted module path."""
    bits = package.rsplit(".", level - 1)
    if len(bits) < level:
        raise ImportError("attempted relative import beyond top-level package")
    base = bits[0]
    return f"{base}.{module}" if module else base


def _pack_of(dotted: str) -> str | None:
    """If `dotted` names something under agentic_eval.domains.<pack>, return
    <pack>; else None (stdlib, third-party, or non-domains agentic_eval)."""
    prefix = "agentic_eval.domains."
    if dotted == "agentic_eval.domains" or not dotted.startswith(prefix):
        return None
    rest = dotted[len(prefix) :]
    return rest.split(".", 1)[0] if rest else None


def _iter_source_files(root: Path, *, exclude: Path | None = None) -> list[Path]:
    files = []
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        if exclude is not None and exclude in path.parents:
            continue
        files.append(path)
    return files


def _find_pack_imports(py_file: Path) -> list[tuple[int, str]]:
    """Walk every Import/ImportFrom in `py_file` (including function-local
    ones, via ast.walk) and return (line, imported_pack) for every import
    that resolves into agentic_eval.domains.<pack>."""
    _module_name, package_name = _module_and_package(py_file)
    tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))

    hits: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                pack = _pack_of(alias.name)
                if pack is not None:
                    hits.append((node.lineno, pack))
        elif isinstance(node, ast.ImportFrom):
            if node.level > 0:
                try:
                    resolved = _resolve_relative(node.module, node.level, package_name)
                except ImportError:
                    continue
            else:
                resolved = node.module or ""
            pack = _pack_of(resolved)
            if pack is not None:
                hits.append((node.lineno, pack))
            elif resolved == "agentic_eval.domains":
                # `from agentic_eval.domains import retail_ops` style: the
                # pack name arrives as an imported NAME, not in the module path.
                for alias in node.names:
                    hits.append((node.lineno, alias.name))
    return hits


def test_no_domain_pack_imports_another_domain_pack() -> None:
    packs = _discover_packs()
    assert packs, "expected at least one domain pack under src/agentic_eval/domains/"

    violations: list[Violation] = []
    for pack in packs:
        pack_dir = DOMAINS / pack
        for py_file in _iter_source_files(pack_dir):
            for line, imported_pack in _find_pack_imports(py_file):
                if imported_pack != pack:
                    violations.append(Violation(py_file, line, imported_pack))

    if violations:
        lines = "\n".join(f"  {v}" for v in violations)
        raise AssertionError(
            "domain.py claims 'domains never collide' but the following imports "
            "cross a pack boundary (file:line -> imported pack):\n"
            f"{lines}\n"
            f"({len(violations)} violation(s) across {len(packs)} discovered pack(s): "
            f"{', '.join(packs)})"
        )


def test_engine_imports_no_domain_pack() -> None:
    """The other half of the docstring claim: 'adding a domain is additive —
    no engine edit required' implies the engine never reaches INTO domains/
    for a specific pack. Verified independently of the pack-boundary test
    above so a pass/fail here is reported on its own terms."""
    violations: list[Violation] = []
    for py_file in _iter_source_files(AGENTIC_EVAL, exclude=DOMAINS):
        for line, imported_pack in _find_pack_imports(py_file):
            violations.append(Violation(py_file, line, imported_pack))

    if violations:
        lines = "\n".join(f"  {v}" for v in violations)
        raise AssertionError(
            "engine module(s) outside domains/ import a specific domain pack "
            "(file:line -> imported pack):\n"
            f"{lines}"
        )


if __name__ == "__main__":  # pragma: no cover
    sys.exit(0)
