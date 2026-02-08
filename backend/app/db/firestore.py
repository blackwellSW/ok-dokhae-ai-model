
from app.core.firebase import get_firestore_client

# Use the singleton client from core module
try:
    db = get_firestore_client()
except Exception as e:
    print(f"Warning: Failed to get firestore client in module scope: {e}")
    db = None 

class FirestoreRepository:
    def __init__(self, collection_name: str):
        # Ensure db is initialized if it wasn't at module level
        if db is None:
             self.db = get_firestore_client()
        else:
             self.db = db
        self.collection = self.db.collection(collection_name)

    async def get(self, doc_id: str):
        doc = self.collection.document(doc_id).get()
        if doc.exists:
            return doc.to_dict()
        return None

    async def create(self, doc_id: str, data: dict):
        self.collection.document(doc_id).set(data)
        return data

    async def update(self, doc_id: str, data: dict):
        self.collection.document(doc_id).update(data)
        return await self.get(doc_id)

    async def delete(self, doc_id: str):
        self.collection.document(doc_id).delete()
        return True
    
    async def list_all(self, limit: int = 100):
        docs = self.collection.limit(limit).stream()
        return [doc.to_dict() for doc in docs]
    
    async def query(self, field: str, operator: str, value: any):
        docs = self.collection.where(field, operator, value).stream()
        return [doc.to_dict() for doc in docs]
