import logging
from langchain_openai import ChatOpenAI
from langchain_core.messages import RemoveMessage
from app.utils.prompts import SUMMARY_PROMPT

logger = logging.getLogger("uvicorn")
fast_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)

# We removed ltm_node and chat_node because they are replaced by memory_service and chat_generator
# But we KEEP summarize_node

async def summarize_node(state: dict):
    messages = state["messages"]
    summary = state.get("summary", "")

    # Rule: Summarize if > 6 messages
    if len(messages) > 6:
        logger.info("🧹 [Background] Summarizing history...")
        to_summarize = messages[:-2]
        
        prompt = SUMMARY_PROMPT.format(
            existing_summary=summary if summary else "None",
            new_lines="\n".join([f"{m.type}: {m.content}" for m in to_summarize])
        )
        
        new_summary_msg = await fast_llm.ainvoke(prompt)
        
        return {
            "summary": new_summary_msg.content,
            "messages": [RemoveMessage(id=m.id) for m in to_summarize]
        }
    
    return None