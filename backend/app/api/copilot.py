"""
AI Copilot API endpoints
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.simple_database import get_db
from app.models.contract import Contract
from app.models.obligation import Obligation
from app.utils.llm_client import LLMClient
from app.utils.simple_vector_store import SimpleVectorStore
import structlog

logger = structlog.get_logger()
router = APIRouter()


class CopilotQuery(BaseModel):
    query: str
    context_filters: Optional[Dict[str, Any]] = None
    max_results: Optional[int] = 10


class CopilotResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    confidence: float
    query_type: str


@router.post("/query", response_model=CopilotResponse)
async def query_copilot(
    query_data: CopilotQuery,
    db: Session = Depends(get_db)
):
    """Query the AI copilot with natural language"""
    
    logger.info("Copilot query received", query=query_data.query[:100])
    
    try:
        # Initialize services
        llm_client = LLMClient()
        vector_store = SimpleVectorStore()
        await vector_store.initialize()
        
        # Search for relevant documents
        search_results = await vector_store.search_documents(
            query=query_data.query,
            limit=query_data.max_results or 10,
            filters=query_data.context_filters
        )
        
        # Generate response using LLM
        answer = await llm_client.generate_copilot_response(
            query_data.query,
            search_results
        )
        
        # Determine query type
        query_type = _classify_query_type(query_data.query)
        
        # Calculate confidence based on search results
        confidence = _calculate_confidence(search_results)
        
        logger.info("Copilot query completed", 
                   query_type=query_type,
                   confidence=confidence,
                   sources_count=len(search_results))
        
        return CopilotResponse(
            answer=answer,
            sources=search_results,
            confidence=confidence,
            query_type=query_type
        )
        
    except Exception as e:
        logger.error("Copilot query failed", error=str(e))
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
        vector_store = SimpleVectorStore()
        await vector_store.initialize()
        
        # Determine search filters
        filters = None
        if type == "contract":
            filters = {"doc_type": "contract"}
        elif type == "obligation":
            filters = {"doc_type": "obligation"}
        
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


def _classify_query_type(query: str) -> str:
    """Classify the type of query"""
    query_lower = query.lower()
    
    if any(word in query_lower for word in ["due", "deadline", "when", "next"]):
        return "deadline_query"
    elif any(word in query_lower for word in ["risk", "high", "critical", "danger"]):
        return "risk_query"
    elif any(word in query_lower for word in ["penalty", "rebate", "money", "amount"]):
        return "financial_query"
    elif any(word in query_lower for word in ["overdue", "late", "missed"]):
        return "compliance_query"
    elif any(word in query_lower for word in ["party", "client", "vendor"]):
        return "party_query"
    else:
        return "general_query"


def _calculate_confidence(search_results: List[Dict[str, Any]]) -> float:
    """Calculate confidence score based on search results"""
    if not search_results:
        return 0.0
    
    # Average similarity score
    similarities = [result.get("similarity", 0) for result in search_results]
    avg_similarity = sum(similarities) / len(similarities)
    
    # Convert to percentage
    confidence = min(avg_similarity * 100, 100)
    
    return round(confidence, 2)
