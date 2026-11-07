"""Free, local retrieval: BM25 over policy clauses, with English + Hinglish normalisation.

Why not embeddings? A company's HR policies are a few hundred clauses. Keyword ranking with
synonyms is fast, explainable, needs no model or GPU, and costs nothing. Retrieval is always
FILTERED first (tenant, active version, effective date, the employee's location/grade/type), so
a clause the employee isn't covered by can never be cited to them.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Employee, Policy, PolicyClause

_STOP = set("""
a an the and or of to in on at for from by with about as is are was were be been being am do does did done
have has had having i me my mine we our you your he she it its they them their this that these those what
which who whom whose when where why how can could would should shall will may might must if then than so
not no any some all per each every there here please tell know want need get got also just like into out
up down over under again more most other such only own same too very s t don doesn isn
kya kitni kitne kitna kab hai hain ho hota hoti hote mera meri mere mujhe hum humko ka ki ke ko se me mein
kaise karna karne kar sakta sakti sakte milegi milta milti milega chahiye ye yeh woh wo aur bhi toh to na
main hoon hun hu mai apna apni apne
""".split())

# Variants -> canonical term. Applied to both questions and clauses.
_SYNONYMS = {
    "chutti": "leave", "chhutti": "leave", "chuti": "leave", "chhuti": "leave", "leaves": "leave",
    "holiday": "holiday", "holidays": "holiday",
    "wfh": "remote", "remote": "remote", "hybrid": "remote",
    "pf": "provident", "epf": "provident", "ppf": "provident",
    "ot": "overtime", "overtime": "overtime",
    "cl": "casual", "sl": "sick", "el": "earned", "pl": "earned", "privilege": "earned",
    "sick": "sick", "bimar": "sick", "bimaar": "sick", "medical": "sick",
    "hike": "appraisal", "increment": "appraisal", "appraisal": "appraisal", "review": "appraisal",
    "resign": "resignation", "resigning": "resignation", "quit": "resignation", "resignation": "resignation",
    "buyout": "buyout", "buy": "buyout",
    "salary": "pay", "payroll": "pay", "payslip": "pay", "tankhwah": "pay",
    "refer": "referral", "referral": "referral", "referrals": "referral",
    "training": "training", "trainings": "training", "course": "training", "lms": "training",
    "mandatory": "mandatory", "compulsory": "mandatory", "zaroori": "mandatory", "required": "mandatory",
    "club": "combine", "clubbing": "combine", "combine": "combine", "together": "combine",
    "nominee": "nomination", "nomination": "nomination",
    "maternity": "maternity", "paternity": "paternity",
}


def _stem(t: str) -> str:
    if len(t) > 4 and t.endswith("ies"):
        return t[:-3] + "y"
    if len(t) > 5 and t.endswith("ing"):
        return t[:-3]
    if len(t) > 4 and t.endswith("ed"):
        return t[:-2]
    if len(t) > 3 and t.endswith("s") and not t.endswith("ss"):
        return t[:-1]
    return t


def tokens(text: str) -> list[str]:
    out = []
    for raw in re.findall(r"[a-z0-9]+", text.lower()):
        if raw in _SYNONYMS:
            out.append(_SYNONYMS[raw])
            continue
        if raw in _STOP or len(raw) < 2:
            continue
        t = _stem(raw)
        out.append(_SYNONYMS.get(t, t))
    return out


@dataclass
class Hit:
    clause: PolicyClause
    policy: Policy
    score: float  # fused rank score (higher is better)
    coverage: float  # share of the question's terms found in this clause (keyword evidence)
    similarity: float = 0.0  # cosine similarity from embeddings (semantic evidence), 0 if unused

    @property
    def relevant(self) -> bool:
        """Enough evidence to show this clause to an employee."""
        return self.coverage >= MIN_COVERAGE or self.similarity >= MIN_SIMILARITY


MIN_COVERAGE = 0.5
MIN_SIMILARITY = 0.62
RRF_K = 60  # reciprocal-rank fusion constant


def applies_to(policy: Policy, emp: Employee, today: date) -> bool:
    if policy.status != "active" or policy.effective_from > today:
        return False

    def ok(values: list, mine: str) -> bool:
        return not values or (mine or "").strip().lower() in {str(v).strip().lower() for v in values}

    return ok(policy.locations, emp.location) and ok(policy.grades, emp.grade) and \
        ok(policy.employment_types, emp.employment_type)


def search(session: Session, emp: Employee, question: str, today: date, k: int = 4) -> list[Hit]:
    """Hybrid retrieval (idea 5, RAG): filter by audience, rank with BM25, optionally fuse with
    embedding similarity (idea 2) using reciprocal-rank fusion."""
    from . import embed  # local import: keeps this module importable without httpx config

    q = tokens(question)
    policies = {p.id: p for p in session.scalars(
        select(Policy).where(Policy.tenant_id == emp.tenant_id, Policy.status == "active"))
        if applies_to(p, emp, today)}
    if not policies:
        return []
    clauses = list(session.scalars(select(PolicyClause).where(
        PolicyClause.tenant_id == emp.tenant_id, PolicyClause.policy_id.in_(policies))))
    if not clauses:
        return []

    # ---- keyword ranking (BM25)
    bm25: dict[int, float] = {}
    coverage: dict[int, float] = {}
    if q:
        docs = []
        for c in clauses:
            p = policies[c.policy_id]
            # Headings and the policy title count twice: "Sick leave" in a heading is a strong signal.
            docs.append(tokens(f"{c.heading} {c.heading} {p.title} {c.text}"))
        n = len(docs)
        avgdl = sum(len(d) for d in docs) / n or 1
        df = Counter(t for d in docs for t in set(d))
        qset = list(dict.fromkeys(q))
        k1, b = 1.4, 0.75
        for c, d in zip(clauses, docs):
            tf = Counter(d)
            score, found = 0.0, 0
            for t in qset:
                if not tf[t]:
                    continue
                found += 1
                idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
                score += idf * tf[t] * (k1 + 1) / (tf[t] + k1 * (1 - b + b * len(d) / avgdl))
            if score > 0:
                bm25[c.id] = score
                coverage[c.id] = found / len(qset)

    # ---- semantic ranking (embeddings), only when a model is configured and vectors exist
    sim: dict[int, float] = {}
    if embed.enabled():
        from ..config import get_settings

        model = get_settings().embed_model
        with_vec = [c for c in clauses if c.embedding and c.embed_model == model]
        qv = embed.embed_query(question) if with_vec else None
        if qv:
            sim = {c.id: embed.cosine(qv, c.embedding) for c in with_vec}

    # ---- reciprocal-rank fusion
    fused: dict[int, float] = {}
    for ranking in (sorted(bm25, key=bm25.get, reverse=True), sorted(sim, key=sim.get, reverse=True)):
        for rank, cid in enumerate(ranking):
            fused[cid] = fused.get(cid, 0.0) + 1.0 / (RRF_K + rank + 1)
    by_id = {c.id: c for c in clauses}
    hits = [Hit(by_id[cid], policies[by_id[cid].policy_id], s, coverage.get(cid, 0.0), sim.get(cid, 0.0))
            for cid, s in fused.items()]
    hits.sort(key=lambda h: (h.score, h.coverage, h.similarity), reverse=True)
    return hits[:k]


_FAQ_FILLER = {"contact", "handle", "ask", "find", "help", "process", "procedure", "way", "person", "someone",
               "team", "reach", "send", "submit", "apply", "check", "info", "information", "detail"}


def faq_match_score(question: str, faq_question: str) -> float:
    """How well an employee's question matches an HR-written FAQ (0..1)."""
    q, f = set(tokens(question)), set(tokens(faq_question))
    # "Who handles referrals?" should match "Who do I contact for referrals?": ignore filler verbs
    # as long as something more specific is left on both sides.
    if q - _FAQ_FILLER and f - _FAQ_FILLER:
        q, f = q - _FAQ_FILLER, f - _FAQ_FILLER
    if not q or not f:
        return 0.0
    both = len(q & f)
    return min(both / len(f), both / len(q) + 0.25)
