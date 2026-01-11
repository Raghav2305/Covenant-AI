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
import sqlite3
import os

logger = structlog.get_logger()

# Define the path for the SQLite database
DB_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "live_data.db")

async def get_db_connection():
    """Get a new SQLite database connection."""
    # Use a thread pool or run in executor for synchronous sqlite3 operations
    return await asyncio.to_thread(sqlite3.connect, DB_FILE)

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
    """Execute raw database query against SQLite."""
    query = params.get("query", "")
    query_params = params.get("params", {})

    conn = None
    try:
        conn = await get_db_connection()
        conn.row_factory = sqlite3.Row # This allows accessing columns by name
        cursor = conn.cursor()

        # Replace named parameters with positional ones for sqlite3
        # And extract values in order
        ordered_params = []
        formatted_query = query
        for key, value in query_params.items():
            # Simple replacement for :param_name, might need more robust regex for complex cases
            if f":{key}" in formatted_query:
                formatted_query = formatted_query.replace(f":{key}", "?")
                ordered_params.append(value)
            elif f"${key}" in formatted_query: # Handle $param_name for some SQL dialects
                formatted_query = formatted_query.replace(f"${key}", "?")
                ordered_params.append(value)

        await asyncio.to_thread(cursor.execute, formatted_query, ordered_params)
        rows = await asyncio.to_thread(cursor.fetchall)

        results = []
        for row in rows:
            results.append(dict(row)) # Convert sqlite3.Row to dict

        return {"rows": results, "count": len(results)}
    except Exception as e:
        logger.error("SQLite query execution failed", query=query, params=query_params, error=str(e))
        raise
    finally:
        if conn:
            await asyncio.to_thread(conn.close)


async def get_transaction_data(params: Dict[str, Any]) -> Dict[str, Any]:
    """Get transaction data for obligation monitoring from SQLite."""
    contract_id = params.get("contract_id")
    start_date = params.get("start_date")
    end_date = params.get("end_date")

    conn = None
    try:
        conn = await get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = """
        SELECT transaction_id, amount, transaction_date, transaction_type,
               discount_percentage, discount_amount, customer_id
        FROM transactions
        WHERE contract_id = ? AND transaction_date BETWEEN ? AND ?
        ORDER BY transaction_date DESC
        """
        await asyncio.to_thread(cursor.execute, query, (contract_id, start_date, end_date))
        rows = await asyncio.to_thread(cursor.fetchall)

        transactions = [dict(row) for row in rows]

        total_amount = sum(t['amount'] for t in transactions)
        total_discount = sum(t['discount_amount'] for t in transactions)
        transaction_count = len(transactions)
        avg_discount_percentage = (sum(t['discount_percentage'] for t in transactions) / transaction_count) if transaction_count > 0 else 0

        return {
            "contract_id": contract_id,
            "period": {"start": start_date, "end": end_date},
            "transactions": transactions,
            "summary": {
                "total_amount": total_amount,
                "total_discount": total_discount,
                "transaction_count": transaction_count,
                "avg_discount_percentage": avg_discount_percentage
            }
        }
    except Exception as e:
        logger.error("Failed to get transaction data from SQLite", contract_id=contract_id, error=str(e))
        raise
    finally:
        if conn:
            await asyncio.to_thread(conn.close)


async def get_customer_volume(params: Dict[str, Any]) -> Dict[str, Any]:
    """Get customer transaction volume for rebate calculations from SQLite."""
    contract_id = params.get("contract_id")
    period_start = params.get("period_start")

    conn = None
    try:
        conn = await get_db_connection()
        cursor = conn.cursor()

        query = """
        SELECT COUNT(*) as transaction_count, SUM(amount) as total_amount
        FROM transactions
        WHERE contract_id = ? AND transaction_date >= ?
        """
        await asyncio.to_thread(cursor.execute, query, (contract_id, period_start))
        result = await asyncio.to_thread(cursor.fetchone)

        transaction_count = result[0] if result[0] is not None else 0
        total_amount = result[1] if result[1] is not None else 0.0

        # Define a simple volume threshold for demo purposes
        volume_threshold = 1000000.00 # Example: 1 Million
        rebate_percentage = 2.0 # Example: 2% rebate

        rebate_eligible = total_amount >= volume_threshold
        estimated_rebate = (total_amount * rebate_percentage / 100) if rebate_eligible else 0.0

        return {
            "contract_id": contract_id,
            "period_start": period_start,
            "transaction_count": transaction_count,
            "total_amount": total_amount,
            "volume_threshold": volume_threshold,
            "rebate_eligible": rebate_eligible,
            "rebate_percentage": rebate_percentage,
            "estimated_rebate": estimated_rebate
        }
    except Exception as e:
        logger.error("Failed to get customer volume from SQLite", contract_id=contract_id, error=str(e))
        raise
    finally:
        if conn:
            await asyncio.to_thread(conn.close)


async def get_discount_data(params: Dict[str, Any]) -> Dict[str, Any]:
    """Get discount data for cap monitoring from SQLite."""
    contract_id = params.get("contract_id")
    start_date = params.get("start_date")
    end_date = params.get("end_date")

    conn = None
    try:
        conn = await get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = """
        SELECT transaction_id, discount_percentage, discount_amount, transaction_date, customer_id
        FROM transactions
        WHERE contract_id = ? AND discount_percentage > 0 AND transaction_date BETWEEN ? AND ?
        ORDER BY transaction_date DESC
        """
        await asyncio.to_thread(cursor.execute, query, (contract_id, start_date, end_date))
        rows = await asyncio.to_thread(cursor.fetchall)

        discounts = [dict(row) for row in rows]

        max_discount_percentage = 0.0
        avg_discount_percentage = 0.0
        total_discount_amount = 0.0
        discount_cap = 10.0 # Example: 10% discount cap

        if discounts:
            max_discount_percentage = max(d['discount_percentage'] for d in discounts)
            avg_discount_percentage = sum(d['discount_percentage'] for d in discounts) / len(discounts)
            total_discount_amount = sum(d['discount_amount'] for d in discounts)

        cap_breach = max_discount_percentage > discount_cap

        return {
            "contract_id": contract_id,
            "period": {"start": start_date, "end": end_date},
            "discounts": discounts,
            "summary": {
                "max_discount_percentage": max_discount_percentage,
                "avg_discount_percentage": avg_discount_percentage,
                "total_discount_amount": total_discount_amount,
                "discount_cap": discount_cap,
                "cap_breach": cap_breach
            }
        }
    except Exception as e:
        logger.error("Failed to get discount data from SQLite", contract_id=contract_id, error=str(e))
        raise
    finally:
        if conn:
            await asyncio.to_thread(conn.close)


if __name__ == "__main__":
    import uvicorn
    port = int(settings.MCP_SERVER_PORT or 3001)
    uvicorn.run(
        "app.mcp.database_server:app",
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
