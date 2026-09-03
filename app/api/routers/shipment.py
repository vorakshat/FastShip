from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Form, Request
from fastapi.templating import Jinja2Templates

from app.api.dependencies import (
    DeliveryPartnerDep,
    SellerDep,
    SessionDep,
    ShipmentServiceDep,
)
from app.api.schemas.shipment import (
    ShipmentCreate,
    ShipmentRead,
    ShipmentUpdate,
)
from app.config import app_settings
from app.core.exceptions import NothingToUpdate
from app.database.models import Shipment, TagName
from app.utils import TEMPLATE_DIR

router = APIRouter(prefix="/shipment", tags=["Shipment"])


@router.get("/", response_model=ShipmentRead) 
async def get_shipment(id: UUID, _: SellerDep, service: ShipmentServiceDep):    # Id to search, SellerDep to authorize the seller and service to access service layer
    return await service.get(id)

templates = Jinja2Templates(TEMPLATE_DIR)

@router.get("/track")
async def get_tracking(request: Request ,id: UUID, service: ShipmentServiceDep):
    # Check for shipment with given id
    shipment = await service.get(id)

    context = shipment.model_dump() # The relationships are not included
    context["status"] = shipment.status
    context["partner"] = shipment.delivery_partner.name
    context["timeline"] = shipment.timeline
    context["timeline"].reverse()

    return templates.TemplateResponse(
        request=request,
        name="track.html",
        context=context
    )

@router.post("/")
async def submit_shipment(seller: SellerDep, shipment: ShipmentCreate, service: ShipmentServiceDep) -> Shipment:    # seller  is the authorized seller
    return await service.add(shipment, seller)

@router.patch("/", response_model=ShipmentRead)
async def update_shipment(id: UUID, shipment_update: ShipmentUpdate, partner: DeliveryPartnerDep ,service: ShipmentServiceDep):
    # Update data with given fields
    updates = shipment_update.model_dump(exclude_none=True)
    if not updates:
        raise NothingToUpdate()
    return await service.update(id, shipment_update, partner)

### Update fields of a shipment
@router.get("/tagged", response_model=list[ShipmentRead])
async def get_shipments_with_tag(tag_name: TagName, session: SessionDep):
    tag = await tag_name.tag(session)
    return tag.shipments

### Add a tag to a shipment
@router.get("/tag", response_model=ShipmentRead)
async def add_tag_to_shipment(
        id: UUID,
        tag_name: TagName,
        service: ShipmentServiceDep
):
    return await service.add_tag(id, tag_name)

### Remove tag from a shipment
@router.delete("/remove_tag", response_model=ShipmentRead)
async def remove_tag_from_shipment(
        id: UUID,
        tag_name: TagName,
        service: ShipmentServiceDep
):
    return await service.remove_tag(id, tag_name)

@router.delete("/")
async def delete_shipment(id: UUID, service: ShipmentServiceDep) -> dict[str, str]:
    await service.delete(id) 
    return {"detail": f"Shipment with id #{id} is deleted!"}

### Cancel shipment by id
@router.get("/cancel", response_model=ShipmentRead)
async def cancel_shipment(
    id: UUID,
    seller: SellerDep,
    service: ShipmentServiceDep
):
    return await service.cancel(id, seller)

### Submit a review for a shipment
@router.get("/review")
async def submit_review_page(request: Request, token: str):
    return templates.TemplateResponse(
        request=request, 
        name="review.html",
        context={
            "review_url": f"http://{app_settings.APP_DOMAIN}/shipment/review?token={token}"
        }
    )

### Submit a review for a shipment
@router.post("/review")
async def submit_review(
    token: str,
    rating: Annotated[int, Form(ge=1, le=5)],
    comment: Annotated[str | None, Form()],
    service: ShipmentServiceDep
):
    await service.rate(token, rating, comment)
    return {"detail": "Review has been submitted"}