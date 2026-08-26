from datetime import datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.shipment import ShipmentCreate, ShipmentUpdate
from app.database.models import (
    DeliveryPartner,
    Review,
    Seller,
    Shipment,
    ShipmentStatus,
)
from app.database.redis import get_shipment_verification_code
from app.services.shipment_event import ShipmentEventService
from app.utils import decode_url_safe_token

from .base import BaseService
from .delivery_partner import DeliveryPartnerService


class ShipmentService(BaseService[Shipment]):
    def __init__(
        self,
        session: AsyncSession,
        partner_service: DeliveryPartnerService,
        event_service: ShipmentEventService
    ):
        super().__init__(Shipment, session)
        self.partner_service = partner_service
        self.event_service = event_service

    async def get(self, id: UUID) -> Shipment:
        shipment = await self._get(id)

        if shipment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shipment with given id doesn't exist",
            )
        return shipment

    async def add(self, shipment: ShipmentCreate, seller: Seller) -> Shipment:
        new_shipment = Shipment(
            **shipment.model_dump(),
            # status=ShipmentStatus.placed,
            estimated_delivery=datetime.now() + timedelta(days=3),  # noqa: DTZ005
            seller_id=seller.id,
            # seller=seller will work as well
        )

        # Assign delivery partner
        partner = await self.partner_service.assign_shipment(new_shipment)
        # Add the delivery partner foreign key
        new_shipment.delivery_partner_id = partner.id

        shipment_ =  await self._add(new_shipment)

        event = await self.event_service.add(
            shipment=shipment_,
            location=seller.zip_code,
            status=ShipmentStatus.placed,
            description=f"assigned to {partner.name}"
        )

        shipment_.timeline.append(event)
        
        return shipment_
    
    async def update(self, id: UUID, shipment_update: ShipmentUpdate, partner: DeliveryPartner) -> Shipment:
        shipment = await self.get(id)

        #Validate logged in partner with the assigned partner
        if shipment.delivery_partner_id != partner.id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Delivery partner not authorized"
            )

        if shipment_update.status == ShipmentStatus.delivered:
            code = await get_shipment_verification_code(shipment.id)

            if code != shipment_update.verification_code:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Client not authorized"
                )

        updates = shipment_update.model_dump(
            exclude_none=True,
            exclude={"verification_code"}
        )

        if shipment_update.estimated_delivery:
            shipment.estimated_delivery = shipment_update.estimated_delivery

        if len(updates) > 0 and not shipment_update.estimated_delivery:
            await self.event_service.add(
                shipment=shipment,
                **updates
            )
        
        return await self._update(shipment.sqlmodel_update(shipment))

    async def delete(self, id: UUID):
        await self._delete(await self.get(id))

    async def cancel(self, id: UUID, seller: Seller):
        shipment = await self.get(id)
        
        #Validate logged in partner with the assigned partner
        if shipment.seller_id != seller.id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Seller not authorized"
            )

        event = await self.event_service.add(
            shipment=shipment,
            status=ShipmentStatus.cancelled
        )

        shipment.timeline.append(event)
        return shipment

    async def rate(self, token: str, rating: int, comment: str | None):
        token_data = decode_url_safe_token(token=token, salt="shipment-review")

        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not Authorized"
            )

        shipment = await self.get(UUID(token_data["id"]))

        new_review = Review(
            rating=rating,
            comment=comment if comment else None,
            shipment_id=shipment.id
        )

        self.session.add(new_review)
        await self.session.commit()