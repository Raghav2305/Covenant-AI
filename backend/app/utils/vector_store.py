"""
Vector Store for RAG (Retrieval Augmented Generation)
"""

import asyncio
import json
from typing import List, Dict, Any, Optional
import structlog
import weaviate
from sentence_transformers import SentenceTransformer
from app.core.config import settings

logger = structlog.get_logger()


class VectorStore:
    """Vector database for semantic search and RAG"""
    
    def __init__(self):
        self.client = None
        self.embedding_model = None
        self.initialized = False
    
    async def initialize(self):
        """Initialize vector store connection"""
        if self.initialized:
            return
        
        try:
            # Initialize Weaviate client
            self.client = weaviate.Client(
                url=settings.VECTOR_DB_URL,
                timeout_config=(5, 15)  # (connect timeout, read timeout)
            )
            
            # Initialize embedding model
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Create schema if it doesn't exist
            await self._create_schema()
            
            self.initialized = True
            logger.info("Vector store initialized successfully")
            
        except Exception as e:
            logger.error("Vector store initialization failed", error=str(e))
            raise
    
    async def _create_schema(self):
        """Create Weaviate schema for documents"""
        try:
            # Check if schema already exists
            if self.client.schema.exists("ContractDocument"):
                logger.info("Schema already exists")
                return
            
            # Create schema
            schema = {
                "class": "ContractDocument",
                "description": "Contract and obligation documents for semantic search",
                "vectorizer": "none",  # We'll provide our own embeddings
                "properties": [
                    {
                        "name": "content",
                        "dataType": ["text"],
                        "description": "Document content"
                    },
                    {
                        "name": "doc_id",
                        "dataType": ["string"],
                        "description": "Document ID"
                    },
                    {
                        "name": "doc_type",
                        "dataType": ["string"],
                        "description": "Document type (contract, obligation)"
                    },
                    {
                        "name": "title",
                        "dataType": ["string"],
                        "description": "Document title"
                    },
                    {
                        "name": "party_a",
                        "dataType": ["string"],
                        "description": "Contract party A"
                    },
                    {
                        "name": "party_b",
                        "dataType": ["string"],
                        "description": "Contract party B"
                    },
                    {
                        "name": "contract_type",
                        "dataType": ["string"],
                        "description": "Type of contract"
                    },
                    {
                        "name": "obligation_type",
                        "dataType": ["string"],
                        "description": "Type of obligation"
                    },
                    {
                        "name": "deadline",
                        "dataType": ["date"],
                        "description": "Obligation deadline"
                    },
                    {
                        "name": "risk_level",
                        "dataType": ["string"],
                        "description": "Risk level"
                    },
                    {
                        "name": "metadata",
                        "dataType": ["object"],
                        "description": "Additional metadata"
                    }
                ]
            }
            
            self.client.schema.create_class(schema)
            logger.info("Vector store schema created")
            
        except Exception as e:
            logger.error("Schema creation failed", error=str(e))
            raise
    
    async def add_document(
        self, 
        doc_id: str, 
        content: str, 
        metadata: Dict[str, Any]
    ) -> bool:
        """Add document to vector store"""
        if not self.initialized:
            await self.initialize()
        
        try:
            # Generate embedding
            embedding = self.embedding_model.encode(content).tolist()
            
            # Prepare document data
            doc_data = {
                "content": content,
                "doc_id": doc_id,
                "doc_type": metadata.get("type", "unknown"),
                "title": metadata.get("title", ""),
                "party_a": metadata.get("party_a", ""),
                "party_b": metadata.get("party_b", ""),
                "contract_type": metadata.get("contract_type", ""),
                "obligation_type": metadata.get("obligation_type", ""),
                "deadline": metadata.get("deadline"),
                "risk_level": metadata.get("risk_level", ""),
                "metadata": metadata
            }
            
            # Add to Weaviate
            self.client.data_object.create(
                data_object=doc_data,
                class_name="ContractDocument",
                vector=embedding
            )
            
            logger.info("Document added to vector store", doc_id=doc_id, doc_type=metadata.get("type"))
            return True
            
        except Exception as e:
            logger.error("Failed to add document to vector store", doc_id=doc_id, error=str(e))
            return False
    
    async def search_documents(
        self, 
        query: str, 
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search documents using semantic similarity"""
        if not self.initialized:
            await self.initialize()
        
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode(query).tolist()
            
            # Build search query
            search_query = {
                "vector": query_embedding,
                "limit": limit,
                "with_metadata": True
            }
            
            # Add filters if provided
            if filters:
                where_filter = self._build_where_filter(filters)
                if where_filter:
                    search_query["where"] = where_filter
            
            # Perform search
            result = self.client.query.get(
                "ContractDocument",
                ["content", "doc_id", "doc_type", "title", "party_a", "party_b", 
                 "contract_type", "obligation_type", "deadline", "risk_level", "metadata"]
            ).with_near_vector(search_query).do()
            
            # Process results
            documents = []
            if "data" in result and "Get" in result["data"]:
                for item in result["data"]["Get"]["ContractDocument"]:
                    doc = {
                        "content": item.get("content", ""),
                        "doc_id": item.get("doc_id", ""),
                        "doc_type": item.get("doc_type", ""),
                        "title": item.get("title", ""),
                        "party_a": item.get("party_a", ""),
                        "party_b": item.get("party_b", ""),
                        "contract_type": item.get("contract_type", ""),
                        "obligation_type": item.get("obligation_type", ""),
                        "deadline": item.get("deadline"),
                        "risk_level": item.get("risk_level", ""),
                        "metadata": item.get("metadata", {}),
                        "similarity": item.get("_additional", {}).get("certainty", 0)
                    }
                    documents.append(doc)
            
            logger.info("Document search completed", 
                       query=query[:100], 
                       results_count=len(documents))
            
            return documents
            
        except Exception as e:
            logger.error("Document search failed", query=query[:100], error=str(e))
            return []
    
    def _build_where_filter(self, filters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Build Weaviate where filter from filters dict"""
        if not filters:
            return None
        
        conditions = []
        
        for key, value in filters.items():
            if value is not None:
                if isinstance(value, list):
                    # OR condition for list values
                    or_conditions = []
                    for v in value:
                        or_conditions.append({
                            "path": [key],
                            "operator": "Equal",
                            "valueString": str(v)
                        })
                    conditions.append({
                        "operator": "Or",
                        "operands": or_conditions
                    })
                else:
                    conditions.append({
                        "path": [key],
                        "operator": "Equal",
                        "valueString": str(value)
                    })
        
        if len(conditions) == 1:
            return conditions[0]
        elif len(conditions) > 1:
            return {
                "operator": "And",
                "operands": conditions
            }
        
        return None
    
    async def get_similar_obligations(
        self, 
        obligation_description: str, 
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Find similar obligations for compliance checking"""
        return await self.search_documents(
            query=obligation_description,
            limit=limit,
            filters={"doc_type": "obligation"}
        )
    
    async def get_contract_context(
        self, 
        contract_id: str, 
        query: str = ""
    ) -> List[Dict[str, Any]]:
        """Get contract context for copilot queries"""
        filters = {"doc_type": "contract"}
        
        if contract_id:
            # This would need to be implemented based on how contract_id is stored
            pass
        
        return await self.search_documents(
            query=query or "contract obligations terms conditions",
            limit=10,
            filters=filters
        )
    
    async def delete_document(self, doc_id: str) -> bool:
        """Delete document from vector store"""
        if not self.initialized:
            await self.initialize()
        
        try:
            # Find document by doc_id
            result = self.client.query.get(
                "ContractDocument",
                ["doc_id"]
            ).with_where({
                "path": ["doc_id"],
                "operator": "Equal",
                "valueString": doc_id
            }).do()
            
            if "data" in result and "Get" in result["data"]:
                documents = result["data"]["Get"]["ContractDocument"]
                if documents:
                    # Delete the document
                    self.client.data_object.delete(
                        uuid=documents[0]["_additional"]["id"],
                        class_name="ContractDocument"
                    )
                    logger.info("Document deleted from vector store", doc_id=doc_id)
                    return True
            
            logger.warning("Document not found for deletion", doc_id=doc_id)
            return False
            
        except Exception as e:
            logger.error("Failed to delete document from vector store", doc_id=doc_id, error=str(e))
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics"""
        if not self.initialized:
            await self.initialize()
        
        try:
            # Get total document count
            result = self.client.query.aggregate("ContractDocument").with_meta_count().do()
            
            total_docs = 0
            if "data" in result and "Aggregate" in result["data"]:
                total_docs = result["data"]["Aggregate"]["ContractDocument"][0]["meta"]["count"]
            
            return {
                "total_documents": total_docs,
                "status": "connected",
                "embedding_model": "all-MiniLM-L6-v2"
            }
            
        except Exception as e:
            logger.error("Failed to get vector store stats", error=str(e))
            return {
                "total_documents": 0,
                "status": "error",
                "error": str(e)
            }
