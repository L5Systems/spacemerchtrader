from typing import Any

from sqlalchemy.orm import Session

from agents.base import BaseAgent
from starfall.services import get_order, price_order


class PricingAgent(BaseAgent):
    agent_id = "pricing"

    def run(self, db: Session, payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
        order_id = payload["order_id"]
        order = get_order(db, order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")

        result = price_order(db, order)
        reasoning = (
            f"Priced {order.order_type.value} order for {order.quantity} units "
            f"at {result['unit_price']} credits/unit. "
            f"Handling fee {result['handling_fee']} → total {result['total_credits']} credits."
        )
        return result, reasoning
