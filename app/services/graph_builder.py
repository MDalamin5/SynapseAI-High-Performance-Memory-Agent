import logging
from functools import partial
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END

# --- CORRECT ASYNC IMPORTS ---
# 1. Async Store (LTM)
# We try to import AsyncPostgresStore. 
# If your version is slightly different, it might be in .aio, but usually it is here:
try:
    from langgraph.store.postgres import AsyncPostgresStore
except ImportError:
    # Fallback for different versions
    from langgraph.store.postgres.aio import AsyncPostgresStore

# 2. Async Checkpointer (STM)
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.core.database import db
from app.models.state import AgentState
from app.services.nodes import ltm_node, chat_node, summarize_node

logger = logging.getLogger("uvicorn")

class ChatService:
    def __init__(self):
        self.graph = None
        self.store = None
        self.checkpointer = None

    async def initialize_graph(self):
        try:
            pool = db.get_pool()
            
            # --- 1. SETUP LTM STORE (ASYNC) ---
            # We use AsyncPostgresStore which accepts AsyncConnectionPool
            self.store = AsyncPostgresStore(pool)
            
            # Initialize table generation
            # Note: For AsyncStore, 'setup' is usually an async method.
            await self.store.setup()
            
            # --- 2. SETUP STM CHECKPOINTER (ASYNC) ---
            self.checkpointer = AsyncPostgresSaver(pool)
            await self.checkpointer.setup()

            # --- 3. BUILD GRAPH ---
            builder = StateGraph(AgentState)
            
            # Pass the ASYNC store to the nodes
            builder.add_node("ltm_manager", partial(ltm_node, store=self.store))
            builder.add_node("chat_agent", partial(chat_node, store=self.store))
            builder.add_node("stm_summarizer", summarize_node)

            builder.add_edge(START, "ltm_manager")
            builder.add_edge("ltm_manager", "chat_agent")
            builder.add_edge("chat_agent", "stm_summarizer")
            builder.add_edge("stm_summarizer", END)

            self.graph = builder.compile(checkpointer=self.checkpointer, store=self.store)
            logger.info("✅ Async LangGraph compiled successfully.")
            
        except Exception as e:
            logger.error(f"❌ Failed to init graph: {e}")
            # Optional: Print dir(self.store) to debug if method names change
            # print(dir(self.store)) 
            raise e

    async def process_message(self, user_id: str, thread_id: str, message: str):
        if not self.graph:
            raise Exception("Graph not initialized")

        config = {"configurable": {"user_id": user_id, "thread_id": thread_id}}
        input_message = HumanMessage(content=message)
        final_response = ""

        try:
            async for event in self.graph.astream(
                {"messages": [input_message]}, 
                config=config, 
                stream_mode="values"
            ):
                if "messages" in event:
                    last_msg = event["messages"][-1]
                    if last_msg.type == "ai":
                        final_response = last_msg.content
        except Exception as e:
            logger.error(f"❌ Graph Execution Error: {e}")
            raise e

        return final_response

chat_service = ChatService()