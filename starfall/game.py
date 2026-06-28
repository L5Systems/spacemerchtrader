import random
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from starfall.models import (
    Client,
    CollectionJob,
    CollectionOutcome,
    Container,
    GameState,
    MarketPrice,
    Mission,
    MissionProgress,
    MissionType,
    Order,
    OrderStatus,
    OrderType,
    PlayerProfile,
    RecordStatus,
    ServiceCategory,
    ServiceProvider,
)

STARTING_CREDITS = 10000.0
XP_PER_LEVEL = 500
ORDER_XP_BASE = 25
ORDER_REP_BASE = 2.5


def xp_to_level(xp: int) -> int:
    return 1 + xp // XP_PER_LEVEL


def get_or_create_profile(db: Session, client_id: str) -> PlayerProfile:
    profile = db.get(PlayerProfile, client_id)
    if profile:
        profile.last_active = datetime.now(timezone.utc)
        db.commit()
        db.refresh(profile)
        return profile

    profile = PlayerProfile(client_id=client_id, credits=STARTING_CREDITS)
    db.add(profile)
    db.flush()
    _ensure_mission_progress(db, client_id)
    db.commit()
    db.refresh(profile)
    return profile


def _ensure_mission_progress(db: Session, client_id: str) -> None:
    missions = db.query(Mission).order_by(Mission.sort_order).all()
    existing = {
        row.mission_id
        for row in db.query(MissionProgress).filter(MissionProgress.client_id == client_id).all()
    }
    for mission in missions:
        if mission.id not in existing:
            db.add(MissionProgress(client_id=client_id, mission_id=mission.id, progress=0))


def get_game_state(db: Session) -> GameState:
    state = db.get(GameState, 1)
    if not state:
        state = GameState(id=1)
        db.add(state)
        db.commit()
        db.refresh(state)
    return state


def get_world_status(db: Session) -> dict:
    state = get_game_state(db)
    online_players = db.query(PlayerProfile).count()
    return {
        "market_cycle": state.market_cycle,
        "last_tick_at": state.last_tick_at,
        "event_message": state.event_message,
        "online_players": online_players,
    }


def get_player_status(db: Session, client: Client) -> dict:
    profile = get_or_create_profile(db, client.id)
    missions = list_player_missions(db, client.id)
    from starfall.banking import account_summary

    bank = account_summary(db, client.id)
    return {
        "player": {
            "client_id": client.id,
            "display_name": client.display_name,
            "credits": round(profile.credits, 2),
            "bank_balance": bank["bank_balance"],
            "bank_account": bank["account_number"],
            "xp": profile.xp,
            "level": profile.level,
            "reputation": round(profile.reputation, 1),
            "orders_completed": profile.orders_completed,
            "missions_completed": profile.missions_completed,
            "xp_to_next_level": XP_PER_LEVEL - (profile.xp % XP_PER_LEVEL),
        },
        "world": get_world_status(db),
        "missions": missions,
    }


def list_player_missions(db: Session, client_id: str) -> list[dict]:
    _ensure_mission_progress(db, client_id)
    rows = (
        db.query(MissionProgress, Mission)
        .join(Mission, MissionProgress.mission_id == Mission.id)
        .filter(MissionProgress.client_id == client_id)
        .order_by(Mission.sort_order)
        .all()
    )
    return [
        {
            "id": mission.id,
            "title": mission.title,
            "description": mission.description,
            "mission_type": mission.mission_type.value,
            "target_quantity": mission.target_quantity,
            "progress": progress.progress,
            "completed": progress.completed,
            "reward_credits": mission.reward_credits,
            "reward_xp": mission.reward_xp,
        }
        for progress, mission in rows
    ]


def get_leaderboard(db: Session, limit: int = 10) -> list[dict]:
    rows = (
        db.query(PlayerProfile, Client)
        .join(Client, PlayerProfile.client_id == Client.id)
        .order_by(PlayerProfile.reputation.desc(), PlayerProfile.xp.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "rank": index + 1,
            "display_name": client.display_name,
            "level": profile.level,
            "reputation": round(profile.reputation, 1),
            "credits": round(profile.credits, 2),
            "orders_completed": profile.orders_completed,
            "missions_completed": profile.missions_completed,
        }
        for index, (profile, client) in enumerate(rows)
    ]


def _complete_mission(db: Session, profile: PlayerProfile, progress: MissionProgress, mission: Mission) -> dict:
    if progress.completed:
        return {}
    progress.completed = True
    progress.progress = mission.target_quantity
    progress.completed_at = datetime.now(timezone.utc)
    profile.credits += mission.reward_credits
    profile.xp += mission.reward_xp
    profile.missions_completed += 1
    profile.level = xp_to_level(profile.xp)
    return {
        "mission_id": mission.id,
        "title": mission.title,
        "credits": mission.reward_credits,
        "xp": mission.reward_xp,
    }


def _count_service_progress(db: Session, client_id: str, mission: Mission) -> int:
    if mission.ship_ref:
        from starfall.manifest import count_manifest_mission_progress

        return count_manifest_mission_progress(db, client_id, mission)
    if mission.service_category == ServiceCategory.CONTAINER_ASSEMBLY:
        return db.query(Container).filter(Container.client_id == client_id).count()
    if mission.service_category == ServiceCategory.CONTAINER_COLLECTION:
        query = db.query(CollectionJob).filter(
            CollectionJob.client_id == client_id,
            CollectionJob.status == RecordStatus.COMPLETED,
            CollectionJob.outcome.in_(
                [CollectionOutcome.PICKED_UP, CollectionOutcome.SKIMMED]
            ),
        )
        if mission.contractor_disposition:
            query = query.join(ServiceProvider).filter(
                ServiceProvider.contractor_disposition == mission.contractor_disposition
            )
        return query.count()
    return 0


def _check_missions(db: Session, client_id: str, profile: PlayerProfile) -> list[dict]:
    completed_events: list[dict] = []
    rows = (
        db.query(MissionProgress, Mission)
        .join(Mission, MissionProgress.mission_id == Mission.id)
        .filter(MissionProgress.client_id == client_id, MissionProgress.completed.is_(False))
        .all()
    )
    for progress, mission in rows:
        if mission.mission_type == MissionType.ORDER_COUNT:
            progress.progress = profile.orders_completed
        elif mission.mission_type == MissionType.SERVICE_ACTION and mission.service_category:
            progress.progress = _count_service_progress(db, client_id, mission)

        if progress.progress >= mission.target_quantity:
            reward = _complete_mission(db, profile, progress, mission)
            if reward:
                completed_events.append(reward)

    return completed_events


def on_order_completed(db: Session, client_id: str | None, order: Order) -> dict | None:
    if not client_id or order.status != OrderStatus.ROUTED:
        return None

    profile = get_or_create_profile(db, client_id)
    profit = order.total_credits or 0.0
    if order.order_type == OrderType.SELL:
        profile.credits += profit
    profile.orders_completed += 1
    profile.xp += ORDER_XP_BASE
    profile.reputation += ORDER_REP_BASE
    profile.level = xp_to_level(profile.xp)
    profile.last_active = datetime.now(timezone.utc)

    rows = (
        db.query(MissionProgress, Mission)
        .join(Mission, MissionProgress.mission_id == Mission.id)
        .filter(
            MissionProgress.client_id == client_id,
            MissionProgress.completed.is_(False),
            Mission.mission_type == MissionType.TRADE_ROUTE,
        )
        .all()
    )
    mission_rewards: list[dict] = []
    for progress, mission in rows:
        matches = True
        if mission.product_id and mission.product_id != order.product_id:
            matches = False
        if mission.origin_system_id and mission.origin_system_id != order.origin_system_id:
            matches = False
        if mission.destination_system_id and mission.destination_system_id != order.destination_system_id:
            matches = False
        if matches:
            progress.progress += order.quantity
        if progress.progress >= mission.target_quantity:
            reward = _complete_mission(db, profile, progress, mission)
            if reward:
                mission_rewards.append(reward)

    mission_rewards.extend(_check_missions(db, client_id, profile))
    db.commit()
    db.refresh(profile)

    return {
        "credits_earned": round(profit if order.order_type == OrderType.SELL else 0, 2),
        "xp_gained": ORDER_XP_BASE,
        "reputation_gained": ORDER_REP_BASE,
        "total_credits": round(profile.credits, 2),
        "level": profile.level,
        "mission_rewards": mission_rewards,
    }


def on_collection_completed(db: Session, client_id: str, job: CollectionJob) -> dict | None:
    profile = get_or_create_profile(db, client_id)
    fee = 120.0
    xp_gain = 35
    rep_gain = 4.0

    if job.outcome == CollectionOutcome.SKIMMED:
        profile.credits = max(0, profile.credits - 150)
        profile.reputation -= 1.0
        xp_gain = 45
    else:
        profile.credits -= fee
        profile.reputation += rep_gain

    profile.xp += xp_gain
    profile.level = xp_to_level(profile.xp)
    profile.last_active = datetime.now(timezone.utc)

    mission_rewards = _check_missions(db, client_id, profile)
    db.commit()
    db.refresh(profile)

    return {
        "pickup_fee": fee,
        "xp_gained": xp_gain,
        "outcome": job.outcome.value,
        "outcome_detail": job.outcome_detail,
        "total_credits": round(profile.credits, 2),
        "mission_rewards": mission_rewards,
    }


def on_service_record_created(db: Session, client_id: str, category: ServiceCategory) -> dict | None:
    profile = get_or_create_profile(db, client_id)
    mission_rewards = _check_missions(db, client_id, profile)
    db.commit()
    if not mission_rewards:
        return None
    db.refresh(profile)
    return {"mission_rewards": mission_rewards, "total_credits": round(profile.credits, 2)}


def on_manifest_updated(db: Session, client_id: str) -> dict | None:
    profile = get_or_create_profile(db, client_id)
    mission_rewards = _check_missions(db, client_id, profile)
    db.commit()
    db.refresh(profile)
    if not mission_rewards:
        return None
    return {
        "mission_rewards": mission_rewards,
        "total_credits": round(profile.credits, 2),
    }



def advance_market_tick(db: Session) -> dict:
    state = get_game_state(db)
    prices = db.query(MarketPrice).all()
    events = [
        "Solar flare disrupts Sol lane pricing.",
        "Vega trade guild announces bulk spice demand.",
        "Kepler rim convoy delays tighten supply lines.",
        "Corporate arbitrage bots sweep hydro markets.",
        "Independent traders flood alloy routes.",
    ]

    for price in prices:
        shift = random.uniform(0.95, 1.08)
        price.buy_price = round(price.buy_price * shift, 2)
        price.sell_price = round(price.sell_price * shift, 2)
        price.updated_at = datetime.now(timezone.utc)

    state.market_cycle += 1
    state.last_tick_at = datetime.now(timezone.utc)
    state.event_message = random.choice(events)
    db.commit()

    return get_world_status(db)
