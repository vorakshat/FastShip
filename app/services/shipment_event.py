from random import randint

from app.config import app_settings
from app.database.models import Shipment, ShipmentEvent, ShipmentStatus
from app.database.redis import add_shipment_verification_code
from app.services.base import BaseService
from app.utils import generate_url_safe_token
from app.worker.tasks import send_sms, send_email_with_template


class ShipmentEventService(BaseService[ShipmentEvent]):
    def __init__(self, session):
        super().__init__(ShipmentEvent, session)

    async def add(
        self,
        shipment: Shipment,
        location: int | None = None,
        status: ShipmentStatus | None = None,
        description: str | None = None
    ) -> ShipmentEvent:
        if not location or not status:
            last_event = await self.get_latest_event(shipment)

            location = location if location else last_event.location
            status = status if status else last_event.status
          
        new_event = ShipmentEvent(
            location = location,
            status=status,
            description=description if description else self._generate_description(status, location),
            shipment_id=shipment.id,
        )

        await self._notify(shipment, status)

        return await self._add(new_event)

    async def get_latest_event(self, shipment: Shipment):
        timeline = shipment.timeline
        timeline.sort(key=lambda item: item.created_at)

        return timeline[-1]

    def _generate_description(self, status: ShipmentStatus, location: int):
        match status:
            case ShipmentStatus.placed:
                return "assigned delivery partner"
            case ShipmentStatus.out_for_delivery:
                return "shipment out for delivery"
            case ShipmentStatus.delivered:
                return "shipment delivered successfully"
            case ShipmentStatus.cancelled:
                return "shipment cancelled by the seller"
            case _:
                return f"scanned at {location}"

    async def _notify(self, shipment: Shipment, status: ShipmentStatus):

        if status == ShipmentStatus.in_transit:
            return

        subject: str
        context: dict[str, str] = {}
        template_name: str

        match status:
            case ShipmentStatus.placed:
                subject = "Your Order is Shipped 🚛"
                context["seller"] = shipment.seller.name
                context["partner"] = shipment.delivery_partner.name
                context["id"] = str(shipment.id)
                template_name = "mail_placed.html"

            case ShipmentStatus.out_for_delivery:
                subject = "Your Order is Arriving Soon 🛵"
                template_name = "mail_out_for_delivery.html"

                code = randint(100_000, 999_999)
                await add_shipment_verification_code(shipment.id, code)

                # if shipment.client_contact_phone:
                #     send_sms(
                #         to=shipment.client_contact_phone,
                #         body=f"Your order is arriving soon! Share the {code} code with your"
                #         "delivery executive to recieve your package."
                #     )
                # else:
                context["verification_code"] = str(code)

            case ShipmentStatus.delivered:
                subject = "Your Order is Delivered ✅"
                context["seller"] = shipment.seller.name
                token = generate_url_safe_token({"id": str(shipment.id)}, salt="shipment-review")
                context["review_url"] = f"http://{app_settings.APP_DOMAIN}/shipment/review?token={token}"
                template_name = "mail_delivered.html"

            case ShipmentStatus.cancelled:
                subject = "Your Order is Cancelled ❌"
                template_name = "mail_delivered.html"

        send_email_with_template.delay(
            recipients=[shipment.client_contact_email],
            subject=subject,
            context=context,
            template_name=template_name
        )