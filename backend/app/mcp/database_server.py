"""
MCP Database Server
Provides live database access for obligation monitoring
"""

import asyncio
import json
from typing import Dict, Any, List
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import structlog
from app.core.config import settings

logger = structlog.get_logger()

# Create FastAPI app for MCP server
app = FastAPI(title="MCP Database Server")

# Store connected clients
connected_clients: Dict[str, Dict[str, Any]] = {}


class MCPRequest(BaseModel):
    client_id: str
    query_type: str
    params: Dict[str, Any] = {}


class MCPResponse(BaseModel):
    success: bool
    data: Any = None
    error: str = None


@app.post("/connect")
async def connect_client(request: Dict[str, str]):
    """Connect a client to the MCP server"""
    client_id = request.get("client_id")
    if not client_id:
        raise HTTPException(status_code=400, detail="client_id required")
    
    connected_clients[client_id] = {
        "connected_at": asyncio.get_event_loop().time(),
        "queries_executed": 0
    }
    
    logger.info("Client connected to MCP database server", client_id=client_id)
    return {"status": "connected", "client_id": client_id}


@app.post("/query")
async def execute_query(request: MCPRequest):
    """Execute database query via MCP"""
    client_id = request.client_id
    query_type = request.query_type
    params = request.params
    
    if client_id not in connected_clients:
        raise HTTPException(status_code=401, detail="Client not connected")
    
    try:
        # Increment query counter
        connected_clients[client_id]["queries_executed"] += 1
        
        # Route query based on type
        if query_type == "database_query":
            result = await execute_database_query(params)
        elif query_type == "transaction_data":
            result = await get_transaction_data(params)
        elif query_type == "customer_volume":
            result = await get_customer_volume(params)
        elif query_type == "discount_data":
            result = await get_discount_data(params)
        else:
            raise ValueError(f"Unknown query type: {query_type}")
        
        logger.info("MCP database query executed", 
                   client_id=client_id, 
                   query_type=query_type,
                   query_count=connected_clients[client_id]["queries_executed"])
        
        return MCPResponse(success=True, data=result)
        
    except Exception as e:
        logger.error("MCP database query failed", 
                    client_id=client_id, 
                    query_type=query_type, 
                    error=str(e))
        return MCPResponse(success=False, error=str(e))


@app.get("/schema")
async def get_schema():
    """Get available database schema and query types"""
    return {
        "query_types": [
            "database_query",
            "transaction_data", 
            "customer_volume",
            "discount_data"
        ],
        "tables": [
            "transactions",
            "customers", 
            "contracts",
            "obligations"
        ],
        "description": "MCP Database Server for Contract AI Copilot"
    }


@app.post("/disconnect")
async def disconnect_client(request: Dict[str, str]):
    """Disconnect a client from the MCP server"""
    client_id = request.get("client_id")
    if client_id in connected_clients:
        del connected_clients[client_id]
        logger.info("Client disconnected from MCP database server", client_id=client_id)
    
    return {"status": "disconnected", "client_id": client_id}


async def execute_database_query(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute raw database query"""
    query = params.get("query", "")
    query_params = params.get("params", {})
    
    # In a real implementation, this would connect to the actual database
    # For now, return mock data based on query patterns
    
    if "transactions" in query.lower():
        return {
            "rows": [
                {
                    "transaction_id": "TXN-001",
                    "amount": 150000.00,
                    "transaction_date": "2024-09-27",
                    "customer_id": query_params.get("customer_id", "CUST-001"),
                    "transaction_type": "payment"
                },
                {
                    "transaction_id": "TXN-002", 
                    "amount": 75000.00,
                    "transaction_date": "2024-09-26",
                    "customer_id": query_params.get("customer_id", "CUST-001"),
                    "transaction_type": "refund"
                }
            ],
            "count": 2
        }
    
    return {"rows": [], "count": 0}


async def get_transaction_data(params: Dict[str, Any]) -> Dict[str, Any]:
    """Get transaction data for obligation monitoring"""
    customer_id = params.get("customer_id")
    start_date = params.get("start_date")
    end_date = params.get("end_date")
    
    # Mock transaction data
    return {
        "customer_id": customer_id,
        "period": {"start": start_date, "end": end_date},
        "transactions": [
            {
                "transaction_id": "TXN-001",
                "amount": 150000.00,
                "transaction_date": "2024-09-27",
                "transaction_type": "payment",
                "discount_percentage": 5.0,
                "discount_amount": 7500.00
            },
            {
                "transaction_id": "TXN-002",
                "amount": 75000.00, 
                "transaction_date": "2024-09-26",
                "transaction_type": "refund",
                "discount_percentage": 0.0,
                "discount_amount": 0.00
            }
        ],
        "summary": {
            "total_amount": 225000.00,
            "total_discount": 7500.00,
            "transaction_count": 2,
            "avg_discount_percentage": 2.5
        }
    }


async def get_customer_volume(params: Dict[str, Any]) -> Dict[str, Any]:
    """Get customer transaction volume for rebate calculations"""
    customer_id = params.get("customer_id")
    period_start = params.get("period_start")
    
    # Mock volume data
    return {
        "customer_id": customer_id,
        "period_start": period_start,
        "transaction_count": 1250,
        "total_amount": 2500000.00,
        "volume_threshold": 1000000.00,
        "rebate_eligible": True,
        "rebate_percentage": 2.0,
        "estimated_rebate": 50000.00
    }


async def get_discount_data(params: Dict[str, Any]) -> Dict[str, Any]:
    """Get discount data for cap monitoring"""
    customer_id = params.get("customer_id")
    start_date = params.get("start_date")
    end_date = params.get("end_date")
    
    # Mock discount data
    return {
        "customer_id": customer_id,
        "period": {"start": start_date, "end": end_date},
        "discounts": [
            {
                "transaction_id": "TXN-001",
                "discount_percentage": 5.0,
                "discount_amount": 7500.00,
                "transaction_date": "2024-09-27"
            },
            {
                "transaction_id": "TXN-003",
                "discount_percentage": 8.0,
                "discount_amount": 12000.00,
                "transaction_date": "2024-09-25"
            }
        ],
        "summary": {
            "max_discount_percentage": 8.0,
            "avg_discount_percentage": 6.5,
            "total_discount_amount": 19500.00,
            "discount_cap": 10.0,
            "cap_breach": False
        }
    }


if __name__ == "__main__":
    import uvicorn
    port = int(settings.MCP_SERVER_PORT or 3001)
    uvicorn.run(
        "app.mcp.database_server:app",
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
