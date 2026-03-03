import asyncio
import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse

from app.models.schemas import ChatRequest
from app.core.database import db
from app.services.memory_service import memory_service # Import the INSTANCE
from app.services.chat_generator import stream_chat_response
from app.services.background import run_background_tasks
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

router = APIRouter()
logger = logging.getLogger("uvicorn")

@router.post("/chat")
async def chat_endpoint(request: ChatRequest, background_tasks: BackgroundTasks):
    try:
        user_id = request.user_id
        thread_id = request.thread_id
        message = request.message

        # --- 1. FETCH CONTEXT (Parallel) ---
        
        # Task A: Get Profile from Redis (via MemoryService Instance)
        task_profile = memory_service.get_user_profile(user_id)
        
        # Task B: Get History from Postgres
        async def fetch_history():
            pool = db.get_pg_pool()
            checkpointer = AsyncPostgresSaver(pool)
            config = {"configurable": {"thread_id": thread_id}}
            checkpoint = await checkpointer.aget(config)
            if checkpoint and "channel_values" in checkpoint:
                return checkpoint["channel_values"].get("messages", []), checkpoint["channel_values"].get("summary", "")
            return [], ""

        task_history = fetch_history()

        # Run both
        profile_text, (history_messages, summary_text) = await asyncio.gather(task_profile, task_history)

        # --- 2. STREAM RESPONSE ---
        async def response_generator():
            full_response = ""
            async for chunk in stream_chat_response(
                message=message,
                user_profile=profile_text,
                conversation_summary=summary_text,
                recent_history=history_messages
            ):
                full_response += chunk
                yield chunk
            
            # --- 3. TRIGGER BACKGROUND ---
            background_tasks.add_task(
                run_background_tasks, 
                user_id, 
                thread_id, 
                message, 
                full_response
            )

        return StreamingResponse(response_generator(), media_type="text/event-stream")

    except Exception as e:
        logger.error(f"🔥 API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))