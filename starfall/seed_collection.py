import uuid

from sqlalchemy.orm import Session

from starfall.models import (
    ClientAccess,
    ContractorDisposition,
    Mission,
    MissionProgress,
    MissionType,
    ServiceCategory,
    ServiceOffering,
    ServiceProvider,
)


def seed_collection_data(db: Session) -> None:
    if db.query(ServiceProvider).filter(ServiceProvider.id == "prov-harbor-line").first():
        _seed_collection_missions(db)
        _grant_collection_access(db)
        return

    providers = [
        ServiceProvider(
            id="prov-harbor-line",
            name="Harbor Line Collectors",
            description="Licensed offshore pickup crews with bonded manifests and clean safety records.",
            home_system_id="sol",
            verified=True,
            rating=4.9,
            contractor_disposition=ContractorDisposition.RELIABLE,
        ),
        ServiceProvider(
            id="prov-driftwood",
            name="Driftwood Offshore Partners",
            description="Steady contractors for routine container lifts from orbital transfer stations.",
            home_system_id="vega",
            verified=True,
            rating=4.6,
            contractor_disposition=ContractorDisposition.RELIABLE,
        ),
        ServiceProvider(
            id="prov-black-tidemark",
            name="Black Tidemark Salvage",
            description="Fast pickups, questionable paperwork, and creative fee structures.",
            home_system_id="kepler",
            verified=False,
            rating=3.8,
            contractor_disposition=ContractorDisposition.CROOKED,
        ),
        ServiceProvider(
            id="prov-rim-jobbers",
            name="Rim Jobbers Union",
            description="Offshore crews that always find something extra to charge for.",
            home_system_id="vega",
            verified=False,
            rating=3.5,
            contractor_disposition=ContractorDisposition.CROOKED,
        ),
        ServiceProvider(
            id="prov-slipstream",
            name="Slipstream Recovery Co.",
            description="Aggressive pickup windows and a history of crane incidents.",
            home_system_id="sol",
            verified=True,
            rating=3.2,
            contractor_disposition=ContractorDisposition.ACCIDENT_PRONE,
        ),
        ServiceProvider(
            id="prov-broken-boom",
            name="Broken Boom Logistics",
            description="Cheap offshore collection with frequent equipment failures.",
            home_system_id="kepler",
            verified=False,
            rating=2.9,
            contractor_disposition=ContractorDisposition.ACCIDENT_PRONE,
        ),
    ]
    db.add_all(providers)

    offerings = [
        ServiceOffering(
            id=str(uuid.uuid4()),
            provider_id="prov-harbor-line",
            category=ServiceCategory.CONTAINER_COLLECTION,
            system_id="sol",
            base_rate=320.0,
            capacity=50,
            unit="pickup",
            description="Certified offshore container collection at Sol drift platforms.",
        ),
        ServiceOffering(
            id=str(uuid.uuid4()),
            provider_id="prov-driftwood",
            category=ServiceCategory.CONTAINER_COLLECTION,
            system_id="vega",
            base_rate=290.0,
            capacity=40,
            unit="pickup",
            description="Vega offshore pickup from outer mooring stations.",
        ),
        ServiceOffering(
            id=str(uuid.uuid4()),
            provider_id="prov-black-tidemark",
            category=ServiceCategory.CONTAINER_COLLECTION,
            system_id="kepler",
            base_rate=180.0,
            capacity=35,
            unit="pickup",
            description="Low-cost rim pickup with flexible invoicing.",
        ),
        ServiceOffering(
            id=str(uuid.uuid4()),
            provider_id="prov-rim-jobbers",
            category=ServiceCategory.CONTAINER_COLLECTION,
            system_id="vega",
            base_rate=210.0,
            capacity=30,
            unit="pickup",
            description="Union offshore crews with side contracts available.",
        ),
        ServiceOffering(
            id=str(uuid.uuid4()),
            provider_id="prov-slipstream",
            category=ServiceCategory.CONTAINER_COLLECTION,
            system_id="sol",
            base_rate=150.0,
            capacity=45,
            unit="pickup",
            description="Budget Sol pickup runs with high incident reports.",
        ),
        ServiceOffering(
            id=str(uuid.uuid4()),
            provider_id="prov-broken-boom",
            category=ServiceCategory.CONTAINER_COLLECTION,
            system_id="kepler",
            base_rate=130.0,
            capacity=25,
            unit="pickup",
            description="Kepler offshore salvage pickup on a best-effort basis.",
        ),
    ]
    db.add_all(offerings)
    db.commit()

    _seed_collection_missions(db)
    _grant_collection_access(db)


def _seed_collection_missions(db: Session) -> None:
    missions = [
        Mission(
            id="mis-safe-pickup",
            title="Safe Pickup",
            description="Complete an offshore collection with a reliable contractor.",
            mission_type=MissionType.SERVICE_ACTION,
            service_category=ServiceCategory.CONTAINER_COLLECTION,
            contractor_disposition=ContractorDisposition.RELIABLE,
            target_quantity=1,
            reward_credits=700,
            reward_xp=140,
            sort_order=6,
        ),
        Mission(
            id="mis-under-the-table",
            title="Under the Table",
            description="Survive a pickup with a crooked offshore contractor.",
            mission_type=MissionType.SERVICE_ACTION,
            service_category=ServiceCategory.CONTAINER_COLLECTION,
            contractor_disposition=ContractorDisposition.CROOKED,
            target_quantity=1,
            reward_credits=900,
            reward_xp=180,
            sort_order=7,
        ),
        Mission(
            id="mis-hazard-pay",
            title="Hazard Pay",
            description="Complete a pickup with an accident-prone contractor.",
            mission_type=MissionType.SERVICE_ACTION,
            service_category=ServiceCategory.CONTAINER_COLLECTION,
            contractor_disposition=ContractorDisposition.ACCIDENT_PRONE,
            target_quantity=1,
            reward_credits=850,
            reward_xp=170,
            sort_order=8,
        ),
    ]
    for mission in missions:
        if not db.get(Mission, mission.id):
            db.add(mission)
    db.commit()

    from starfall.models import Client

    for client in db.query(Client).all():
        for mission in missions:
            exists = (
                db.query(MissionProgress)
                .filter(
                    MissionProgress.client_id == client.id,
                    MissionProgress.mission_id == mission.id,
                )
                .first()
            )
            if not exists:
                db.add(MissionProgress(client_id=client.id, mission_id=mission.id, progress=0))
    db.commit()


def _grant_collection_access(db: Session) -> None:
    from starfall.models import Client

    for client in db.query(Client).all():
        exists = (
            db.query(ClientAccess)
            .filter(
                ClientAccess.client_id == client.id,
                ClientAccess.category == ServiceCategory.CONTAINER_COLLECTION,
            )
            .first()
        )
        if not exists:
            db.add(
                ClientAccess(
                    client_id=client.id,
                    category=ServiceCategory.CONTAINER_COLLECTION,
                    enabled=True,
                )
            )
    db.commit()
