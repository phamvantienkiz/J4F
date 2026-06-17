from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class AgentState(BaseModel):
    session_id: str
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    slots: Dict[str, Any] = Field(default_factory=dict)
    current_intent: Optional[str] = None

    def update_slot(self, key: str, value: Any):
        self.slots[key] = value

    def get_slot(self, key: str, default: Any = None) -> Any:
        return self.slots.get(key, default)
