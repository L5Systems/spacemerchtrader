import uuid

from sqlalchemy.orm import Session

from starfall.marketplace import hash_password, register_client
from starfall.models import (
    Client,
    ServiceCategory,
    ServiceOffering,
    ServiceProvider,
)


def seed_marketplace_data(db: Session) -> None:
    if db.query(ServiceProvider).first():
        return

    providers = [
        ServiceProvider(
            id="prov-orbit-crate",
            name="Orbital CrateWorks",
            description="Precision container assembly for high-value and hazardous cargo.",
            home_system_id="sol",
            verified=True,
            rating=4.8,
        ),
        ServiceProvider(
            id="prov-launchstack",
            name="LaunchStack Aggregators",
            description="Stacks and balances container loads for efficient orbital launch windows.",
            home_system_id="sol",
            verified=True,
            rating=4.6,
        ),
        ServiceProvider(
            id="prov-terralift",
            name="TerraLift Ground Launch",
            description="Heavy-lift ground launch from Sol planetary pads to orbital transfer lanes.",
            home_system_id="sol",
            verified=True,
            rating=4.4,
        ),
        ServiceProvider(
            id="prov-portmaster",
            name="PortMaster Logistics",
            description="Station-to-yard container porters with bonded transfer clearance.",
            home_system_id="vega",
            verified=True,
            rating=4.5,
        ),
        ServiceProvider(
            id="prov-kepler-gate",
            name="Kepler Gate Terminal",
            description="Offworld endpoint gateway for rim-system intake and customs staging.",
            home_system_id="kepler",
            verified=True,
            rating=4.2,
        ),
        ServiceProvider(
            id="prov-deep-haul",
            name="Deep Haul Offworld",
            description="Long-range offworld container delivery to remote stations and mining outposts.",
            home_system_id="vega",
            verified=True,
            rating=4.7,
        ),
    ]
    db.add_all(providers)

    offerings = [
        ServiceOffering(
            id=str(uuid.uuid4()),
            provider_id="prov-orbit-crate",
            category=ServiceCategory.CONTAINER_ASSEMBLY,
            system_id="sol",
            base_rate=420.0,
            capacity=40,
            unit="container",
            description="Standard crate assembly at Sol Orbital Dock.",
        ),
        ServiceOffering(
            id=str(uuid.uuid4()),
            provider_id="prov-orbit-crate",
            category=ServiceCategory.CONTAINER_ASSEMBLY,
            system_id="vega",
            base_rate=510.0,
            capacity=25,
            unit="container",
            description="Remote assembly line at Vega Trade Hub.",
        ),
        ServiceOffering(
            id=str(uuid.uuid4()),
            provider_id="prov-launchstack",
            category=ServiceCategory.CONTAINER_AGGREGATOR,
            system_id="sol",
            base_rate=880.0,
            capacity=12,
            unit="stack",
            description="Launch-stack aggregation for Sol departure windows.",
        ),
        ServiceOffering(
            id=str(uuid.uuid4()),
            provider_id="prov-launchstack",
            category=ServiceCategory.CONTAINER_AGGREGATOR,
            system_id="vega",
            base_rate=920.0,
            capacity=10,
            unit="stack",
            description="Vega orbital aggregation for multi-lane departures.",
        ),
        ServiceOffering(
            id=str(uuid.uuid4()),
            provider_id="prov-terralift",
            category=ServiceCategory.GROUND_LAUNCH,
            system_id="sol",
            base_rate=2400.0,
            capacity=6,
            unit="launch",
            description="Surface pad launch to high-orbit transfer slot.",
        ),
        ServiceOffering(
            id=str(uuid.uuid4()),
            provider_id="prov-portmaster",
            category=ServiceCategory.CONTAINER_PORTER,
            system_id="vega",
            base_rate=190.0,
            capacity=80,
            unit="container",
            description="Intra-station porter service across Vega Alpha facilities.",
        ),
        ServiceOffering(
            id=str(uuid.uuid4()),
            provider_id="prov-portmaster",
            category=ServiceCategory.CONTAINER_PORTER,
            system_id="kepler",
            base_rate=260.0,
            capacity=45,
            unit="container",
            description="Rim yard porter runs with escort for high-risk lanes.",
        ),
        ServiceOffering(
            id=str(uuid.uuid4()),
            provider_id="prov-kepler-gate",
            category=ServiceCategory.OFFWORLD_ENDPOINT,
            system_id="kepler",
            base_rate=350.0,
            capacity=120,
            unit="container",
            description="Offworld gateway receipt and staging at Kepler Rim.",
        ),
        ServiceOffering(
            id=str(uuid.uuid4()),
            provider_id="prov-deep-haul",
            category=ServiceCategory.OFFWORLD_DELIVERY,
            system_id="sol",
            base_rate=1100.0,
            capacity=30,
            unit="container",
            description="Sol-origin offworld delivery to registered endpoints.",
        ),
        ServiceOffering(
            id=str(uuid.uuid4()),
            provider_id="prov-deep-haul",
            category=ServiceCategory.OFFWORLD_DELIVERY,
            system_id="vega",
            base_rate=980.0,
            capacity=35,
            unit="container",
            description="Vega hub outbound delivery to frontier sites.",
        ),
        ServiceOffering(
            id=str(uuid.uuid4()),
            provider_id="prov-deep-haul",
            category=ServiceCategory.OFFWORLD_DELIVERY,
            system_id="kepler",
            base_rate=1450.0,
            capacity=20,
            unit="container",
            description="Kepler rim last-leg delivery with delay insurance.",
        ),
    ]
    db.add_all(offerings)
    db.commit()

    if not db.query(Client).filter(Client.email == "trader@starfall.corp").first():
        register_client(
            db,
            email="trader@starfall.corp",
            password="starfall123",
            display_name="Aurora Trader",
        )

    if not db.query(Client).filter(Client.email == "admin@starfall.corp").first():
        from starfall.models import ClientRole

        register_client(
            db,
            email="admin@starfall.corp",
            password="starfall123",
            display_name="Marketplace Admin",
            role=ClientRole.ADMIN,
        )
