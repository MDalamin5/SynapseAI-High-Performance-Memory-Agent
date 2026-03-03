import logging
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.core.database import db
from app.services.memory_service import memory_service
from app.services.nodes import summarize_node

logger = logging.getLogger("uvicorn")

async def run_background_tasks(user_id: str, thread_id: str, user_message: str, bot_response: str):
    """
    Background Task to update LTM and STM.
    """
    try:
        # --- TASK 1: Long-Term Memory (LTM) ---
        # Only run LLM extraction if message is meaningful
        if len(user_message.split()) > 2:
            await memory_service.update_user_profile(user_id, user_message)

        # --- TASK 2: Short-Term Memory (STM) ---
        pool = db.get_pg_pool()
        checkpointer = AsyncPostgresSaver(pool)
        
        # FIX: Add 'checkpoint_ns' (Namespace) to the config
        config = {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": ""  # <--- CRITICAL FIX: Required by LangGraph
            }
        }
        
        # 1. Load current state
        # We use aget_tuple to get the latest checkpoint
        checkpoint_tuple = await checkpointer.aget_tuple(config)
        
        current_messages = []
        current_summary = ""
        
        if checkpoint_tuple and checkpoint_tuple.checkpoint:
             # Extract data from the checkpoint object
            data = checkpoint_tuple.checkpoint["channel_values"]
            current_messages = data.get("messages", [])
            current_summary = data.get("summary", "")

        # 2. Prepare new messages
        new_messages = [
            HumanMessage(content=user_message),
            AIMessage(content=bot_response)
        ]
        
        # 3. Combine History
        updated_messages = current_messages + new_messages
        
        # 4. Run Summarization Logic
        mock_state = {"messages": updated_messages, "summary": current_summary}
        summary_result = await summarize_node(mock_state)
        
        if summary_result:
            final_channels = {
                "messages": summary_result["messages"], # Pruned history
                "summary": summary_result["summary"]
            }
            logger.info("🧹 [Background] Conversation summarized.")
        else:
            final_channels = {
                "messages": updated_messages,
                "summary": current_summary
            }

        # 5. Save to Checkpointer
        # We use aput to write the new state
        # We must provide empty dicts for metadata and new_versions if not tracking them explicitly
        await checkpointer.aput(
            config, 
            create_checkpoint(final_channels), # Helper to format checkpoint
            {}, # metadata
            {}  # new_versions
        )
        logger.info("✅ [Background] History updated.")
        
    except Exception as e:
        logger.error(f"❌ Background Task Failed: {e}")

# --- Helper function to format data for LangGraph Saver ---
def create_checkpoint(channel_values):
    """
    Creates a dictionary structure that mimics a LangGraph Checkpoint.
    """
    import uuid
    from datetime import datetime, timezone
    return {
        "v": 1,
        "id": str(uuid.uuid4()),
        "ts": datetime.now(timezone.utc).isoformat(),
        "channel_values": channel_values,
        "channel_versions": {}, # We let the saver handle versions or ignore
        "versions_seen": {},
        "pending_sends": [],
    }