from typing import Any

from sqlalchemy.orm import Session

from agents.base import BaseAgent
from starfall.mission_guide import guide_respond


class MissionGuideAgent(BaseAgent):
    agent_id = "mission_guide"

    def run(self, db: Session, payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
        instruction = str(payload.get("instruction") or payload.get("message") or "")
        client_id = payload.get("client_id")
        result = guide_respond(db, client_id, instruction, payload)
        reasoning = f"Mission guide action: {result.get('action', 'help')}"
        return result, reasoning
