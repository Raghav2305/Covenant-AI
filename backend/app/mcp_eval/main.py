"""
MCP Evaluation Server
Receives evaluation requests and returns triggered status.
"""

from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Dict, Any

app = FastAPI(
    title="MCP Evaluation Server",
    description="A service that evaluates contract obligations against live data.",
    version="0.1.0"
)

class EvaluationRequest(BaseModel):
    """Request model for an obligation evaluation."""
    check_type: str = Field(..., description="The type of check to perform (e.g., 'discount_check').")
    check_parameters: Dict[str, Any] = Field(..., description="The parameters for the check, extracted from the obligation.")
    context: Dict[str, Any] = Field(..., description="The context from the contract (e.g., linked_entity_id).")

class EvaluationResponse(BaseModel):
    """Response model for an obligation evaluation."""
    triggered: bool = Field(..., description="Whether the condition was met and an alert should be triggered.")
    evidence: Dict[str, Any] = Field(..., description="The data used to make the determination.")

@app.post("/evaluate", response_model=EvaluationResponse)
async def evaluate_obligation(request: EvaluationRequest):
    """
    Receives an obligation check, evaluates it, and returns the result.
    
    This is the core endpoint for the MCP Evaluation Server.
    
    - **check_type**: The identifier for the evaluation logic to run.
    - **check_parameters**: The specific rules from the contract obligation.
    - **context**: The link back to the operational entity (e.g., customer ID).
    """
    print(f"Received evaluation request: {request.dict()}")

    # --- Dummy Logic ---
    # In the future, this is where we will have a dispatcher that calls the
    # appropriate handler based on `request.check_type`.
    # For now, we'll just return a hardcoded response.
    
    triggered_status = False
    evidence_payload = {
        "message": "This is a dummy response from the MCP Evaluation Server.",
        "request_received": request.dict()
    }

    return EvaluationResponse(triggered=triggered_status, evidence=evidence_payload)

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
