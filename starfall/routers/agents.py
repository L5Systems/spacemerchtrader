from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from starfall.database import get_db
from starfall.models import AgentRun
from starfall.schemas import AgentRunOut, AgentRunRequest
from agents.orchestrator import AGENTS, run_agent

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


@router.get("/runs/{run_id}", response_model=AgentRunOut)
def get_agent_run(run_id: str, db: Session = Depends(get_db)) -> AgentRunOut:
    run = db.get(AgentRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found")
    return run
