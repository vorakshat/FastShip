from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.templating import Jinja2Templates

from app.api.dependencies import DeliveryPartnerDep, SellerDep, ShipmentServiceDep
from app.api.schemas.shipment import (
    ShipmentCreate,
    ShipmentRead,
    ShipmentUpdate,
)
from app.database.models import Shipment
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No data provided to update",
        )
    return await service.update(id, shipment_update, partner)
    
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
   