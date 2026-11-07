"""Idea 8, MCP: let HR use Reporter's help-desk knowledge from any MCP client (Claude Desktop,
Claude Code, Cursor...). MCP is an open standard for connecting AI apps to tools and data.

What it exposes (read-only, organisation level, ONE tenant):
- list_policies, search_policies, preview_answer (ask as an employee *profile*, nothing recorded),
- list_faqs, helpdesk_stats (counts only), run_checks (evals, results not saved).
What it never exposes: employee names or emails, leave balances, ticket messages, candidates.

Runs locally over stdio, so nothing listens on the network. Install into its own environment
(the `mcp` package pins newer web libraries than the portals use):

    python -m venv .venv-mcp
    .venv-mcp/Scripts/pip install -r requirements-mcp.txt
    PP_MCP_TENANT_ID=1 .venv-mcp/Scripts/python -m peoplepilot.mcp_server

Claude Desktop config (claude_desktop_config.json):
    {"mcpServers": {"reporter": {"command": "<path>/.venv-mcp/Scripts/python.exe",
      "args": ["-m", "peoplepilot.mcp_server"], "cwd": "<path>/backend",
      "env": {"PP_MCP_TENANT_ID": "1"}}}}
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import timedelta

from mcp.server.fastmcp import FastMCP
from sqlalchemy import select

from .assist.answer import ask
from .assist.evals import ROUTE_OF, run_all, test_employee
from .assist.retrieve import search
from .db import scoped, session_scope, set_tenant, utcnow
from .models import AskEvent, EvalCase, FaqOverride, HrTicket, Policy
from .security.redact import install_log_redaction

mcp = FastMCP("reporter-hr")


def _tenant() -> int:
    raw = os.environ.get("PP_MCP_TENANT_ID", "")
    if not raw.isdigit():
        raise RuntimeError("Set PP_MCP_TENANT_ID to your organisation's id (1 for a single-company install)")
    return int(raw)


@contextmanager
def _session():
    s = session_scope()
    try:
        set_tenant(s, _tenant())
        yield s
    finally:
        s.rollback()  # read-only: never commit anything from MCP
        s.close()


def _profile(location: str, grade: str, employment_type: str):
    return test_employee(_tenant(), EvalCase(question="", expect_route="", as_location=location[:100],
                                             as_grade=grade[:50], as_employment_type=employment_type[:50]))


@mcp.tool()
def list_policies() -> list[dict]:
    """All HR policy versions: title, version, status, effective date and who they apply to."""
    with _session() as s:
        return [{"id": p.id, "title": p.title, "version": p.version, "status": p.status,
                 "effective_from": p.effective_from.isoformat(), "locations": p.locations or ["all"],
                 "grades": p.grades or ["all"], "employment_types": p.employment_types or ["all"]}
                for p in s.scalars(scoped(Policy, _tenant()).order_by(Policy.title, Policy.id))]


@mcp.tool()
def search_policies(query: str, location: str = "", grade: str = "", employment_type: str = "") -> list[dict]:
    """Find the active policy clauses that answer `query` for an employee with this location/grade/type."""
    from datetime import date

    with _session() as s:
        hits = search(s, _profile(location, grade, employment_type), query[:300], date.today(), k=5)
        return [{"policy": h.policy.title, "version": h.policy.version, "ref": h.clause.ref,
                 "heading": h.clause.heading, "text": h.clause.text, "keyword_coverage": round(h.coverage, 2),
                 "semantic_similarity": round(h.similarity, 2), "strong_match": h.relevant} for h in hits]


@mcp.tool()
def preview_answer(question: str, location: str = "", grade: str = "", employment_type: str = "") -> dict:
    """What the employee assistant would reply to `question` for this profile. Nothing is recorded."""
    with _session() as s:
        res = ask(s, _profile(location, grade, employment_type), question[:1000], record=False)
        out = res.public()
        out["route"] = ROUTE_OF.get(res.kind, res.kind)
        return out


@mcp.tool()
def list_faqs() -> list[dict]:
    """HR-written answers that take priority over policy search."""
    with _session() as s:
        return [{"question": f.question, "answer": f.answer, "active": f.active}
                for f in s.scalars(scoped(FaqOverride, _tenant()))]


@mcp.tool()
def helpdesk_stats(days: int = 7) -> dict:
    """Organisation-level counts for the last `days` days: questions by route, open tickets, model usage."""
    days = max(1, min(days, 90))
    with _session() as s:
        evs = list(s.scalars(scoped(AskEvent, _tenant()).where(AskEvent.created_at >= utcnow() - timedelta(days=days))))
        routes: dict[str, int] = {}
        for e in evs:
            routes[e.route] = routes.get(e.route, 0) + 1
        open_tickets = len(list(s.scalars(select(HrTicket.id).where(HrTicket.tenant_id == _tenant(),
                                                                    HrTicket.status == "open"))))
        return {"days": days, "questions": len(evs), "by_route": routes, "open_tickets": open_tickets,
                "model_calls": sum(e.used_llm for e in evs), "tokens_in": sum(e.tokens_in for e in evs),
                "tokens_out": sum(e.tokens_out for e in evs)}


@mcp.tool()
def run_checks() -> dict:
    """Run HR's test questions (evals) and return the score. Results are not saved from here."""
    with _session() as s:
        return run_all(s, _tenant()).as_dict()


def main() -> None:
    install_log_redaction()
    _tenant()
    mcp.run()  # stdio


if __name__ == "__main__":
    main()
