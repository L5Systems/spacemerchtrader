import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from starfall.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class OrderType(str, enum.Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    PRICED = "priced"
    RESERVED = "reserved"
    ROUTED = "routed"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    FAILED = "failed"


class ShipmentStatus(str, enum.Enum):
    PLANNED = "planned"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    DELAYED = "delayed"
    FAILED = "failed"


class AgentRunStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ESCALATED = "escalated"
    FAILED = "failed"


class ClientRole(str, enum.Enum):
    TRADER = "trader"
    LOGISTICS = "logistics"
    ADMIN = "admin"


class ClientStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"


class ServiceCategory(str, enum.Enum):
    CONTAINER_ASSEMBLY = "container_assembly"
    CONTAINER_AGGREGATOR = "container_aggregator"
    CONTAINER_COLLECTION = "container_collection"
    GROUND_LAUNCH = "ground_launch"
    CONTAINER_PORTER = "container_porter"
    OFFWORLD_ENDPOINT = "offworld_endpoint"
    OFFWORLD_DELIVERY = "offworld_delivery"


class ContractorDisposition(str, enum.Enum):
    RELIABLE = "reliable"
    CROOKED = "crooked"
    ACCIDENT_PRONE = "accident_prone"


class CollectionOutcome(str, enum.Enum):
    PENDING = "pending"
    PICKED_UP = "picked_up"
    SKIMMED = "skimmed"
    INCIDENT = "incident"


SERVICE_CATEGORY_LABELS: dict[ServiceCategory, str] = {
    ServiceCategory.CONTAINER_ASSEMBLY: "Container Assembly",
    ServiceCategory.CONTAINER_AGGREGATOR: "Container Aggregator (Launch)",
    ServiceCategory.CONTAINER_COLLECTION: "Container Collection",
    ServiceCategory.GROUND_LAUNCH: "Ground Launch Provider",
    ServiceCategory.CONTAINER_PORTER: "Container Porter",
    ServiceCategory.OFFWORLD_ENDPOINT: "Offworld Endpoint",
    ServiceCategory.OFFWORLD_DELIVERY: "Offworld Container Delivery",
}

CONTRACTOR_DISPOSITION_LABELS: dict[ContractorDisposition, str] = {
    ContractorDisposition.RELIABLE: "Reliable",
    ContractorDisposition.CROOKED: "Crooked",
    ContractorDisposition.ACCIDENT_PRONE: "Accident-prone",
}


class StarSystem(Base):
    __tablename__ = "star_systems"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True)
    risk_level: Mapped[float] = mapped_column(Float, default=0.1)

    warehouses: Mapped[list["Warehouse"]] = relationship(back_populates="system")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    category: Mapped[str] = mapped_column(String(64))
    base_price: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(32), default="crate")

    stock_items: Mapped[list["StockItem"]] = relationship(back_populates="product")
    market_prices: Mapped[list["MarketPrice"]] = relationship(back_populates="product")


class Warehouse(Base):
    __tablename__ = "warehouses"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    system_id: Mapped[str] = mapped_column(ForeignKey("star_systems.id"))
    station: Mapped[str] = mapped_column(String(128))
    capacity: Mapped[int] = mapped_column(Integer, default=10000)

    system: Mapped["StarSystem"] = relationship(back_populates="warehouses")
    stock_items: Mapped[list["StockItem"]] = relationship(back_populates="warehouse")


class StockItem(Base):
    __tablename__ = "stock_items"
    __table_args__ = (UniqueConstraint("warehouse_id", "product_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    warehouse_id: Mapped[str] = mapped_column(ForeignKey("warehouses.id"))
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    reserved: Mapped[int] = mapped_column(Integer, default=0)

    warehouse: Mapped["Warehouse"] = relationship(back_populates="stock_items")
    product: Mapped["Product"] = relationship(back_populates="stock_items")

    @property
    def available(self) -> int:
        return max(self.quantity - self.reserved, 0)


class Route(Base):
    __tablename__ = "routes"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    origin_system_id: Mapped[str] = mapped_column(ForeignKey("star_systems.id"))
    destination_system_id: Mapped[str] = mapped_column(ForeignKey("star_systems.id"))
    jump_lanes: Mapped[str] = mapped_column(String(256))
    base_days: Mapped[int] = mapped_column(Integer)
    base_cost: Mapped[float] = mapped_column(Float)
    risk_multiplier: Mapped[float] = mapped_column(Float, default=1.0)


class MarketPrice(Base):
    __tablename__ = "market_prices"
    __table_args__ = (UniqueConstraint("product_id", "system_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"))
    system_id: Mapped[str] = mapped_column(ForeignKey("star_systems.id"))
    buy_price: Mapped[float] = mapped_column(Float)
    sell_price: Mapped[float] = mapped_column(Float)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    product: Mapped["Product"] = relationship(back_populates="market_prices")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    client_id: Mapped[str] = mapped_column(String(64))
    order_type: Mapped[OrderType] = mapped_column(Enum(OrderType))
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[int] = mapped_column(Integer)
    origin_system_id: Mapped[str] = mapped_column(ForeignKey("star_systems.id"))
    destination_system_id: Mapped[str] = mapped_column(ForeignKey("star_systems.id"))
    unit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    handling_fee: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_credits: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), default=OrderStatus.PENDING)
    warehouse_id: Mapped[str | None] = mapped_column(ForeignKey("warehouses.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    product: Mapped["Product"] = relationship()
    shipment: Mapped["Shipment | None"] = relationship(back_populates="order", uselist=False)


class Shipment(Base):
    __tablename__ = "shipments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), unique=True)
    route_id: Mapped[str] = mapped_column(ForeignKey("routes.id"))
    carrier: Mapped[str] = mapped_column(String(128))
    eta_days: Mapped[int] = mapped_column(Integer)
    freight_cost: Mapped[float] = mapped_column(Float)
    status: Mapped[ShipmentStatus] = mapped_column(Enum(ShipmentStatus), default=ShipmentStatus.PLANNED)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    order: Mapped["Order"] = relationship(back_populates="shipment")
    route: Mapped["Route"] = relationship()


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    agent_id: Mapped[str] = mapped_column(String(64))
    trigger: Mapped[str] = mapped_column(String(128))
    status: Mapped[AgentRunStatus] = mapped_column(Enum(AgentRunStatus), default=AgentRunStatus.PENDING)
    input_json: Mapped[str] = mapped_column(Text, default="{}")
    output_json: Mapped[str] = mapped_column(Text, default="{}")
    reasoning: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    display_name: Mapped[str] = mapped_column(String(128))
    role: Mapped[ClientRole] = mapped_column(Enum(ClientRole), default=ClientRole.TRADER)
    status: Mapped[ClientStatus] = mapped_column(Enum(ClientStatus), default=ClientStatus.ACTIVE)
    api_token: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    access_grants: Mapped[list["ClientAccess"]] = relationship(back_populates="client")
    player_profile: Mapped["PlayerProfile | None"] = relationship(
        back_populates="client", uselist=False
    )


class ClientAccess(Base):
    __tablename__ = "client_access"
    __table_args__ = (UniqueConstraint("client_id", "category"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"))
    category: Mapped[ServiceCategory] = mapped_column(Enum(ServiceCategory))
    enabled: Mapped[bool] = mapped_column(default=True)

    client: Mapped["Client"] = relationship(back_populates="access_grants")


class ServiceProvider(Base):
    __tablename__ = "service_providers"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text, default="")
    home_system_id: Mapped[str] = mapped_column(ForeignKey("star_systems.id"))
    verified: Mapped[bool] = mapped_column(default=True)
    rating: Mapped[float] = mapped_column(Float, default=4.0)
    contractor_disposition: Mapped[ContractorDisposition | None] = mapped_column(
        Enum(ContractorDisposition), nullable=True
    )

    offerings: Mapped[list["ServiceOffering"]] = relationship(back_populates="provider")
    home_system: Mapped["StarSystem"] = relationship()


class ServiceOffering(Base):
    __tablename__ = "service_offerings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    provider_id: Mapped[str] = mapped_column(ForeignKey("service_providers.id"))
    category: Mapped[ServiceCategory] = mapped_column(Enum(ServiceCategory))
    system_id: Mapped[str] = mapped_column(ForeignKey("star_systems.id"))
    base_rate: Mapped[float] = mapped_column(Float)
    capacity: Mapped[int] = mapped_column(Integer, default=100)
    unit: Mapped[str] = mapped_column(String(32), default="container")
    description: Mapped[str] = mapped_column(Text, default="")

    provider: Mapped["ServiceProvider"] = relationship(back_populates="offerings")
    system: Mapped["StarSystem"] = relationship()


class RecordStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Container(Base):
    __tablename__ = "containers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"))
    container_code: Mapped[str] = mapped_column(String(64))
    owner_name: Mapped[str] = mapped_column(String(128))
    system_id: Mapped[str] = mapped_column(ForeignKey("star_systems.id"))
    status: Mapped[RecordStatus] = mapped_column(Enum(RecordStatus), default=RecordStatus.DRAFT)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    packages: Mapped[list["ContainerPackage"]] = relationship(
        back_populates="container", cascade="all, delete-orphan"
    )


class ContainerPackage(Base):
    __tablename__ = "container_packages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    container_id: Mapped[str] = mapped_column(ForeignKey("containers.id"))
    package_id: Mapped[str] = mapped_column(String(64))
    owner_name: Mapped[str] = mapped_column(String(128))
    recipient_name: Mapped[str] = mapped_column(String(128))
    recipient_id: Mapped[str] = mapped_column(String(64))
    address: Mapped[str] = mapped_column(String(256))
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    container: Mapped["Container"] = relationship(back_populates="packages")


class LaunchStack(Base):
    __tablename__ = "launch_stacks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"))
    stack_code: Mapped[str] = mapped_column(String(64))
    system_id: Mapped[str] = mapped_column(ForeignKey("star_systems.id"))
    container_codes: Mapped[str] = mapped_column(String(512), default="")
    target_orbit: Mapped[str] = mapped_column(String(128), default="LEO transfer")
    status: Mapped[RecordStatus] = mapped_column(Enum(RecordStatus), default=RecordStatus.DRAFT)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class LaunchBooking(Base):
    __tablename__ = "launch_bookings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"))
    booking_code: Mapped[str] = mapped_column(String(64))
    pad_location: Mapped[str] = mapped_column(String(128))
    launch_window: Mapped[str] = mapped_column(String(128))
    payload_ref: Mapped[str] = mapped_column(String(128), default="")
    mass_kg: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[RecordStatus] = mapped_column(Enum(RecordStatus), default=RecordStatus.DRAFT)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class PorterJob(Base):
    __tablename__ = "porter_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"))
    job_code: Mapped[str] = mapped_column(String(64))
    container_code: Mapped[str] = mapped_column(String(64))
    owner_name: Mapped[str] = mapped_column(String(128))
    package_id: Mapped[str] = mapped_column(String(64), default="")
    recipient_name: Mapped[str] = mapped_column(String(128), default="")
    recipient_id: Mapped[str] = mapped_column(String(64), default="")
    origin_address: Mapped[str] = mapped_column(String(256))
    destination_address: Mapped[str] = mapped_column(String(256))
    status: Mapped[RecordStatus] = mapped_column(Enum(RecordStatus), default=RecordStatus.DRAFT)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class EndpointReceipt(Base):
    __tablename__ = "endpoint_receipts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"))
    receipt_code: Mapped[str] = mapped_column(String(64))
    container_code: Mapped[str] = mapped_column(String(64))
    package_id: Mapped[str] = mapped_column(String(64))
    owner_name: Mapped[str] = mapped_column(String(128))
    recipient_name: Mapped[str] = mapped_column(String(128))
    recipient_id: Mapped[str] = mapped_column(String(64))
    gateway_address: Mapped[str] = mapped_column(String(256))
    status: Mapped[RecordStatus] = mapped_column(Enum(RecordStatus), default=RecordStatus.DRAFT)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class DeliveryOrder(Base):
    __tablename__ = "delivery_orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"))
    delivery_code: Mapped[str] = mapped_column(String(64))
    package_id: Mapped[str] = mapped_column(String(64))
    owner_name: Mapped[str] = mapped_column(String(128))
    recipient_name: Mapped[str] = mapped_column(String(128))
    recipient_id: Mapped[str] = mapped_column(String(64))
    destination_address: Mapped[str] = mapped_column(String(256))
    status: Mapped[RecordStatus] = mapped_column(Enum(RecordStatus), default=RecordStatus.DRAFT)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class CollectionJob(Base):
    __tablename__ = "collection_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"))
    job_code: Mapped[str] = mapped_column(String(64))
    container_code: Mapped[str] = mapped_column(String(64))
    contractor_id: Mapped[str] = mapped_column(ForeignKey("service_providers.id"))
    system_id: Mapped[str] = mapped_column(ForeignKey("star_systems.id"))
    pickup_site: Mapped[str] = mapped_column(String(256))
    owner_name: Mapped[str] = mapped_column(String(128))
    package_id: Mapped[str] = mapped_column(String(64), default="")
    recipient_name: Mapped[str] = mapped_column(String(128), default="")
    recipient_id: Mapped[str] = mapped_column(String(64), default="")
    delivery_address: Mapped[str] = mapped_column(String(256), default="")
    outcome: Mapped[CollectionOutcome] = mapped_column(
        Enum(CollectionOutcome), default=CollectionOutcome.PENDING
    )
    outcome_detail: Mapped[str] = mapped_column(Text, default="")
    pickup_attempts: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[RecordStatus] = mapped_column(Enum(RecordStatus), default=RecordStatus.DRAFT)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    contractor: Mapped["ServiceProvider"] = relationship()


class MissionType(str, enum.Enum):
    TRADE_ROUTE = "trade_route"
    ORDER_COUNT = "order_count"
    SERVICE_ACTION = "service_action"


class PlayerProfile(Base):
    __tablename__ = "player_profiles"

    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), primary_key=True)
    credits: Mapped[float] = mapped_column(Float, default=10000.0)
    xp: Mapped[int] = mapped_column(Integer, default=0)
    level: Mapped[int] = mapped_column(Integer, default=1)
    reputation: Mapped[float] = mapped_column(Float, default=0.0)
    orders_completed: Mapped[int] = mapped_column(Integer, default=0)
    missions_completed: Mapped[int] = mapped_column(Integer, default=0)
    last_active: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    client: Mapped["Client"] = relationship(back_populates="player_profile")


class Mission(Base):
    __tablename__ = "missions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    title: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text)
    mission_type: Mapped[MissionType] = mapped_column(Enum(MissionType))
    product_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    origin_system_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    destination_system_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    service_category: Mapped[ServiceCategory | None] = mapped_column(Enum(ServiceCategory), nullable=True)
    contractor_disposition: Mapped[ContractorDisposition | None] = mapped_column(
        Enum(ContractorDisposition), nullable=True
    )
    target_quantity: Mapped[int] = mapped_column(Integer, default=1)
    reward_credits: Mapped[float] = mapped_column(Float)
    reward_xp: Mapped[int] = mapped_column(Integer)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class MissionProgress(Base):
    __tablename__ = "mission_progress"
    __table_args__ = (UniqueConstraint("client_id", "mission_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"))
    mission_id: Mapped[str] = mapped_column(ForeignKey("missions.id"))
    progress: Mapped[int] = mapped_column(Integer, default=0)
    completed: Mapped[bool] = mapped_column(default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    mission: Mapped["Mission"] = relationship()


class GameState(Base):
    __tablename__ = "game_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    market_cycle: Mapped[int] = mapped_column(Integer, default=1)
    last_tick_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    event_message: Mapped[str] = mapped_column(String(256), default="Markets stable across all systems.")
