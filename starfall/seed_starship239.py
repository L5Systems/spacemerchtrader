import uuid

from sqlalchemy.orm import Session

from starfall.marketplace import register_client
from starfall.models import (
    Client,
    Container,
    ContainerPackage,
    LaunchBooking,
    LaunchSlot,
    LaunchSlotStatus,
    ManifestStatus,
    Mission,
    MissionProgress,
    MissionType,
    PlayerManifest,
    RecordStatus,
)
from starfall.manifest import rebuild_starship_registry, sync_starship_registry


def seed_starship239_data(db: Session) -> None:
    if db.query(LaunchSlot).filter(LaunchSlot.id == "slot-starship239-sep-a").first():
        _seed_starship239_mission(db)
        _seed_registry_demo_booking(db)
        rebuild_starship_registry(db)
        return

    slots = [
        LaunchSlot(
            id="slot-starship239-sep-a",
            slot_code="SS239-SEP-A",
            ship_ref="starship239",
            target_orbit="LEO",
            berth_destination="Starship239 Factory Ring, LEO",
            launch_window="2032-09-08 06:00 UTC",
            pad_location="Sol Pad 7",
            package_capacity=8,
            packages_reserved=0,
            status=LaunchSlotStatus.AVAILABLE,
        ),
        LaunchSlot(
            id="slot-starship239-sep-b",
            slot_code="SS239-SEP-B",
            ship_ref="starship239",
            target_orbit="LEO",
            berth_destination="Starship239 Factory Ring, LEO",
            launch_window="2032-09-22 11:30 UTC",
            pad_location="Sol Pad 3",
            package_capacity=8,
            packages_reserved=0,
            status=LaunchSlotStatus.AVAILABLE,
        ),
        LaunchSlot(
            id="slot-starship239-sep-c",
            slot_code="SS239-SEP-C",
            ship_ref="starship239",
            target_orbit="LEO",
            berth_destination="Starship239 Factory Ring, LEO",
            launch_window="2032-09-29 18:00 UTC",
            pad_location="Sol Pad 7",
            package_capacity=8,
            packages_reserved=8,
            status=LaunchSlotStatus.FULL,
        ),
    ]
    db.add_all(slots)
    db.commit()
    _seed_starship239_mission(db)
    _seed_registry_demo_booking(db)
    rebuild_starship_registry(db)


def _seed_starship239_mission(db: Session) -> None:
    if db.query(Mission).filter(Mission.id == "mis-starship239-leo").first():
        return

    mission = Mission(
        id="mis-starship239-leo",
        title="Starship239 LEO Manifest",
        description=(
            "Book a September 2032 LEO berth at the Starship239 factory, advertise capacity, "
            "and validate 2 outbound and 2 return packages on your container."
        ),
        mission_type=MissionType.SERVICE_ACTION,
        ship_ref="starship239",
        min_outbound_packages=2,
        min_return_packages=2,
        target_quantity=4,
        reward_credits=2200,
        reward_xp=350,
        sort_order=8,
    )
    db.add(mission)
    db.commit()

    for client in db.query(Client).all():
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


def _seed_registry_demo_booking(db: Session) -> None:
    """Pre-book slot C for Orion Logistics so the manifest registry is populated at startup."""
    if db.query(PlayerManifest).filter(PlayerManifest.id == "manifest-orion-ss239-c").first():
        return

    client = db.query(Client).filter(Client.email == "logistics@starfall.corp").first()
    if not client:
        client = register_client(
            db,
            email="logistics@starfall.corp",
            password="starfall123",
            display_name="Orion Logistics",
        )

    slot = db.get(LaunchSlot, "slot-starship239-sep-c")
    if not slot:
        return

    container = Container(
        id="container-orion-ss239-c",
        client_id=client.id,
        container_code="CNT-SS239-009",
        owner_name="Orion Logistics",
        system_id="sol",
        status=RecordStatus.ACTIVE,
        notes="Pre-loaded Starship239 LEO manifest container",
    )
    db.add(container)
    db.flush()

    packages = [
        ContainerPackage(
            id=str(uuid.uuid4()),
            container_id=container.id,
            package_id="PKG-9001",
            owner_name="Helios Components",
            recipient_name="Starship239 Factory Intake",
            recipient_id="RCPT-9001",
            address="Starship239 Factory Ring, LEO",
            manifest_leg="outbound",
            manifest_validated=True,
            notes="Factory spare parts shipment",
        ),
        ContainerPackage(
            id=str(uuid.uuid4()),
            container_id=container.id,
            package_id="PKG-9002",
            owner_name="Nova Retail Group",
            recipient_name="Starship239 Factory Intake",
            recipient_id="RCPT-9002",
            address="Starship239 Factory Ring, LEO",
            manifest_leg="outbound",
            manifest_validated=True,
            notes="Retail display modules",
        ),
        ContainerPackage(
            id=str(uuid.uuid4()),
            container_id=container.id,
            package_id="PKG-9010",
            owner_name="Orion Logistics",
            recipient_name="Sol Orbital Dock Receiving",
            recipient_id="RCPT-9010",
            address="Sol Orbital Dock, Bay 12",
            manifest_leg="return",
            manifest_validated=True,
            notes="Finished goods return leg",
        ),
    ]
    db.add_all(packages)

    booking = LaunchBooking(
        id="booking-orion-ss239-c",
        client_id=client.id,
        booking_code="BK-SS239-SEP-C",
        pad_location=slot.pad_location,
        launch_window=slot.launch_window,
        payload_ref=container.container_code,
        mass_kg=2600.0,
        target_orbit=slot.target_orbit,
        berth_destination=slot.berth_destination,
        ship_ref=slot.ship_ref,
        slot_id=slot.id,
        status=RecordStatus.ACTIVE,
        notes="Orion Logistics factory berth on Starship239",
    )
    db.add(booking)

    manifest = PlayerManifest(
        id="manifest-orion-ss239-c",
        client_id=client.id,
        slot_id=slot.id,
        container_id=container.id,
        container_code=container.container_code,
        booking_id=booking.id,
        status=ManifestStatus.READY,
        outbound_slots=4,
        return_slots=4,
        notes="Demo registry entry for Starship239 slot C",
    )
    db.add(manifest)

    slot.status = LaunchSlotStatus.FULL
    slot.booked_by_client_id = client.id
    slot.packages_reserved = slot.package_capacity
    db.commit()
    sync_starship_registry(db, manifest)
