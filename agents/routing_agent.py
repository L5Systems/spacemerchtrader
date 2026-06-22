from typing import Any

from sqlalchemy.orm import Session

from agents.base import BaseAgent
from starfall.services import get_order, route_order


class RoutingAgent(BaseAgent):
    agent_id = "routing"

    def run(self, db: Session, payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
        order_id = payload["order_id"]
        order = get_order(db, order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")

        result = route_order(db, order)
        reasoning = (
            f"Assigned route {result['route_id']} via {result['carrier']}. "
            f"ETA {result['eta_days']} days, freight {result['freight_cost']} credits."
        )
        return result, reasoning
