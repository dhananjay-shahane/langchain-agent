#!/usr/bin/env python3
"""
MCP Server for Email Processing
Handles email reading, parsing, content analysis, and natural language understanding
"""

from mcp.server import Server
import os
import json
import email
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

server = Server("email_processing")

DATA_DIR = Path("./data")
EMAIL_ATTACHMENTS_DIR = DATA_DIR / "email-attachments"

@server.tool("parse_email")
def parse_email(email_id: str) -> Dict[str, Any]:
    """Parse email and extract structured information including content analysis"""
    try:
        # This would fetch from database in real implementation
        # For now, simulate email structure
        return {
            "id": email_id,
            "content_type": "business_inquiry",
            "priority": "medium", 
            "sentiment": "neutral",
            "key_topics": ["inquiry", "information_request"],
            "requires_attachments": True,
            "response_type": "informational_with_documents"
        }
    except Exception as e:
        return {"error": f"Failed to parse email: {e}"}

@server.tool("analyze_email_intent")
def analyze_email_intent(email_content: str, subject: str) -> Dict[str, Any]:
    """Analyze email intent and determine appropriate response strategy using natural language understanding"""
    try:
        content_lower = email_content.lower()
        subject_lower = subject.lower()
        
        # Intent classification
        intent = "general"
        confidence = 0.7
        
        if any(word in content_lower for word in ["analysis", "report", "data", "chart", "graph"]):
            intent = "data_analysis_request"
            confidence = 0.9
        elif any(word in content_lower for word in ["question", "inquiry", "information", "help"]):
            intent = "information_request" 
            confidence = 0.8
        elif any(word in content_lower for word in ["urgent", "asap", "immediately", "emergency"]):
            intent = "urgent_request"
            confidence = 0.95
        elif any(word in content_lower for word in ["thank", "thanks", "appreciate"]):
            intent = "appreciation"
            confidence = 0.85
            
        # Extract key entities and topics
        entities = []
        if "las" in content_lower or "well" in content_lower or "log" in content_lower:
            entities.append("well_data")
        if "report" in content_lower:
            entities.append("report_generation")
        if "plot" or "chart" in content_lower:
            entities.append("visualization")
            
        return {
            "intent": intent,
            "confidence": confidence,
            "entities": entities,
            "requires_documents": intent in ["data_analysis_request", "information_request"],
            "urgency": "high" if "urgent" in intent else "normal",
            "response_strategy": determine_response_strategy(intent, entities)
        }
    except Exception as e:
        return {"error": f"Failed to analyze intent: {e}"}

def determine_response_strategy(intent: str, entities: List[str]) -> Dict[str, Any]:
    """Determine the appropriate response strategy based on intent and entities"""
    strategy = {
        "include_analysis": False,
        "include_plots": False, 
        "include_report": False,
        "response_tone": "professional"
    }
    
    if intent == "data_analysis_request":
        strategy.update({
            "include_analysis": True,
            "include_plots": True,
            "include_report": True
        })
    elif intent == "information_request":
        strategy.update({
            "include_report": True,
            "response_tone": "helpful"
        })
    elif intent == "urgent_request":
        strategy.update({
            "response_tone": "urgent_professional",
            "priority": "high"
        })
        
    return strategy

@server.tool("extract_attachments_info")
def extract_attachments_info(attachments: List[str]) -> Dict[str, Any]:
    """Extract and analyze information from email attachments"""
    try:
        attachment_info = {
            "total_count": len(attachments),
            "file_types": {},
            "processable_files": [],
            "analysis_ready": False
        }
        
        for attachment in attachments:
            file_ext = attachment.split('.')[-1].lower() if '.' in attachment else 'unknown'
            
            if file_ext not in attachment_info["file_types"]:
                attachment_info["file_types"][file_ext] = 0
            attachment_info["file_types"][file_ext] += 1
            
            # Check if file is processable for analysis
            if file_ext in ['las', 'txt', 'csv', 'json']:
                attachment_info["processable_files"].append(attachment)
                attachment_info["analysis_ready"] = True
                
        return attachment_info
    except Exception as e:
        return {"error": f"Failed to extract attachment info: {e}"}

@server.tool("prepare_email_context")
def prepare_email_context(email_data: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare comprehensive context for LLM processing"""
    try:
        context = {
            "email_id": email_data.get("id", ""),
            "sender": email_data.get("from", ""),
            "subject": email_data.get("subject", ""),
            "content": email_data.get("body", ""),
            "attachments": email_data.get("attachments", []),
            "timestamp": datetime.now().isoformat(),
            "processing_notes": "Email prepared for LLM analysis"
        }
        
        # Add metadata for better LLM understanding
        context["metadata"] = {
            "word_count": len(context["content"].split()),
            "has_attachments": len(context["attachments"]) > 0,
            "estimated_complexity": "high" if len(context["content"].split()) > 100 else "low"
        }
        
        return context
    except Exception as e:
        return {"error": f"Failed to prepare context: {e}"}

if __name__ == "__main__":
    server.run()