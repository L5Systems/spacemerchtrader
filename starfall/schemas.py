from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from starfall.models import AgentRunStatus, ClientRole, ClientStatus, OrderStatus, OrderType, ServiceCategory, ShipmentStatus


class HealthResponse(BaseModel):
    status: str
    company: str


class ProductOut(BaseModel):
    id: str
    sku: str
    name: str
    category: str
    base_price: float
    unit: str

    model_config = {"from_attributes": True}


class MarketPriceOut(BaseModel):
    product_id: str
    product_name: str
    sku: str
    buy_price: float
    sell_price: float
    updated_at: datetime


class StockItemOut(BaseModel):
    product_id: str
    product_name: str
    sku: str
    quantity: int
    reserved: int
    available: int


class WarehouseStockOut(BaseModel):
    warehouse_id: str
    warehouse_name: str
    system_id: str
    station: str
    items: list[StockItemOut]


class RouteQuoteOut(BaseModel):
    origin_system_id: str
    destination_system_id: str
    route_id: str
    jump_lanes: str
    base_days: int
    freight_cost: float
    risk_premium: float
    total_cost: float


class OrderCreate(BaseModel):
    client_id: str = Field(..., examples=["trader-aurora-7"])
    order_type: OrderType
    product_id: str
    quantity: int = Field(..., gt=0)
    origin_system_id: str
    destination_system_id: str


class OrderOut(BaseModel):
    id: str
    client_id: str
    order_type: OrderType
    product_id: str
    quantity: int
    origin_system_id: str
    destination_system_id: str
    unit_price: float | None
    handling_fee: float | None
    total_credits: float | None
    status: OrderStatus
    warehouse_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ShipmentOut(BaseModel):
    id: str
    order_id: str
    route_id: str
    carrier: str
    eta_days: int
    freight_cost: float
    status: ShipmentStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentRunRequest(BaseModel):
    trigger: str = "manual"
    payload: dict[str, Any] = Field(default_factory=dict)


class AgentRunOut(BaseModel):
    id: str
    agent_id: str
    trigger: str
    status: AgentRunStatus
    input_json: str
    output_json: str
    reasoning: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ClientSignup(BaseModel):
    email: str = Field(..., examples=["trader@starfall.corp"])
    password: str = Field(..., min_length=8)
    display_name: str = Field(..., examples=["Aurora Trader"])
    role: ClientRole = ClientRole.TRADER


class ClientLogin(BaseModel):
    email: str
    password: str


class ClientOut(BaseModel):
    id: str
    email: str
    display_name: str
    role: ClientRole
    status: ClientStatus
    access_token: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ServiceCategoryOut(BaseModel):
    id: str
    label: str
    description: str


class ServiceOfferingOut(BaseModel):
    id: str
    category: str
    category_label: str
    system_id: str
    base_rate: float
    capacity: int
    unit: str
    description: str


class ServiceProviderOut(BaseModel):
    id: str
    name: str
    description: str
    home_system_id: str
    verified: bool
    rating: float
    offerings: list[ServiceOfferingOut]


class ClientAccessUpdate(BaseModel):
    categories: list[ServiceCategory]


class MarketplaceMenuOut(BaseModel):
    client: dict[str, str]
    access: list[str]
    categories: list[ServiceCategoryOut]
    providers_by_category: dict[str, list[dict[str, Any]]]
    providers: list[ServiceProviderOut]
