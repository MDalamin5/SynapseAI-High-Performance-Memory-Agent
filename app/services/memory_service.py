import logging
import uuid
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
# Fallback import for different library versions
try:
    from langgraph.store.postgres import AsyncPostgresStore
except ImportError:
    from langgraph.store.postgres.aio import AsyncPostgresStore

from app.core.database import db
from app.models.schemas import MemoryOutput
from app.utils.prompts import MEMORY_SYSTEM_PROMPT

logger = logging.getLogger("uvicorn")

class MemoryService:
    def __init__(self, llm):
        self.llm = llm
        self.store = None

    async def setup_store(self):
        pool = db.get_pg_pool()
        self.store = AsyncPostgresStore(pool)
        await self.store.setup()

    async def get_user_profile(self, user_id: str) -> str:
        redis_client = db.get_redis()
        cache_key = f"user:{user_id}:profile"

        # 1. Try Redis
        cached_profile = await redis_client.get(cache_key)
        if cached_profile:
            return cached_profile

        # 2. Fallback to Postgres
        if not self.store:
            await self.setup_store()

        namespace = ("user", user_id, "profile")
        
        # Safe search (handles different library versions)
        if hasattr(self.store, "asearch"):
            items = await self.store.asearch(namespace)
        else:
            items = await self.store.search(namespace)

        if items:
            profile_text = "\n".join([f"- {i.value['data']}" for i in items])
        else:
            profile_text = "No known details."

        # 3. Write back to Redis
        await redis_client.setex(cache_key, 3600, profile_text)
        
        return profile_text

    async def update_user_profile(self, user_id: str, message: str):
        if not self.store:
            await self.setup_store()

        namespace = ("user", user_id, "profile")
        
        # Fetch current
        if hasattr(self.store, "asearch"):
            items = await self.store.asearch(namespace)
        else:
            items = await self.store.search(namespace)
            
        existing_text = "\n".join([f"ID: {i.key} | Fact: {i.value['data']}" for i in items])

        # Analyze
        extractor = self.llm.with_structured_output(MemoryOutput)
        decision = await extractor.ainvoke([
            SystemMessage(content=MEMORY_SYSTEM_PROMPT.format(
                existing_memories=existing_text, 
                user_message=message
            ))
        ])

        # Write
        changes_made = False
        if decision.operations:
            logger.info(f"🧠 [Background] Updating LTM: {decision.thoughts}")
            for op in decision.operations:
                changes_made = True
                if op.action == "create" and op.content:
                    await self.store.aput(namespace, str(uuid.uuid4()), {"data": op.content})
                elif op.action == "update" and op.memory_id and op.content:
                    await self.store.aput(namespace, op.memory_id, {"data": op.content})
                elif op.action == "delete" and op.memory_id:
                    await self.store.adelete(namespace, op.memory_id)

        # Refresh Redis
        if changes_made:
            if hasattr(self.store, "asearch"):
                updated_items = await self.store.asearch(namespace)
            else:
                updated_items = await self.store.search(namespace)
            
            new_profile_text = "\n".join([f"- {i.value['data']}" for i in updated_items])
            
            redis_client = db.get_redis()
            cache_key = f"user:{user_id}:profile"
            await redis_client.setex(cache_key, 3600, new_profile_text)
            logger.info("✅ Redis Cache Updated.")

# --- CRITICAL: INSTANTIATE THE SERVICE HERE ---
smart_llm = ChatOpenAI(model="gpt-4o", temperature=0)
memory_service = MemoryService(llm=smart_llm)