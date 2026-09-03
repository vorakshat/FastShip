from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.database.models import ShipmentEvent, ShipmentStatus, TagName


class BaseShipment(BaseModel):
    content: str 
    weight: float = Field(le=25, gt=0)
    destination: int

class TagRead(BaseModel):
    name: TagName 
    instruction: str

class ShipmentRead(BaseShipment):
    id: UUID
    created_at: datetime
    seller_id: UUID
    delivery_partner_id: UUID
    timeline: list[ShipmentEvent]
    estimated_delivery: datetime
    tags: list[TagRead]

class ShipmentCreate(BaseShipment):
    client_contact_email: EmailStr
    client_contact_phone: str | None

class ShipmentUpdate(BaseModel):
    location: int | None = Field(default=None)
    status: ShipmentStatus | None = Field(default=None)
    verification_code: str | None = Field(default=None)
    description: str | None = Field(default=None)   # Not in Shipment DB Model
    estimated_delivery: datetime | None = Field(default=None)

class ShipmentReview(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None)
    