"""
LLM Client for OpenAI integration
"""

import asyncio
import json
from typing import Dict, Any, List, Optional
import structlog
from openai import AsyncOpenAI
from app.core.config import settings

logger = structlog.get_logger()


class LLMClient:
    """OpenAI LLM client for contract processing"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
        self.embedding_model = "text-embedding-3-small"

    async def get_embedding(self, text: str) -> List[float]:
        """Generate embedding for a given text."""
        try:
            text = text.replace("\n", " ")
            response = await self.client.embeddings.create(input=[text], model=self.embedding_model)
            return response.data[0].embedding
        except Exception as e:
            logger.error("Failed to create embedding", text=text[:100], error=str(e))
            raise

    async def extract_obligations(self, prompt: str) -> str:
        """Extract obligations from contract text"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert contract analyst specializing in extracting obligations, deadlines, and financial terms from legal documents. Always respond with valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,  # Low temperature for consistent extraction
                max_tokens=4000
            )
            
            content = response.choices[0].message.content
            logger.info("LLM obligation extraction completed", 
                       model=self.model, 
                       response_length=len(content))
            
            return content
            
        except Exception as e:
            logger.error("LLM obligation extraction failed", error=str(e))
            raise
    
    async def analyze_obligation_compliance(
        self, 
        obligation_description: str, 
        live_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze obligation compliance using live data"""
        
        prompt = f"""
Analyze the compliance status of this obligation based on the provided live data.

Obligation: {obligation_description}

Live Data: {json.dumps(live_data, indent=2)}

Determine:
1. Is the obligation being met?
2. What evidence supports this conclusion?
3. What is the risk level?
4. Are there any violations or breaches?

Respond in JSON format:
{{
    "compliant": true/false,
    "compliance_status": "compliant|non_compliant|at_risk|unknown",
    "evidence": "description of evidence",
    "risk_level": "low|medium|high|critical",
    "violations": ["list of any violations"],
    "recommendations": ["list of recommendations"]
}}
"""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a compliance analyst. Analyze obligation compliance based on live data and provide structured insights."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content
            return json.loads(content)
            
        except Exception as e:
            logger.error("LLM compliance analysis failed", error=str(e))
            return {
                "compliant": False,
                "compliance_status": "unknown",
                "evidence": "Analysis failed",
                "risk_level": "medium",
                "violations": [],
                "recommendations": ["Manual review required"]
            }
    
    async def generate_copilot_response(
        self, 
        query: str, 
        context_documents: List[Dict[str, Any]]
    ) -> str:
        """Generate natural language response for copilot queries"""
        
        context_text = ""
        for doc in context_documents:
            doc_type = doc.get('metadata', {}).get('type', 'Unknown')
            doc_identifier = ""
            if doc_type == 'contract':
                doc_identifier = doc.get('metadata', {}).get('title', 'Contract')
            elif doc_type == 'obligation':
                doc_identifier = doc.get('metadata', {}).get('obligation_id', 'Obligation')
                if doc.get('metadata', {}).get('description'):
                    doc_identifier += f": {doc.get('metadata', {}).get('description')}"
            else:
                doc_identifier = doc.get('id', 'Document') # Fallback to doc_id or generic

            context_text += f"Document Type: {doc_type}\nIdentifier: {doc_identifier}\nContent: {doc.get('content', '')}\n\n"
        
        prompt = f"""
You are an AI copilot for contract lifecycle management. Answer the user's question based on the provided contract and obligation context.

User Question: {query}

Context Documents:
{context_text}

Provide a helpful, accurate response that:
1. Directly answers the question
2. Cites specific contract clauses or obligations
3. Includes relevant deadlines, amounts, or conditions
4. Offers actionable insights when appropriate
5. **Uses Markdown for clear formatting (e.g., bullet points, bold text, newlines).**

Be conversational but professional. If you cannot find relevant information, say so clearly.
"""
        
        logger.info("LLM copilot prompt generated", query=query[:100], context_documents_count=len(context_documents), prompt_length=len(prompt), full_prompt=prompt) # Add this line
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful AI assistant for contract management. Provide accurate, cited responses based on contract data."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=700, # Reduced max_tokens
                timeout=30.0 # Added timeout
            )
            logger.debug("OpenAI API call successful, processing response.") # New log
            
            logger.info("LLM raw copilot response", raw_response=response.choices[0].message.content)
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error("LLM copilot response failed", error=str(e))
            return "I apologize, but I'm unable to process your request at the moment. Please try again later."
    
    async def generate_alert_message(
        self, 
        alert_type: str, 
        obligation_data: Dict[str, Any],
        compliance_data: Dict[str, Any]
    ) -> str:
        """Generate human-readable alert message"""
        
        prompt = f"""
Generate a clear, actionable alert message for this contract obligation issue.

Alert Type: {alert_type}
Obligation: {obligation_data.get('description', 'Unknown')}
Party: {obligation_data.get('party', 'Unknown')}
Deadline: {obligation_data.get('deadline', 'Not specified')}
Risk Level: {obligation_data.get('risk_level', 'medium')}

Compliance Data: {json.dumps(compliance_data, indent=2)}

Create a message that:
1. Clearly states the issue
2. Explains the potential impact
3. Suggests immediate actions
4. Includes relevant contract details

Keep it concise but informative.
"""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a contract management assistant. Generate clear, actionable alert messages for obligation issues."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.4,
                max_tokens=800
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error("LLM alert message generation failed", error=str(e))
            return f"Alert: {alert_type} - {obligation_data.get('description', 'Unknown obligation')} requires attention."
    
    async def summarize_contract(self, contract_text: str) -> Dict[str, Any]:
        """Generate contract summary"""
        
        prompt = f"""
Analyze this contract and provide a comprehensive summary.

Contract Text: {contract_text[:4000]}

Provide a JSON summary with:
{{
    "parties": ["list of main parties"],
    "contract_type": "type of contract",
    "key_obligations": ["list of main obligations"],
    "financial_terms": ["list of financial terms"],
    "risk_factors": ["list of risk factors"],
    "summary": "brief overall summary"
}}
"""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a contract analyst. Provide structured summaries of legal documents."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,
                max_tokens=1500
            )
            
            content = response.choices[0].message.content
            return json.loads(content)
            
        except Exception as e:
            logger.error("LLM contract summary failed", error=str(e))
            return {
                "parties": ["Unknown"],
                "contract_type": "Unknown",
                "key_obligations": ["Unable to extract"],
                "financial_terms": ["Unable to extract"],
                "risk_factors": ["Unable to assess"],
                "summary": "Contract analysis failed"
            }
