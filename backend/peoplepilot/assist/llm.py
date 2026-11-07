"""Talking to the language model: ideas 1 (tokens), 3 (next token) and 4 (context window).

- Tokens: a model reads and writes tokens, not words. We estimate them (~4 characters each) to
  stay inside a budget BEFORE calling, and record the real counts the server reports AFTER.
- Next token: the model writes one token at a time, picking from probabilities. temperature=0
  makes it pick the most likely token every time, so the same question gets the same answer,
  and max_tokens caps how long it can ramble.
- Context window: the model only "knows" what we put in front of it. pack_context() fits the most
  relevant policy clauses into a fixed budget (PP_LLM_CONTEXT_TOKENS) and labels each one [C1],
  [C2]... so the answer can cite them and we can check the citations.

Any OpenAI-compatible server works: local Ollama (free), or a key you already have.
"""
from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass, field

import httpx

from ..config import get_settings

log = logging.getLogger("peoplepilot.llm")


def enabled() -> bool:
    s = get_settings()
    return bool(s.llm_base_url and s.llm_model)


def approx_tokens(text: str) -> int:
    """Rough token count (English averages ~4 characters per token). Used for budgeting only."""
    return math.ceil(len(text) / 4)


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: str  # raw JSON string from the model; parsed and validated by the caller


@dataclass
class ChatResult:
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    tokens_in: int = 0
    tokens_out: int = 0
    assistant_message: dict = field(default_factory=dict)  # to append back into the conversation


class LLMError(RuntimeError):
    pass


def chat(messages: list[dict], tools: list[dict] | None = None) -> ChatResult:
    s = get_settings()
    if not enabled():
        raise LLMError("no model configured")
    body: dict = {
        "model": s.llm_model,
        "messages": messages,
        "temperature": 0,  # always take the most likely next token: repeatable answers
        "max_tokens": s.llm_max_output_tokens,
    }
    if tools:
        body["tools"] = tools
        body["tool_choice"] = "auto"
    try:
        resp = httpx.post(
            s.llm_base_url.rstrip("/") + "/chat/completions",
            headers={"Authorization": f"Bearer {s.llm_api_key}"} if s.llm_api_key else {},
            json=body,
            timeout=90,
        )
        resp.raise_for_status()
        data = resp.json()
        msg = data["choices"][0]["message"]
    except Exception as exc:
        log.warning("LLM call failed: %s", type(exc).__name__)
        raise LLMError(type(exc).__name__) from exc
    usage = data.get("usage") or {}
    calls = []
    for tc in msg.get("tool_calls") or []:
        fn = tc.get("function") or {}
        args = fn.get("arguments")
        calls.append(ToolCall(id=str(tc.get("id") or fn.get("name")), name=str(fn.get("name")),
                              arguments=args if isinstance(args, str) else json.dumps(args or {})))
    content = msg.get("content") or ""
    return ChatResult(
        content=content,
        tool_calls=calls,
        tokens_in=int(usage.get("prompt_tokens") or approx_tokens(json.dumps(messages))),
        tokens_out=int(usage.get("completion_tokens") or approx_tokens(content)),
        assistant_message={"role": "assistant", "content": content,
                           **({"tool_calls": msg["tool_calls"]} if msg.get("tool_calls") else {})},
    )


def parse_json_object(text: str) -> dict | None:
    """Pull the first {...} object out of a model reply. Returns None if there isn't a valid one."""
    try:
        start, end = text.index("{"), text.rindex("}") + 1
        data = json.loads(text[start:end])
    except (ValueError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


@dataclass
class Packed:
    label: str  # "C1"
    hit: object  # retrieve.Hit
    text: str  # possibly trimmed to fit the budget


def pack_context(hits: list, budget_tokens: int, start: int = 1) -> list[Packed]:
    """Fit clauses (best first) into the token budget. The last one may be trimmed; the rest are
    left out entirely rather than half-included."""
    out: list[Packed] = []
    used = 0
    for i, h in enumerate(hits, start=start):
        header = f"[C{i}] {h.policy.title} (version {h.policy.version}) §{h.clause.ref or '-'} {h.clause.heading}\n"
        body = h.clause.text
        cost = approx_tokens(header + body)
        if used + cost > budget_tokens:
            room = (budget_tokens - used - approx_tokens(header)) * 4
            if room < 200:
                break
            body = body[:room].rsplit(" ", 1)[0] + " …"
            cost = approx_tokens(header + body)
        out.append(Packed(f"C{i}", h, body))
        used += cost
        if used >= budget_tokens:
            break
    return out


def render_context(packed: list[Packed]) -> str:
    return "\n\n".join(
        f"[{p.label}] {p.hit.policy.title} (version {p.hit.policy.version}) "
        f"§{p.hit.clause.ref or '-'} {p.hit.clause.heading}\n{p.text}" for p in packed)
