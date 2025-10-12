"""
Simple Vector Store for RAG (without external dependencies)
"""

import json
import os
from typing import List, Dict, Any, Optional
import structlog
from app.core.config import settings

logger = structlog.get_logger()


class SimpleVectorStore:
    """Simple in-memory vector store for demo purposes"""
    
    def __init__(self):
        self.documents = {}
        self.initialized = False
    
    async def initialize(self):
        """Initialize vector store"""
        if self.initialized:
            return
        
        # Load existing documents if any
        await self._load_documents()
        self.initialized = True
        logger.info("Simple vector store initialized")
    
    async def _load_documents(self):
        """Load documents from file asynchronously"""
        try:
            docs_file = "data/vector_documents.json"
            if os.path.exists(docs_file):
                import aiofiles
                async with aiofiles.open(docs_file, mode="r", encoding="utf-8") as f:
                    content = await f.read()
                    self.documents = json.loads(content)
                logger.info(f"Loaded {len(self.documents)} documents from file")
        except json.JSONDecodeError as e:
            logger.error("Error decoding JSON from vector store file", file=docs_file, error=str(e))
            self.documents = {}
        except Exception as e:
            logger.error("Failed to load documents", error=str(e))
            self.documents = {}
    
    async def _save_documents(self):
        """Save documents to file asynchronously"""
        try:
            docs_file = "data/vector_documents.json"
            os.makedirs(os.path.dirname(docs_file), exist_ok=True)
            import aiofiles
            async with aiofiles.open(docs_file, mode="w", encoding="utf-8") as f:
                await f.write(json.dumps(self.documents, indent=2, ensure_ascii=False))
            logger.info("Documents saved to file", file=docs_file, count=len(self.documents))
        except Exception as e:
            logger.error("Failed to save documents", error=str(e))
            raise # Re-raise the exception to make it visible
    
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
            # Simple keyword-based indexing
            keywords = self._extract_keywords(content)
            
            self.documents[doc_id] = {
                "content": content,
                "metadata": metadata,
                "keywords": keywords,
                "doc_id": doc_id
            }
            
            await self._save_documents()
            logger.info("Document added to simple vector store", doc_id=doc_id)
            return True
            
        except Exception as e:
            logger.error("Failed to add document", doc_id=doc_id, error=str(e))
            return False
    
    def _extract_keywords(self, content: str) -> List[str]:
        """Extract keywords from content"""
        # Simple keyword extraction
        words = content.lower().split()
        # Filter out common words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should'}
        keywords = [word for word in words if len(word) > 3 and word not in stop_words]
        return list(set(keywords))[:20]  # Limit to 20 keywords
    
    async def search_documents(
        self, 
        query: str, 
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search documents using keyword matching"""
        if not self.initialized:
            await self.initialize()
        
        try:
            query_keywords = self._extract_keywords(query)
            
            # Step 1: Filter documents based on metadata filters
            candidate_documents = []
            for doc_id, doc_data in self.documents.items():
                if filters:
                    if not self._matches_filters(doc_data, filters):
                        continue
                candidate_documents.append(doc_data)

            # Step 2: Calculate relevance score for candidate documents
            results = []
            for doc_data in candidate_documents:
                score = self._calculate_relevance_score(query_keywords, doc_data["keywords"])
                
                # Even if score is 0, if it passed filters, include it.
                # The LLM can decide relevance from content.
                result = {
                    "content": doc_data["content"],
                    "doc_id": doc_data["doc_id"],
                    "metadata": doc_data["metadata"],
                    "similarity": score / 100.0  # Normalize to 0-1
                }
                results.append(result)
            
            # Sort by relevance (highest score first)
            results.sort(key=lambda x: x["similarity"], reverse=True)
            
            return results[:limit]
            
        except Exception as e:
            logger.error("Document search failed", query=query[:100], error=str(e))
            return []
    
    def _matches_filters(self, doc_data: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check if document matches filters"""
        metadata = doc_data.get("metadata", {})
        
        for key, value in filters.items():
            logger.debug("Checking filter", doc_id=doc_data.get("doc_id"), filter_key=key, filter_value=value, doc_metadata_value=metadata.get(key))
            if key in metadata:
                if isinstance(value, list):
                    if metadata[key] not in value:
                        logger.debug("Filter mismatch (list)", doc_id=doc_data.get("doc_id"), filter_key=key, filter_value=value, doc_metadata_value=metadata.get(key))
                        return False
                else:
                    if metadata[key] != value:
                        logger.debug("Filter mismatch (single)", doc_id=doc_data.get("doc_id"), filter_key=key, filter_value=value, doc_metadata_value=metadata.get(key))
                        return False
            else:
                logger.debug("Filter key not in metadata", doc_id=doc_data.get("doc_id"), filter_key=key)
                return False
        
        return True
    
    def _calculate_relevance_score(self, query_keywords: List[str], doc_keywords: List[str]) -> float:
        """Calculate relevance score based on keyword overlap"""
        if not query_keywords or not doc_keywords:
            return 0.0
        
        # Count matching keywords
        matches = sum(1 for keyword in query_keywords if keyword in doc_keywords)
        
        # Calculate score as percentage of query keywords matched
        score = (matches / len(query_keywords)) * 100
        
        return score
    
    async def get_similar_obligations(
        self, 
        obligation_description: str, 
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Find similar obligations"""
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
        """Get contract context"""
        filters = {"doc_type": "contract"}
        
        if contract_id:
            filters["contract_id"] = contract_id
        
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
            if doc_id in self.documents:
                del self.documents[doc_id]
                self._save_documents()
                logger.info("Document deleted from simple vector store", doc_id=doc_id)
                return True
            
            logger.warning("Document not found for deletion", doc_id=doc_id)
            return False
            
        except Exception as e:
            logger.error("Failed to delete document", doc_id=doc_id, error=str(e))
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics"""
        if not self.initialized:
            await self.initialize()
        
        return {
            "total_documents": len(self.documents),
            "status": "connected",
            "type": "simple_in_memory"
        }
