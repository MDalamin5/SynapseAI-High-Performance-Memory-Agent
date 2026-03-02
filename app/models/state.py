from langgraph.graph import MessagesState
from typing import TypedDict, Annotated

class AgentState(MessagesState):
    """
    The unified state of the agent.
    Inherits 'messages' from MessagesState.
    """
    summary: str      # Short-Term Memory
    user_profile: str # Long-Term Memory (Cached from DB)