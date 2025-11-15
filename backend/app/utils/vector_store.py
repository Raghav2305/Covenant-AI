import weaviate
import structlog
from typing import List, Dict, Any, Optional

from app.core.config import settings
from app.utils.llm_client import LLMClient

logger = structlog.get_logger()

class VectorStore:
    """Vector database for semantic search and RAG using weaviate-client v3"""

    def __init__(self):
        self.client = weaviate.Client(
            url=settings.VECTOR_DB_URL,
            timeout_config=(5, 15)
        )
        self.llm_client = LLMClient()
        self.collection_name = "ContractDocument"

    async def setup_schema(self):
        """Create Weaviate schema for documents if it doesn't exist."""
        try:
            if self.client.schema.exists(self.collection_name):
                logger.info("Weaviate schema already exists", collection=self.collection_name)
                return

            schema = {
                "class": self.collection_name,
                "description": "Documents for contract analysis",
                "vectorizer": "none",
                "properties": [
                    {"name": "content", "dataType": ["text"]},
                    {"name": "doc_id", "dataType": ["string"], "tokenization": "word"},
                    {"name": "doc_type", "dataType": ["string"], "tokenization": "word"},
                    {"name": "contract_id", "dataType": ["string"], "tokenization": "word"},
                    {"name": "title", "dataType": ["string"]},
                    {"name": "party", "dataType": ["string"], "tokenization": "word"},
                ]
            }
            self.client.schema.create_class(schema)
            logger.info("Weaviate schema created", collection=self.collection_name)
        except Exception as e:
            logger.error("Failed to set up Weaviate schema", error=str(e))
            raise

    async def add_document(self, doc_id: str, content: str, metadata: Dict[str, Any]) -> str:
        """Generate embedding and add document to Weaviate."""
        if not content.strip():
            logger.warning("Skipping document with empty content", doc_id=doc_id)
            return ""

        try:
            vector = await self.llm_client.get_embedding(content)
        except Exception as e:
            logger.error("Failed to generate embedding", doc_id=doc_id, error=str(e))
            return ""

        properties = {
            "content": content,
            "doc_id": doc_id,
            **metadata
        }

        try:
            uuid = self.client.data_object.create(
                data_object=properties,
                class_name=self.collection_name,
                vector=vector
            )
            logger.info("Document added to Weaviate", doc_id=doc_id, weaviate_uuid=uuid)
            return str(uuid)
        except Exception as e:
            logger.error("Failed to add document to Weaviate", doc_id=doc_id, error=str(e))
            return ""

    def _build_where_filter(self, filters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Build a Weaviate v3 'where' filter from a dictionary."""
        if not filters:
            return None
        
        operands = []
        for key, value in filters.items():
            operands.append({
                "path": [key],
                "operator": "Equal",
                "valueString": str(value)
            })

        if not operands:
            return None
        
        return {
            "operator": "And",
            "operands": operands
        }

    async def search_documents(self, query: str, limit: int = 10, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Perform a semantic search in Weaviate with an optional metadata filter."""
        try:
            query_vector = await self.llm_client.get_embedding(query)
        except Exception as e:
            logger.error("Failed to generate query embedding", query=query[:100], error=str(e))
            return []

        near_vector = {"vector": query_vector}

        query_builder = (
            self.client.query
            .get(self.collection_name, ["content", "doc_id", "doc_type", "contract_id", "title", "party"])
            .with_near_vector(near_vector)
            .with_limit(limit)
            .with_additional(["distance"])
        )

        if filters:
            where_filter = self._build_where_filter(filters)
            if where_filter:
                query_builder = query_builder.with_where(where_filter)

        try:
            response = query_builder.do()
            results = response.get("data", {}).get("Get", {}).get(self.collection_name, [])

            processed_results = []
            for item in results:
                processed_results.append({
                    "content": item.get("content"),
                    "metadata": {
                        "doc_id": item.get("doc_id"),
                        "doc_type": item.get("doc_type"),
                        "contract_id": item.get("contract_id"),
                        "title": item.get("title"),
                        "party": item.get("party"),
                    },
                    "similarity": 1 - item["_additional"]["distance"]
                })
            return processed_results
        except Exception as e:
            logger.error("Weaviate search failed", query=query[:100], error=str(e))
            return []

    async def delete_all_documents(self):
        """Delete all schemas and data from Weaviate. Use with caution."""
        try:
            self.client.schema.delete_all()
            logger.info("Deleted all Weaviate schemas and data.")
            await self.setup_schema()
        except Exception as e:
            logger.error("Failed to delete all documents", error=str(e))
