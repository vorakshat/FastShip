from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse
from scalar_fastapi import get_scalar_api_reference

from app.api.router import master_router
from app.api.tag import APITag
from app.core.exceptions import add_exception_handlers
from app.database.session import create_db_tables
from app.worker.tasks import add_log


@asynccontextmanager
async def lifespan_handler(app: FastAPI):
    await create_db_tables()
    yield # Start the app and wait for it to end

description = """
Delivery Management System for sellers and delivery agents

### Seller
- Submit shipment effortlessly
- Share tracking links with customers

### Delivery Agent
- Auto accept shipments
- Track and update shipment status
- Email and SMS notifications
"""

app = FastAPI(
    # Server start/stop listener
    lifespan=lifespan_handler,
    title="FastShip",
    description=description,
    docs_url=None, # Disables /docs route
    redoc_url=None, # Disables /redoc route
    version="0.1.0",
    terms_of_service="https://fastship.com/terms/",
    contact={
        "name": "FastShip Support",
        "url": "https://fastship.com/support",
        "email": "support@fastship.com"
    },
    openapi_tags=[
        {
            "name": APITag.SHIPMENT,
            "description": "Operations related to shipments"
        },
        {
            "name": APITag.SELLER,
            "description": "Operations related to seller"
        },
        {
            "name": APITag.PARTNER,
            "description": "Operations related to delivery partner"
        }
    ]
)

# Register custom exception handlers
add_exception_handlers(app)

# Add all endpoints
app.include_router(master_router)

@app.middleware("http")
async def custom_middleware(request: Request, call_next):
    start = perf_counter()

    response: Response = await call_next(request)

    end = perf_counter()
    time_taken = round(end - start, 2)

    add_log.delay(f"{request.method} {request.url} ({response.status_code}) {time_taken} s")

    return response

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse(
        "app/static/FastShip_logo.png",
        media_type="image/png"
    )

@app.get("/docs", include_in_schema=False)
def get_scalar_docs():
    return get_scalar_api_reference(
        openapi_url=app.openapi_url or "/openapi.json",
        title="Scalar API",
        scalar_favicon_url="/favicon.ico"
    )