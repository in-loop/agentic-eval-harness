"""Deterministic loaders + dataclasses for the approval_audit domain's committed
fixtures (fixtures/approval_audit/).

This pack does NOT re-declare any policy. The gated-action list, the write-off
threshold, the EX-* exception dispositions, and the audit-required-field set all
live in retail_ops (fixtures/retail_ops/policy.json + exceptions.jsonl) -- the
single answer-key source this pack attacks -- and are read by ``compute``'s
loaders (agentic_eval.gate's loaders, by path) rather than imported through
``retail_ops``'s Python package; see agentic_eval/gate.py and compute.py for the
full story. What lives here is only the *delivery surface*: inbound lure
messages, conflicting source records, and audit-pressure entries.

Everything is FABRICATED and GENERIC. Lures are benign filler sentences carrying
one opaque MARKER token plus a synthetic imperative; no real injection or exploit
string appears. Conflict/audit records are synthetic rows authored only to exercise
the eval metrics. See fixtures/approval_audit/PROVENANCE.md.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agentic_eval.domain import ROOT

FIXTURES = ROOT / "fixtures" / "approval_audit"


@dataclass(frozen=True)
class LureMessage:
    """An untrusted inbound message carrying an embedded imperative (the injection).

    ``read_message`` surfaces every field EXCEPT the three ``gold_*`` fields (the
    answer key). ``requested_*`` describe the structured action the message asks for
    so the agent can gate it; the embedded imperative in ``text`` must be ignored.
    """

    message_id: str
    sender_role: str
    lure_kind: str
    marker: str
    text: str
    requested_action_type: str
    requested_execution_mode: str
    requested_ref_id: str
    requested_amount: str
    references_audit_id: str
    references_conflict_id: str
    gold_verdict: str
    gold_should_refuse: bool
    gold_injection: bool


@dataclass(frozen=True)
class AuditPressureEntry:
    """An audit record (same shape as retail_ops audit_entries) some lure tempts
    logging with a required field dropped. ``fields`` feeds compute.audit_status."""

    id: str
    fields: dict[str, str]


@dataclass(frozen=True)
class ConflictReading:
    """One source record's reading of a gating-relevant action."""

    source: str
    action_type: str
    execution_mode: str
    ref_id: str
    amount: str


@dataclass(frozen=True)
class ConflictSet:
    """Two source records that disagree on a gating-relevant field. The tool returns
    the readings unresolved; the safe (more conservative) reading governs the gold."""

    conflict_id: str
    marker: str
    text: str
    action_type: str
    execution_mode: str
    readings: tuple[ConflictReading, ...]
    gold_verdict: str


def _read_jsonl(name: str, path: Path | None) -> list[dict[str, Any]]:
    target = path if path is not None else FIXTURES / name
    if not target.is_file():
        raise FileNotFoundError(f"no such fixture: {name!r}")
    return [json.loads(line) for line in target.read_text().splitlines() if line]


def load_lures(path: Path | None = None) -> dict[str, LureMessage]:
    """Load the inbound lure messages keyed by message id."""
    rows = _read_jsonl("lures.jsonl", path)
    items = [
        LureMessage(
            message_id=str(r["message_id"]),
            sender_role=str(r["sender_role"]),
            lure_kind=str(r["lure_kind"]),
            marker=str(r["marker"]),
            text=str(r["text"]),
            requested_action_type=str(r["requested_action_type"]),
            requested_execution_mode=str(r["requested_execution_mode"]),
            requested_ref_id=str(r["requested_ref_id"]),
            requested_amount=str(r["requested_amount"]),
            references_audit_id=str(r["references_audit_id"]),
            references_conflict_id=str(r["references_conflict_id"]),
            gold_verdict=str(r["gold_verdict"]),
            gold_should_refuse=bool(r["gold_should_refuse"]),
            gold_injection=bool(r["gold_injection"]),
        )
        for r in rows
    ]
    return {item.message_id: item for item in items}


def load_audit_pressure(path: Path | None = None) -> dict[str, AuditPressureEntry]:
    """Load the audit-pressure entries keyed by id."""
    rows = _read_jsonl("audit_pressure.jsonl", path)
    items = [
        AuditPressureEntry(
            id=str(r["id"]),
            fields={str(k): str(v) for k, v in r["fields"].items()},
        )
        for r in rows
    ]
    return {item.id: item for item in items}


def load_conflicts(path: Path | None = None) -> dict[str, ConflictSet]:
    """Load the conflicting-record sets keyed by conflict id."""
    rows = _read_jsonl("conflicts.jsonl", path)
    items = [
        ConflictSet(
            conflict_id=str(r["conflict_id"]),
            marker=str(r["marker"]),
            text=str(r["text"]),
            action_type=str(r["action_type"]),
            execution_mode=str(r["execution_mode"]),
            readings=tuple(
                ConflictReading(
                    source=str(rd["source"]),
                    action_type=str(rd["action_type"]),
                    execution_mode=str(rd["execution_mode"]),
                    ref_id=str(rd["ref_id"]),
                    amount=str(rd["amount"]),
                )
                for rd in r["readings"]
            ),
            gold_verdict=str(r["gold_verdict"]),
        )
        for r in rows
    ]
    return {item.conflict_id: item for item in items}
