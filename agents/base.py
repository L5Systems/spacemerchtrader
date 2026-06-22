from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy.orm import Session

from starfall.models import AgentRun, AgentRunStatus
from starfall.services import complete_agent_run, create_agent_run


class BaseAgent(ABC):
    agent_id: str

    @abstractmethod
    def run(self, db: Session, payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
        """Execute agent logic and return (output, reasoning)."""

    def execute(
        self,
        db: Session,
        trigger: str,
        payload: dict[str, Any],
    ) -> AgentRun:
        run = create_agent_run(db, self.agent_id, trigger, payload)
        try:
            output, reasoning = self.run(db, payload)
            return complete_agent_run(db, run, output, reasoning)
        except Exception as exc:
            return complete_agent_run(
                db,
                run,
                {"error": str(exc)},
                f"Agent failed: {exc}",
                status=AgentRunStatus.FAILED,
            )
