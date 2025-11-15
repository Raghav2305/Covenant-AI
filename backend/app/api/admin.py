"""
Admin API endpoints for administrative tasks.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import structlog

from app.core.database import get_db
from app.models.contract import Contract
from app.utils.vector_store import VectorStore
from app.services.contract_processor import ContractProcessor

logger = structlog.get_logger()
router = APIRouter()


@router.post("/reindex-all", status_code=200)
async def reindex_all_contracts(db: Session = Depends(get_db)):
    """
    Deletes all documents from the vector store and re-indexes all existing contracts.
    This is a safe way to rebuild the search index after a model change.
    """
    logger.warning("Starting full re-indexing process for all contracts.")
    
    try:
        vector_store = VectorStore()
        contract_processor = ContractProcessor()

        # 1. Wipe the existing vector store collection
        logger.info("Deleting all existing documents from Weaviate...")
        await vector_store.delete_all_documents()
        logger.info("Vector store has been wiped and schema recreated.")

        # 2. Get all contracts from the PostgreSQL database
        contracts = db.query(Contract).all()
        if not contracts:
            return {"message": "No contracts found in the database to re-index."}
        
        logger.info(f"Found {len(contracts)} contracts to re-index.")

        # 3. Loop through each contract and re-index it
        indexed_count = 0
        for contract in contracts:
            try:
                # The index_contract method handles chunking and embedding
                await contract_processor.index_contract(contract, contract.obligations)
                indexed_count += 1
                logger.info(f"Successfully re-indexed contract: {contract.title} ({contract.id})")
            except Exception as e:
                logger.error(
                    "Failed to re-index a specific contract during the process.",
                    contract_id=contract.id,
                    error=str(e)
                )
        
        logger.warning(f"Re-indexing process completed. Successfully indexed {indexed_count} out of {len(contracts)} contracts.")
        return {
            "message": "Re-indexing process completed successfully.",
            "total_contracts_found": len(contracts),
            "contracts_reindexed": indexed_count,
        }

    except Exception as e:
        logger.error("A critical error occurred during the re-indexing process.", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
