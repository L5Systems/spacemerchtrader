from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from starfall.database import get_db
from starfall.marketplace import get_client_access
from starfall.models import Client, ServiceCategory
from starfall.routers.marketplace import get_current_client
from starfall.schemas import (
    CollectionJobCreate,
    CollectionJobUpdate,
    ContainerCreate,
    ContainerPackageCreate,
    ContainerPackageUpdate,
    ContainerUpdate,
    DeliveryOrderCreate,
    DeliveryOrderUpdate,
    EndpointReceiptCreate,
    EndpointReceiptUpdate,
    LaunchBookingCreate,
    LaunchBookingUpdate,
    LaunchStackCreate,
    LaunchStackUpdate,
    PorterJobCreate,
    PorterJobUpdate,
)
from starfall.service_records import (
    create_category_record,
    create_package,
    delete_category_record,
    delete_container,
    delete_package,
    execute_collection_pickup,
    get_category_record,
    get_container,
    get_package,
    list_category_records,
    list_collection_contractors,
    list_containers,
    update_category_record,
    update_container,
    update_package,
)

router = APIRouter(prefix="/marketplace/services", tags=["marketplace-services"])

CREATE_SCHEMAS: dict[ServiceCategory, type] = {
    ServiceCategory.CONTAINER_ASSEMBLY: ContainerCreate,
    ServiceCategory.CONTAINER_COLLECTION: CollectionJobCreate,
    ServiceCategory.CONTAINER_AGGREGATOR: LaunchStackCreate,
    ServiceCategory.GROUND_LAUNCH: LaunchBookingCreate,
    ServiceCategory.CONTAINER_PORTER: PorterJobCreate,
    ServiceCategory.OFFWORLD_ENDPOINT: EndpointReceiptCreate,
    ServiceCategory.OFFWORLD_DELIVERY: DeliveryOrderCreate,
}

UPDATE_SCHEMAS: dict[ServiceCategory, type] = {
    ServiceCategory.CONTAINER_ASSEMBLY: ContainerUpdate,
    ServiceCategory.CONTAINER_COLLECTION: CollectionJobUpdate,
    ServiceCategory.CONTAINER_AGGREGATOR: LaunchStackUpdate,
    ServiceCategory.GROUND_LAUNCH: LaunchBookingUpdate,
    ServiceCategory.CONTAINER_PORTER: PorterJobUpdate,
    ServiceCategory.OFFWORLD_ENDPOINT: EndpointReceiptUpdate,
    ServiceCategory.OFFWORLD_DELIVERY: DeliveryOrderUpdate,
}


def _parse_category(category: str) -> ServiceCategory:
    try:
        return ServiceCategory(category)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown service category '{category}'") from exc


def _require_category_access(
    category: ServiceCategory,
    client: Client,
    db: Session,
) -> None:
    allowed = get_client_access(db, client.id)
    if category not in allowed:
        raise HTTPException(status_code=403, detail=f"Access denied for category '{category.value}'")


@router.get("/{category}/records")
def list_records(
    category: str,
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    cat = _parse_category(category)
    _require_category_access(cat, client, db)
    return list_category_records(db, cat, client.id)


@router.post("/{category}/records", status_code=201)
def create_record(
    category: str,
    payload: dict[str, Any],
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    cat = _parse_category(category)
    _require_category_access(cat, client, db)
    schema = CREATE_SCHEMAS[cat]
    data = schema.model_validate(payload).model_dump()
    return create_category_record(db, cat, client.id, data)


@router.get("/{category}/records/{record_id}")
def read_record(
    category: str,
    record_id: str,
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    cat = _parse_category(category)
    _require_category_access(cat, client, db)
    record = get_category_record(db, cat, client.id, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    if cat == ServiceCategory.CONTAINER_ASSEMBLY:
        from starfall.service_records import _container_out

        return _container_out(record)
    if cat == ServiceCategory.CONTAINER_COLLECTION:
        from starfall.service_records import _collection_out

        return _collection_out(record)
    from starfall.service_records import (
        BOOKING_FIELDS,
        DELIVERY_FIELDS,
        PORTER_FIELDS,
        RECEIPT_FIELDS,
        STACK_FIELDS,
        _generic_out,
    )

    field_map = {
        ServiceCategory.CONTAINER_AGGREGATOR: STACK_FIELDS,
        ServiceCategory.GROUND_LAUNCH: BOOKING_FIELDS,
        ServiceCategory.CONTAINER_PORTER: PORTER_FIELDS,
        ServiceCategory.OFFWORLD_ENDPOINT: RECEIPT_FIELDS,
        ServiceCategory.OFFWORLD_DELIVERY: DELIVERY_FIELDS,
    }
    return _generic_out(record, field_map[cat])


@router.put("/{category}/records/{record_id}")
def update_record(
    category: str,
    record_id: str,
    payload: dict[str, Any],
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    cat = _parse_category(category)
    _require_category_access(cat, client, db)
    record = get_category_record(db, cat, client.id, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    schema = UPDATE_SCHEMAS[cat]
    data = schema.model_validate(payload).model_dump(exclude_unset=True)
    return update_category_record(db, cat, record, data)


@router.delete("/{category}/records/{record_id}", status_code=204)
def remove_record(
    category: str,
    record_id: str,
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
) -> None:
    cat = _parse_category(category)
    _require_category_access(cat, client, db)
    record = get_category_record(db, cat, client.id, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    if cat == ServiceCategory.CONTAINER_ASSEMBLY:
        delete_container(db, record)
    else:
        delete_category_record(db, record)


@router.get("/container_assembly/containers")
def list_assembly_containers(
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    _require_category_access(ServiceCategory.CONTAINER_ASSEMBLY, client, db)
    return list_containers(db, client.id)


@router.post("/container_assembly/containers/{container_id}/packages", status_code=201)
def add_package(
    container_id: str,
    payload: ContainerPackageCreate,
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    _require_category_access(ServiceCategory.CONTAINER_ASSEMBLY, client, db)
    container = get_container(db, client.id, container_id)
    if not container:
        raise HTTPException(status_code=404, detail="Container not found")
    return create_package(db, container, payload.model_dump())


@router.put("/container_assembly/packages/{package_id}")
def edit_package(
    package_id: str,
    payload: ContainerPackageUpdate,
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    _require_category_access(ServiceCategory.CONTAINER_ASSEMBLY, client, db)
    package = get_package(db, client.id, package_id)
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    container = get_container(db, client.id, package.container_id)
    assert container is not None
    return update_package(db, package, container, payload.model_dump(exclude_unset=True))


@router.delete("/container_assembly/packages/{package_id}", status_code=204)
def remove_package(
    package_id: str,
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
) -> None:
    _require_category_access(ServiceCategory.CONTAINER_ASSEMBLY, client, db)
    package = get_package(db, client.id, package_id)
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    container = get_container(db, client.id, package.container_id)
    assert container is not None
    delete_package(db, package, container)


@router.get("/container_collection/contractors")
def collection_contractors(
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    _require_category_access(ServiceCategory.CONTAINER_COLLECTION, client, db)
    return list_collection_contractors(db)


@router.post("/container_collection/records/{record_id}/pickup")
def collection_pickup(
    record_id: str,
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    _require_category_access(ServiceCategory.CONTAINER_COLLECTION, client, db)
    try:
        return execute_collection_pickup(db, client.id, record_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
