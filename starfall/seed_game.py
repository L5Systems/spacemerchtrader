from sqlalchemy.orm import Session

from starfall.models import Mission, MissionType, ServiceCategory


def seed_game_data(db: Session) -> None:
    if db.query(Mission).first():
        return

    missions = [
        Mission(
            id="mis-first-haul",
            title="First Haul",
            description="Sell 5 alloy crates from Sol to Vega.",
            mission_type=MissionType.TRADE_ROUTE,
            product_id="alloy",
            origin_system_id="sol",
            destination_system_id="vega",
            target_quantity=5,
            reward_credits=500,
            reward_xp=100,
            sort_order=1,
        ),
        Mission(
            id="mis-ice-runner",
            title="Ice Runner",
            description="Sell 10 hydro units on any route involving Vega.",
            mission_type=MissionType.TRADE_ROUTE,
            product_id="hydro",
            destination_system_id="vega",
            target_quantity=10,
            reward_credits=800,
            reward_xp=150,
            sort_order=2,
        ),
        Mission(
            id="mis-rim-trader",
            title="Rim Trader",
            description="Complete 2 successful routed orders.",
            mission_type=MissionType.ORDER_COUNT,
            target_quantity=2,
            reward_credits=1000,
            reward_xp=200,
            sort_order=3,
        ),
        Mission(
            id="mis-container-pioneer",
            title="Container Pioneer",
            description="Assemble your first cargo container in the marketplace.",
            mission_type=MissionType.SERVICE_ACTION,
            service_category=ServiceCategory.CONTAINER_ASSEMBLY,
            target_quantity=1,
            reward_credits=600,
            reward_xp=120,
            sort_order=4,
        ),
        Mission(
            id="mis-fleet-builder",
            title="Fleet Builder",
            description="Complete 5 successful trade runs to climb the leaderboard.",
            mission_type=MissionType.ORDER_COUNT,
            target_quantity=5,
            reward_credits=1500,
            reward_xp=300,
            sort_order=5,
        ),
    ]
    db.add_all(missions)
    db.commit()

    from starfall.game import get_game_state, get_or_create_profile
    from starfall.models import Client

    get_game_state(db)
    for client in db.query(Client).all():
        get_or_create_profile(db, client.id)
