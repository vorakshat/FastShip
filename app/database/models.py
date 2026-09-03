from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import EmailStr
from sqlalchemy import ARRAY, INTEGER
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Column, Field, Relationship, SQLModel, select


class TagName(str, Enum):
    EXPRESS = "expess"
    STANDARD = "standard"
    FRAGILE = "fragile"
    HEAVY = "heavy"
    INTERNATIONAL = "international"
    DOMESTIC = "domestic"
    TEMPERATURE_CONTROLLED = "temperature_controlled"
    GIFT = "gift"
    RETURN = "return"
    DOCUMENTS = "documents"

    async def tag(self, session: AsyncSession):
        return await session.scalar(
            select(Tag).where(Tag.name == self.value)
        )

class ShipmentStatus(str, Enum):
    placed = "placed"
    in_transit = "in_transit"
    out_for_delivery = "out_for_delivery"
    delivered = "delivered"
    cancelled = "cancelled"

class ShipmentTag(SQLModel, table=True):
    __tablename__="shipment_tag"

    shipment_id: UUID = Field(
        foreign_key="shipment.id",
        primary_key=True
    )
    tag_id: UUID = Field(
        foreign_key="tag.id",
        primary_key=True
    )

class Tag(SQLModel, table=True):
    __tablename__="tag"

    id: UUID = Field(
        sa_column=Column(
            postgresql.UUID,
            default=uuid4,
            primary_key=True
        )
    )
    name: TagName
    instruction: str

    shipments: list["Shipment"] = Relationship(
        back_populates="tags",
        link_model=ShipmentTag,
        sa_relationship_kwargs={"lazy": "immediate"}
    )

class Order(SQLModel, table=True):
    shipment_id: UUID = Field(foreign_key="shipment.id", primary_key=True)
    product_id: UUID = Field(foreign_key="product.id", primary_key=True)

    created_at: datetime
    quantity: int

    shipment: "Shipment" = Relationship(back_populates="orders")
    product: "Product" = Relationship(back_populates="orders")

class Product(SQLModel, table=True):
    id: UUID = Field(
        sa_column=Column(
            postgresql.UUID,
            default=uuid4,
            primary_key=True
        )
    )
    title: str
    description: str
    price: float
    weight: float

    orders: list[Order] = Relationship(
        back_populates="product"
    )

class Shipment(SQLModel, table=True):
    # Provide table name (defualt: class name)
    __tablename__ = "shipment"

    id: UUID = Field(
        sa_column=Column(
            postgresql.UUID,
            default=uuid4,
            primary_key=True
        )
    )
    created_at: datetime = Field(
        sa_column=Column(
            postgresql.TIMESTAMP,
            default=datetime.now  
        )
    )

    client_contact_email: EmailStr 
    client_contact_phone: str | None

    content: str
    weight: float = Field(le=25)
    destination: int
    estimated_delivery: datetime

    orders: list[Order] = Relationship(
        back_populates="shipments"
    )

    timeline: list["ShipmentEvent"] = Relationship(
        back_populates="shipment",
        sa_relationship_kwargs={"lazy": "selectin", "cascade": "all, delete-orphan"}
    )

    seller_id: UUID = Field(foreign_key="seller.id")  
    seller: "Seller" = Relationship(
        back_populates="shipments",
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    delivery_partner_id: UUID = Field(foreign_key="delivery_partner.id")
    delivery_partner: "DeliveryPartner" = Relationship(
        back_populates="shipments",
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    review: "Review" = Relationship(
        back_populates="shipment",
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    tags: list[Tag] = Relationship(
        back_populates="shipments",
        link_model=ShipmentTag,
        sa_relationship_kwargs={"lazy": "immediate"}
    )

    @property
    def status(self):
        return self.timeline[-1].status if len(self.timeline) > 0 else None

class ShipmentEvent(SQLModel, table=True):
    __tablename__="shipment_event"
    id: UUID = Field(
        sa_column=Column(
            postgresql.UUID,
            default=uuid4,
            primary_key=True
        )
    )
    created_at: datetime = Field(
        sa_column=Column(
            postgresql.TIMESTAMP,
            default=datetime.now  
        )
    )

    location: int
    status: ShipmentStatus
    description: str | None = Field(default=None)

    shipment_id: UUID = Field(foreign_key="shipment.id", ondelete="CASCADE")
    shipment: Shipment = Relationship(
        back_populates="timeline",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

class User(SQLModel):
    name: str

    email: EmailStr = Field(
        sa_column_kwargs={"unique": True},
        index=True  # Optional: adds an index for fast lookups
    )
    email_verified: bool = Field(default=False)
    password_hash: str = Field(exclude=True)    # Will be excluded from model_dump()

class Seller(User, table=True):
    __tablename__="seller"

    id: UUID = Field(
        sa_column=Column(
            postgresql.UUID,
            default=uuid4,
            primary_key=True
        )
    )
    created_at: datetime = Field(
        sa_column=Column(
            postgresql.TIMESTAMP,
            default=datetime.now  
        )
    )

    address: str | None = Field(default=None)
    zip_code: int | None = Field(default=None)

    shipments: list[Shipment] = Relationship(
        back_populates="seller",
        sa_relationship_kwargs={"lazy": "selectin"}
    )

class DeliveryPartner(User, table=True):
    __tablename__="delivery_partner"

    id: UUID = Field(
        sa_column=Column(
            postgresql.UUID,
            default=uuid4,
            primary_key=True
        )
    )
    created_at: datetime = Field(
        sa_column=Column(
            postgresql.TIMESTAMP,
            default=datetime.now
        )
    )

    serviceable_zip_codes: list[int] = Field(
        sa_column=Column(ARRAY(INTEGER)),
    )
    max_handling_capacity: int

    shipments: list[Shipment] = Relationship(
        back_populates="delivery_partner",
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    @property   # For Sellers or Delivery Partners
    def active_shipments(self):
        return [
            shipment 
            for shipment in self.shipments
            if shipment.status != ShipmentStatus.delivered
            or shipment.status != ShipmentStatus.cancelled
        ]
    
    @property   # For Delivery Partners
    def current_handling_capacity(self):
        return self.max_handling_capacity - len(self.active_shipments)

class Review(SQLModel, table=True):
    __tablename__="reviews"

    id: UUID = Field(
        sa_column=Column(
            postgresql.UUID,
            default=uuid4,
            primary_key=True
        )
    )
    created_at: datetime = Field(
        sa_column=Column(
            postgresql.TIMESTAMP,
            default=datetime.now  
        )
    )

    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None)

    shipment_id: UUID = Field(foreign_key="shipment.id")
    shipment: Shipment = Relationship(
        back_populates="review",
        sa_relationship_kwargs={"lazy": "selectin"}
    )