from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any

class TicketInput(BaseModel):
    subject: str
    description: str
    customer_id: Optional[str] = None
    priority: Optional[str] = "normal"

class TicketResponse(BaseModel):
    request_id: str
    status: str
    message: str

class AIStructuredOutput(BaseModel):
    decision: str = Field(description="The decision made by AI: e.g., approve, reject, escalate, manual_review")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0")
    reason: str = Field(description="Reason for the decision")
    uncertainty: bool = Field(description="True if the AI is unsure and recommends human review")
    category: str = Field(description="Category of the ticket")

class RuleCreate(BaseModel):
    name: str
    condition: Dict[str, Any]
    action: str

class RuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    condition: Dict[str, Any]
    action: str
    is_active: bool

class ExplainResponse(BaseModel):
    request_id: str
    input_data: Dict[str, Any]
    retrieved_context: List[str]
    ai_output: Optional[Dict[str, Any]]
    rules_triggered: List[str]
    final_decision: Optional[str]
    confidence_score: Optional[float]
    failure_reasons: Optional[str]
    current_state: str
