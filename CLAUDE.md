# agentic-eval-harness

One agentic plan-act-observe loop over real tools, plus the reproducible eval harness (golden set, rubric, regression tracking) that scores it

**Tier**: T1  **Language**: python  **Test discipline**: pragmatic

This file is **read by every Claude Code session** that opens this repo.
Keep it short, scannable, and load-bearing. Long-form prose belongs in
`docs/`. Personal scratch notes (TODOs, ad-hoc commands, half-formed
ideas) belong in `CLAUDE.local.md` (gitignored).

## What this is

A plan-act-observe agent loop (Anthropic SDK, manual loop) over offline
deterministic tools, plus the eval harness that scores it — across pluggable
domain packs selected with `--domain`. Mechanical checkers
(numeric/exact/regex/set-F1), partial-credit rubric, per-metric rollups, hard
gates, scorecard history + regression diff, and a record/replay backend seam so
CI runs the full path without an API key. Eleven domains ship: `generic` (22 cases),
`industrial` (CAN/ISOBUS edge decode + diagnostics, 17 cases; public-standard
decode ground-truth from opendbc-ag over a synthetic corpus), `trust_safety`
(content-enforcement, 18 cases; methodology-only — a fully synthetic, generic policy
with abstract MARKER tokens and benign filler, no real policy or harmful content), and
`data_semantic` (NL→metric/SQL accuracy + metric-correctness, 20 cases; methodology-only
— a fully synthetic, generic semantic layer / metric catalog over a tiny star schema, no
real data model or data); the FDE-dimension packs `customer_support` (18 cases),
`fintech_compliance` (19), and `routing` (16). Four retail/FDE domains join them:
`retail_ops` (buyer-side
retail/CPG supply-chain ops — 3-way match, exception disposition, OTIF, chase ladder,
deduction reconciliation, and a deterministic human-approval hard gate on money-moving
actions; 34 cases), `approval_audit` (red-team of that gate — tool-result injection lures
tempting auto-execution; 24 cases), `process_mapping` (messy multi-source process
description → structured workflow graph + fix-before-automate flags; 25 cases), and
`browser_ops` (browser-automation reliability — idempotency, stop-conditions, retry
safety against a mock portal state machine; 24 cases). All four are fully synthetic
(MARKER-token corpora, PROVENANCE.md per fixture set).
It does NOT use an agent framework, LLM judges, or online
tools — see docs/design.md for why.

## Build / test / lint

All verbs go through `just`. Never run the underlying tool directly in
docs — that creates two sources of truth.

```sh
just            # list all recipes
just fmt        # auto-format
just lint       # lint (warnings → errors)
just test       # run tests per discipline (pragmatic)
just build      # build release artifact
just check      # fmt + lint + test (the merge gate)
```

Tier-2 release path:

```sh
just release patch    # tag + push (CI does the build/sign/SBOM/SLSA)
just release minor
just release major
```

## Architecture

Three to five bullets. Where the code lives, what each top-level dir
does, key invariants a newcomer can't infer from a `tree` listing.
Update when the layout changes.

- `src/agentic_eval/` — engine (domain-agnostic): loop (agent.py), CLI (runner.py),
  domain seam (domain.py), golden-set loading + checkers (cases.py), the reusable
  scorer library (dimensions.py — retrieval precision/recall/f1/MRR/AP/nDCG, tool-use
  correctness, grounding/citation; packs compose it), the approval-gate/audit-
  completeness safety spine (gate.py — shared by retail_ops and approval_audit so
  neither pack imports the other; see tests/test_pack_contract.py), rubric + rollups +
  history (scoring.py).
- `src/agentic_eval/domains/<name>/` — a domain pack: `tools.py` + `__init__.py`
  exporting `DOMAIN`. `industrial` also has `codec.py` (bit-field decode/encode) and
  `generate.py` (deterministic corpus generator); `trust_safety` has `policy.py`
  (synthetic policy + fixture loaders) and `generate.py`; `data_semantic` has
  `semantic.py` (synthetic metric-model + fixture loaders), `compute.py` (the shared
  metric/SQL compute that is the single answer-key source), and `generate.py`. Adding a
  domain is additive — no engine edit.
- `fixtures/<name>/` — that domain's committed fixtures (the tools' only world);
  case expected-values derive from these. Changing a fixture means recomputing the
  domain's `eval/<name>/cases.yaml` expectations. For `industrial`, regenerate logs
  with `uv run python -m agentic_eval.domains.industrial.generate`; for `trust_safety`,
  `uv run python -m agentic_eval.domains.trust_safety.generate`.
- `eval/<name>/` — cases.yaml, transcripts/ (recorded conversation: task + assistant turns + tool_result outputs), history/ (scorecards).
- `tools/` — FDE deployment tools over the retail corpus: `exception-spec-dsl/`
  (single-file spec board that round-trips to the retail_ops `policy.json`), `roi/`
  (honest-ROI harness — false positives dock the score), `newdeploy/` (per-customer
  deployment-kit scaffolder), `supplier-scorecard/` (per-supplier grade rollup +
  single-file dashboard). Each has its own tests; `deployments/` output is gitignored.
- `tests/` — scripted-backend tests; no network, no key. Keep it that way.
- `.github/workflows/` — CI; SHA-pinned actions.

## Conventions

- **Conventional Commits**, signed (`git commit -sS`).
- **Lockfile committed**.
- **Pre-commit installed** — `pre-commit install` once after clone.
- **GitHub Actions pinned by SHA** — Renovate / Dependabot keeps fresh.
- **Container base images pinned by digest** if any.
- **Structured logging** — no `print()` / `console.log` in committed code.

## License

See LICENSE files at repo root. Default scaffolding is Apache-2.0 OR MIT
dual (apache-mit-dual).

## See also

- `CLAUDE.local.md` (gitignored) — your scratch notes for this repo.
- `docs/adr/` — Architecture Decision Records.
- `~/.claude/CLAUDE.md` (user-scope) — global invariants that apply
  across every repo.
- `~/Documents/coding-standard.md` — the standard this repo conforms to.
