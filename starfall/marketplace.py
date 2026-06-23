import hashlib
import secrets
import uuid

from sqlalchemy.orm import Session

from starfall.models import (
    SERVICE_CATEGORY_LABELS,
    Client,
    ClientAccess,
    ClientRole,
    ClientStatus,
    ServiceCategory,
    ServiceOffering,
    ServiceProvider,
)

DEFAULT_ACCESS_BY_ROLE: dict[ClientRole, list[ServiceCategory]] = {
    ClientRole.TRADER: [
        ServiceCategory.CONTAINER_ASSEMBLY,
        ServiceCategory.CONTAINER_COLLECTION,
        ServiceCategory.CONTAINER_PORTER,
        ServiceCategory.OFFWORLD_DELIVERY,
    ],
    ClientRole.LOGISTICS: list(ServiceCategory),
    ClientRole.ADMIN: list(ServiceCategory),
}


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    salt, digest = stored.split("$", 1)
    check = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
    return secrets.compare_digest(check.hex(), digest)


def _new_token() -> str:
    return secrets.token_urlsafe(32)


def _grant_access(db: Session, client: Client, categories: list[ServiceCategory]) -> None:
    for category in categories:
        db.add(ClientAccess(client_id=client.id, category=category, enabled=True))


def register_client(
    db: Session,
    *,
    email: str,
    password: str,
    display_name: str,
    role: ClientRole = ClientRole.TRADER,
) -> Client:
    existing = db.query(Client).filter(Client.email == email.lower()).first()
    if existing:
        raise ValueError("Email already registered")

    client = Client(
        id=str(uuid.uuid4()),
        email=email.lower().strip(),
        password_hash=hash_password(password),
        display_name=display_name.strip(),
        role=role,
        status=ClientStatus.ACTIVE,
        api_token=_new_token(),
    )
    db.add(client)
    db.flush()
    _grant_access(db, client, DEFAULT_ACCESS_BY_ROLE[role])
    db.commit()
    db.refresh(client)

    from starfall.game import get_or_create_profile

    get_or_create_profile(db, client.id)
    return client


def authenticate_client(db: Session, *, email: str, password: str) -> Client | None:
    client = db.query(Client).filter(Client.email == email.lower().strip()).first()
    if not client or client.status != ClientStatus.ACTIVE:
        return None
    if not verify_password(password, client.password_hash):
        return None
    client.api_token = _new_token()
    db.commit()
    db.refresh(client)
    return client


def get_client_by_token(db: Session, token: str) -> Client | None:
    return (
        db.query(Client)
        .filter(Client.api_token == token, Client.status == ClientStatus.ACTIVE)
        .first()
    )


def get_client_access(db: Session, client_id: str) -> list[ServiceCategory]:
    rows = (
        db.query(ClientAccess)
        .filter(ClientAccess.client_id == client_id, ClientAccess.enabled.is_(True))
        .all()
    )
    return [row.category for row in rows]


def list_categories() -> list[dict]:
    return [
        {
            "id": category.value,
            "label": SERVICE_CATEGORY_LABELS[category],
            "description": _category_description(category),
        }
        for category in ServiceCategory
    ]


def _category_description(category: ServiceCategory) -> str:
    descriptions = {
        ServiceCategory.CONTAINER_ASSEMBLY: "Build and configure cargo containers for interstellar shipment.",
        ServiceCategory.CONTAINER_AGGREGATOR: "Aggregate containers into launch-ready stacks for orbital insertion.",
        ServiceCategory.CONTAINER_COLLECTION: "Hire offshore contractors to collect containers from remote platforms.",
        ServiceCategory.GROUND_LAUNCH: "Surface-to-orbit launch services from planetary facilities.",
        ServiceCategory.CONTAINER_PORTER: "Move containers between docks, yards, and transfer stations.",
        ServiceCategory.OFFWORLD_ENDPOINT: "Receive and hand off containers at offworld gateway terminals.",
        ServiceCategory.OFFWORLD_DELIVERY: "Last-leg delivery to offworld destinations and remote sites.",
    }
    return descriptions[category]


def list_providers(
    db: Session,
    *,
    category: ServiceCategory | None = None,
    system_id: str | None = None,
    allowed_categories: list[ServiceCategory] | None = None,
) -> list[dict]:
    query = (
        db.query(ServiceOffering, ServiceProvider)
        .join(ServiceProvider, ServiceOffering.provider_id == ServiceProvider.id)
        .order_by(ServiceProvider.rating.desc(), ServiceProvider.name)
    )
    if category:
        query = query.filter(ServiceOffering.category == category)
    if system_id:
        query = query.filter(ServiceOffering.system_id == system_id)
    if allowed_categories is not None:
        query = query.filter(ServiceOffering.category.in_(allowed_categories))

    providers: dict[str, dict] = {}
    for offering, provider in query.all():
        if provider.id not in providers:
            providers[provider.id] = {
                "id": provider.id,
                "name": provider.name,
                "description": provider.description,
                "home_system_id": provider.home_system_id,
                "verified": provider.verified,
                "rating": provider.rating,
                "contractor_disposition": (
                    provider.contractor_disposition.value if provider.contractor_disposition else None
                ),
                "offerings": [],
            }
        providers[provider.id]["offerings"].append(
            {
                "id": offering.id,
                "category": offering.category.value,
                "category_label": SERVICE_CATEGORY_LABELS[offering.category],
                "system_id": offering.system_id,
                "base_rate": offering.base_rate,
                "capacity": offering.capacity,
                "unit": offering.unit,
                "description": offering.description,
            }
        )
    return list(providers.values())


def build_client_menu(db: Session, client: Client) -> dict:
    allowed = get_client_access(db, client.id)
    providers = list_providers(db, allowed_categories=allowed)
    categories = [c for c in list_categories() if ServiceCategory(c["id"]) in allowed]

    by_category: dict[str, list[dict]] = {c["id"]: [] for c in categories}
    for provider in providers:
        for offering in provider["offerings"]:
            by_category.setdefault(offering["category"], []).append(
                {
                    "provider_id": provider["id"],
                    "provider_name": provider["name"],
                    "verified": provider["verified"],
                    "rating": provider["rating"],
                    **offering,
                }
            )

    return {
        "client": {
            "id": client.id,
            "email": client.email,
            "display_name": client.display_name,
            "role": client.role.value,
        },
        "access": [c.value for c in allowed],
        "categories": categories,
        "providers_by_category": by_category,
        "providers": providers,
    }


def update_client_access(
    db: Session,
    *,
    client_id: str,
    categories: list[ServiceCategory],
    actor: Client,
) -> Client:
    if actor.role != ClientRole.ADMIN:
        raise PermissionError("Only admins can manage client access")

    client = db.get(Client, client_id)
    if not client:
        raise ValueError("Client not found")

    db.query(ClientAccess).filter(ClientAccess.client_id == client_id).delete()
    _grant_access(db, client, categories)
    db.commit()
    db.refresh(client)
    return client
