from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import oauth2_scheme_partner, oauth2_scheme_seller
from app.database.models import DeliveryPartner, Seller
from app.database.redis import is_jti_blacklisted
from app.database.session import get_session
from app.services.delivery_partner import DeliveryPartnerService
from app.services.seller import SellerService
from app.services.shipment import ShipmentService
from app.services.shipment_event import ShipmentEventService
from app.utils import decode_access_token

SessionDep = Annotated[AsyncSession, Depends(get_session)]

### Seller Dependenices


# Access token data dependency
async def _get_access_token(token: str) -> dict:
    data = decode_access_token(token)

    if data is None or await is_jti_blacklisted(data["jti"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        )

    # if data is None:
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Unauthorized"
    #     )
    # if await is_jti_blacklisted(data["jti"]):
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Expired token"
    #     )

    return data


# Seller access token data
async def get_seller_access_token(token: Annotated[str, Depends(oauth2_scheme_seller)]):
    return await _get_access_token(token)


# Partner access token data
async def get_partner_access_token(
    token: Annotated[str, Depends(oauth2_scheme_partner)],
):
    return await _get_access_token(token)


# Logged in seller
async def get_current_seller(
    token_data: Annotated[dict, Depends(get_seller_access_token)], session: SessionDep
) -> Seller:
    seller = await session.get(Seller, UUID(token_data["user"]["id"]))

    if seller:
        return seller
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authorized"
        )


# Logged in delivery partner
async def get_current_partner(
    token_data: Annotated[dict, Depends(get_partner_access_token)], session: SessionDep
) -> DeliveryPartner:
    partner = await session.get(DeliveryPartner, UUID(token_data["user"]["id"]))

    if partner:
        return partner
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authorized"
        )


# Getting the Seller or the partner by decoding the Authorization token
# Seller dep
SellerDep = Annotated[Seller, Depends(get_current_seller)]
# Delivery Partner dep
DeliveryPartnerDep = Annotated[DeliveryPartner, Depends(get_current_partner)]


### Service Dependencies will help us to avail services provided by the files in Serive folder by returning an instance of their respective classes
def get_shipment_service(session: SessionDep):
    return ShipmentService(
        session,
        DeliveryPartnerService(session),
        ShipmentEventService(session)
    )


def get_seller_service(session: SessionDep):
    return SellerService(session)


def get_delivery_partner_service(session: SessionDep):
    return DeliveryPartnerService(session)


ShipmentServiceDep = Annotated[ShipmentService, Depends(get_shipment_service)]
SellerServiceDep = Annotated[SellerService, Depends(get_seller_service)]
DeliveryPartnerServiceDep = Annotated[
    DeliveryPartnerService, Depends(get_delivery_partner_service)
]
