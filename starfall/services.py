import json
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from starfall.models import (
    AgentRun,
    AgentRunStatus,
    MarketPrice,
    Order,
    OrderStatus,
    OrderType,
    Product,
    Route,
    Shipment,
    ShipmentStatus,
    StockItem,
    Warehouse,
)


HANDLING_FEE_RATE = 0.05
RISK_PREMIUM_RATE = 0.02


def get_market_prices(db: Session, system_id: str) -> list[dict]:
    rows = (
        db.query(MarketPrice, Product)
        .join(Product, MarketPrice.product_id == Product.id)
        .filter(MarketPrice.system_id == system_id)
        .all()
    )
    return [
        {
            "product_id": price.product_id,
            "product_name": product.name,
            "sku": product.sku,
            "buy_price": price.buy_price,
            "sell_price": price.sell_price,
            "updated_at": price.updated_at,
        }
        for price, product in rows
    ]


def get_warehouse_stock(db: Session, warehouse_id: str) -> dict | None:
    warehouse = db.get(Warehouse, warehouse_id)
    if not warehouse:
        return None

    items = (
        db.query(StockItem, Product)
        .join(Product, StockItem.product_id == Product.id)
        .filter(StockItem.warehouse_id == warehouse_id)
        .all()
    )
    return {
        "warehouse_id": warehouse.id,
        "warehouse_name": warehouse.name,
        "system_id": warehouse.system_id,
        "station": warehouse.station,
        "items": [
            {
                "product_id": stock.product_id,
                "product_name": product.name,
                "sku": product.sku,
                "quantity": stock.quantity,
                "reserved": stock.reserved,
                "available": stock.available,
            }
            for stock, product in items
        ],
    }


def quote_route(
    db: Session,
    origin_system_id: str,
    destination_system_id: str,
    quantity: int = 1,
) -> dict | None:
    route = (
        db.query(Route)
        .filter(
            Route.origin_system_id == origin_system_id,
            Route.destination_system_id == destination_system_id,
        )
        .first()
    )
    if not route:
        return None

    freight_cost = route.base_cost * quantity
    risk_premium = freight_cost * route.risk_multiplier * RISK_PREMIUM_RATE
    return {
        "origin_system_id": origin_system_id,
        "destination_system_id": destination_system_id,
        "route_id": route.id,
        "jump_lanes": route.jump_lanes,
        "base_days": route.base_days,
        "freight_cost": round(freight_cost, 2),
        "risk_premium": round(risk_premium, 2),
        "total_cost": round(freight_cost + risk_premium, 2),
    }


def create_order(db: Session, data: dict) -> Order:
    order = Order(
        id=str(uuid.uuid4()),
        client_id=data["client_id"],
        order_type=data["order_type"],
        product_id=data["product_id"],
        quantity=data["quantity"],
        origin_system_id=data["origin_system_id"],
        destination_system_id=data["destination_system_id"],
        status=OrderStatus.PENDING,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def get_order(db: Session, order_id: str) -> Order | None:
    return db.get(Order, order_id)


def get_shipment_for_order(db: Session, order_id: str) -> Shipment | None:
    return db.query(Shipment).filter(Shipment.order_id == order_id).first()


def create_agent_run(
    db: Session,
    agent_id: str,
    trigger: str,
    payload: dict,
    status: AgentRunStatus = AgentRunStatus.RUNNING,
) -> AgentRun:
    run = AgentRun(
        id=str(uuid.uuid4()),
        agent_id=agent_id,
        trigger=trigger,
        status=status,
        input_json=json.dumps(payload),
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def complete_agent_run(
    db: Session,
    run: AgentRun,
    output: dict,
    reasoning: str,
    status: AgentRunStatus = AgentRunStatus.COMPLETED,
) -> AgentRun:
    run.output_json = json.dumps(output)
    run.reasoning = reasoning
    run.status = status
    db.commit()
    db.refresh(run)
    return run


def price_order(db: Session, order: Order) -> dict:
    market = (
        db.query(MarketPrice)
        .filter(
            MarketPrice.product_id == order.product_id,
            MarketPrice.system_id == order.origin_system_id,
        )
        .first()
    )
    if not market:
        raise ValueError(f"No market price for product {order.product_id}")

    unit_price = market.buy_price if order.order_type == OrderType.BUY else market.sell_price
    subtotal = unit_price * order.quantity
    handling_fee = round(subtotal * HANDLING_FEE_RATE, 2)
    total = round(subtotal + handling_fee, 2)

    order.unit_price = unit_price
    order.handling_fee = handling_fee
    order.total_credits = total
    order.status = OrderStatus.PRICED
    order.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(order)

    return {
        "order_id": order.id,
        "unit_price": unit_price,
        "handling_fee": handling_fee,
        "total_credits": total,
        "status": order.status.value,
    }


def reserve_inventory(db: Session, order: Order) -> dict:
    if order.order_type != OrderType.SELL:
        order.status = OrderStatus.RESERVED
        order.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(order)
        return {
            "order_id": order.id,
            "reserved": False,
            "reason": "Buy orders source from suppliers; no warehouse reservation needed.",
            "status": order.status.value,
        }

    stock = (
        db.query(StockItem)
        .filter(
            StockItem.warehouse_id.isnot(None),
            StockItem.product_id == order.product_id,
            StockItem.warehouse.has(system_id=order.origin_system_id),
        )
        .order_by(StockItem.quantity.desc())
        .first()
    )
    if not stock or stock.available < order.quantity:
        order.status = OrderStatus.FAILED
        order.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(order)
        raise ValueError("Insufficient inventory at origin system")

    stock.reserved += order.quantity
    order.warehouse_id = stock.warehouse_id
    order.status = OrderStatus.RESERVED
    order.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(order)

    return {
        "order_id": order.id,
        "warehouse_id": stock.warehouse_id,
        "reserved_quantity": order.quantity,
        "status": order.status.value,
    }


def route_order(db: Session, order: Order) -> dict:
    route = (
        db.query(Route)
        .filter(
            Route.origin_system_id == order.origin_system_id,
            Route.destination_system_id == order.destination_system_id,
        )
        .first()
    )
    if not route:
        order.status = OrderStatus.FAILED
        db.commit()
        raise ValueError("No route between origin and destination")

    quote = quote_route(
        db,
        order.origin_system_id,
        order.destination_system_id,
        order.quantity,
    )
    assert quote is not None

    existing = get_shipment_for_order(db, order.id)
    if existing:
        return {
            "order_id": order.id,
            "shipment_id": existing.id,
            "status": order.status.value,
            "message": "Shipment already exists",
        }

    shipment = Shipment(
        id=str(uuid.uuid4()),
        order_id=order.id,
        route_id=route.id,
        carrier="Starfall Fleet — Lane Courier",
        eta_days=route.base_days,
        freight_cost=quote["total_cost"],
        status=ShipmentStatus.PLANNED,
    )
    order.status = OrderStatus.ROUTED
    order.updated_at = datetime.now(timezone.utc)
    db.add(shipment)
    db.commit()
    db.refresh(order)
    db.refresh(shipment)

    return {
        "order_id": order.id,
        "shipment_id": shipment.id,
        "route_id": route.id,
        "carrier": shipment.carrier,
        "eta_days": shipment.eta_days,
        "freight_cost": shipment.freight_cost,
        "status": order.status.value,
    }
