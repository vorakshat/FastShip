from collections.abc import Sequence

from sqlmodel import any_, select

from app.api.schemas.delivery_partner import DeliveryPartnerCreate
from app.core.exceptions import DeliveryPartnerCapacityExceeded
from app.database.models import DeliveryPartner, Shipment

from .user import UserService


class DeliveryPartnerService(UserService[DeliveryPartner]):
    def __init__(self, session):
        super().__init__(DeliveryPartner, session)

    async def add(self, delivery_partner: DeliveryPartnerCreate):
        return await self._add_user(
            delivery_partner.model_dump(),
            router_prefix="partner"
        )

    async def get_partners_by_zipcode(self, zipcode: int) -> Sequence[DeliveryPartner]:
        return (
            await self.session.scalars(
                select(DeliveryPartner).where(
                    zipcode == any_(DeliveryPartner.serviceable_zip_codes)
                )
            )
        ).all()

    async def assign_shipment(self, shipment: Shipment):
        eligible_partners = await self.get_partners_by_zipcode(shipment.destination)

        for partner in eligible_partners:
            if partner.current_handling_capacity > 0:
                partner.shipments.append(shipment)
                return partner

        raise DeliveryPartnerCapacityExceeded()
            
    async def update(self, partner: DeliveryPartner):
        return await self._update(partner)

    async def token(self, email, password) -> str:
        return await self._generate_token(email, password)