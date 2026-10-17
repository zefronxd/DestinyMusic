from motor.motor_asyncio import AsyncIOMotorClient

from config import MONGO_DB_NAME, MONGO_DB_URI

from ..logging import LOGGER

LOGGER(__name__).info("Connecting to your Mongo Database...")
if not MONGO_DB_URI:
    raise RuntimeError("Set MONGO_URI or MONGO_DB_URI to connect to MongoDB.")

_mongo_async_ = AsyncIOMotorClient(MONGO_DB_URI, serverSelectionTimeoutMS=8000)
mongodb = _mongo_async_[MONGO_DB_NAME]


async def verify_mongo_connection():
    try:
        await _mongo_async_.admin.command("ping")
    except Exception as error:
        LOGGER(__name__).error(
            "MongoDB connection failed (%s).", type(error).__name__
        )
        raise
    LOGGER(__name__).info(
        "Connected to MongoDB database '%s'.", MONGO_DB_NAME
    )
