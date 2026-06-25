"""
Generic repository helpers — thin wrappers over pymongo that enforce
business_id scoping. Views import these, never raw pymongo collections.
"""
from bson import ObjectId
from datetime import datetime, timezone
from pymongo.collection import Collection


def _scope(business_id: str, extra: dict = None) -> dict:
    """Build a query filter scoped to a specific business."""
    q = {'business_id': str(business_id)}
    if extra:
        q.update(extra)
    return q


def find_all(col: Collection, business_id: str, query: dict = None,
             sort: list = None, limit: int = 0) -> list:
    q = _scope(business_id, query)
    cursor = col.find(q)
    if sort:
        cursor = cursor.sort(sort)
    if limit:
        cursor = cursor.limit(limit)
    return list(cursor)


def find_one(col: Collection, business_id: str, doc_id: str) -> dict | None:
    return col.find_one(_scope(business_id, {'_id': ObjectId(doc_id)}))


def insert_one(col: Collection, business_id: str, doc: dict) -> str:
    doc['business_id'] = str(business_id)
    doc.setdefault('created_at', datetime.now(timezone.utc))
    result = col.insert_one(doc)
    return str(result.inserted_id)


def insert_many(col: Collection, business_id: str, docs: list) -> list:
    now = datetime.now(timezone.utc)
    for d in docs:
        d['business_id'] = str(business_id)
        d.setdefault('created_at', now)
    result = col.insert_many(docs)
    return [str(i) for i in result.inserted_ids]


def update_one(col: Collection, business_id: str, doc_id: str, updates: dict) -> bool:
    updates['updated_at'] = datetime.now(timezone.utc)
    result = col.update_one(
        _scope(business_id, {'_id': ObjectId(doc_id)}),
        {'$set': updates}
    )
    return result.modified_count > 0


def delete_one(col: Collection, business_id: str, doc_id: str) -> bool:
    result = col.delete_one(_scope(business_id, {'_id': ObjectId(doc_id)}))
    return result.deleted_count > 0


def count(col: Collection, business_id: str, query: dict = None) -> int:
    return col.count_documents(_scope(business_id, query))


def aggregate(col: Collection, pipeline: list) -> list:
    return list(col.aggregate(pipeline))
