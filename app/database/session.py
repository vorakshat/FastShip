from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from app.config import database_settings

# Create a database engine to connect with database
engine = create_async_engine(   # Creates the async connection pool to PostgreSQL
    # database type/dialect and file name
    url=database_settings.POSTGRES_URL,
    # Log sql queries
    echo=True # prints every generated SQL query to your terminal for debugging
)

async_session = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False  # critical in async SQLAlchemy so accessing attributes on a model after await session.commit() 
        # doesn't trigger a hidden synchronous reload query (which crashes in async mode).
    )

async def create_db_tables():
    async with engine.begin() as connection:
        from .models import DeliveryPartner, Seller, Shipment  # noqa: F401
        await connection.run_sync(SQLModel.metadata.create_all) # create_all is a sync func and will not return a co-routine, 
        # so to avoid the event loop to fail we ise run_sync() which allows safe execution of sync function in async func

# Session to interact with the database
async def get_session():
    async with async_session() as session:
        yield session   # FastAPI injects a fresh session per request and automatically closes it when the request finishes.