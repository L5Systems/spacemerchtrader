"""Guided delivery contract missions with step scoring and player-reported progress."""

from __future__ import annotations

import json
import logging
import random
import re
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx
from sqlalchemy.orm import Session

from starfall.config import settings
from starfall.llm_http import llm_http_client
from starfall.models import Container, GuidedMission, GuidedMissionStatus, PlayerProfile

logger = logging.getLogger(__name__)

COMPANIES = [
    "Helios Mining Corp",
    "RedDust Logistics",
    "Orbital Foundry Group",
    "Nova AgriTech",
    "Titan Heavy Industries",
    "ElonsTown Municipal Supply",
]

CARGO_CATALOG = [
    ("mining welding gear", 100, "20x40x50"),
    ("precision drill bits", 45, "15x30x25"),
    ("habitat air scrubbers", 80, "30x30x40"),
    ("hydroponic nutrient packs", 60, "25x35x30"),
    ("EVA suit repair kits", 35, "18x22x28"),
    ("fusion coolant cells", 120, "22x38x45"),
]

DESTINATIONS = [
    {
        "destination": "ElonsTown, Mars",
        "destination_system": "mars",
        "customs_authority": "Mars Customs Authority",
        "lead_days": 45,
    },
    {
        "destination": "New Armstrong Dome, Luna",
        "destination_system": "luna",
        "customs_authority": "Lunar Trade Office",
        "lead_days": 21,
    },
    {
        "destination": "Vega Station Alpha",
        "destination_system": "vega",
        "customs_authority": "Vega Import Control",
        "lead_days": 30,
    },
    {
        "destination": "Kepler Rim Depot",
        "destination_system": "kepler",
        "customs_authority": "Rim Compliance Bureau",
        "lead_days": 55,
    },
]

DEFAULT_DELIVERY_STEPS: list[dict[str, Any]] = [
    {
        "id": "accept",
        "title": "Accept contract",
        "prompt": "Review the contract terms and reply ACCEPT to begin the mission.",
        "max_points": 10,
        "accept_keywords": ["accept", "confirmed", "agreed", "understood"],
    },
    {
        "id": "container",
        "title": "Place container",
        "prompt": "Have you placed a container? Reply with your Container ID (e.g. CNT-MARS-001).",
        "max_points": 15,
        "required_patterns": [r"cnt[-\w]+"],
        "verify_container": True,
    },
    {
        "id": "procure_pack",
        "title": "Procure and pack cargo",
        "prompt": "Have you purchased the equipment and packed the container? Describe what you loaded.",
        "max_points": 15,
        "min_words": 6,
        "cargo_keywords": True,
    },
    {
        "id": "manifest",
        "title": "Manifest shipment",
        "prompt": "Create a manifest entry. Provide a package ID and whether it is outbound or return leg.",
        "max_points": 10,
        "required_patterns": [r"pkg[-\w]+"],
    },
    {
        "id": "launch_book",
        "title": "Book launch capacity",
        "prompt": "Book orbital or interplanetary launch capacity. State your slot or booking reference.",
        "max_points": 15,
        "required_patterns": [r"(slot[-\w]+|booking|launch|berth|stack)"],
    },
    {
        "id": "customs",
        "title": "Destination customs & compliance",
        "prompt": "File destination customs and import forms before arrival. Name the forms filed.",
        "max_points": 15,
        "compliance_keywords": ["customs", "form", "import", "declaration", "cleared", "filing"],
        "penalty_if_missing": 20,
        "compliance_step": True,
    },
    {
        "id": "transit",
        "title": "In-transit handoff",
        "prompt": "Confirm porter or offworld delivery handoff toward the destination endpoint.",
        "max_points": 10,
        "required_patterns": [r"(porter|handoff|delivery|endpoint|transit|carrier)"],
    },
    {
        "id": "delivery_confirm",
        "title": "Confirm delivery",
        "prompt": "Confirm delivery at the destination by the required date with recipient acknowledgment.",
        "max_points": 10,
        "required_patterns": [r"(delivered|received|confirmed|signed|handed over)"],
        "destination_keywords": True,
    },
]


def _touch(record) -> None:
    record.updated_at = datetime.now(timezone.utc)


def _load_steps(mission: GuidedMission) -> list[dict[str, Any]]:
    return json.loads(mission.steps_json or "[]")


def _load_step_results(mission: GuidedMission) -> dict[str, Any]:
    return json.loads(mission.step_results_json or "{}")


def _save_step_results(mission: GuidedMission, results: dict[str, Any]) -> None:
    mission.step_results_json = json.dumps(results)


def get_active_guided_mission(db: Session, client_id: str) -> GuidedMission | None:
    return (
        db.query(GuidedMission)
        .filter(
            GuidedMission.client_id == client_id,
            GuidedMission.status == GuidedMissionStatus.ACTIVE,
        )
        .order_by(GuidedMission.created_at.desc())
        .first()
    )


def _mission_brief(mission: GuidedMission) -> str:
    return (
        f"{mission.company_name} requests delivery of {mission.cargo_description} "
        f"({mission.dimensions_cm} cm, {mission.weight_kg:.0f} kg) to {mission.destination} "
        f"by {mission.required_delivery_date}."
    )


def mission_to_dict(mission: GuidedMission) -> dict[str, Any]:
    steps = _load_steps(mission)
    results = _load_step_results(mission)
    current = steps[mission.current_step_index] if mission.current_step_index < len(steps) else None
    completed_steps = [step["id"] for step in steps if step["id"] in results]
    return {
        "id": mission.id,
        "contract_code": mission.contract_code,
        "company_name": mission.company_name,
        "title": mission.title,
        "brief": _mission_brief(mission),
        "cargo_description": mission.cargo_description,
        "dimensions_cm": mission.dimensions_cm,
        "weight_kg": mission.weight_kg,
        "destination": mission.destination,
        "destination_system": mission.destination_system,
        "required_delivery_date": mission.required_delivery_date,
        "status": mission.status.value,
        "score": mission.score,
        "max_score": mission.max_score,
        "penalties": mission.penalties,
        "current_step_index": mission.current_step_index,
        "total_steps": len(steps),
        "current_step": current,
        "completed_steps": completed_steps,
        "step_results": results,
        "reward_credits": mission.reward_credits,
        "reward_xp": mission.reward_xp,
    }


def _generate_contract_payload(client_id: str, brief_hint: str | None = None) -> dict[str, Any]:
    company = random.choice(COMPANIES)
    cargo, weight, dims = random.choice(CARGO_CATALOG)
    dest = random.choice(DESTINATIONS)
    delivery = date.today() + timedelta(days=dest["lead_days"] + random.randint(5, 20))
    contract_code = f"CTR-{uuid.uuid4().hex[:6].upper()}"

    if brief_hint and len(brief_hint) > 10:
        cargo = brief_hint.strip()

    steps = []
    for step in DEFAULT_DELIVERY_STEPS:
        copied = dict(step)
        if copied["id"] == "customs":
            copied["prompt"] = (
                f"File {dest['customs_authority']} import forms before arrival. "
                "Reply with the forms filed (e.g. Mars customs declaration MC-12)."
            )
        if copied["id"] == "delivery_confirm":
            copied["prompt"] = (
                f"Confirm delivery at {dest['destination']} by {delivery.isoformat()} "
                "with recipient acknowledgment."
            )
        steps.append(copied)

    max_score = sum(step["max_points"] for step in steps)
    title = f"{company}: {cargo} to {dest['destination']}"

    return {
        "id": str(uuid.uuid4()),
        "client_id": client_id,
        "contract_code": contract_code,
        "company_name": company,
        "title": title,
        "cargo_description": cargo,
        "dimensions_cm": dims,
        "weight_kg": weight,
        "destination": dest["destination"],
        "destination_system": dest["destination_system"],
        "required_delivery_date": delivery.isoformat(),
        "reward_credits": round(1200 + weight * 4 + random.randint(0, 400), 2),
        "reward_xp": 180 + random.randint(0, 120),
        "steps_json": json.dumps(steps),
        "max_score": max_score,
    }


def _generate_with_llm(brief_hint: str | None) -> dict[str, Any] | None:
    if not settings.launch_broker_llm_api_key:
        return None

    prompt = (
        "Generate a sci-fi merchandise delivery contract as JSON with keys: "
        "company_name, cargo_description, dimensions_cm (AxBxC), weight_kg, "
        "destination, destination_system, required_delivery_date (YYYY-MM-DD), reward_credits, reward_xp."
    )
    if brief_hint:
        prompt += f" Base it on this request: {brief_hint}"

    body = {
        "model": settings.launch_broker_llm_model,
        "messages": [
            {"role": "system", "content": "Return strict JSON only."},
            {"role": "user", "content": prompt},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.7,
    }
    headers = {"Authorization": f"Bearer {settings.launch_broker_llm_api_key}"}
    url = f"{settings.launch_broker_llm_api_base.rstrip('/')}/chat/completions"

    try:
        with llm_http_client(timeout=25.0) as client:
            response = client.post(url, headers=headers, json=body)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            return json.loads(content)
    except Exception as exc:
        logger.warning("Mission guide LLM generation failed: %s", exc)
        return None


def generate_guided_mission(
    db: Session,
    client_id: str,
    *,
    brief_hint: str | None = None,
    replace_active: bool = False,
) -> GuidedMission:
    active = get_active_guided_mission(db, client_id)
    if active and not replace_active:
        raise ValueError(
            f"You already have active contract {active.contract_code}. "
            "Say 'mission status' or 'abandon mission' before generating a new one."
        )
    if active and replace_active:
        active.status = GuidedMissionStatus.ABANDONED
        _touch(active)

    payload = _generate_contract_payload(client_id, brief_hint)
    llm_data = _generate_with_llm(brief_hint)
    if llm_data:
        for key in (
            "company_name",
            "cargo_description",
            "dimensions_cm",
            "weight_kg",
            "destination",
            "destination_system",
            "required_delivery_date",
            "reward_credits",
            "reward_xp",
        ):
            if llm_data.get(key) is not None:
                payload[key] = llm_data[key]
        payload["title"] = (
            f"{payload['company_name']}: {payload['cargo_description']} to {payload['destination']}"
        )

    mission = GuidedMission(**payload)
    db.add(mission)
    db.commit()
    db.refresh(mission)
    return mission


def _word_count(text: str) -> int:
    return len(re.findall(r"\w+", text))


def _evaluate_submission(
    db: Session,
    mission: GuidedMission,
    step: dict[str, Any],
    submission: str,
    *,
    skipped: bool = False,
) -> tuple[int, int, str]:
    """Return (points_awarded, penalty_applied, feedback)."""
    max_points = int(step.get("max_points", 10))
    if skipped:
        penalty = int(step.get("penalty_if_missing", max_points))
        return 0, penalty, f"Step skipped. −{penalty} points for missing {step['title']}."

    text = submission.strip()
    lowered = text.lower()
    if not text:
        return 0, 5, "No details provided. −5 points. Please describe what you completed."

    if step.get("accept_keywords"):
        if any(word in lowered for word in step["accept_keywords"]):
            return max_points, 0, f"Contract accepted. +{max_points} points."
        return 0, 3, "Reply ACCEPT (or confirmed/agreed) to accept the contract."

    points = max_points
    feedback_parts: list[str] = []

    for pattern in step.get("required_patterns", []):
        if not re.search(pattern, text, re.IGNORECASE):
            points = max(0, points - 5)
            feedback_parts.append(f"missing expected detail matching `{pattern}`")

    if step.get("min_words") and _word_count(text) < int(step["min_words"]):
        points = max(0, points - 4)
        feedback_parts.append("needs a more detailed description")

    if step.get("cargo_keywords"):
        cargo_terms = mission.cargo_description.lower().split()
        if not any(term in lowered for term in cargo_terms if len(term) > 3):
            points = max(0, points - 4)
            feedback_parts.append(f"mention the cargo ({mission.cargo_description})")

    if step.get("compliance_step"):
        keywords = step.get("compliance_keywords", [])
        if not any(word in lowered for word in keywords):
            penalty = int(step.get("penalty_if_missing", 20))
            return 0, penalty, (
                f"No customs/compliance forms mentioned. −{penalty} points. "
                f"File import paperwork for {mission.destination}."
            )

    if step.get("destination_keywords"):
        dest_token = mission.destination.split(",")[0].lower()
        if dest_token not in lowered and mission.destination_system not in lowered:
            points = max(0, points - 3)
            feedback_parts.append(f"confirm arrival at {mission.destination}")

    if step.get("verify_container"):
        match = re.search(r"(cnt[-\w]+)", text, re.IGNORECASE)
        if match:
            code = match.group(1).upper()
            container = (
                db.query(Container)
                .filter(
                    Container.client_id == mission.client_id,
                    Container.container_code == code,
                )
                .first()
            )
            if container:
                points = min(max_points + 2, points + 2)
                feedback_parts.append(f"verified container {code} in your records (+2 bonus)")
            else:
                feedback_parts.append(
                    f"noted container {code} (not yet in Container Assembly — create it for a bonus)"
                )

    if feedback_parts:
        feedback = f"+{points} points. Notes: {'; '.join(feedback_parts)}."
    else:
        feedback = f"Step complete. +{points} points."
    penalty = max(0, max_points - points) if not step.get("compliance_step") else 0
    return points, penalty, feedback


def submit_guided_step(
    db: Session,
    client_id: str,
    submission: str,
    *,
    skip: bool = False,
) -> tuple[GuidedMission, dict[str, Any]]:
    mission = get_active_guided_mission(db, client_id)
    if not mission:
        raise ValueError("No active guided mission. Say 'generate mission' to receive a contract.")

    steps = _load_steps(mission)
    if mission.current_step_index >= len(steps):
        raise ValueError("Mission already completed. Say 'generate mission' for a new contract.")

    step = steps[mission.current_step_index]
    results = _load_step_results(mission)
    if step["id"] in results:
        raise ValueError(f"Step '{step['title']}' already completed. Check mission status.")

    points, penalty, feedback = _evaluate_submission(db, mission, step, submission, skipped=skip)
    results[step["id"]] = {
        "submission": submission,
        "points": points,
        "penalty": penalty,
        "feedback": feedback,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    mission.score += points
    mission.penalties += penalty
    mission.current_step_index += 1
    _save_step_results(mission, results)
    _touch(mission)

    game_result = None
    if mission.current_step_index >= len(steps):
        mission.status = GuidedMissionStatus.COMPLETED
        mission.completed_at = datetime.now(timezone.utc)
        game_result = _finalize_mission_rewards(db, mission)

    db.commit()
    db.refresh(mission)
    return mission, {"points": points, "penalty": penalty, "feedback": feedback, "game_result": game_result}


def _finalize_mission_rewards(db: Session, mission: GuidedMission) -> dict[str, Any]:
    profile = db.get(PlayerProfile, mission.client_id)
    if not profile:
        return {}

    ratio = mission.score / mission.max_score if mission.max_score else 0
    credits = round(mission.reward_credits * ratio, 2)
    xp = int(mission.reward_xp * ratio)
    profile.credits += credits
    profile.xp += xp
    profile.reputation += round(ratio * 5, 1)
    profile.missions_completed += 1
    from starfall.game import xp_to_level

    profile.level = xp_to_level(profile.xp)
    db.commit()
    return {
        "guided_mission_id": mission.id,
        "contract_code": mission.contract_code,
        "score": mission.score,
        "max_score": mission.max_score,
        "penalties": mission.penalties,
        "credits_earned": credits,
        "xp_gained": xp,
        "total_credits": round(profile.credits, 2),
        "outcome_detail": (
            f"Contract {mission.contract_code} closed with score "
            f"{mission.score}/{mission.max_score} (−{mission.penalties} penalties)."
        ),
    }


def abandon_guided_mission(db: Session, client_id: str) -> GuidedMission | None:
    mission = get_active_guided_mission(db, client_id)
    if not mission:
        return None
    mission.status = GuidedMissionStatus.ABANDONED
    _touch(mission)
    db.commit()
    db.refresh(mission)
    return mission


def format_status_message(mission: GuidedMission) -> str:
    data = mission_to_dict(mission)
    lines = [
        f"Contract {data['contract_code']} — {data['title']}",
        data["brief"],
        f"Score: {data['score']}/{data['max_score']} (penalties: −{data['penalties']})",
        f"Progress: step {min(data['current_step_index'] + 1, data['total_steps'])}/{data['total_steps']}",
    ]
    if data["status"] == GuidedMissionStatus.COMPLETED.value:
        lines.append("Status: COMPLETED")
        return "\n".join(lines)

    current = data.get("current_step")
    if current:
        lines.append(f"\nNext step — {current['title']}:")
        lines.append(current["prompt"])
    return "\n".join(lines)


def parse_guide_action(instruction: str, payload: dict[str, Any]) -> str:
    if payload.get("action"):
        return str(payload["action"]).lower()

    text = instruction.lower().strip()
    if any(word in text for word in ("help", "process", "what can you")):
        return "help"
    if any(phrase in text for phrase in ("generate", "new contract", "new mission", "create mission")):
        return "generate"
    if any(phrase in text for phrase in ("abandon", "cancel mission", "drop mission")):
        return "abandon"
    if any(phrase in text for phrase in ("status", "progress", "readout", "where am i", "mission status")):
        return "status"
    if text in ("accept", "confirmed", "agreed", "understood") or text.startswith("accept "):
        return "submit"
    if text.startswith("skip") or text == "skip step":
        return "submit"
    if any(phrase in text for phrase in ("report:", "submit:", "done:", "completed:")):
        return "submit"
    if len(text) > 12 and not text.startswith(("help", "generate", "abandon", "mission status")):
        return "submit"
    return "help"


def guide_respond(
    db: Session,
    client_id: str | None,
    instruction: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    action = parse_guide_action(instruction, payload)

    if action == "help":
        return {
            "message": (
                "I am your Mission Guide. I issue company delivery contracts and walk you through "
                "every logistics step — container, packing, manifest, launch, customs, and delivery.\n\n"
                "You report what you've done in plain language; I score thoroughness and compliance "
                "(e.g. −20 if you forget Mars customs forms).\n\n"
                "Try: generate mission · mission status · report: I placed container CNT-MARS-001"
            ),
            "action": action,
            "suggestions": [
                "generate mission",
                "generate mission: 100kg mining welding gear to ElonsTown on Mars",
                "mission status",
            ],
        }

    if not client_id:
        return {
            "message": "Sign in via Marketplace to receive guided delivery contracts.",
            "action": action,
            "suggestions": ["Sign in, then say: generate mission"],
        }

    if action == "generate":
        brief = payload.get("brief") or instruction
        if brief.lower().startswith("generate mission"):
            brief = brief.split(":", 1)[-1].strip() or None
        replace = "replace" in instruction.lower() or payload.get("replace") is True
        try:
            mission = generate_guided_mission(db, client_id, brief_hint=brief, replace_active=replace)
        except ValueError as exc:
            return {"message": str(exc), "action": action, "suggestions": ["mission status", "abandon mission"]}

        data = mission_to_dict(mission)
        current = data["current_step"]
        return {
            "message": (
                f"New contract {data['contract_code']}\n"
                f"{data['brief']}\n"
                f"Potential reward: {data['reward_credits']} cr / {data['reward_xp']} XP "
                f"(scaled by your final score out of {data['max_score']}).\n\n"
                f"Step 1 — {current['title']}:\n{current['prompt']}"
            ),
            "action": action,
            "data": {"mission": data},
            "suggestions": ["ACCEPT", "mission status"],
        }

    if action == "abandon":
        mission = abandon_guided_mission(db, client_id)
        if not mission:
            return {"message": "No active mission to abandon.", "action": action}
        return {
            "message": f"Abandoned contract {mission.contract_code}. Say 'generate mission' for a new one.",
            "action": action,
        }

    if action == "status":
        mission = get_active_guided_mission(db, client_id)
        if not mission:
            completed = (
                db.query(GuidedMission)
                .filter(
                    GuidedMission.client_id == client_id,
                    GuidedMission.status == GuidedMissionStatus.COMPLETED,
                )
                .order_by(GuidedMission.completed_at.desc())
                .first()
            )
            if completed:
                return {
                    "message": format_status_message(completed),
                    "action": action,
                    "data": {"mission": mission_to_dict(completed)},
                    "suggestions": ["generate mission"],
                }
            return {
                "message": "No active guided mission. Say 'generate mission' to receive a company contract.",
                "action": action,
                "suggestions": ["generate mission"],
            }
        return {
            "message": format_status_message(mission),
            "action": action,
            "data": {"mission": mission_to_dict(mission)},
            "suggestions": ["report your progress for the current step"],
        }

    if action == "submit":
        submission = instruction
        for prefix in ("report:", "submit:", "done:", "completed:"):
            if instruction.lower().startswith(prefix):
                submission = instruction.split(":", 1)[-1].strip()
                break
        skip = instruction.lower().strip().startswith("skip")
        try:
            mission, result = submit_guided_step(db, client_id, submission, skip=skip)
        except ValueError as exc:
            return {"message": str(exc), "action": action, "suggestions": ["mission status", "help"]}

        data = mission_to_dict(mission)
        lines = [result["feedback"], f"Score: {data['score']}/{data['max_score']} (−{data['penalties']} penalties)"]
        if mission.status == GuidedMissionStatus.COMPLETED:
            lines.append("Mission complete!")
            if result.get("game_result"):
                gr = result["game_result"]
                lines.append(
                    f"Earned {gr.get('credits_earned', 0)} cr and {gr.get('xp_gained', 0)} XP."
                )
        elif data.get("current_step"):
            step = data["current_step"]
            lines.append(f"\nNext step — {step['title']}:\n{step['prompt']}")

        response: dict[str, Any] = {
            "message": "\n".join(lines),
            "action": action,
            "data": {"mission": data, "step_result": result},
            "suggestions": ["mission status"],
        }
        if result.get("game_result"):
            response["game_result"] = result["game_result"]
        elif data.get("current_step"):
            response["suggestions"] = ["mission status", "skip step"]
        return response

    return guide_respond(db, client_id, "help", payload)
