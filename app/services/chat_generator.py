import logging
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from app.utils.prompts import CHAT_SYSTEM_PROMPT

logger = logging.getLogger("uvicorn")
fast_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)

async def stream_chat_response(
    message: str, 
    user_profile: str, 
    conversation_summary: str,
    recent_history: list
):
    """
    Generates a streaming response using the latest Context.
    This is the "Pit Crew" - it needs to be fast.
    """
    
    # 1. Build the Prompt
    system_msg = SystemMessage(content=CHAT_SYSTEM_PROMPT.format(
        user_profile=user_profile,
        summary=conversation_summary
    ))

    # 2. Prepare Messages (System + History + Latest)
    # Ensure history is formatted correctly for LangChain
    full_history = [system_msg] + recent_history + [HumanMessage(content=message)]

    # 3. Stream
    # We yield chunks so FastAPI can send them via Server-Sent Events (SSE)
    async for chunk in fast_llm.astream(full_history):
        if chunk.content:
            yield chunk.content