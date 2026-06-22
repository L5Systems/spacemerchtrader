from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from starfall.database import get_db
from starfall.marketplace import (
    authenticate_client,
    build_client_menu,
    get_client_by_token,
    list_categories,
    list_providers,
    register_client,
    update_client_access,
)
from starfall.models import Client, ClientRole, ServiceCategory
from starfall.schemas import (
    ClientAccessUpdate,
    ClientLogin,
    ClientOut,
    ClientSignup,
    MarketplaceMenuOut,
    ServiceCategoryOut,
    ServiceProviderOut,
)

router = APIRouter(prefix="/marketplace", tags=["marketplace"])


def _client_out(client: Client) -> ClientOut:
    return ClientOut(
        id=client.id,
        email=client.email,
        display_name=client.display_name,
        role=client.role,
        status=client.status,
        access_token=client.api_token,
        created_at=client.created_at,
    )


def get_current_client(
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
) -> Client:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    token = authorization.removeprefix("Bearer ").strip()
    client = get_client_by_token(db, token)
    if not client:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return client


def get_admin_client(client: Client = Depends(get_current_client)) -> Client:
    if client.role != ClientRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return client


@router.get("/categories", response_model=list[ServiceCategoryOut])
def marketplace_categories() -> list[ServiceCategoryOut]:
    return list_categories()


@router.get("/providers", response_model=list[ServiceProviderOut])
def marketplace_providers(
    category: ServiceCategory | None = None,
    system_id: str | None = None,
    db: Session = Depends(get_db),
) -> list[ServiceProviderOut]:
    return list_providers(db, category=category, system_id=system_id)


@router.post("/signup", response_model=ClientOut, status_code=201)
def signup(payload: ClientSignup, db: Session = Depends(get_db)) -> ClientOut:
    try:
        client = register_client(
            db,
            email=payload.email,
            password=payload.password,
            display_name=payload.display_name,
            role=payload.role,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _client_out(client)


@router.post("/login", response_model=ClientOut)
def login(payload: ClientLogin, db: Session = Depends(get_db)) -> ClientOut:
    client = authenticate_client(db, email=payload.email, password=payload.password)
    if not client:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return _client_out(client)


@router.get("/me", response_model=ClientOut)
def current_client(client: Client = Depends(get_current_client)) -> ClientOut:
    return _client_out(client)


@router.get("/menu", response_model=MarketplaceMenuOut)
def client_menu(
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
) -> MarketplaceMenuOut:
    return build_client_menu(db, client)


@router.put("/clients/{client_id}/access", response_model=MarketplaceMenuOut)
def set_client_access(
    client_id: str,
    payload: ClientAccessUpdate,
    actor: Client = Depends(get_admin_client),
    db: Session = Depends(get_db),
) -> MarketplaceMenuOut:
    try:
        target = update_client_access(
            db,
            client_id=client_id,
            categories=payload.categories,
            actor=actor,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return build_client_menu(db, target)
