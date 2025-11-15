"""
AI Copilot API endpoints
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.models.contract import Contract
from app.models.obligation import Obligation
from app.utils.llm_client import LLMClient
from app.utils.vector_store import VectorStore
import structlog

logger = structlog.get_logger()
router = APIRouter()


class CopilotQuery(BaseModel):
    query: str
    contract_id: Optional[str] = None # Allow filtering by a specific contract
    max_results: Optional[int] = 10


class CopilotResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]


@router.post("/query", response_model=CopilotResponse)
async def query_copilot(
    query_data: CopilotQuery,
    db: Session = Depends(get_db)
):
    """Query the AI copilot with natural language, with optional contract-specific context."""
    
    logger.info("Copilot query received", query=query_data.query, contract_id=query_data.contract_id)
    
    try:
        llm_client = LLMClient()
        vector_store = VectorStore()

        # If a contract_id is provided, use it to filter the search
        filters = None
        if query_data.contract_id:
            filters = {"contract_id": query_data.contract_id}

        # Search for relevant document chunks semantically
        search_results = await vector_store.search_documents(
            query=query_data.query,
            limit=query_data.max_results or 10,
            filters=filters
        )
        
        # Generate response using LLM with the retrieved context
        answer = await llm_client.generate_copilot_response(
            query_data.query,
            search_results
        )
        
        logger.info("Copilot query completed", contract_id=query_data.contract_id, sources_count=len(search_results))
        
        return CopilotResponse(
            answer=answer,
            sources=search_results,
        )
        
    except Exception as e:
        logger.error("Copilot query failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Copilot query failed: {str(e)}")


@router.get("/suggestions")
async def get_query_suggestions(
    context: Optional[str] = Query(None, description="Context for suggestions"),
    db: Session = Depends(get_db)
):
    """Get suggested queries for the copilot"""
    
    suggestions = [
        "Show me all obligations due next month",
        "Which contracts have rebate triggers active this quarter?",
        "What are the highest risk obligations?",
        "Show me all overdue obligations",
        "Which contracts have penalty amounts over ₹1 lakh?",
        "What obligations are due this week?",
        "Show me all compliance alerts",
        "Which parties have the most obligations?",
        "What are the total penalty exposures?",
        "Show me contracts with discount caps"
    ]
    
    if context:
        # Filter suggestions based on context
        context_lower = context.lower()
        filtered_suggestions = [
            s for s in suggestions 
            if any(word in s.lower() for word in context_lower.split())
        ]
        suggestions = filtered_suggestions[:5] if filtered_suggestions else suggestions[:5]
    
    return {
        "suggestions": suggestions,
        "context": context
    }

# The other endpoints below are more for structured data retrieval and don't use the RAG system.
# They can be kept as they are for now.

@router.get("/obligations/due")
async def get_obligations_due(
    timeframe: str = Query("month", description="Timeframe: week, month, quarter"),
    party: Optional[str] = Query(None, description="Filter by party"),
    risk_level: Optional[str] = Query(None, description="Filter by risk level"),
    db: Session = Depends(get_db)
):
    """Get obligations due within specified timeframe"""
    
    from datetime import datetime, timedelta
    
    # Calculate date range
    now = datetime.now()
    if timeframe == "week":
        end_date = now + timedelta(days=7)
    elif timeframe == "month":
        end_date = now + timedelta(days=30)
    elif timeframe == "quarter":
        end_date = now + timedelta(days=90)
    else:
        end_date = now + timedelta(days=30)
    
    # Build query
    query = db.query(Obligation).filter(
        Obligation.status == "active",
        Obligation.deadline.isnot(None),
        Obligation.deadline >= now,
        Obligation.deadline <= end_date
    )
    
    if party:
        query = query.filter(Obligation.party.ilike(f"%{party}%"))
    
    if risk_level:
        query = query.filter(Obligation.risk_level == risk_level)
    
    obligations = query.order_by(Obligation.deadline).all()
    
    return {
        "timeframe": timeframe,
        "obligations": [obligation.to_dict() for obligation in obligations],
        "count": len(obligations),
        "filters": {
            "party": party,
            "risk_level": risk_level
        }
    }


@router.get("/obligations/overdue")
async def get_overdue_obligations(
    party: Optional[str] = Query(None, description="Filter by party"),
    risk_level: Optional[str] = Query(None, description="Filter by risk level"),
    db: Session = Depends(get_db)
):
    """Get all overdue obligations"""
    
    from datetime import datetime
    
    query = db.query(Obligation).filter(
        Obligation.status == "active",
        Obligation.deadline.isnot(None),
        Obligation.deadline < datetime.now()
    )
    
    if party:
        query = query.filter(Obligation.party.ilike(f"%{party}%"))
    
    if risk_level:
        query = query.filter(Obligation.risk_level == risk_level)
    
    obligations = query.order_by(Obligation.deadline).all()
    
    return {
        "obligations": [obligation.to_dict() for obligation in obligations],
        "count": len(obligations),
        "filters": {
            "party": party,
            "risk_level": risk_level
        }
    }


@router.get("/obligations/high-risk")
async def get_high_risk_obligations(
    db: Session = Depends(get_db)
):
    """Get all high-risk obligations"""
    
    obligations = db.query(Obligation).filter(
        Obligation.status == "active",
        Obligation.risk_level.in_(["high", "critical"])
    ).order_by(Obligation.deadline).all()
    
    return {
        "obligations": [obligation.to_dict() for obligation in obligations],
        "count": len(obligations),
        "risk_levels": ["high", "critical"]
    }


@router.get("/contracts/summary")
async def get_contracts_summary(
    db: Session = Depends(get_db)
):
    """Get summary of all contracts"""
    
    contracts = db.query(Contract).all()
    obligations = db.query(Obligation).all()
    
    # Calculate summary metrics
    total_contracts = len(contracts)
    active_contracts = len([c for c in contracts if c.status == "active"])
    processing_contracts = len([c for c in contracts if c.processing_status == "processing"])
    failed_contracts = len([c for c in contracts if c.processing_status == "failed"])
    
    total_obligations = len(obligations)
    active_obligations = len([o for o in obligations if o.status == "active"])
    overdue_obligations = len([o for o in obligations if o.is_overdue()])
    
    # Risk distribution
    risk_distribution = {}
    for obligation in obligations:
        risk_level = obligation.risk_level
        risk_distribution[risk_level] = risk_distribution.get(risk_level, 0) + 1
    
    # Party distribution
    party_distribution = {}
    for obligation in obligations:
        party = obligation.party
        party_distribution[party] = party_distribution.get(party, 0) + 1
    
    return {
        "contracts": {
            "total": total_contracts,
            "active": active_contracts,
            "processing": processing_contracts,
            "failed": failed_contracts
        },
        "obligations": {
            "total": total_obligations,
            "active": active_obligations,
            "overdue": overdue_obligations
        },
        "risk_distribution": risk_distribution,
        "party_distribution": party_distribution
    }


@router.get("/search")
async def search_contracts_and_obligations(
    q: str = Query(..., description="Search query"),
    type: Optional[str] = Query(None, description="Search type: contract, obligation, all"),
    limit: int = Query(10, description="Maximum results"),
    db: Session = Depends(get_db)
):
    """Search contracts and obligations using vector similarity"""
    
    try:
        vector_store = VectorStore()
        
        # Determine search filters
        filters = None
        if type:
            filters = {"doc_type": type}
        
        # Perform vector search
        results = await vector_store.search_documents(
            query=q,
            limit=limit,
            filters=filters
        )
        
        return {
            "query": q,
            "type": type or "all",
            "results": results,
            "count": len(results)
        }
        
    except Exception as e:
        logger.error("Search failed", query=q, error=str(e))
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
