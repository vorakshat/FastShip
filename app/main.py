from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse
from scalar_fastapi import get_scalar_api_reference

from app.api.router import master_router
from app.core.exceptions import add_exception_handlers
from app.database.session import create_db_tables
from app.worker.tasks import add_log


@asynccontextmanager
async def lifespan_handler(app: FastAPI):
    await create_db_tables()
    yield # Start the app and wait for it to end

app = FastAPI(
    # Server start/stop listener
    lifespan=lifespan_handler
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

@app.get("/scalar", include_in_schema=False)
def get_scalar_docs():
    return get_scalar_api_reference(
        openapi_url=app.openapi_url or "/openapi.json",
        title="Scalar API",
        scalar_favicon_url="/favicon.ico"
    )