"""Plan Launch Broker requests via tool selection (optional LLM + heuristic fallback)."""

from __future__ import annotations

import json
import logging
import re
from datetime import date
from typing import Any

import httpx

from starfall.config import settings
from starfall.llm_http import llm_http_client
from starfall.manifest import parse_date_hint, parse_month_hint

logger = logging.getLogger(__name__)

MANIFEST_TOOL_SPECS: list[dict[str, Any]] = [
    {
        "name": "query_registry",
        "description": (
            "Answer analytical questions about booked containers and package counts, "
            "optionally filtered by starship and launch date or month."
        ),
        "signals": [
            "how many",
            "how much",
            "count",
            "number of",
            "total packages",
            "total containers",
            "packages booked",
            "containers booked",
            "packages on",
            "containers on",
        ],
        "examples": [
            "How many packages are booked for Starship239 on 20 Sept 2032?",
            "How many containers are on starship239 in September 2032?",
        ],
    },
    {
        "name": "list_registry",
        "description": "List all booked containers on a starship with package and owner details.",
        "signals": [
            "manifest registry",
            "starship registry",
            "booked containers",
            "containers booked",
            "registry",
            "all containers on",
        ],
    },
    {
        "name": "list_packages",
        "description": "List packages on the signed-in player's booked container.",
        "signals": ["list package", "show package", "packages on my", "what packages", "my container"],
    },
    {
        "name": "find_slots",
        "description": "Find available LEO launch slots on a starship.",
        "signals": ["find", "search", "available slot", "open slot", "september", "2032", "leo"],
    },
    {
        "name": "book_slot",
        "description": "Book a launch slot for a container.",
        "signals": ["book slot", "book the slot", "reserve slot"],
    },
    {
        "name": "add_package",
        "description": "Place a package on the player's booked container.",
        "signals": ["add package", "place package", "load package", "create package"],
    },
    {
        "name": "advertise",
        "description": "Advertise outbound and return package capacity on a booked manifest.",
        "signals": ["advert"],
    },
    {
        "name": "validate_package",
        "description": "Validate a package for outbound or return manifest leg.",
        "signals": ["valid"],
    },
    {
        "name": "status",
        "description": "Show the player's active manifest progress.",
        "signals": ["status", "progress"],
    },
    {
        "name": "help",
        "description": "Explain how to use the Launch Broker.",
        "signals": ["help", "how do", "how to", "how can", "what can you"],
    },
]


def _tokenize(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", text.lower()) if len(token) > 1}


def _score_tool(text: str, spec: dict[str, Any]) -> float:
    lowered = text.lower()
    score = 0.0
    for signal in spec.get("signals", []):
        if signal in lowered:
            score += 3.0 + len(signal.split()) * 0.5
    description_tokens = _tokenize(spec.get("description", ""))
    overlap = len(_tokenize(lowered) & description_tokens)
    score += overlap * 0.35
    for example in spec.get("examples", []):
        if example.lower() in lowered:
            score += 5.0
    return score


def _extract_ship_ref(text: str, payload: dict[str, Any]) -> str | None:
    if payload.get("ship_ref"):
        return str(payload["ship_ref"]).lower()
    lowered = text.lower()
    if "starship239" in lowered or "starship 239" in lowered or "ss239" in lowered:
        return "starship239"
    match = re.search(r"starship\s*(\w+)", lowered)
    if match:
        return f"starship{match.group(1)}"
    return None


def _extract_params(tool: str, instruction: str, payload: dict[str, Any]) -> dict[str, Any]:
    params: dict[str, Any] = {}
    ship_ref = _extract_ship_ref(instruction, payload)
    if ship_ref:
        params["ship_ref"] = ship_ref

    if tool == "query_registry":
        date_hint = payload.get("date") or parse_date_hint(instruction)
        if date_hint:
            params["date"] = date_hint.isoformat()
        month_hint = payload.get("month") or parse_month_hint(instruction)
        if month_hint and "date" not in params:
            params["month"] = month_hint

        lowered = instruction.lower()
        if any(word in lowered for word in ("container", "containers", "berth", "berths", "slot", "slots")):
            if "package" not in lowered:
                params["metric"] = "containers"
            elif any(word in lowered for word in ("container", "containers")):
                params["metric"] = "both"
            else:
                params["metric"] = "packages"
        else:
            params["metric"] = "packages"

    if tool == "list_registry":
        match_container = re.search(r"(cnt[-\w]+)", instruction.lower())
        if match_container:
            params["container_code"] = match_container.group(1).upper()

    return params


def plan_with_heuristics(instruction: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    text = instruction.strip()
    if not text:
        return None

    ranked = sorted(
        ((spec["name"], _score_tool(text, spec)) for spec in MANIFEST_TOOL_SPECS),
        key=lambda item: item[1],
        reverse=True,
    )
    best_tool, best_score = ranked[0]
    if best_score < 2.5:
        return None

    second_score = ranked[1][1] if len(ranked) > 1 else 0.0
    confidence = min(1.0, best_score / 8.0)
    if best_score - second_score < 1.0 and best_tool != "query_registry":
        return None

    params = _extract_params(best_tool, text, payload)
    return {
        "tool": best_tool,
        "params": params,
        "confidence": round(confidence, 2),
        "source": "heuristic",
    }


def plan_with_llm(instruction: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    if not settings.launch_broker_llm_api_key:
        return None

    tool_lines = []
    for spec in MANIFEST_TOOL_SPECS:
        examples = "; ".join(spec.get("examples", [])[:2])
        tool_lines.append(
            f"- {spec['name']}: {spec['description']}"
            + (f" Examples: {examples}." if examples else "")
        )

    system_prompt = (
        "You route Launch Broker user requests to one manifest tool. "
        "Return strict JSON only with keys: tool (string), params (object), confidence (0-1). "
        "Allowed tools:\n"
        + "\n".join(tool_lines)
        + "\nParams may include: ship_ref, date (YYYY-MM-DD), month (YYYY-MM), "
        "metric (packages|containers|both), container_code, slot_id, package_id, leg."
    )

    body = {
        "model": settings.launch_broker_llm_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": instruction},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0,
    }

    headers = {"Authorization": f"Bearer {settings.launch_broker_llm_api_key}"}
    url = f"{settings.launch_broker_llm_api_base.rstrip('/')}/chat/completions"

    try:
        with llm_http_client(timeout=20.0) as client:
            response = client.post(url, headers=headers, json=body)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            parsed = json.loads(content)
    except Exception as exc:
        logger.warning("Launch broker LLM planner failed: %s", exc)
        return None

    tool = str(parsed.get("tool") or "").lower()
    allowed = {spec["name"] for spec in MANIFEST_TOOL_SPECS}
    if tool not in allowed:
        return None

    params = dict(parsed.get("params") or {})
    params.update(_extract_params(tool, instruction, {**payload, **params}))
    return {
        "tool": tool,
        "params": params,
        "confidence": float(parsed.get("confidence") or 0.8),
        "source": "llm",
    }


def plan_manifest_request(instruction: str, payload: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Select a manifest tool and parameters from natural language."""
    payload = payload or {}
    if payload.get("action"):
        return None

    if settings.launch_broker_use_llm:
        llm_plan = plan_with_llm(instruction, payload)
        if llm_plan and llm_plan.get("confidence", 0) >= 0.55:
            return llm_plan

    return plan_with_heuristics(instruction, payload)
