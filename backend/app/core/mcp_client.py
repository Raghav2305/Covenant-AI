"""
MCP (Model Context Protocol) Client Manager
Handles connections to MCP servers for live data access
"""

import asyncio
import httpx
import json
from typing import Dict, Any, Optional, List
import structlog
from app.core.config import settings

logger = structlog.get_logger()


class MCPClient:
    """Individual MCP client for connecting to a specific MCP server"""
    
    def __init__(self, server_url: str, client_id: str):
        self.server_url = server_url
        self.client_id = client_id
        self.client = httpx.AsyncClient(timeout=30.0)
        self.connected = False
    
    async def connect(self) -> bool:
        """Connect to MCP server"""
        logger.info("Attempting to connect to MCP server", server_url=self.server_url)
        try:
            response = await self.client.post(
                f"{self.server_url}/connect",
                json={"client_id": self.client_id}
            )
            response.raise_for_status()
            self.connected = True
            logger.info("Connected to MCP server", server_url=self.server_url)
            return True
        except Exception as e:
            logger.error("Failed to connect to MCP server", 
                        server_url=self.server_url, error=str(e))
            return False
    
    async def query(self, query_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send query to MCP server"""
        if not self.connected:
            await self.connect()
        
        try:
            response = await self.client.post(
                f"{self.server_url}/query",
                json={
                    "query_type": query_type,
                    "params": params,
                    "client_id": self.client_id
                }
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("MCP query failed", 
                        server_url=self.server_url, 
                        query_type=query_type, 
                        error=str(e))
            raise
    
    async def get_schema(self) -> Dict[str, Any]:
        """Get MCP server schema"""
        try:
            response = await self.client.get(f"{self.server_url}/schema")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("Failed to get MCP schema", 
                        server_url=self.server_url, error=str(e))
            raise
    
    async def disconnect(self):
        """Disconnect from MCP server"""
        try:
            await self.client.post(
                f"{self.server_url}/disconnect",
                json={"client_id": self.client_id}
            )
            self.connected = False
            logger.info("Disconnected from MCP server", server_url=self.server_url)
        except Exception as e:
            logger.error("Error disconnecting from MCP server", 
                        server_url=self.server_url, error=str(e))
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


class MCPClientManager:
    """Manages multiple MCP client connections"""
    
    def __init__(self):
        self.clients: Dict[str, MCPClient] = {}
        self.initialized = False
    
    async def initialize(self):
        """Initialize all MCP clients"""
        if self.initialized:
            return
        
        # Initialize database connector
        self.clients["database"] = MCPClient(
            settings.MCP_DATABASE_CONNECTOR_URL,
            settings.MCP_CLIENT_ID
        )
        
        # Initialize CRM connector
        # self.clients["crm"] = MCPClient(
        #     settings.MCP_CRM_CONNECTOR_URL,
        #     settings.MCP_CLIENT_ID
        # )
        
        # Initialize finance connector
        # self.clients["finance"] = MCPClient(
        #     settings.MCP_FINANCE_CONNECTOR_URL,
        #     settings.MCP_CLIENT_ID
        # )
        
        # Connect to all servers
        connection_tasks = [
            client.connect() for client in self.clients.values()
        ]
        await asyncio.gather(*connection_tasks, return_exceptions=True)
        
        self.initialized = True
        logger.info("MCP client manager initialized", 
                   client_count=len(self.clients))
    
    async def query_database(self, query: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Query database via MCP"""
        if "database" not in self.clients:
            raise ValueError("Database MCP client not initialized")
        
        return await self.clients["database"].query("database_query", {
            "query": query,
            "params": params or {}
        })
    
    async def query_crm(self, query_type: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Query CRM system via MCP"""
        if "crm" not in self.clients:
            raise ValueError("CRM MCP client not initialized")
        
        return await self.clients["crm"].query(query_type, params or {})
    
    async def query_finance(self, query_type: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Query finance system via MCP"""
        if "finance" not in self.clients:
            raise ValueError("Finance MCP client not initialized")
        
        return await self.clients["finance"].query(query_type, params or {})
    
    async def get_live_transaction_data(self, customer_id: str, date_range: Dict[str, str]) -> Dict[str, Any]:
        """Get live transaction data for obligation monitoring"""
        return await self.query_database(
            """
            SELECT transaction_id, amount, transaction_date, customer_id, transaction_type
            FROM transactions 
            WHERE customer_id = :customer_id 
            AND transaction_date BETWEEN :start_date AND :end_date
            ORDER BY transaction_date DESC
            """,
            {
                "customer_id": customer_id,
                "start_date": date_range["start"],
                "end_date": date_range["end"]
            }
        )
    
    async def get_customer_volume(self, customer_id: str, period: str) -> Dict[str, Any]:
        """Get customer transaction volume for rebate calculations"""
        return await self.query_database(
            """
            SELECT COUNT(*) as transaction_count, SUM(amount) as total_amount
            FROM transactions 
            WHERE customer_id = :customer_id 
            AND transaction_date >= :period_start
            """,
            {
                "customer_id": customer_id,
                "period_start": period
            }
        )
    
    async def get_discount_data(self, customer_id: str, date_range: Dict[str, str]) -> Dict[str, Any]:
        """Get discount data for cap monitoring"""
        return await self.query_database(
            """
            SELECT discount_percentage, discount_amount, transaction_date
            FROM transactions 
            WHERE customer_id = :customer_id 
            AND discount_percentage > 0
            AND transaction_date BETWEEN :start_date AND :end_date
            """,
            {
                "customer_id": customer_id,
                "start_date": date_range["start"],
                "end_date": date_range["end"]
            }
        )
    
    async def cleanup(self):
        """Cleanup all MCP connections"""
        cleanup_tasks = [
            client.disconnect() for client in self.clients.values()
        ]
        await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        close_tasks = [
            client.close() for client in self.clients.values()
        ]
        await asyncio.gather(*close_tasks, return_exceptions=True)
        
        self.clients.clear()
        self.initialized = False
        logger.info("MCP client manager cleaned up")


# Global MCP client manager instance
mcp_manager: Optional[MCPClientManager] = None


async def get_mcp_manager() -> MCPClientManager:
    """Get global MCP client manager instance"""
    global mcp_manager
    if mcp_manager is None:
        mcp_manager = MCPClientManager()
        await mcp_manager.initialize()
    return mcp_manager
