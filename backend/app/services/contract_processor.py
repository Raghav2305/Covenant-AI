"""
Contract Processing Service
Handles contract ingestion, text extraction, and obligation extraction
"""

import asyncio
import json
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
import structlog
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.core.config import settings
from app.models.contract import Contract
from app.models.obligation import Obligation
from app.utils.llm_client import LLMClient
from app.utils.ocr_processor import OCRProcessor
from app.utils.simple_vector_store import SimpleVectorStore

logger = structlog.get_logger()


class ContractProcessor:
    """Main contract processing service"""
    
    def __init__(self):
        self.llm_client = LLMClient()
        self.ocr_processor = OCRProcessor()
        self.vector_store = SimpleVectorStore()
    
    async def process_contract(
        self, 
        file_path: str, 
        contract_data: Dict[str, Any], 
        db: Session
    ) -> Contract:
        """Process a contract file and extract obligations"""
        
        contract_id = uuid.uuid4()
        logger.info("Starting contract processing", contract_id=str(contract_id), file_path=file_path)
        
        try:
            # Step 1: Extract text from document
            extracted_text = await self.extract_text(file_path)
            logger.info("Text extraction completed", contract_id=str(contract_id), text_length=len(extracted_text))
            
            # Step 2: Create contract record
            contract = Contract(
                id=contract_id,
                title=contract_data.get("title", "Untitled Contract"),
                party_a=contract_data.get("party_a", ""),
                party_b=contract_data.get("party_b", ""),
                contract_type=contract_data.get("contract_type"),
                start_date=contract_data.get("start_date"),
                end_date=contract_data.get("end_date"),
                file_path=file_path,
                extracted_text=extracted_text,
                processing_status="processing"
            )
            
            db.add(contract)
            db.commit()
            db.refresh(contract)
            
            # Step 3: Extract obligations using LLM
            obligations_data = await self.extract_obligations(extracted_text, contract_data)
            logger.info("Obligation extraction completed", 
                       contract_id=str(contract_id), 
                       obligation_count=len(obligations_data))
            
            # Step 4: Create obligation records
            created_obligations = []
            for i, obligation_data in enumerate(obligations_data):
                obligation = await self.create_obligation(
                    contract_id, obligation_data, i + 1, db
                )
                created_obligations.append(obligation)
            
            # Step 5: Index contract and obligations in vector store
            await self.index_contract(contract, created_obligations)
            
            # Step 6: Update contract status
            contract.processing_status = "completed"
            contract.updated_at = datetime.now()
            db.commit()
            
            logger.info("Contract processing completed successfully", 
                       contract_id=str(contract_id),
                       obligation_count=len(created_obligations))
            
            return contract
            
        except Exception as e:
            logger.error("Contract processing failed", 
                        contract_id=str(contract_id), 
                        error=str(e))
            
            # Update contract with error status
            if 'contract' in locals():
                contract.processing_status = "failed"
                contract.processing_error = str(e)
                db.commit()
            
            raise
    
    async def extract_text(self, file_path: str) -> str:
        """Extract text from contract file"""
        try:
            # Determine file type and extract accordingly
            if file_path.lower().endswith('.pdf'):
                text = await self.ocr_processor.extract_from_pdf(file_path)
            elif file_path.lower().endswith(('.docx', '.doc')):
                text = await self.ocr_processor.extract_from_docx(file_path)
            elif file_path.lower().endswith('.txt'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
            else:
                raise ValueError(f"Unsupported file type: {file_path}")
            
            return text.strip()
            
        except Exception as e:
            logger.error("Text extraction failed", file_path=file_path, error=str(e))
            raise
    
    async def extract_obligations(self, text: str, contract_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract obligations from contract text using LLM"""
        
        prompt = self._build_extraction_prompt(text, contract_data)
        
        try:
            response = await self.llm_client.extract_obligations(prompt)
            obligations = self._parse_obligations_response(response)
            
            # Validate and clean obligations
            validated_obligations = []
            for obligation in obligations:
                if self._validate_obligation(obligation):
                    validated_obligations.append(self._clean_obligation(obligation))
            
            return validated_obligations
            
        except Exception as e:
            logger.error("Obligation extraction failed", error=str(e))
            raise
    
    def _build_extraction_prompt(self, text: str, contract_data: Dict[str, Any]) -> str:
        """Build prompt for obligation extraction"""
        
        return f"""
You are an expert contract analyst. Extract all obligations, deadlines, and financial terms from the following contract text.

Contract Information:
- Party A: {contract_data.get('party_a', 'Unknown')}
- Party B: {contract_data.get('party_b', 'Unknown')}
- Contract Type: {contract_data.get('contract_type', 'Unknown')}

Contract Text:
{text[:8000]}  # Limit text length for API

Please extract ALL obligations and return them in the following JSON format:
{{
    "obligations": [
        {{
            "party": "Party A or Party B",
            "obligation_type": "Report Submission|Payment|SLA|Compliance|Rebate|Discount|Other",
            "description": "Clear description of the obligation",
            "deadline": "YYYY-MM-DD or null if no specific deadline",
            "frequency": "Daily|Weekly|Monthly|Quarterly|Annually|One-time|null",
            "penalty_amount": "numeric amount or null",
            "penalty_currency": "INR|USD|EUR|etc",
            "rebate_amount": "numeric amount or null", 
            "rebate_currency": "INR|USD|EUR|etc",
            "condition": "Any conditions or triggers",
            "risk_level": "low|medium|high|critical"
        }}
    ]
}}

Focus on:
1. All deadlines and due dates
2. Financial penalties and rebates
3. Reporting requirements
4. SLA commitments
5. Compliance obligations
6. Discount caps and limits
7. Volume-based triggers

Return ONLY the JSON, no additional text.
"""
    
    def _parse_obligations_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse LLM response into obligation objects"""
        try:
            # Clean response and extract JSON
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:]
            if response.endswith('```'):
                response = response[:-3]
            
            data = json.loads(response)
            return data.get('obligations', [])
            
        except json.JSONDecodeError as e:
            logger.error("Failed to parse obligations response", response=response[:200], error=str(e))
            return []
    
    def _validate_obligation(self, obligation: Dict[str, Any]) -> bool:
        """Validate obligation data"""
        required_fields = ['party', 'obligation_type', 'description']
        
        for field in required_fields:
            if not obligation.get(field):
                logger.warning("Obligation missing required field", field=field, obligation=obligation)
                return False
        
        return True
    
    def _clean_obligation(self, obligation: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and standardize obligation data"""
        cleaned = {}
        
        # Required fields
        cleaned['party'] = str(obligation.get('party', '')).strip()
        cleaned['obligation_type'] = str(obligation.get('obligation_type', 'Other')).strip()
        cleaned['description'] = str(obligation.get('description', '')).strip()
        
        # Optional fields with defaults
        cleaned['deadline'] = self._parse_date(obligation.get('deadline'))
        cleaned['frequency'] = str(obligation.get('frequency', '')).strip() or None
        cleaned['penalty_amount'] = self._parse_amount(obligation.get('penalty_amount'))
        cleaned['penalty_currency'] = str(obligation.get('penalty_currency', 'INR')).strip()
        cleaned['rebate_amount'] = self._parse_amount(obligation.get('rebate_amount'))
        cleaned['rebate_currency'] = str(obligation.get('rebate_currency', 'INR')).strip()
        cleaned['condition'] = str(obligation.get('condition', '')).strip() or None
        cleaned['risk_level'] = str(obligation.get('risk_level', 'medium')).strip().lower()
        
        # Validate risk level
        if cleaned['risk_level'] not in ['low', 'medium', 'high', 'critical']:
            cleaned['risk_level'] = 'medium'
        
        return cleaned
    
    def _parse_date(self, date_str: Any) -> Optional[datetime]:
        """Parse date string to datetime object"""
        if not date_str:
            return None
        
        try:
            if isinstance(date_str, str):
                # Try common date formats
                for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y-%m-%d %H:%M:%S']:
                    try:
                        return datetime.strptime(date_str, fmt)
                    except ValueError:
                        continue
            return None
        except Exception:
            return None
    
    def _parse_amount(self, amount: Any) -> Optional[float]:
        """Parse amount string to float"""
        if not amount:
            return None
        
        try:
            if isinstance(amount, (int, float)):
                return float(amount)
            elif isinstance(amount, str):
                # Remove currency symbols and commas
                cleaned = amount.replace(',', '').replace('₹', '').replace('$', '').replace('€', '')
                return float(cleaned)
            return None
        except (ValueError, TypeError):
            return None
    
    async def create_obligation(
        self, 
        contract_id: uuid.UUID, 
        obligation_data: Dict[str, Any], 
        sequence_number: int,
        db: Session
    ) -> Obligation:
        """Create obligation record in database"""
        
        obligation_id = f"O-{contract_id.hex[:8]}-{sequence_number:03d}"
        
        obligation = Obligation(
            contract_id=contract_id,
            obligation_id=obligation_id,
            party=obligation_data['party'],
            obligation_type=obligation_data['obligation_type'],
            description=obligation_data['description'],
            deadline=obligation_data.get('deadline'),
            frequency=obligation_data.get('frequency'),
            penalty_amount=obligation_data.get('penalty_amount'),
            penalty_currency=obligation_data.get('penalty_currency', 'INR'),
            rebate_amount=obligation_data.get('rebate_amount'),
            rebate_currency=obligation_data.get('rebate_currency', 'INR'),
            condition=obligation_data.get('condition'),
            risk_level=obligation_data.get('risk_level', 'medium')
        )
        
        db.add(obligation)
        db.commit()
        db.refresh(obligation)
        
        return obligation
    
    async def index_contract(self, contract: Contract, obligations: List[Obligation]):
        """Index contract and obligations in vector store for RAG"""
        try:
            # Index contract text
            await self.vector_store.add_document(
                doc_id=str(contract.id),
                content=contract.extracted_text,
                metadata={
                    "type": "contract",
                    "title": contract.title,
                    "party_a": contract.party_a,
                    "party_b": contract.party_b,
                    "contract_type": contract.contract_type
                }
            )
            
            # Index obligations
            for obligation in obligations:
                await self.vector_store.add_document(
                    doc_id=str(obligation.id),
                    content=f"{obligation.description} {obligation.condition or ''}",
                    metadata={
                        "type": "obligation",
                        "contract_id": str(contract.id),
                        "obligation_id": obligation.obligation_id,
                        "party": obligation.party,
                        "obligation_type": obligation.obligation_type,
                        "deadline": obligation.deadline.isoformat() if obligation.deadline else None,
                        "risk_level": obligation.risk_level
                    }
                )
            
            logger.info("Contract indexed in vector store", 
                       contract_id=str(contract.id),
                       obligation_count=len(obligations))
            
        except Exception as e:
            logger.error("Failed to index contract", 
                        contract_id=str(contract.id), 
                        error=str(e))
            # Don't raise - indexing failure shouldn't break contract processing
    
    async def reprocess_contract(self, contract_id: uuid.UUID, db: Session) -> Contract:
        """Reprocess an existing contract"""
        contract = db.query(Contract).filter(Contract.id == contract_id).first()
        if not contract:
            raise ValueError(f"Contract {contract_id} not found")
        
        logger.info("Reprocessing contract", contract_id=str(contract_id))
        
        # Delete existing obligations
        db.query(Obligation).filter(Obligation.contract_id == contract_id).delete()
        
        # Reprocess
        contract_data = {
            "title": contract.title,
            "party_a": contract.party_a,
            "party_b": contract.party_b,
            "contract_type": contract.contract_type,
            "start_date": contract.start_date,
            "end_date": contract.end_date
        }
        
        return await self.process_contract(contract.file_path, contract_data, db)
