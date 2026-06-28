from typing import Any

from sqlalchemy.orm import Session

from agents.base import BaseAgent
from starfall.banking import banker_respond


class BankingAgent(BaseAgent):
    agent_id = "banking"

    def run(self, db: Session, payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
        instruction = str(payload.get("instruction") or payload.get("message") or "")
        client_id = payload.get("client_id")
        result = banker_respond(db, client_id, instruction, payload)
        reasoning = f"Banking action: {result.get('action', 'help')}"
        return result, reasoning
