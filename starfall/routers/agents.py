import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from agents.orchestrator import AGENTS, run_agent
from starfall.database import get_db
from starfall.models import AgentRun, Client
from starfall.manifest import list_starship_registry
from starfall.routers.marketplace import get_current_client
from starfall.schemas import AgentRunOut, AgentRunRequest, LaunchBrokerChatRequest, MissionGuideChatRequest

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=list[str])
def list_agents() -> list[str]:
    return list(AGENTS.keys())


@router.post("/{agent_id}/run", response_model=AgentRunOut)
def trigger_agent(
    agent_id: str,
    payload: AgentRunRequest,
    db: Session = Depends(get_db),
) -> AgentRunOut:
    if agent_id not in AGENTS:
        raise HTTPException(status_code=404, detail=f"Unknown agent '{agent_id}'")
    return run_agent(db, agent_id, payload.trigger, payload.payload)


@router.post("/launch_broker/chat")
def launch_broker_chat(
    body: LaunchBrokerChatRequest,
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    payload = body.model_dump(exclude_none=True)
    payload["client_id"] = client.id
    payload["instruction"] = body.instruction
    run = run_agent(db, "launch_broker", "chat", payload)
    try:
        output = json.loads(run.output_json or "{}")
    except json.JSONDecodeError:
        output = {}
    return {
        "message": output.get("message", ""),
        "action": output.get("action"),
        "data": output.get("data"),
        "suggestions": output.get("suggestions", []),
        "game_result": output.get("game_result"),
        "planner": output.get("planner"),
        "reasoning": run.reasoning,
        "run_id": run.id,
    }


@router.get("/launch_broker/registry")
def launch_broker_registry(
    ship_ref: str | None = None,
    container_code: str | None = None,
    _: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Structured manifest registry: booked containers per starship with package owners."""
    return list_starship_registry(db, ship_ref=ship_ref, container_code=container_code)


@router.post("/mission_guide/chat")
def mission_guide_chat(
    body: MissionGuideChatRequest,
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    payload = body.model_dump(exclude_none=True)
    payload["client_id"] = client.id
    payload["instruction"] = body.instruction
    run = run_agent(db, "mission_guide", "chat", payload)
    try:
        output = json.loads(run.output_json or "{}")
    except json.JSONDecodeError:
        output = {}
    return {
        "message": output.get("message", ""),
        "action": output.get("action"),
        "data": output.get("data"),
        "suggestions": output.get("suggestions", []),
        "game_result": output.get("game_result"),
        "reasoning": run.reasoning,
        "run_id": run.id,
    }


@router.get("/runs/{run_id}", response_model=AgentRunOut)
def get_agent_run(run_id: str, db: Session = Depends(get_db)) -> AgentRunOut:
    run = db.get(AgentRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found")
    return run
