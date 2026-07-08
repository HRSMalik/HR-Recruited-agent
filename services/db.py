"""Single MongoDB client for the whole application.

One `MongoClient` (one connection pool) shared by every module — replaces the
per-module clients that were scattered across services/. The URI and DB name
come from `.env` (secrets); callers use `get_db()` / `get_collection(name)`.
"""
import os

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

load_dotenv()

_CLIENT: MongoClient = None
_DB: Database = None


def get_db() -> Database:
    """Return the shared application database, connecting lazily on first use."""
    global _CLIENT, _DB
    if _DB is None:
        uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        db_name = os.getenv("MONGODB_DB", "recruitment-module")
        _CLIENT = MongoClient(uri)
        _DB = _CLIENT[db_name]
    return _DB


def get_collection(name: str) -> Collection:
    """Return a named collection from the shared database."""
    return get_db()[name]
