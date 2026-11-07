"""Idea 9, evals: check the assistant against HR's own test questions before employees rely on it.

HR writes cases like "Can I club sick and casual leave?" -> expect a policy answer citing
Leave Policy §4.2. "Run checks" asks every question as a test employee (nothing is recorded)
and scores it. Re-run after every policy upload, FAQ edit or model change.

The headline numbers:
- pass rate: cases that got the expected route, source and phrase;
- sensitive recall: of the cases HR marked sensitive, how many went to a human. Must be 100%.

CLI:  python -m peoplepilot.assist.evals --tenant 1
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import utcnow
from ..models import Employee, EvalCase
from .answer import ask

ROUTE_OF = {"policy_answer": "policy", "policy_quote": "policy", "tool_answer": "agent"}


def test_employee(tenant_id: int, case: EvalCase) -> Employee:
    """A throwaway profile, never saved: it has no leave balances or tickets of its own."""
    return Employee(id=0, tenant_id=tenant_id, name="Test employee", email="", location=case.as_location,
                    grade=case.as_grade, employment_type=case.as_employment_type, is_interviewer=False)


def run_case(session: Session, tenant_id: int, case: EvalCase, today: date | None = None) -> tuple[bool, str]:
    res = ask(session, test_employee(tenant_id, case), case.question, today, record=False)
    route = ROUTE_OF.get(res.kind, res.kind)
    if route != case.expect_route:
        return False, f"Expected {case.expect_route}, got {route}"
    if case.expect_route == "policy":
        if case.expect_policy_title and not any(
                c.policy_title.strip().lower() == case.expect_policy_title.strip().lower() for c in res.citations):
            got = ", ".join(sorted({c.policy_title for c in res.citations})) or "no citation"
            return False, f"Expected a citation from {case.expect_policy_title}, got {got}"
        if case.expect_ref and not any(c.ref == case.expect_ref or c.ref.startswith(case.expect_ref + ".")
                                       for c in res.citations):
            return False, f"Expected §{case.expect_ref}, got " + (", ".join(f"§{c.ref}" for c in res.citations) or "none")
    if case.must_include:
        hay = (res.text + " " + " ".join(c.excerpt for c in res.citations)).lower()
        if case.must_include.lower() not in hay:
            return False, f'Answer doesn\'t mention "{case.must_include}"'
    return True, "Passed" + (" (model)" if res.used_llm else "")


@dataclass
class Report:
    total: int = 0
    passed: int = 0
    sensitive_total: int = 0
    sensitive_routed: int = 0
    failures: list[dict] = field(default_factory=list)

    @property
    def sensitive_recall(self) -> float | None:
        return self.sensitive_routed / self.sensitive_total if self.sensitive_total else None

    def as_dict(self) -> dict:
        return {"total": self.total, "passed": self.passed, "sensitive_total": self.sensitive_total,
                "sensitive_routed": self.sensitive_routed, "sensitive_recall": self.sensitive_recall,
                "failures": self.failures}


def run_all(session: Session, tenant_id: int, today: date | None = None) -> Report:
    rep = Report()
    now = utcnow()
    for case in session.scalars(select(EvalCase).where(EvalCase.tenant_id == tenant_id).order_by(EvalCase.id)):
        ok, detail = run_case(session, tenant_id, case, today)
        case.last_passed, case.last_detail, case.last_run_at = ok, detail[:300], now
        rep.total += 1
        rep.passed += ok
        if case.expect_route == "sensitive":
            rep.sensitive_total += 1
            rep.sensitive_routed += ok
        if not ok:
            rep.failures.append({"id": case.id, "question": case.question, "detail": detail})
    return rep


def main() -> None:  # pragma: no cover - CLI
    from ..db import session_scope

    ap = argparse.ArgumentParser(description="Run HR's test questions against the assistant")
    ap.add_argument("--tenant", type=int, required=True)
    args = ap.parse_args()
    session = session_scope()
    try:
        rep = run_all(session, args.tenant)
        session.commit()
    finally:
        session.close()
    print(f"{rep.passed}/{rep.total} passed")
    if rep.sensitive_recall is not None:
        print(f"Sensitive topics routed to a person: {rep.sensitive_routed}/{rep.sensitive_total}")
    for f in rep.failures:
        print(f"  ✗ #{f['id']} {f['question']}: {f['detail']}")
    raise SystemExit(0 if rep.passed == rep.total else 1)


if __name__ == "__main__":  # pragma: no cover
    main()
