from pydantic import BaseModel, Field
from typing import List, Literal, Optional

# --- API Request/Response ---
class ChatRequest(BaseModel):
    user_id: str = Field(..., description="Unique user identifier for LTM")
    thread_id: str = Field(..., description="Session identifier for STM")
    message: str

class ChatResponse(BaseModel):
    response: str

# --- Internal Logic Schemas (LLM Structured Output) ---
class MemoryOp(BaseModel):
    action: Literal["create", "update", "delete"]
    memory_id: Optional[str] = Field(default=None)
    content: Optional[str] = Field(default=None)

class MemoryOutput(BaseModel):
    thoughts: str
    operations: List[MemoryOp]