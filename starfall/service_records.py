import random
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from starfall.models import (
    CollectionJob,
    CollectionOutcome,
    Container,
    ContainerPackage,
    ContractorDisposition,
    CONTRACTOR_DISPOSITION_LABELS,
    DeliveryOrder,
    EndpointReceipt,
    LaunchBooking,
    LaunchStack,
    PorterJob,
    RecordStatus,
    ServiceCategory,
    ServiceProvider,
)

CATEGORY_ENTITY_MAP = {
    ServiceCategory.CONTAINER_ASSEMBLY: "containers",
    ServiceCategory.CONTAINER_AGGREGATOR: "launch_stacks",
    ServiceCategory.GROUND_LAUNCH: "launch_bookings",
    ServiceCategory.CONTAINER_PORTER: "porter_jobs",
    ServiceCategory.OFFWORLD_ENDPOINT: "endpoint_receipts",
    ServiceCategory.OFFWORLD_DELIVERY: "delivery_orders",
}


def _touch(record) -> None:
    record.updated_at = datetime.now(timezone.utc)


def _container_out(container: Container) -> dict:
    return {
        "id": container.id,
        "container_code": container.container_code,
        "owner_name": container.owner_name,
        "system_id": container.system_id,
        "status": container.status.value,
        "notes": container.notes,
        "package_count": len(container.packages),
        "packages": [_package_out(p) for p in container.packages],
        "created_at": container.created_at,
        "updated_at": container.updated_at,
    }


def _package_out(package: ContainerPackage) -> dict:
    return {
        "id": package.id,
        "container_id": package.container_id,
        "package_id": package.package_id,
        "owner_name": package.owner_name,
        "recipient_name": package.recipient_name,
        "recipient_id": package.recipient_id,
        "address": package.address,
        "notes": package.notes,
        "created_at": package.created_at,
        "updated_at": package.updated_at,
    }


def _generic_out(record, fields: list[str]) -> dict:
    data = {field: getattr(record, field) for field in fields}
    if hasattr(record, "status"):
        data["status"] = record.status.value
    data["created_at"] = record.created_at
    data["updated_at"] = record.updated_at
    return data


def list_containers(db: Session, client_id: str) -> list[dict]:
    rows = db.query(Container).filter(Container.client_id == client_id).order_by(Container.created_at.desc())
    return [_container_out(row) for row in rows.all()]


def get_container(db: Session, client_id: str, container_id: str) -> Container | None:
    return (
        db.query(Container)
        .filter(Container.id == container_id, Container.client_id == client_id)
        .first()
    )


def create_container(db: Session, client_id: str, data: dict) -> dict:
    container = Container(
        id=str(uuid.uuid4()),
        client_id=client_id,
        container_code=data["container_code"],
        owner_name=data["owner_name"],
        system_id=data["system_id"],
        status=RecordStatus(data.get("status", RecordStatus.DRAFT.value)),
        notes=data.get("notes", ""),
    )
    db.add(container)
    db.commit()
    db.refresh(container)

    from starfall.game import on_service_record_created
    from starfall.models import ServiceCategory

    on_service_record_created(db, client_id, ServiceCategory.CONTAINER_ASSEMBLY)
    db.refresh(container)
    return _container_out(container)


def update_container(db: Session, container: Container, data: dict) -> dict:
    for field in ("container_code", "owner_name", "system_id", "notes"):
        if field in data:
            setattr(container, field, data[field])
    if "status" in data:
        container.status = RecordStatus(data["status"])
    _touch(container)
    db.commit()
    db.refresh(container)
    return _container_out(container)


def delete_container(db: Session, container: Container) -> None:
    db.delete(container)
    db.commit()


def list_packages(db: Session, container: Container) -> list[dict]:
    return [_package_out(p) for p in container.packages]


def get_package(db: Session, client_id: str, package_id: str) -> ContainerPackage | None:
    return (
        db.query(ContainerPackage)
        .join(Container)
        .filter(ContainerPackage.id == package_id, Container.client_id == client_id)
        .first()
    )


def create_package(db: Session, container: Container, data: dict) -> dict:
    package = ContainerPackage(
        id=str(uuid.uuid4()),
        container_id=container.id,
        package_id=data["package_id"],
        owner_name=data["owner_name"],
        recipient_name=data["recipient_name"],
        recipient_id=data["recipient_id"],
        address=data["address"],
        notes=data.get("notes", ""),
    )
    db.add(package)
    _touch(container)
    db.commit()
    db.refresh(package)
    return _package_out(package)


def update_package(db: Session, package: ContainerPackage, container: Container, data: dict) -> dict:
    for field in ("package_id", "owner_name", "recipient_name", "recipient_id", "address", "notes"):
        if field in data:
            setattr(package, field, data[field])
    _touch(package)
    _touch(container)
    db.commit()
    db.refresh(package)
    return _package_out(package)


def delete_package(db: Session, package: ContainerPackage, container: Container) -> None:
    db.delete(package)
    _touch(container)
    db.commit()


def _list_model(db: Session, model, client_id: str, fields: list[str]) -> list[dict]:
    rows = db.query(model).filter(model.client_id == client_id).order_by(model.created_at.desc())
    return [_generic_out(row, fields) for row in rows.all()]


def _get_model(db: Session, model, client_id: str, record_id: str):
    return db.query(model).filter(model.id == record_id, model.client_id == client_id).first()


def _create_model(db: Session, model, client_id: str, data: dict, fields: list[str]) -> dict:
    payload = {field: data[field] for field in fields if field in data}
    record = model(id=str(uuid.uuid4()), client_id=client_id, **payload)
    if "status" in data:
        record.status = RecordStatus(data["status"])
    db.add(record)
    db.commit()
    db.refresh(record)
    return _generic_out(record, fields)


def _update_model(db: Session, record, data: dict, fields: list[str]) -> dict:
    for field in fields:
        if field in data:
            setattr(record, field, data[field])
    if "status" in data:
        record.status = RecordStatus(data["status"])
    _touch(record)
    db.commit()
    db.refresh(record)
    return _generic_out(record, fields)


def _delete_model(db: Session, record) -> None:
    db.delete(record)
    db.commit()


STACK_FIELDS = ["stack_code", "system_id", "container_codes", "target_orbit", "notes"]
BOOKING_FIELDS = ["booking_code", "pad_location", "launch_window", "payload_ref", "mass_kg", "notes"]
PORTER_FIELDS = [
    "job_code",
    "container_code",
    "owner_name",
    "package_id",
    "recipient_name",
    "recipient_id",
    "origin_address",
    "destination_address",
    "notes",
]
RECEIPT_FIELDS = [
    "receipt_code",
    "container_code",
    "package_id",
    "owner_name",
    "recipient_name",
    "recipient_id",
    "gateway_address",
    "notes",
]
DELIVERY_FIELDS = [
    "delivery_code",
    "package_id",
    "owner_name",
    "recipient_name",
    "recipient_id",
    "destination_address",
    "notes",
]


DELIVERY_FIELDS = [
    "delivery_code",
    "package_id",
    "owner_name",
    "recipient_name",
    "recipient_id",
    "destination_address",
    "notes",
]
COLLECTION_FIELDS = [
    "job_code",
    "container_code",
    "contractor_id",
    "system_id",
    "pickup_site",
    "owner_name",
    "package_id",
    "recipient_name",
    "recipient_id",
    "delivery_address",
    "notes",
]


def _collection_out(job: CollectionJob) -> dict:
    contractor = job.contractor
    data = _generic_out(job, COLLECTION_FIELDS)
    data["outcome"] = job.outcome.value
    data["outcome_detail"] = job.outcome_detail
    data["pickup_attempts"] = job.pickup_attempts
    data["contractor_name"] = contractor.name if contractor else ""
    data["contractor_disposition"] = (
        contractor.contractor_disposition.value
        if contractor and contractor.contractor_disposition
        else None
    )
    data["contractor_disposition_label"] = (
        CONTRACTOR_DISPOSITION_LABELS[contractor.contractor_disposition]
        if contractor and contractor.contractor_disposition
        else None
    )
    return data


def list_collection_contractors(db: Session) -> list[dict]:
    rows = (
        db.query(ServiceProvider)
        .filter(ServiceProvider.contractor_disposition.isnot(None))
        .order_by(ServiceProvider.rating.desc())
        .all()
    )
    return [
        {
            "id": provider.id,
            "name": provider.name,
            "description": provider.description,
            "home_system_id": provider.home_system_id,
            "verified": provider.verified,
            "rating": provider.rating,
            "disposition": provider.contractor_disposition.value,
            "disposition_label": CONTRACTOR_DISPOSITION_LABELS[provider.contractor_disposition],
        }
        for provider in rows
    ]


def get_collection_job(db: Session, client_id: str, job_id: str) -> CollectionJob | None:
    return (
        db.query(CollectionJob)
        .filter(CollectionJob.id == job_id, CollectionJob.client_id == client_id)
        .first()
    )


def execute_collection_pickup(db: Session, client_id: str, job_id: str) -> dict:
    job = get_collection_job(db, client_id, job_id)
    if not job:
        raise ValueError("Collection job not found")

    contractor = db.get(ServiceProvider, job.contractor_id)
    if not contractor or not contractor.contractor_disposition:
        raise ValueError("Invalid offshore contractor")

    job.pickup_attempts += 1
    disposition = contractor.contractor_disposition
    game_hint: dict | None = None

    if disposition == ContractorDisposition.RELIABLE:
        job.outcome = CollectionOutcome.PICKED_UP
        job.outcome_detail = f"{contractor.name} collected the container cleanly at {job.pickup_site}."
        job.status = RecordStatus.COMPLETED
    elif disposition == ContractorDisposition.CROOKED:
        if random.random() < 0.45:
            job.outcome = CollectionOutcome.SKIMMED
            job.outcome_detail = (
                f"{contractor.name} picked up the container but skimmed a side manifest fee."
            )
        else:
            job.outcome = CollectionOutcome.PICKED_UP
            job.outcome_detail = f"{contractor.name} collected the container with no reported losses."
        job.status = RecordStatus.COMPLETED
    else:
        if random.random() < 0.4:
            job.outcome = CollectionOutcome.INCIDENT
            job.outcome_detail = (
                f"{contractor.name} reported a crane failure at {job.pickup_site}. Try again."
            )
            job.status = RecordStatus.DRAFT
        else:
            job.outcome = CollectionOutcome.PICKED_UP
            job.outcome_detail = f"{contractor.name} barely completed the pickup after an equipment scare."
            job.status = RecordStatus.COMPLETED

    _touch(job)
    db.commit()
    db.refresh(job)

    if job.status == RecordStatus.COMPLETED:
        from starfall.game import on_collection_completed

        game_hint = on_collection_completed(db, client_id, job)

    return {"job": _collection_out(job), "game_result": game_hint}


def list_category_records(db: Session, category: ServiceCategory, client_id: str) -> list[dict]:
    if category == ServiceCategory.CONTAINER_ASSEMBLY:
        return list_containers(db, client_id)
    if category == ServiceCategory.CONTAINER_COLLECTION:
        rows = (
            db.query(CollectionJob)
            .filter(CollectionJob.client_id == client_id)
            .order_by(CollectionJob.created_at.desc())
            .all()
        )
        return [_collection_out(row) for row in rows]
    if category == ServiceCategory.CONTAINER_AGGREGATOR:
        return _list_model(db, LaunchStack, client_id, STACK_FIELDS)
    if category == ServiceCategory.GROUND_LAUNCH:
        return _list_model(db, LaunchBooking, client_id, BOOKING_FIELDS)
    if category == ServiceCategory.CONTAINER_PORTER:
        return _list_model(db, PorterJob, client_id, PORTER_FIELDS)
    if category == ServiceCategory.OFFWORLD_ENDPOINT:
        return _list_model(db, EndpointReceipt, client_id, RECEIPT_FIELDS)
    if category == ServiceCategory.OFFWORLD_DELIVERY:
        return _list_model(db, DeliveryOrder, client_id, DELIVERY_FIELDS)
    return []


def get_category_record(db: Session, category: ServiceCategory, client_id: str, record_id: str):
    if category == ServiceCategory.CONTAINER_ASSEMBLY:
        return get_container(db, client_id, record_id)
    if category == ServiceCategory.CONTAINER_COLLECTION:
        return get_collection_job(db, client_id, record_id)
    model_map = {
        ServiceCategory.CONTAINER_AGGREGATOR: LaunchStack,
        ServiceCategory.GROUND_LAUNCH: LaunchBooking,
        ServiceCategory.CONTAINER_PORTER: PorterJob,
        ServiceCategory.OFFWORLD_ENDPOINT: EndpointReceipt,
        ServiceCategory.OFFWORLD_DELIVERY: DeliveryOrder,
    }
    model = model_map.get(category)
    if not model:
        return None
    return _get_model(db, model, client_id, record_id)


def create_category_record(db: Session, category: ServiceCategory, client_id: str, data: dict) -> dict:
    if category == ServiceCategory.CONTAINER_ASSEMBLY:
        return create_container(db, client_id, data)
    if category == ServiceCategory.CONTAINER_COLLECTION:
        record = CollectionJob(
            id=str(uuid.uuid4()),
            client_id=client_id,
            job_code=data["job_code"],
            container_code=data["container_code"],
            contractor_id=data["contractor_id"],
            system_id=data["system_id"],
            pickup_site=data["pickup_site"],
            owner_name=data["owner_name"],
            package_id=data.get("package_id", ""),
            recipient_name=data.get("recipient_name", ""),
            recipient_id=data.get("recipient_id", ""),
            delivery_address=data.get("delivery_address", ""),
            notes=data.get("notes", ""),
            outcome=CollectionOutcome.PENDING,
            status=RecordStatus.DRAFT,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return _collection_out(record)
    if category == ServiceCategory.CONTAINER_AGGREGATOR:
        return _create_model(db, LaunchStack, client_id, data, STACK_FIELDS)
    if category == ServiceCategory.GROUND_LAUNCH:
        return _create_model(db, LaunchBooking, client_id, data, BOOKING_FIELDS)
    if category == ServiceCategory.CONTAINER_PORTER:
        return _create_model(db, PorterJob, client_id, data, PORTER_FIELDS)
    if category == ServiceCategory.OFFWORLD_ENDPOINT:
        return _create_model(db, EndpointReceipt, client_id, data, RECEIPT_FIELDS)
    if category == ServiceCategory.OFFWORLD_DELIVERY:
        return _create_model(db, DeliveryOrder, client_id, data, DELIVERY_FIELDS)
    raise ValueError("Unsupported category")


def update_category_record(db: Session, category: ServiceCategory, record, data: dict) -> dict:
    if category == ServiceCategory.CONTAINER_ASSEMBLY:
        return update_container(db, record, data)
    if category == ServiceCategory.CONTAINER_COLLECTION:
        for field in COLLECTION_FIELDS:
            if field in data:
                setattr(record, field, data[field])
        if "status" in data:
            record.status = RecordStatus(data["status"])
        _touch(record)
        db.commit()
        db.refresh(record)
        return _collection_out(record)
    field_map = {
        ServiceCategory.CONTAINER_AGGREGATOR: STACK_FIELDS,
        ServiceCategory.GROUND_LAUNCH: BOOKING_FIELDS,
        ServiceCategory.CONTAINER_PORTER: PORTER_FIELDS,
        ServiceCategory.OFFWORLD_ENDPOINT: RECEIPT_FIELDS,
        ServiceCategory.OFFWORLD_DELIVERY: DELIVERY_FIELDS,
    }
    return _update_model(db, record, data, field_map[category])


def delete_category_record(db: Session, record) -> None:
    _delete_model(db, record)
