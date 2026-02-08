
from typing import Optional
from app.db.firestore import FirestoreRepository
from datetime import datetime

class UserRepository(FirestoreRepository):
    def __init__(self):
        super().__init__("users")

    async def get_by_email(self, email: str) -> Optional[dict]:
        users = await self.query("email", "==", email)
        return users[0] if users else None

    async def get_by_user_id(self, user_id: str) -> Optional[dict]:
        users = await self.query("user_id", "==", user_id)
        return users[0] if users else None

    async def create_user(self, user_data: dict) -> dict:
        # Generate a unique document ID (can use email or user_id as key)
        # Using auto-generated ID from Firestore is also an option, but here we might want to control it.
        # Let's use user_id as the document ID for easy lookup.
        doc_id = user_data.get("user_id") 
        if not doc_id:
             # Fallback if user_id is not provided (should not happen based on current logic)
             # In a real scenario we might generate a UUID here.
             import uuid
             doc_id = str(uuid.uuid4())
             user_data["user_id"] = doc_id
        
        user_data["created_at"] = datetime.utcnow().isoformat()
        user_data["updated_at"] = datetime.utcnow().isoformat()
        
        await self.create(doc_id, user_data)
        return user_data

    async def update_user(self, user_id: str, update_data: dict) -> Optional[dict]:
        # First check if user exists
        # In this design, doc_id is user_id
        update_data["updated_at"] = datetime.utcnow().isoformat()
        return await self.update(user_id, update_data)

    async def get_users_by_type(self, user_type: str) -> list[dict]:
        return await self.query("user_type", "==", user_type)

