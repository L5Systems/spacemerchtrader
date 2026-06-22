from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from starfall.database import get_db
from starfall.schemas import (
    AgentRunOut,
    AgentRunRequest,
    HealthResponse,
    MarketPriceOut,
    OrderCreate,
    OrderOut,
    RouteQuoteOut,
    ShipmentOut,
    WarehouseStockOut,
)
from starfall.services import (
    create_order,
    get_market_prices,
    get_order,
    get_shipment_for_order,
    get_warehouse_stock,
    quote_route,
)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    from starfall.config import settings

    return HealthResponse(status="ok", company=settings.company_name)


@router.get("/markets/{system_id}/prices", response_model=list[MarketPriceOut])
def market_prices(system_id: str, db: Session = Depends(get_db)) -> list[MarketPriceOut]:
    prices = get_market_prices(db, system_id)
    if not prices:
        raise HTTPException(status_code=404, detail=f"No market data for system '{system_id}'")
    return prices


@router.get("/routes/quote", response_model=RouteQuoteOut)
def route_quote(
    origin: str,
    dest: str,
    qty: int = 1,
    db: Session = Depends(get_db),
) -> RouteQuoteOut:
    quote = quote_route(db, origin, dest, qty)
    if not quote:
        raise HTTPException(status_code=404, detail="Route not found")
    return quote


@router.get("/warehouses/{warehouse_id}/stock", response_model=WarehouseStockOut)
def warehouse_stock(warehouse_id: str, db: Session = Depends(get_db)) -> WarehouseStockOut:
    stock = get_warehouse_stock(db, warehouse_id)
    if not stock:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    return stock


@router.post("/orders", response_model=OrderOut, status_code=201)
def place_order(payload: OrderCreate, db: Session = Depends(get_db)) -> OrderOut:
    from agents.orchestrator import process_new_order

    order = create_order(db, payload.model_dump())
    process_new_order(db, order.id)
    refreshed = get_order(db, order.id)
    assert refreshed is not None
    return refreshed


@router.get("/orders/{order_id}", response_model=OrderOut)
def fetch_order(order_id: str, db: Session = Depends(get_db)) -> OrderOut:
    order = get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.get("/orders/{order_id}/shipment", response_model=ShipmentOut)
def fetch_order_shipment(order_id: str, db: Session = Depends(get_db)) -> ShipmentOut:
    shipment = get_shipment_for_order(db, order_id)
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found for order")
    return shipment
