"""
Monitoring Engine for Real-time Obligation Tracking
Integrates with MCP for live data access
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import structlog
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.obligation import Obligation
from app.models.alert import Alert
from app.core.mcp_client import get_mcp_manager
from app.utils.llm_client import LLMClient

logger = structlog.get_logger()


class MonitoringEngine:
    """Real-time obligation monitoring engine"""
    
    def __init__(self):
        self.llm_client = LLMClient()
        self.mcp_manager = None
    
    async def initialize(self):
        """Initialize monitoring engine"""
        self.mcp_manager = await get_mcp_manager()
        logger.info("Monitoring engine initialized")
    
    async def check_all_obligations(self, db: Session) -> Dict[str, Any]:
        """Check all active obligations for compliance"""
        if not self.mcp_manager:
            await self.initialize()
        
        logger.info("Starting comprehensive obligation check")
        
        # Get all active obligations
        obligations = db.query(Obligation).filter(
            Obligation.status == "active"
        ).all()
        
        results = {
            "total_checked": len(obligations),
            "compliant": 0,
            "non_compliant": 0,
            "at_risk": 0,
            "unknown": 0,
            "alerts_generated": 0,
            "obligations": []
        }
        
        for obligation in obligations:
            try:
                check_result = await self.check_obligation_compliance(obligation, db)
                results["obligations"].append(check_result)
                
                # Update counters
                compliance_status = check_result.get("compliance_status", "unknown")
                if compliance_status == "compliant":
                    results["compliant"] += 1
                elif compliance_status == "non_compliant":
                    results["non_compliant"] += 1
                elif compliance_status == "at_risk":
                    results["at_risk"] += 1
                else:
                    results["unknown"] += 1
                
                # Count alerts generated
                if check_result.get("alert_generated"):
                    results["alerts_generated"] += 1
                
            except Exception as e:
                logger.error("Failed to check obligation", 
                           obligation_id=str(obligation.id), 
                           error=str(e))
                results["unknown"] += 1
        
        logger.info("Comprehensive obligation check completed", **results)
        return results
    
    async def check_obligation_compliance(
        self, 
        obligation: Obligation, 
        db: Session
    ) -> Dict[str, Any]:
        """Check compliance for a specific obligation"""
        
        logger.info("Checking obligation compliance", 
                   obligation_id=str(obligation.id),
                   obligation_type=obligation.obligation_type)
        
        result = {
            "obligation_id": str(obligation.id),
            "obligation_type": obligation.obligation_type,
            "party": obligation.party,
            "compliance_status": "unknown",
            "evidence": {},
            "risk_level": obligation.risk_level,
            "alert_generated": False,
            "check_timestamp": datetime.now().isoformat()
        }
        
        try:
            # Get live data based on obligation type
            live_data = await self._get_live_data_for_obligation(obligation)
            
            # Analyze compliance using LLM
            compliance_analysis = await self.llm_client.analyze_obligation_compliance(
                obligation.description, 
                live_data
            )
            
            result.update(compliance_analysis)
            result["evidence"] = live_data
            
            # Update obligation record
            obligation.compliance_status = compliance_analysis["compliance_status"]
            obligation.compliance_evidence = live_data
            obligation.last_checked = datetime.now()
            
            # Check if alert should be generated
            if self._should_generate_alert(obligation, compliance_analysis):
                alert = await self._create_compliance_alert(
                    obligation, compliance_analysis, db
                )
                result["alert_generated"] = True
                result["alert_id"] = str(alert.id)
            
            # Update breach count if non-compliant
            if compliance_analysis["compliance_status"] == "non_compliant":
                obligation.breach_count += 1
                obligation.last_breach_date = datetime.now()
            
            db.commit()
            
            logger.info("Obligation compliance check completed",
                       obligation_id=str(obligation.id),
                       compliance_status=compliance_analysis["compliance_status"])
            
        except Exception as e:
            logger.error("Obligation compliance check failed",
                        obligation_id=str(obligation.id),
                        error=str(e))
            result["error"] = str(e)
        
        return result
    
    async def _get_live_data_for_obligation(self, obligation: Obligation) -> Dict[str, Any]:
        """Get relevant live data for obligation monitoring"""
        
        live_data = {
            "obligation_type": obligation.obligation_type,
            "party": obligation.party,
            "deadline": obligation.deadline.isoformat() if obligation.deadline else None,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Extract customer/party identifier from obligation
            customer_id = self._extract_customer_id(obligation)
            
            if not customer_id:
                logger.warning("Could not extract customer ID", 
                              obligation_id=str(obligation.id))
                return live_data
            
            # Get data based on obligation type
            if "discount" in obligation.obligation_type.lower():
                live_data.update(await self._get_discount_data(customer_id))
            elif "rebate" in obligation.obligation_type.lower():
                live_data.update(await self._get_rebate_data(customer_id))
            elif "volume" in obligation.obligation_type.lower():
                live_data.update(await self._get_volume_data(customer_id))
            elif "transaction" in obligation.obligation_type.lower():
                live_data.update(await self._get_transaction_data(customer_id))
            else:
                # General compliance data
                live_data.update(await self._get_general_compliance_data(customer_id))
            
        except Exception as e:
            logger.error("Failed to get live data", 
                       obligation_id=str(obligation.id), 
                       error=str(e))
            live_data["error"] = str(e)
        
        return live_data
    
    def _extract_customer_id(self, obligation: Obligation) -> Optional[str]:
        """Extract customer ID from obligation data"""
        # This is a simplified extraction - in reality, you'd have more sophisticated logic
        party = obligation.party.lower()
        
        # Look for common customer ID patterns
        if "cust" in party or "client" in party:
            # Extract ID from party name
            import re
            match = re.search(r'(cust|client)[-_]?(\d+)', party)
            if match:
                return f"CUST-{match.group(2)}"
        
        # Default mapping for demo
        party_mapping = {
            "client a": "CUST-001",
            "client b": "CUST-002", 
            "vendor x": "VEND-001",
            "partner y": "PART-001"
        }
        
        return party_mapping.get(party, "CUST-001")  # Default for demo
    
    async def _get_discount_data(self, customer_id: str) -> Dict[str, Any]:
        """Get discount data for cap monitoring"""
        try:
            date_range = {
                "start": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
                "end": datetime.now().strftime("%Y-%m-%d")
            }
            
            discount_data = await self.mcp_manager.get_discount_data(customer_id, date_range)
            return {
                "discount_data": discount_data,
                "max_discount_percentage": discount_data.get("summary", {}).get("max_discount_percentage", 0),
                "discount_cap_breach": discount_data.get("summary", {}).get("cap_breach", False)
            }
        except Exception as e:
            logger.error("Failed to get discount data", customer_id=customer_id, error=str(e))
            return {"discount_data": {}, "error": str(e)}
    
    async def _get_rebate_data(self, customer_id: str) -> Dict[str, Any]:
        """Get rebate data for volume-based triggers"""
        try:
            period_start = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
            
            volume_data = await self.mcp_manager.get_customer_volume(customer_id, period_start)
            return {
                "volume_data": volume_data,
                "transaction_count": volume_data.get("transaction_count", 0),
                "total_amount": volume_data.get("total_amount", 0),
                "rebate_eligible": volume_data.get("rebate_eligible", False)
            }
        except Exception as e:
            logger.error("Failed to get rebate data", customer_id=customer_id, error=str(e))
            return {"volume_data": {}, "error": str(e)}
    
    async def _get_volume_data(self, customer_id: str) -> Dict[str, Any]:
        """Get transaction volume data"""
        try:
            period_start = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            
            volume_data = await self.mcp_manager.get_customer_volume(customer_id, period_start)
            return {
                "volume_data": volume_data,
                "current_volume": volume_data.get("total_amount", 0),
                "transaction_count": volume_data.get("transaction_count", 0)
            }
        except Exception as e:
            logger.error("Failed to get volume data", customer_id=customer_id, error=str(e))
            return {"volume_data": {}, "error": str(e)}
    
    async def _get_transaction_data(self, customer_id: str) -> Dict[str, Any]:
        """Get transaction data for compliance checking"""
        try:
            date_range = {
                "start": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
                "end": datetime.now().strftime("%Y-%m-%d")
            }
            
            transaction_data = await self.mcp_manager.get_live_transaction_data(customer_id, date_range)
            return {
                "transaction_data": transaction_data,
                "recent_transactions": transaction_data.get("rows", [])
            }
        except Exception as e:
            logger.error("Failed to get transaction data", customer_id=customer_id, error=str(e))
            return {"transaction_data": {}, "error": str(e)}
    
    async def _get_general_compliance_data(self, customer_id: str) -> Dict[str, Any]:
        """Get general compliance data"""
        try:
            # Get recent transaction data as general compliance indicator
            date_range = {
                "start": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
                "end": datetime.now().strftime("%Y-%m-%d")
            }
            
            transaction_data = await self.mcp_manager.get_live_transaction_data(customer_id, date_range)
            return {
                "compliance_data": transaction_data,
                "activity_summary": {
                    "transaction_count": len(transaction_data.get("rows", [])),
                    "period_days": 30
                }
            }
        except Exception as e:
            logger.error("Failed to get general compliance data", customer_id=customer_id, error=str(e))
            return {"compliance_data": {}, "error": str(e)}
    
    def _should_generate_alert(
        self, 
        obligation: Obligation, 
        compliance_analysis: Dict[str, Any]
    ) -> bool:
        """Determine if an alert should be generated"""
        
        # Always alert for non-compliance
        if compliance_analysis.get("compliance_status") == "non_compliant":
            return True
        
        # Alert for high-risk situations
        if compliance_analysis.get("risk_level") in ["high", "critical"]:
            return True
        
        # Alert for deadline proximity
        if obligation.deadline:
            days_until = obligation.days_until_deadline()
            if days_until is not None and days_until <= 7:
                return True
        
        # Alert for repeated breaches
        if obligation.breach_count > 0:
            return True
        
        return False
    
    async def _create_compliance_alert(
        self, 
        obligation: Obligation, 
        compliance_analysis: Dict[str, Any],
        db: Session
    ) -> Alert:
        """Create compliance alert"""
        
        # Generate alert message using LLM
        alert_message = await self.llm_client.generate_alert_message(
            "compliance_check",
            obligation.to_dict(),
            compliance_analysis
        )
        
        # Determine severity
        severity = "medium"
        if compliance_analysis.get("risk_level") == "critical":
            severity = "critical"
        elif compliance_analysis.get("risk_level") == "high":
            severity = "high"
        elif compliance_analysis.get("compliance_status") == "non_compliant":
            severity = "high"
        
        # Create alert
        alert = Alert(
            contract_id=obligation.contract_id,
            obligation_id=obligation.id,
            alert_type="compliance_check",
            severity=severity,
            title=f"Compliance Alert: {obligation.obligation_type}",
            message=alert_message,
            evidence_data=compliance_analysis,
            compliance_data=compliance_analysis
        )
        
        db.add(alert)
        db.commit()
        db.refresh(alert)
        
        logger.info("Compliance alert created", 
                   alert_id=str(alert.id),
                   obligation_id=str(obligation.id),
                   severity=severity)
        
        return alert
    
    async def check_deadline_alerts(self, db: Session) -> List[Alert]:
        """Check for upcoming deadlines and create alerts"""
        
        logger.info("Checking deadline alerts")
        
        # Find obligations due within next 7 days
        upcoming_deadline = datetime.now() + timedelta(days=7)
        
        obligations = db.query(Obligation).filter(
            and_(
                Obligation.status == "active",
                Obligation.deadline.isnot(None),
                Obligation.deadline <= upcoming_deadline,
                Obligation.deadline >= datetime.now()
            )
        ).all()
        
        alerts_created = []
        
        for obligation in obligations:
            # Check if alert already exists for this deadline
            existing_alert = db.query(Alert).filter(
                and_(
                    Alert.obligation_id == obligation.id,
                    Alert.alert_type == "deadline_reminder",
                    Alert.status == "active"
                )
            ).first()
            
            if not existing_alert:
                alert = await self._create_deadline_alert(obligation, db)
                alerts_created.append(alert)
        
        logger.info("Deadline alert check completed", 
                   obligations_checked=len(obligations),
                   alerts_created=len(alerts_created))
        
        return alerts_created
    
    async def _create_deadline_alert(self, obligation: Obligation, db: Session) -> Alert:
        """Create deadline reminder alert"""
        
        days_until = obligation.days_until_deadline()
        
        if days_until == 0:
            title = f"URGENT: {obligation.obligation_type} due TODAY"
            severity = "critical"
        elif days_until <= 3:
            title = f"HIGH PRIORITY: {obligation.obligation_type} due in {days_until} days"
            severity = "high"
        else:
            title = f"REMINDER: {obligation.obligation_type} due in {days_until} days"
            severity = "medium"
        
        message = f"""
Deadline Alert: {obligation.description}

Party: {obligation.party}
Deadline: {obligation.deadline.strftime('%Y-%m-%d')}
Days Remaining: {days_until}

Please ensure this obligation is completed on time to avoid penalties.
"""
        
        alert = Alert(
            contract_id=obligation.contract_id,
            obligation_id=obligation.id,
            alert_type="deadline_reminder",
            severity=severity,
            title=title,
            message=message.strip(),
            scheduled_for=obligation.deadline
        )
        
        db.add(alert)
        db.commit()
        db.refresh(alert)
        
        logger.info("Deadline alert created", 
                   alert_id=str(alert.id),
                   obligation_id=str(obligation.id),
                   days_until=days_until)
        
        return alert
