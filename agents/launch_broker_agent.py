from typing import Any

from sqlalchemy.orm import Session

from agents.base import BaseAgent
from agents.manifest_planner import plan_manifest_request
from starfall.manifest import broker_respond


class LaunchBrokerAgent(BaseAgent):
    agent_id = "launch_broker"

    def run(self, db: Session, payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
        instruction = str(payload.get("instruction") or payload.get("message") or "")
        client_id = payload.get("client_id")

        merged_payload = dict(payload)
        plan = plan_manifest_request(instruction, payload)
        if plan and plan.get("tool"):
            merged_payload["action"] = plan["tool"]
            merged_payload.update(plan.get("params") or {})

        result = broker_respond(db, client_id, instruction, merged_payload)
        if plan:
            result["planner"] = plan
        source = plan.get("source") if plan else "rules"
        reasoning = f"Launch broker action: {result.get('action', 'help')} (via {source})"
        return result, reasoning
