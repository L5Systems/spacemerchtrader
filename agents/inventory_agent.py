from typing import Any

from sqlalchemy.orm import Session

from agents.base import BaseAgent
from starfall.services import get_order, reserve_inventory


class InventoryAgent(BaseAgent):
    agent_id = "inventory"

    def run(self, db: Session, payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
        order_id = payload["order_id"]
        order = get_order(db, order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")

        result = reserve_inventory(db, order)
        if result.get("reserved") is False:
            reasoning = result["reason"]
        else:
            reasoning = (
                f"Reserved {result['reserved_quantity']} units from warehouse "
                f"{result['warehouse_id']} for order {order_id}."
            )
        return result, reasoning
