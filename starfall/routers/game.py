from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from starfall.database import get_db
from starfall.game import advance_market_tick, get_leaderboard, get_player_status, get_world_status
from starfall.marketplace import get_client_by_token
from starfall.models import Client, ClientRole

router = APIRouter(prefix="/game", tags=["game"])


def get_current_client(
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
) -> Client:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Sign in to play")
    token = authorization.removeprefix("Bearer ").strip()
    client = get_client_by_token(db, token)
    if not client:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return client


@router.get("/world")
def game_world(db: Session = Depends(get_db)) -> dict[str, Any]:
    return get_world_status(db)


@router.get("/me")
def game_me(client: Client = Depends(get_current_client), db: Session = Depends(get_db)) -> dict[str, Any]:
    return get_player_status(db, client)


@router.get("/leaderboard")
def game_leaderboard(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    return get_leaderboard(db)


@router.post("/tick")
def game_tick(
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if client.role != ClientRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can advance the market cycle")
    return advance_market_tick(db)
