"""
MongoDB client — singleton connection managed here.
All other code imports get_db() from this module; never touch pymongo directly.
"""
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, ConfigurationError
from django.conf import settings

_client: MongoClient | None = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(
            settings.MONGO_URI,
            serverSelectionTimeoutMS=5000,
            # Explicit TLS options help Python 3.13 negotiate correctly with Atlas
            tls=True,
            tlsAllowInvalidCertificates=getattr(settings, 'MONGO_TLS_ALLOW_INVALID', False),
        )
    return _client


def get_db():
    """Return the SmartServe MongoDB database handle."""
    return get_client()[settings.MONGO_DB_NAME]


def ping() -> bool:
    """Return True if MongoDB is reachable."""
    try:
        get_client().admin.command('ping')
        return True
    except Exception:
        return False


class MongoUnavailableError(Exception):
    """Raised when MongoDB Atlas cannot be reached (IP not whitelisted, cluster paused, etc.)."""
    pass
