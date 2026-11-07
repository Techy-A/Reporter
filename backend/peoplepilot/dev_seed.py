"""Dev only: load the sample help-desk data from backend/samples into organisation 1.

    python -m peoplepilot.dev_seed

Adds/updates the sample employees, makes the sample Leave Policy live, uploads sample leave
balances, one FAQ answer, sensitive-topic contacts and a few checks. Refuses to run in prod.
"""
from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from sqlalchemy import select

from .assist.parse import split_clauses
from .config import get_settings
from .db import init_db, session_scope
from .models import AdminUser, EvalCase, Employee, FaqOverride, LeaveBalance, Policy, PolicyClause, Tenant

SAMPLES = Path(__file__).resolve().parent.parent / "samples"


def main() -> None:
    if get_settings().env == "prod":
        raise SystemExit("dev_seed is for development only")
    init_db()
    s = session_scope()
    try:
        tenant = s.scalars(select(Tenant).order_by(Tenant.id)).first()
        owner = s.scalars(select(AdminUser).where(AdminUser.tenant_id == tenant.id).order_by(AdminUser.id)).first() \
            if tenant else None
        if not tenant or not owner:
            raise SystemExit("Finish first-run setup in the admin portal first")
        tid = tenant.id
        tenant.ic_contact = tenant.ic_contact or "Meera Iyer, Internal Committee · ic@acme.co.in · ext 2104"
        tenant.hr_contact = tenant.hr_contact or "hr@acme.co.in · 080 4000 1234"

        emps = {e.email: e for e in s.scalars(select(Employee).where(Employee.tenant_id == tid))}
        with open(SAMPLES / "employees.csv", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                e = emps.get(r["email"]) or Employee(tenant_id=tid, email=r["email"], name=r["name"],
                                                     is_interviewer=r["interviewer"] == "yes")
                e.location, e.grade, e.employment_type = r["location"], r["grade"], r["employment_type"]
                s.add(e)
                emps[e.email] = e
        s.flush()

        if not s.scalars(select(Policy).where(Policy.tenant_id == tid, Policy.title == "Leave Policy")).first():
            p = Policy(tenant_id=tid, title="Leave Policy", version="2026-01", effective_from=date(2026, 1, 1),
                       status="active", source_name="leave_policy.md", created_by=owner.id)
            s.add(p)
            s.flush()
            text = (SAMPLES / "leave_policy.md").read_text(encoding="utf-8")
            for i, c in enumerate(split_clauses(text)):
                s.add(PolicyClause(tenant_id=tid, policy_id=p.id, position=i, ref=c.ref, heading=c.heading, text=c.text))

        with open(SAMPLES / "leave_balances.csv", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                e = emps.get(r["email"])
                if not e:
                    continue
                row = s.scalars(select(LeaveBalance).where(LeaveBalance.employee_id == e.id,
                                                           LeaveBalance.leave_type == r["leave_type"])).first()
                row = row or LeaveBalance(tenant_id=tid, employee_id=e.id, leave_type=r["leave_type"], balance=0,
                                          as_of=date.today())
                row.balance, row.as_of = float(r["balance"]), date.fromisoformat(r["as_of"])
                s.add(row)

        if not s.scalars(select(FaqOverride).where(FaqOverride.tenant_id == tid)).first():
            s.add(FaqOverride(tenant_id=tid, created_by=owner.id, question="Who do I contact for referrals?",
                              answer="Send referrals to talent@acme.co.in with the CV and the role. Referral bonus "
                                     "is paid after the new joiner completes 90 days."))
        if not s.scalars(select(EvalCase).where(EvalCase.tenant_id == tid)).first():
            for q, route, ref in (("Can I club sick and casual leave?", "policy", "4.2"),
                                  ("Is POSH training mandatory?", "policy", "7.1"),
                                  ("My manager is harassing me", "sensitive", ""),
                                  ("Who handles referrals?", "faq", ""),
                                  ("What's on the canteen menu?", "no_answer", "")):
                s.add(EvalCase(tenant_id=tid, created_by=owner.id, question=q, expect_route=route, expect_ref=ref,
                               expect_policy_title="Leave Policy" if route == "policy" else ""))
        s.commit()
        print("Sample help-desk data loaded.")
    finally:
        s.close()


if __name__ == "__main__":
    main()
