from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from starfall.models import AgentRunStatus, ClientRole, ClientStatus, OrderStatus, OrderType, RecordStatus, ServiceCategory, ShipmentStatus


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


class PlaceOrderOut(BaseModel):
    order: OrderOut
    game_result: dict[str, Any] | None = None


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


class LaunchBrokerChatRequest(BaseModel):
    instruction: str = Field(..., examples=["find a LEO slot for September 2032 on Starship239"])
    action: str | None = None
    slot_id: str | None = None
    container_code: str | None = None
    package_id: str | None = None
    leg: str | None = None
    ship_ref: str | None = None
    owner_name: str | None = None
    recipient_name: str | None = None
    recipient_id: str | None = None
    address: str | None = None
    notes: str | None = None


class MissionGuideChatRequest(BaseModel):
    instruction: str = Field(
        ...,
        examples=["generate mission: 100kg mining welding gear to ElonsTown on Mars"],
    )
    action: str | None = None
    brief: str | None = None
    replace: bool | None = None


class BankingChatRequest(BaseModel):
    instruction: str = Field(..., examples=["balance", "deposit 500", "transfer 100 to trader@starfall.corp"])
    action: str | None = None
    amount: float | None = Field(None, gt=0)
    recipient_email: str | None = None
    recipient_account: str | None = None
    memo: str | None = None


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


class ContainerCreate(BaseModel):
    container_code: str = Field(..., examples=["CNT-SOL-001"])
    owner_name: str = Field(..., examples=["Aurora Trading Co."])
    system_id: str = Field(..., examples=["sol"])
    status: RecordStatus = RecordStatus.DRAFT
    notes: str = ""


class ContainerUpdate(BaseModel):
    container_code: str | None = None
    owner_name: str | None = None
    system_id: str | None = None
    status: RecordStatus | None = None
    notes: str | None = None


class ContainerPackageCreate(BaseModel):
    package_id: str = Field(..., examples=["PKG-8842"])
    owner_name: str = Field(..., examples=["Aurora Trading Co."])
    recipient_name: str = Field(..., examples=["Dr. Elena Voss"])
    recipient_id: str = Field(..., examples=["RCPT-230"])
    address: str = Field(..., examples=["Lab 230, Starship 4090"])
    notes: str = ""
    manifest_leg: str = Field(default="", examples=["outbound"])


class ContainerPackageUpdate(BaseModel):
    package_id: str | None = None
    owner_name: str | None = None
    recipient_name: str | None = None
    recipient_id: str | None = None
    address: str | None = None
    notes: str | None = None
    manifest_leg: str | None = None


class LaunchStackCreate(BaseModel):
    stack_code: str
    system_id: str
    container_codes: str = ""
    target_orbit: str = "LEO transfer"
    status: RecordStatus = RecordStatus.DRAFT
    notes: str = ""


class LaunchStackUpdate(BaseModel):
    stack_code: str | None = None
    system_id: str | None = None
    container_codes: str | None = None
    target_orbit: str | None = None
    status: RecordStatus | None = None
    notes: str | None = None


class LaunchBookingCreate(BaseModel):
    booking_code: str
    pad_location: str
    launch_window: str
    payload_ref: str = ""
    mass_kg: float = 0.0
    status: RecordStatus = RecordStatus.DRAFT
    notes: str = ""


class LaunchBookingUpdate(BaseModel):
    booking_code: str | None = None
    pad_location: str | None = None
    launch_window: str | None = None
    payload_ref: str | None = None
    mass_kg: float | None = None
    status: RecordStatus | None = None
    notes: str | None = None


class PorterJobCreate(BaseModel):
    job_code: str
    container_code: str
    owner_name: str
    package_id: str = ""
    recipient_name: str = ""
    recipient_id: str = ""
    origin_address: str
    destination_address: str
    status: RecordStatus = RecordStatus.DRAFT
    notes: str = ""


class PorterJobUpdate(BaseModel):
    job_code: str | None = None
    container_code: str | None = None
    owner_name: str | None = None
    package_id: str | None = None
    recipient_name: str | None = None
    recipient_id: str | None = None
    origin_address: str | None = None
    destination_address: str | None = None
    status: RecordStatus | None = None
    notes: str | None = None


class EndpointReceiptCreate(BaseModel):
    receipt_code: str
    container_code: str
    package_id: str
    owner_name: str
    recipient_name: str
    recipient_id: str
    gateway_address: str
    status: RecordStatus = RecordStatus.DRAFT
    notes: str = ""


class EndpointReceiptUpdate(BaseModel):
    receipt_code: str | None = None
    container_code: str | None = None
    package_id: str | None = None
    owner_name: str | None = None
    recipient_name: str | None = None
    recipient_id: str | None = None
    gateway_address: str | None = None
    status: RecordStatus | None = None
    notes: str | None = None


class DeliveryOrderCreate(BaseModel):
    delivery_code: str
    package_id: str
    owner_name: str
    recipient_name: str
    recipient_id: str
    destination_address: str
    status: RecordStatus = RecordStatus.DRAFT
    notes: str = ""


class DeliveryOrderUpdate(BaseModel):
    delivery_code: str | None = None
    package_id: str | None = None
    owner_name: str | None = None
    recipient_name: str | None = None
    recipient_id: str | None = None
    destination_address: str | None = None
    status: RecordStatus | None = None
    notes: str | None = None


class CollectionJobCreate(BaseModel):
    job_code: str
    container_code: str
    contractor_id: str
    system_id: str
    pickup_site: str = Field(..., examples=["Offshore Platform 7, Sol Drift"])
    owner_name: str
    package_id: str = ""
    recipient_name: str = ""
    recipient_id: str = ""
    delivery_address: str = Field(default="", examples=["Lab 230, Starship 4090"])
    notes: str = ""


class CollectionJobUpdate(BaseModel):
    job_code: str | None = None
    container_code: str | None = None
    contractor_id: str | None = None
    system_id: str | None = None
    pickup_site: str | None = None
    owner_name: str | None = None
    package_id: str | None = None
    recipient_name: str | None = None
    recipient_id: str | None = None
    delivery_address: str | None = None
    status: RecordStatus | None = None
    notes: str | None = None
