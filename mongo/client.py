"""
MongoDB client — singleton connection managed here.
All other code imports get_db() from this module; never touch pymongo directly.
"""
from pymongo import MongoClient
from django.conf import settings

_client: MongoClient | None = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(settings.MONGO_URI, serverSelectionTimeoutMS=5000)
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
