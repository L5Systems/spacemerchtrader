from typing import Any

from sqlalchemy.orm import Session

from agents.base import BaseAgent
from agents.inventory_agent import InventoryAgent
from agents.launch_broker_agent import LaunchBrokerAgent
from agents.mission_guide_agent import MissionGuideAgent
from agents.pricing_agent import PricingAgent
from agents.routing_agent import RoutingAgent
from starfall.models import AgentRun, OrderStatus
from starfall.services import get_order


AGENTS: dict[str, BaseAgent] = {
    "pricing": PricingAgent(),
    "inventory": InventoryAgent(),
    "routing": RoutingAgent(),
    "launch_broker": LaunchBrokerAgent(),
    "mission_guide": MissionGuideAgent(),
}


def run_agent(
    db: Session,
    agent_id: str,
    trigger: str,
    payload: dict[str, Any],
) -> AgentRun:
    agent = AGENTS[agent_id]
    return agent.execute(db, trigger, payload)


def process_new_order(db: Session, order_id: str) -> None:
    """Run the handling pipeline: pricing → inventory → routing."""
    order = get_order(db, order_id)
    if not order:
        return

    pricing = AGENTS["pricing"]
    pricing.execute(db, "order.created", {"order_id": order_id})

    db.refresh(order)
    if order.status != OrderStatus.PRICED:
        return

    inventory = AGENTS["inventory"]
    inventory.execute(db, "order.priced", {"order_id": order_id})

    db.refresh(order)
    if order.status != OrderStatus.RESERVED:
        return

    routing = AGENTS["routing"]
    routing.execute(db, "order.reserved", {"order_id": order_id})
