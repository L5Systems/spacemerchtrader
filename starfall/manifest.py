"""Starship239 LEO manifest workflow for the Launch Broker agent."""

from __future__ import annotations

import re
import uuid
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from starfall.models import (
    Client,
    Container,
    ContainerPackage,
    LaunchBooking,
    LaunchSlot,
    LaunchSlotStatus,
    ManifestStatus,
    Mission,
    PlayerManifest,
    RecordStatus,
    StarshipContainerRegistry,
)

STARSHIP239 = "starship239"
LEO_FACTORY_ADDRESS_HINTS = ("starship239", "leo", "factory")

_MONTHS: dict[str, int] = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


def _touch(record) -> None:
    record.updated_at = datetime.now(timezone.utc)


def get_active_manifest(db: Session, client_id: str, ship_ref: str = STARSHIP239) -> PlayerManifest | None:
    return (
        db.query(PlayerManifest)
        .join(LaunchSlot, PlayerManifest.slot_id == LaunchSlot.id)
        .filter(
            PlayerManifest.client_id == client_id,
            LaunchSlot.ship_ref == ship_ref,
            PlayerManifest.status != ManifestStatus.COMPLETED,
        )
        .order_by(PlayerManifest.created_at.desc())
        .first()
    )


def slot_to_dict(slot: LaunchSlot) -> dict[str, Any]:
    remaining = max(0, slot.package_capacity - slot.packages_reserved)
    return {
        "id": slot.id,
        "slot_code": slot.slot_code,
        "ship_ref": slot.ship_ref,
        "target_orbit": slot.target_orbit,
        "berth_destination": slot.berth_destination,
        "launch_window": slot.launch_window,
        "pad_location": slot.pad_location,
        "package_capacity": slot.package_capacity,
        "packages_reserved": slot.packages_reserved,
        "packages_remaining": remaining,
        "status": slot.status.value,
    }


def manifest_to_dict(db: Session, manifest: PlayerManifest) -> dict[str, Any]:
    slot = db.get(LaunchSlot, manifest.slot_id)
    container = db.get(Container, manifest.container_id) if manifest.container_id else None
    outbound = 0
    validated_outbound = 0
    validated_return = 0
    packages: list[dict] = []
    if container:
        for pkg in container.packages:
            packages.append(
                {
                    "package_id": pkg.package_id,
                    "manifest_leg": pkg.manifest_leg,
                    "manifest_validated": pkg.manifest_validated,
                    "recipient_name": pkg.recipient_name,
                    "address": pkg.address,
                }
            )
            if pkg.manifest_leg == "outbound":
                outbound += 1
            if pkg.manifest_validated and pkg.manifest_leg == "outbound":
                validated_outbound += 1
            if pkg.manifest_validated and pkg.manifest_leg == "return":
                validated_return += 1

    return {
        "id": manifest.id,
        "container_code": manifest.container_code,
        "status": manifest.status.value,
        "booking_id": manifest.booking_id,
        "slot": slot_to_dict(slot) if slot else None,
        "outbound_slots": manifest.outbound_slots,
        "return_slots": manifest.return_slots,
        "validated_outbound": validated_outbound,
        "validated_return": validated_return,
        "packages": packages,
    }


def find_leo_slots(
    db: Session,
    *,
    ship_ref: str = STARSHIP239,
    month_hint: str = "2032-09",
) -> list[dict]:
    rows = (
        db.query(LaunchSlot)
        .filter(
            LaunchSlot.ship_ref == ship_ref,
            LaunchSlot.target_orbit == "LEO",
            LaunchSlot.launch_window.contains(month_hint),
        )
        .order_by(LaunchSlot.launch_window)
        .all()
    )
    return [slot_to_dict(row) for row in rows]


def _ensure_container(db: Session, client_id: str, container_code: str) -> Container:
    existing = (
        db.query(Container)
        .filter(Container.client_id == client_id, Container.container_code == container_code)
        .first()
    )
    if existing:
        return existing

    container = Container(
        id=str(uuid.uuid4()),
        client_id=client_id,
        container_code=container_code,
        owner_name="Starfall Trader",
        system_id="sol",
        status=RecordStatus.ACTIVE,
        notes="Starship239 LEO manifest container",
    )
    db.add(container)
    db.flush()
    return container


def book_launch_slot(
    db: Session,
    client_id: str,
    slot_id: str,
    container_code: str,
) -> tuple[PlayerManifest, LaunchBooking]:
    slot = db.get(LaunchSlot, slot_id)
    if not slot:
        slot = (
            db.query(LaunchSlot)
            .filter(LaunchSlot.slot_code == slot_id.upper().replace("SLOT-", ""))
            .first()
        )
    if not slot:
        slot = db.query(LaunchSlot).filter(LaunchSlot.slot_code == slot_id.upper()).first()
    if not slot:
        raise ValueError(f"Launch slot '{slot_id}' not found")
    if slot.status != LaunchSlotStatus.AVAILABLE:
        raise ValueError(f"Slot {slot.slot_code} is not available ({slot.status.value})")

    existing = get_active_manifest(db, client_id, slot.ship_ref)
    if existing and existing.booking_id:
        raise ValueError("You already have an active manifest booking for this ship")

    container = _ensure_container(db, client_id, container_code)
    booking = LaunchBooking(
        id=str(uuid.uuid4()),
        client_id=client_id,
        booking_code=f"BK-{slot.slot_code.upper()}",
        pad_location=slot.pad_location,
        launch_window=slot.launch_window,
        payload_ref=container_code,
        mass_kg=2400.0,
        target_orbit=slot.target_orbit,
        berth_destination=slot.berth_destination,
        ship_ref=slot.ship_ref,
        slot_id=slot.id,
        status=RecordStatus.ACTIVE,
        notes=f"Berth at {slot.berth_destination}",
    )
    db.add(booking)

    manifest = PlayerManifest(
        id=str(uuid.uuid4()),
        client_id=client_id,
        slot_id=slot.id,
        container_id=container.id,
        container_code=container_code,
        booking_id=booking.id,
        status=ManifestStatus.BOOKED,
        outbound_slots=4,
        return_slots=4,
        notes="Starship239 LEO round-trip manifest",
    )
    db.add(manifest)

    slot.status = LaunchSlotStatus.BOOKED
    slot.booked_by_client_id = client_id
    slot.packages_reserved = min(slot.package_capacity, 4)
    db.commit()
    db.refresh(manifest)
    db.refresh(booking)
    sync_starship_registry(db, manifest)
    return manifest, booking


def advertise_manifest(db: Session, client_id: str) -> PlayerManifest:
    manifest = get_active_manifest(db, client_id)
    if not manifest or not manifest.booking_id:
        raise ValueError("Book a launch slot before advertising package capacity")
    manifest.status = ManifestStatus.ADVERTISING
    manifest.notes = (
        f"Seeking outbound and return packages for {manifest.container_code} "
        f"aboard {STARSHIP239} LEO factory berth."
    )
    _touch(manifest)
    db.commit()
    db.refresh(manifest)
    sync_starship_registry(db, manifest)
    return manifest


def _validate_package_record(pkg: ContainerPackage, leg: str) -> tuple[bool, str]:
    required = [pkg.package_id, pkg.owner_name, pkg.recipient_name, pkg.recipient_id, pkg.address]
    if not all(str(value).strip() for value in required):
        return False, "Package is missing required manifest fields"

    address = pkg.address.lower()
    if leg == "outbound":
        if not any(hint in address for hint in LEO_FACTORY_ADDRESS_HINTS):
            return (
                False,
                "Outbound packages must address Starship239 or the LEO factory berth",
            )
    elif leg == "return":
        if any(hint in address for hint in ("starship239 factory", "leo factory ring")):
            return False, "Return packages should use a ground or station delivery address"
    else:
        return False, "Package leg must be outbound or return"

    return True, "Package validated for manifest"


def validate_manifest_package(
    db: Session,
    client_id: str,
    package_id: str,
    *,
    leg: str | None = None,
) -> ContainerPackage:
    manifest = get_active_manifest(db, client_id)
    if not manifest or not manifest.container_id:
        raise ValueError("Book a launch slot and load packages on your manifest container first")

    container = db.get(Container, manifest.container_id)
    if not container or container.client_id != client_id:
        raise ValueError("Manifest container not found")

    pkg = (
        db.query(ContainerPackage)
        .filter(
            ContainerPackage.container_id == container.id,
            ContainerPackage.package_id == package_id,
        )
        .first()
    )
    if not pkg:
        raise ValueError(f"Package '{package_id}' is not on container {manifest.container_code}")

    chosen_leg = (leg or pkg.manifest_leg or "").lower()
    if chosen_leg not in {"outbound", "return"}:
        raise ValueError("Set manifest leg to outbound or return before validation")

    pkg.manifest_leg = chosen_leg
    ok, detail = _validate_package_record(pkg, chosen_leg)
    pkg.manifest_validated = ok
    pkg.notes = detail if ok else f"Rejected: {detail}"
    _touch(pkg)
    if ok and manifest.status == ManifestStatus.ADVERTISING:
        manifest.status = ManifestStatus.READY
        _touch(manifest)
    db.commit()
    db.refresh(pkg)
    manifest = get_active_manifest(db, client_id)
    if manifest:
        sync_starship_registry(db, manifest)
    return pkg


def count_manifest_mission_progress(db: Session, client_id: str, mission: Mission) -> int:
    ship_ref = mission.ship_ref or STARSHIP239
    manifest = get_active_manifest(db, client_id, ship_ref)
    if not manifest or not manifest.booking_id or not manifest.container_id:
        return 0

    container = db.get(Container, manifest.container_id)
    if not container:
        return 0

    validated_outbound = sum(
        1
        for pkg in container.packages
        if pkg.manifest_validated and pkg.manifest_leg == "outbound"
    )
    validated_return = sum(
        1
        for pkg in container.packages
        if pkg.manifest_validated and pkg.manifest_leg == "return"
    )

    min_out = mission.min_outbound_packages or 0
    min_ret = mission.min_return_packages or 0
    if validated_outbound >= min_out and validated_return >= min_ret:
        return mission.target_quantity
    return min(validated_outbound + validated_return, max(mission.target_quantity - 1, 0))


def sync_starship_registry(db: Session, manifest: PlayerManifest) -> StarshipContainerRegistry | None:
    """Upsert or remove a registry row for an active manifest booking."""
    if not manifest.booking_id or manifest.status == ManifestStatus.COMPLETED:
        db.query(StarshipContainerRegistry).filter(
            StarshipContainerRegistry.manifest_id == manifest.id
        ).delete()
        db.commit()
        return None

    slot = db.get(LaunchSlot, manifest.slot_id)
    booking = db.get(LaunchBooking, manifest.booking_id)
    container = db.get(Container, manifest.container_id) if manifest.container_id else None
    client = db.get(Client, manifest.client_id)
    if not slot or not booking or not container or not client:
        return None

    package_count = len(container.packages)
    entry = (
        db.query(StarshipContainerRegistry)
        .filter(StarshipContainerRegistry.manifest_id == manifest.id)
        .first()
    )
    if entry:
        entry.ship_ref = slot.ship_ref
        entry.booking_id = booking.id
        entry.slot_id = slot.id
        entry.container_id = container.id
        entry.container_code = manifest.container_code
        entry.container_owner_name = container.owner_name
        entry.trader_client_id = client.id
        entry.trader_display_name = client.display_name
        entry.slot_code = slot.slot_code
        entry.launch_window = booking.launch_window
        entry.berth_destination = booking.berth_destination
        entry.manifest_status = manifest.status.value
        entry.package_count = package_count
        _touch(entry)
    else:
        entry = StarshipContainerRegistry(
            id=str(uuid.uuid4()),
            ship_ref=slot.ship_ref,
            manifest_id=manifest.id,
            booking_id=booking.id,
            slot_id=slot.id,
            container_id=container.id,
            container_code=manifest.container_code,
            container_owner_name=container.owner_name,
            trader_client_id=client.id,
            trader_display_name=client.display_name,
            slot_code=slot.slot_code,
            launch_window=booking.launch_window,
            berth_destination=booking.berth_destination,
            manifest_status=manifest.status.value,
            package_count=package_count,
        )
        db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def rebuild_starship_registry(db: Session) -> int:
    """Backfill registry rows from active manifests (e.g. after schema migration)."""
    manifests = (
        db.query(PlayerManifest)
        .filter(
            PlayerManifest.booking_id.isnot(None),
            PlayerManifest.status != ManifestStatus.COMPLETED,
        )
        .all()
    )
    for manifest in manifests:
        sync_starship_registry(db, manifest)
    return len(manifests)


def registry_entry_to_dict(db: Session, entry: StarshipContainerRegistry) -> dict[str, Any]:
    container = db.get(Container, entry.container_id)
    packages = [_package_out(pkg) for pkg in container.packages] if container else []
    return {
        "id": entry.id,
        "ship_ref": entry.ship_ref,
        "manifest_id": entry.manifest_id,
        "booking_id": entry.booking_id,
        "container_code": entry.container_code,
        "container_owner_name": entry.container_owner_name,
        "trader_client_id": entry.trader_client_id,
        "trader_display_name": entry.trader_display_name,
        "slot_code": entry.slot_code,
        "launch_window": entry.launch_window,
        "berth_destination": entry.berth_destination,
        "manifest_status": entry.manifest_status,
        "package_count": entry.package_count,
        "packages": packages,
        "updated_at": entry.updated_at.isoformat() if entry.updated_at else None,
    }


def list_starship_registry(
    db: Session,
    *,
    ship_ref: str | None = None,
    container_code: str | None = None,
) -> dict[str, Any]:
    query = db.query(StarshipContainerRegistry).order_by(
        StarshipContainerRegistry.ship_ref,
        StarshipContainerRegistry.launch_window,
        StarshipContainerRegistry.container_code,
    )
    if ship_ref:
        query = query.filter(StarshipContainerRegistry.ship_ref == ship_ref.lower())
    if container_code:
        query = query.filter(StarshipContainerRegistry.container_code == container_code.upper())

    entries = [registry_entry_to_dict(db, row) for row in query.all()]
    ships: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        ships.setdefault(entry["ship_ref"], []).append(entry)

    return {
        "ships": [
            {"ship_ref": ship, "container_count": len(containers), "containers": containers}
            for ship, containers in sorted(ships.items())
        ],
        "total_containers": len(entries),
    }


def _month_token_to_number(token: str) -> int | None:
    return _MONTHS.get(token.lower().strip())


def parse_date_hint(text: str) -> date | None:
    """Extract a calendar date from natural language or ISO text."""
    iso_match = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", text)
    if iso_match:
        year, month, day = map(int, iso_match.groups())
        try:
            return date(year, month, day)
        except ValueError:
            return None

    dmy_match = re.search(
        r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|"
        r"may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t|tember)?|oct(?:ober)?|"
        r"nov(?:ember)?|dec(?:ember)?)\s+(\d{4})\b",
        text,
        re.IGNORECASE,
    )
    if dmy_match:
        day = int(dmy_match.group(1))
        month = _month_token_to_number(dmy_match.group(2))
        year = int(dmy_match.group(3))
        if month:
            try:
                return date(year, month, day)
            except ValueError:
                return None

    mdy_match = re.search(
        r"\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|"
        r"aug(?:ust)?|sep(?:t|tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+"
        r"(\d{1,2})(?:st|nd|rd|th)?(?:,?\s+(\d{4}))?\b",
        text,
        re.IGNORECASE,
    )
    if mdy_match:
        month = _month_token_to_number(mdy_match.group(1))
        day = int(mdy_match.group(2))
        year = int(mdy_match.group(3) or "2032")
        if month:
            try:
                return date(year, month, day)
            except ValueError:
                return None

    return None


def parse_month_hint(text: str) -> str | None:
    """Extract YYYY-MM from phrases like 'September 2032'."""
    iso_match = re.search(r"\b(\d{4})-(\d{2})\b", text)
    if iso_match:
        return f"{iso_match.group(1)}-{iso_match.group(2)}"

    month_match = re.search(
        r"\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|"
        r"aug(?:ust)?|sep(?:t|tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
        r"(?:\s+(\d{4}))?\b",
        text,
        re.IGNORECASE,
    )
    if not month_match:
        return None
    month = _month_token_to_number(month_match.group(1))
    if not month:
        return None
    year = month_match.group(2) or re.search(r"\b(20\d{2})\b", text)
    year_value = int(year.group(1) if hasattr(year, "group") else year or "2032")
    return f"{year_value:04d}-{month:02d}"


def _launch_window_date(launch_window: str) -> date | None:
    try:
        return datetime.strptime(launch_window[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _container_matches_date_filter(container: dict[str, Any], *, on_date: date | None, month: str | None) -> bool:
    launch_date = _launch_window_date(container.get("launch_window", ""))
    if not launch_date:
        return False
    if on_date:
        return launch_date == on_date
    if month:
        return launch_date.strftime("%Y-%m") == month
    return True


def query_manifest_registry(
    db: Session,
    *,
    ship_ref: str | None = None,
    on_date: date | None = None,
    month: str | None = None,
    metric: str = "packages",
) -> dict[str, Any]:
    """Answer analytical questions over the manifest registry."""
    registry = list_starship_registry(db, ship_ref=ship_ref)
    all_containers: list[dict[str, Any]] = []
    for ship in registry["ships"]:
        all_containers.extend(ship["containers"])

    if on_date or month:
        matching = [
            container
            for container in all_containers
            if _container_matches_date_filter(container, on_date=on_date, month=month)
        ]
    else:
        matching = all_containers

    package_count = sum(len(container.get("packages") or []) for container in matching)
    validated_count = sum(
        1
        for container in matching
        for pkg in container.get("packages") or []
        if pkg.get("manifest_validated")
    )

    launch_dates = sorted(
        {
            launch.isoformat()
            for container in all_containers
            if (launch := _launch_window_date(container.get("launch_window", "")))
        }
    )

    return {
        "ship_ref": ship_ref,
        "date": on_date.isoformat() if on_date else None,
        "month": month,
        "metric": metric,
        "container_count": len(matching),
        "package_count": package_count,
        "validated_package_count": validated_count,
        "containers": matching,
        "known_launch_dates": launch_dates,
    }


def format_query_registry_message(result: dict[str, Any]) -> str:
    ship_label = result.get("ship_ref") or "all starships"
    metric = result.get("metric") or "packages"
    container_count = result["container_count"]
    package_count = result["package_count"]

    when_parts: list[str] = []
    if result.get("date"):
        when_parts.append(f"on {result['date']}")
    elif result.get("month"):
        when_parts.append(f"in {result['month']}")
    when_text = " ".join(when_parts)

    if metric == "containers":
        headline = (
            f"{container_count} container(s) booked for {ship_label}{(' ' + when_text) if when_text else ''}."
        )
    elif metric == "both":
        headline = (
            f"{container_count} container(s) and {package_count} package(s) booked for "
            f"{ship_label}{(' ' + when_text) if when_text else ''}."
        )
    else:
        headline = (
            f"{package_count} package(s) booked for {ship_label}{(' ' + when_text) if when_text else ''}."
        )

    lines = [headline]
    if container_count == 0 and when_text and result.get("known_launch_dates"):
        lines.append(
            "Known launch dates with bookings: "
            + ", ".join(result["known_launch_dates"])
            + "."
        )
    elif matching := result.get("containers"):
        lines.append("Matching bookings:")
        for container in matching:
            pkg_count = len(container.get("packages") or [])
            lines.append(
                f"- {container['container_code']} ({container['launch_window']}): "
                f"{pkg_count} package(s), trader {container['trader_display_name']}, "
                f"container owner {container['container_owner_name']}"
            )
            for pkg in container.get("packages") or []:
                lines.append(
                    f"    · {pkg['package_id']} ({pkg['manifest_leg'] or 'unset'}) "
                    f"owner {pkg['owner_name']}"
                )

    if result.get("validated_package_count") is not None and package_count:
        lines.append(f"Validated packages: {result['validated_package_count']} of {package_count}.")

    return "\n".join(lines)


def format_registry_message(registry: dict[str, Any], *, ship_ref: str | None = None) -> str:
    if registry["total_containers"] == 0:
        if ship_ref:
            return f"No containers are currently booked on {ship_ref}."
        return "No containers are currently booked on any starship."

    lines: list[str] = []
    for ship in registry["ships"]:
        ship_label = ship["ship_ref"]
        lines.append(f"{ship_label} ({ship['container_count']} container(s)):")
        for container in ship["containers"]:
            lines.append(
                f"  • {container['container_code']} — container owner: {container['container_owner_name']}, "
                f"trader: {container['trader_display_name']}, slot {container['slot_code']} "
                f"({container['launch_window']})"
            )
            if container["packages"]:
                for pkg in container["packages"]:
                    validated = "validated" if pkg["manifest_validated"] else "pending"
                    lines.append(
                        f"      - {pkg['package_id']} ({pkg['manifest_leg'] or 'unset'}, {validated}) "
                        f"package owner: {pkg['owner_name']} -> {pkg['recipient_name']} @ {pkg['address']}"
                    )
            else:
                lines.append("      (no packages loaded yet)")
        lines.append("")

    title = f"Manifest registry for {ship_ref}" if ship_ref else "Starship manifest registry"
    return title + ":\n" + "\n".join(lines).rstrip()


def _extract_ship_ref(instruction: str, payload: dict[str, Any]) -> str | None:
    if payload.get("ship_ref"):
        return str(payload["ship_ref"]).lower()
    text = instruction.lower()
    if "starship239" in text or "starship 239" in text or "ss239" in text:
        return STARSHIP239
    match = re.search(r"starship\s*(\w+)", text)
    if match:
        return f"starship{match.group(1)}"
    return None


def _package_out(pkg: ContainerPackage) -> dict[str, Any]:
    return {
        "id": pkg.id,
        "package_id": pkg.package_id,
        "owner_name": pkg.owner_name,
        "recipient_name": pkg.recipient_name,
        "recipient_id": pkg.recipient_id,
        "address": pkg.address,
        "manifest_leg": pkg.manifest_leg,
        "manifest_validated": pkg.manifest_validated,
        "notes": pkg.notes,
    }


def _require_booked_manifest(db: Session, client_id: str) -> tuple[PlayerManifest, Container]:
    manifest = get_active_manifest(db, client_id)
    if not manifest or not manifest.booking_id:
        raise ValueError("Book a launch slot before managing packages on your container")
    if not manifest.container_id:
        raise ValueError("Manifest container is not set up yet")
    container = db.get(Container, manifest.container_id)
    if not container or container.client_id != client_id:
        raise ValueError("Manifest container not found")
    return manifest, container


def list_manifest_packages(db: Session, client_id: str) -> list[dict[str, Any]]:
    _, container = _require_booked_manifest(db, client_id)
    return [_package_out(pkg) for pkg in container.packages]


def _default_address_for_leg(leg: str) -> str:
    if leg == "return":
        return "Sol Orbital Dock, Bay 12"
    return "Starship239 Factory Ring, LEO"


def _extract_package_id(instruction: str, payload: dict[str, Any]) -> str | None:
    if payload.get("package_id"):
        return str(payload["package_id"]).upper()
    match = re.search(r"(pkg[-\w]+)", instruction, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    for token in instruction.upper().split():
        if token.startswith("PKG-"):
            return token
    return None


def _extract_leg(instruction: str, payload: dict[str, Any]) -> str:
    leg = payload.get("leg") or payload.get("manifest_leg")
    if leg:
        return str(leg).lower()
    text = instruction.lower()
    if "return" in text:
        return "return"
    if "outbound" in text:
        return "outbound"
    return "outbound"


def add_manifest_package(db: Session, client_id: str, data: dict[str, Any]) -> ContainerPackage:
    manifest, container = _require_booked_manifest(db, client_id)

    leg = _extract_leg("", data)
    package_id = data.get("package_id") or f"PKG-{uuid.uuid4().hex[:4].upper()}"
    package_id = str(package_id).upper()

    existing = (
        db.query(ContainerPackage)
        .filter(
            ContainerPackage.container_id == container.id,
            ContainerPackage.package_id == package_id,
        )
        .first()
    )
    if existing:
        raise ValueError(f"Package '{package_id}' is already on container {manifest.container_code}")

    owner_name = str(data.get("owner_name") or "Starfall Trader").strip()
    recipient_name = str(data.get("recipient_name") or "Manifest Customer").strip()
    recipient_id = str(data.get("recipient_id") or f"RCPT-{package_id[-4:]}").strip()
    address = str(data.get("address") or _default_address_for_leg(leg)).strip()

    pkg = ContainerPackage(
        id=str(uuid.uuid4()),
        container_id=container.id,
        package_id=package_id,
        owner_name=owner_name,
        recipient_name=recipient_name,
        recipient_id=recipient_id,
        address=address,
        notes=str(data.get("notes") or ""),
        manifest_leg=leg,
        manifest_validated=False,
    )
    db.add(pkg)
    _touch(container)
    _touch(manifest)
    db.commit()
    db.refresh(pkg)
    manifest = get_active_manifest(db, client_id)
    if manifest:
        sync_starship_registry(db, manifest)
    return pkg


def parse_broker_action(instruction: str, payload: dict[str, Any]) -> str:
    if payload.get("action"):
        return str(payload["action"]).lower()

    text = instruction.lower()
    if any(
        phrase in text
        for phrase in (
            "manifest registry",
            "starship registry",
            "booked containers",
            "containers booked",
            "registry",
            "all containers on",
        )
    ):
        return "list_registry"
    if re.search(r"\b(help|process)\b", text):
        return "help"
    if re.search(r"\bhow (?:do|to|can|should|would)\b", text):
        return "help"
    if "status" in text or "progress" in text:
        return "status"
    if any(
        phrase in text
        for phrase in (
            "how many",
            "how much",
            "count",
            "number of",
            "total packages",
            "total containers",
        )
    ):
        return "query_registry"
    if any(phrase in text for phrase in ("list package", "show package", "packages on", "what packages")):
        return "list_packages"
    if any(phrase in text for phrase in ("add package", "place package", "load package", "create package")):
        return "add_package"
    if "book" in text and "slot" in text:
        return "book_slot"
    if "book" in text:
        return "book_slot"
    if any(word in text for word in ("find", "search", "slot", "september", "2032", "leo")):
        return "find_slots"
    if "advert" in text:
        return "advertise"
    if "valid" in text:
        return "validate_package"
    return "help"


def broker_respond(
    db: Session,
    client_id: str | None,
    instruction: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    action = parse_broker_action(instruction, payload)

    if action == "help":
        return {
            "message": (
                "I am your Launch Broker for Starship239 LEO manifests. Typical flow:\n"
                "1) Ask me to find a September 2032 LEO slot berthing the factory.\n"
                "2) Book a slot for your container.\n"
                "3) Add packages to your booked container (or use Container Assembly).\n"
                "4) Advertise outbound and return package capacity.\n"
                "5) Ask me to validate each package before launch.\n"
                "6) Query the manifest registry to see all containers booked on each starship.\n"
                "7) Ask analytical questions, e.g. how many packages are booked on a given date."
            ),
            "action": action,
            "suggestions": [
                "find a LEO slot for September 2032 on Starship239",
                "book the slot for container CNT-SS239-001",
                "add package PKG-1001 outbound",
                "list packages on my container",
                "show manifest registry for Starship239",
                "How many packages are booked for Starship239 on 22 Sept 2032?",
                "validate package PKG-1001 outbound",
                "status",
            ],
        }

    if action == "list_registry":
        ship_ref = _extract_ship_ref(instruction, payload)
        container_code = payload.get("container_code")
        match_container = re.search(r"(cnt[-\w]+)", instruction.lower())
        if match_container:
            container_code = match_container.group(1).upper()
        registry = list_starship_registry(db, ship_ref=ship_ref, container_code=container_code)
        return {
            "message": format_registry_message(registry, ship_ref=ship_ref),
            "action": action,
            "data": {"registry": registry},
            "suggestions": [
                "How many packages are booked for Starship239 on 22 Sept 2032?",
                "show manifest registry for Starship239",
                "status",
            ],
        }

    if action == "query_registry":
        ship_ref = _extract_ship_ref(instruction, payload)
        date_text = payload.get("date")
        on_date = None
        if date_text:
            try:
                on_date = datetime.strptime(str(date_text)[:10], "%Y-%m-%d").date()
            except ValueError:
                on_date = parse_date_hint(str(date_text))
        else:
            on_date = parse_date_hint(instruction)
        month = payload.get("month") or (parse_month_hint(instruction) if not on_date else None)
        metric = str(payload.get("metric") or "packages").lower()
        result = query_manifest_registry(
            db,
            ship_ref=ship_ref,
            on_date=on_date,
            month=month,
            metric=metric,
        )
        return {
            "message": format_query_registry_message(result),
            "action": action,
            "data": {"query": result},
            "suggestions": [
                "show manifest registry for Starship239",
                "How many packages are booked for Starship239 on 22 Sept 2032?",
                "status",
            ],
        }

    if not client_id:
        return {
            "message": "Sign in via Marketplace so I can book slots and track your manifest.",
            "action": action,
            "suggestions": ["Sign in, then ask: find a LEO slot for September 2032"],
        }

    if action == "find_slots":
        slots = find_leo_slots(db)
        available = [slot for slot in slots if slot["status"] == "available"]
        if not available:
            return {
                "message": "No LEO factory berths on Starship239 are open for September 2032.",
                "action": action,
                "data": {"slots": slots},
                "suggestions": ["status", "help"],
            }
        lines = [
            f"- {slot['slot_code']}: {slot['launch_window']} -> {slot['berth_destination']} "
            f"({slot['packages_remaining']} slots left)"
            for slot in available
        ]
        return {
            "message": "Open Starship239 LEO slots for September 2032:\n" + "\n".join(lines),
            "action": action,
            "data": {"slots": slots},
            "suggestions": [
                f"book slot {available[0]['id']} for container CNT-SS239-001",
                "help",
            ],
        }

    if action == "book_slot":
        slot_id = payload.get("slot_id")
        container_code = payload.get("container_code") or "CNT-SS239-001"
        match = re.search(r"(slot[-\w]+|ss239[-\w]+)", instruction.lower())
        if not slot_id and match:
            slot_id = match.group(1)
            if slot_id.startswith("ss239"):
                slot_id = f"slot-starship239-{slot_id.split('-', 1)[-1]}"
        match_container = re.search(r"(cnt[-\w]+)", instruction.lower())
        if match_container:
            container_code = match_container.group(1).upper()
        if not slot_id:
            open_slots = [
                slot
                for slot in find_leo_slots(db)
                if slot["status"] == LaunchSlotStatus.AVAILABLE.value
            ]
            if len(open_slots) == 1:
                slot_id = open_slots[0]["id"]
        if not slot_id:
            return {
                "message": "Tell me which slot to book, e.g. book slot slot-starship239-sep-a for CNT-SS239-001",
                "action": action,
                "suggestions": ["find a LEO slot for September 2032 on Starship239"],
            }
        try:
            manifest, booking = book_launch_slot(db, client_id, slot_id, container_code)
        except ValueError as exc:
            return {"message": str(exc), "action": action, "suggestions": ["find a LEO slot for September 2032"]}
        return {
            "message": (
                f"Booked {booking.booking_code} on {booking.launch_window} berthing "
                f"{booking.berth_destination} for container {container_code}."
            ),
            "action": action,
            "data": {"manifest": manifest_to_dict(db, manifest), "booking_id": booking.id},
            "suggestions": ["advertise package capacity", "add package PKG-1001 outbound", "list packages on my container", "show manifest registry"],
        }

    if action == "list_packages":
        try:
            packages = list_manifest_packages(db, client_id)
        except ValueError as exc:
            return {"message": str(exc), "action": action, "suggestions": ["book a launch slot first"]}
        if not packages:
            manifest = get_active_manifest(db, client_id)
            return {
                "message": (
                    f"No packages on {manifest.container_code if manifest else 'your container'} yet. "
                    "Ask me to add one, e.g. add package PKG-1001 outbound."
                ),
                "action": action,
                "data": {"packages": []},
                "suggestions": ["add package PKG-1001 outbound", "add package PKG-2001 return"],
            }
        lines = []
        for pkg in packages:
            validated = "validated" if pkg["manifest_validated"] else "pending"
            lines.append(
                f"- {pkg['package_id']} ({pkg['manifest_leg'] or 'unset'}, {validated}): "
                f"owner {pkg['owner_name']} -> {pkg['recipient_name']} @ {pkg['address']}"
            )
        manifest = get_active_manifest(db, client_id)
        return {
            "message": f"Packages on {manifest.container_code}:\n" + "\n".join(lines),
            "action": action,
            "data": {"packages": packages, "manifest": manifest_to_dict(db, manifest) if manifest else None},
            "suggestions": [
                "validate package PKG-1001 outbound",
                "add package PKG-2001 return",
            ],
        }

    if action == "add_package":
        leg = _extract_leg(instruction, payload)
        package_id = _extract_package_id(instruction, payload)
        package_data = {
            "package_id": package_id,
            "manifest_leg": leg,
            "leg": leg,
            "owner_name": payload.get("owner_name"),
            "recipient_name": payload.get("recipient_name"),
            "recipient_id": payload.get("recipient_id"),
            "address": payload.get("address"),
            "notes": payload.get("notes"),
        }
        if not package_id:
            return {
                "message": (
                    "Tell me the package to add, e.g. add package PKG-1001 outbound "
                    "or add package PKG-2001 return for Sol Orbital Dock."
                ),
                "action": action,
                "suggestions": ["list packages on my container", "book a launch slot first"],
            }
        try:
            pkg = add_manifest_package(db, client_id, package_data)
        except ValueError as exc:
            return {"message": str(exc), "action": action, "suggestions": ["list packages on my container"]}
        manifest = get_active_manifest(db, client_id)
        return {
            "message": (
                f"Placed {pkg.package_id} ({pkg.manifest_leg}) on {manifest.container_code if manifest else 'container'} "
                f"for {pkg.recipient_name} at {pkg.address}. Validation still required."
            ),
            "action": action,
            "data": {
                "package": _package_out(pkg),
                "manifest": manifest_to_dict(db, manifest) if manifest else None,
            },
            "suggestions": [
                f"validate package {pkg.package_id} {pkg.manifest_leg}",
                "list packages on my container",
            ],
        }

    if action == "advertise":
        try:
            manifest = advertise_manifest(db, client_id)
        except ValueError as exc:
            return {"message": str(exc), "action": action, "suggestions": ["book a launch slot first"]}
        return {
            "message": (
                f"Now advertising {manifest.outbound_slots} outbound and {manifest.return_slots} "
                f"return package slots on {manifest.container_code}. "
                "Customers can propose packages; validate each before launch."
            ),
            "action": action,
            "data": {"manifest": manifest_to_dict(db, manifest)},
            "suggestions": [
                "validate package PKG-1001 outbound",
                "validate package PKG-2001 return",
            ],
        }

    if action == "validate_package":
        package_id = payload.get("package_id")
        leg = payload.get("leg")
        match_pkg = re.search(r"(pkg[-\w]+)", instruction, re.IGNORECASE)
        if not package_id and match_pkg:
            package_id = match_pkg.group(1).upper()
        if not package_id:
            for token in instruction.upper().split():
                if token.startswith("PKG-"):
                    package_id = token
                    break
        if "outbound" in instruction.lower():
            leg = "outbound"
        elif "return" in instruction.lower():
            leg = "return"
        if not package_id:
            return {
                "message": "Tell me which package to validate, e.g. validate package PKG-1001 outbound",
                "action": action,
                "suggestions": ["status"],
            }
        try:
            pkg = validate_manifest_package(db, client_id, package_id, leg=leg)
        except ValueError as exc:
            return {"message": str(exc), "action": action, "suggestions": ["status"]}

        from starfall.game import on_manifest_updated

        game_result = on_manifest_updated(db, client_id)
        status = "accepted" if pkg.manifest_validated else "rejected"
        return {
            "message": f"Package {pkg.package_id} ({pkg.manifest_leg}) {status}: {pkg.notes}",
            "action": action,
            "data": {"package": _package_out(pkg), "manifest": manifest_to_dict(db, get_active_manifest(db, client_id))},
            "game_result": game_result,
            "suggestions": ["status", "validate package PKG-2001 return"],
        }

    if action == "status":
        manifest = get_active_manifest(db, client_id)
        if not manifest:
            return {
                "message": "No active Starship239 manifest yet. Start by finding a LEO slot.",
                "action": action,
                "suggestions": ["find a LEO slot for September 2032 on Starship239"],
            }
        data = manifest_to_dict(db, manifest)
        return {
            "message": (
                f"Manifest {data['container_code']} is {data['status']}. "
                f"Validated outbound: {data['validated_outbound']}, "
                f"return: {data['validated_return']}."
            ),
            "action": action,
            "data": data,
            "suggestions": ["advertise package capacity", "list packages on my container", "show manifest registry", "help"],
        }

    return broker_respond(db, client_id, "help", payload)
