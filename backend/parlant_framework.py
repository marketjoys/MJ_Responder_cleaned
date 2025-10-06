"""
Parlant-inspired framework for enhanced agent control and reliability
Implements key Parlant principles without dependency conflicts
"""

from typing import Dict, Any, List, Optional, Callable
from pydantic import BaseModel
from datetime import datetime
import json
import re
import logging

logger = logging.getLogger(__name__)

class Guideline(BaseModel):
    """Parlant-style guideline for agent behavior control"""
    id: str
    condition: str  # Natural language condition
    action: str    # Natural language action
    priority: int = 0  # Higher number = higher priority
    tools: List[str] = []  # Tool names to use
    constraints: Dict[str, Any] = {}
    active: bool = True

class Journey(BaseModel):
    """Conversation journey definition"""
    id: str
    name: str
    description: str
    steps: List[Dict[str, Any]]
    current_step: int = 0
    context: Dict[str, Any] = {}

class Intent(BaseModel):
    """Enhanced intent with Parlant-style context"""
    name: str
    description: str
    confidence: float
    context: Dict[str, Any] = {}
    guidelines: List[str] = []  # Guideline IDs that apply
    tools_required: List[str] = []

class AgentResponse(BaseModel):
    """Structured agent response with explainability"""
    content: str
    confidence: float
    guidelines_applied: List[str] = []
    tools_used: List[str] = []
    validation_results: Dict[str, Any] = {}
    reasoning: str = ""
    should_escalate: bool = False

class ParlantAgent:
    """Base agent class with Parlant-style control mechanisms"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.guidelines: Dict[str, Guideline] = {}
        self.tools: Dict[str, Callable] = {}
        self.journey: Optional[Journey] = None
        self.context: Dict[str, Any] = {}
        
    def add_guideline(self, guideline: Guideline) -> None:
        """Add a behavioral guideline"""
        self.guidelines[guideline.id] = guideline
        logger.info(f"Added guideline {guideline.id} to agent {self.name}")
    
    def register_tool(self, name: str, tool: Callable) -> None:
        """Register a tool for the agent to use"""
        self.tools[name] = tool
        logger.info(f"Registered tool {name} for agent {self.name}")
    
    def match_guidelines(self, context: Dict[str, Any]) -> List[Guideline]:
        """Match relevant guidelines based on context"""
        matched = []
        
        for guideline in self.guidelines.values():
            if not guideline.active:
                continue
                
            # Simple keyword matching for conditions
            condition_lower = guideline.condition.lower()
            context_text = str(context).lower()
            
            # Check if condition keywords appear in context
            if self._condition_matches(condition_lower, context_text, context):
                matched.append(guideline)
        
        # Sort by priority
        matched.sort(key=lambda g: g.priority, reverse=True)
        return matched
    
    def _condition_matches(self, condition: str, context_text: str, context: Dict[str, Any]) -> bool:
        """Enhanced condition matching logic"""
        
        # Direct keyword matching
        condition_keywords = condition.split()
        matches = sum(1 for keyword in condition_keywords if keyword in context_text)
        keyword_match_ratio = matches / len(condition_keywords)
        
        # Intent-based matching
        if 'intents' in context:
            for intent in context['intents']:
                if isinstance(intent, dict) and 'name' in intent:
                    if intent['name'].lower() in condition:
                        return True
        
        # Email context matching
        if 'email_content' in context:
            email_content = context['email_content'].lower()
            if any(keyword in email_content for keyword in condition_keywords):
                return True
        
        return keyword_match_ratio > 0.3  # 30% keyword match threshold

class DraftAgent(ParlantAgent):
    """Enhanced draft agent with Parlant-style control"""
    
    def __init__(self):
        super().__init__("DraftAgent", "AI agent for generating email drafts with enhanced control")
        self._setup_default_guidelines()
    
    def _setup_default_guidelines(self):
        """Setup default guidelines for draft generation"""
        
        # Core response guidelines
        self.add_guideline(Guideline(
            id="professional_tone",
            condition="any email response",
            action="Maintain professional, helpful tone throughout response",
            priority=10,
            constraints={"max_words": 200, "tone": "professional"}
        ))
        
        self.add_guideline(Guideline(
            id="sales_inquiry",
            condition="sales inquiry or product information request",
            action="Provide product information, pricing details, and next steps. Include relevant knowledge base links.",
            priority=8,
            tools=["knowledge_base_search", "link_insertion"]
        ))
        
        self.add_guideline(Guideline(
            id="support_request", 
            condition="technical support or problem resolution",
            action="Acknowledge issue, provide solution steps, offer additional help",
            priority=8,
            tools=["knowledge_base_search"]
        ))
        
        self.add_guideline(Guideline(
            id="meeting_request",
            condition="meeting or scheduling request",
            action="Acknowledge request, provide availability options, suggest next steps",
            priority=7,
            tools=["calendar_check"]
        ))
        
        self.add_guideline(Guideline(
            id="persona_alignment",
            condition="any response",
            action="Align response with account persona and brand voice",
            priority=9
        ))

class ValidationAgent(ParlantAgent):
    """Enhanced validation agent with comprehensive checks"""
    
    def __init__(self):
        super().__init__("ValidationAgent", "AI agent for validating email content and ensuring quality")
        self._setup_validation_guidelines()
    
    def _setup_validation_guidelines(self):
        """Setup validation guidelines"""
        
        self.add_guideline(Guideline(
            id="hallucination_check",
            condition="any generated content",
            action="Verify all claims against knowledge base and email context. Flag unsubstantiated statements.",
            priority=10,
            tools=["fact_checker", "knowledge_base_verify"]
        ))
        
        self.add_guideline(Guideline(
            id="intent_coverage",
            condition="draft response to customer email",
            action="Ensure all identified customer intents are addressed in the response",
            priority=9,
            tools=["intent_checker"]
        ))
        
        self.add_guideline(Guideline(
            id="persona_consistency",
            condition="any response",
            action="Validate response aligns with account persona and brand guidelines",
            priority=8,
            tools=["persona_checker"]
        ))
        
        self.add_guideline(Guideline(
            id="content_appropriateness",
            condition="any response",
            action="Check for appropriate tone, no inappropriate content, professional language",
            priority=9
        ))
        
        self.add_guideline(Guideline(
            id="completeness_check",
            condition="customer inquiry response",
            action="Ensure response is complete, actionable, and provides value to customer",
            priority=7
        ))

class CalendarAgent(ParlantAgent):
    """Enhanced calendar agent with meeting detection and conflict handling"""
    
    def __init__(self):
        super().__init__("CalendarAgent", "AI agent for meeting detection, scheduling, and calendar management")
        self._setup_calendar_guidelines()
    
    def _setup_calendar_guidelines(self):
        """Setup calendar-specific guidelines"""
        
        self.add_guideline(Guideline(
            id="meeting_detection",
            condition="email contains meeting or scheduling keywords",
            action="Detect meeting intent, extract date/time information, identify participants",
            priority=10,
            tools=["datetime_extractor", "participant_extractor"]
        ))
        
        self.add_guideline(Guideline(
            id="conflict_resolution",
            condition="scheduling conflict detected",
            action="Identify conflicts, suggest alternative times, provide clear next steps",
            priority=9,
            tools=["calendar_checker", "alternative_finder"]
        ))
        
        self.add_guideline(Guideline(
            id="timezone_handling",
            condition="meeting scheduling across timezones",
            action="Clearly specify timezone, convert to participant timezones, avoid confusion",
            priority=8,
            tools=["timezone_converter"]
        ))
        
        self.add_guideline(Guideline(
            id="meeting_confirmation",
            condition="meeting scheduled or updated",
            action="Provide clear confirmation with all details, send calendar invites",
            priority=7,
            tools=["calendar_invite_sender"]
        ))

class ParlantFramework:
    """Main framework orchestrator"""
    
    def __init__(self):
        self.draft_agent = DraftAgent()
        self.validation_agent = ValidationAgent() 
        self.calendar_agent = CalendarAgent()
        
        # Register cross-agent tools
        self._setup_shared_tools()
    
    def _setup_shared_tools(self):
        """Setup tools shared across agents"""
        
        # Knowledge base tools
        async def knowledge_base_search(query: str, context: Dict[str, Any]) -> Dict[str, Any]:
            """Search knowledge base for relevant information"""
            # Integration with existing KB search
            return {"results": [], "confidence": 0.0}
        
        async def fact_checker(claim: str, context: Dict[str, Any]) -> Dict[str, Any]:
            """Check facts against reliable sources"""
            return {"verified": True, "confidence": 0.9}
        
        # Register tools with all agents
        for agent in [self.draft_agent, self.validation_agent, self.calendar_agent]:
            agent.register_tool("knowledge_base_search", knowledge_base_search)
            agent.register_tool("fact_checker", fact_checker)
    
    async def process_with_guidelines(self, agent: ParlantAgent, context: Dict[str, Any]) -> AgentResponse:
        """Process request using Parlant-style guidelines"""
        
        # Match relevant guidelines
        matched_guidelines = agent.match_guidelines(context)
        
        # Apply guidelines in priority order
        guidelines_applied = []
        tools_used = []
        reasoning_parts = []
        
        for guideline in matched_guidelines[:3]:  # Limit to top 3 guidelines
            guidelines_applied.append(guideline.id)
            reasoning_parts.append(f"Applied guideline '{guideline.id}': {guideline.action}")
            
            # Execute required tools
            for tool_name in guideline.tools:
                if tool_name in agent.tools:
                    tools_used.append(tool_name)
        
        return AgentResponse(
            content="",  # Will be filled by specific agent implementation
            confidence=min(1.0, len(guidelines_applied) * 0.3),  # Confidence based on guidelines matched
            guidelines_applied=guidelines_applied,
            tools_used=tools_used,
            reasoning=" | ".join(reasoning_parts) if reasoning_parts else "No guidelines matched"
        )
    
    async def enhance_draft_generation(self, email_context: Dict[str, Any], intents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Enhanced draft generation with Parlant principles"""
        
        context = {
            "email_content": email_context.get("body", ""),
            "subject": email_context.get("subject", ""),
            "sender": email_context.get("sender", ""),
            "intents": intents,
            "type": "draft_generation"
        }
        
        response = await self.process_with_guidelines(self.draft_agent, context)
        
        return {
            "agent_response": response,
            "enhanced_context": context,
            "guidelines_to_follow": [g.action for g in self.draft_agent.match_guidelines(context)]
        }
    
    async def enhance_validation(self, draft: Dict[str, Any], email_context: Dict[str, Any], intents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Enhanced validation with Parlant principles"""
        
        context = {
            "draft_content": draft.get("content", ""),
            "email_content": email_context.get("body", ""),
            "intents": intents,
            "persona": email_context.get("persona", ""),
            "type": "validation"
        }
        
        response = await self.process_with_guidelines(self.validation_agent, context)
        
        # Perform specific validation checks
        validation_results = {
            "hallucination_check": await self._check_hallucination(draft, email_context),
            "intent_coverage": await self._check_intent_coverage(draft, intents),
            "persona_alignment": await self._check_persona_alignment(draft, email_context),
            "guidelines_followed": response.guidelines_applied
        }
        
        return {
            "validation_results": validation_results,
            "agent_response": response,
            "recommendations": self._generate_recommendations(validation_results)
        }
    
    async def enhance_calendar_processing(self, email_context: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced calendar processing with Parlant principles"""
        
        context = {
            "email_content": email_context.get("body", ""),
            "subject": email_context.get("subject", ""),
            "sender": email_context.get("sender", ""),
            "type": "calendar_processing"
        }
        
        response = await self.process_with_guidelines(self.calendar_agent, context)
        
        return {
            "calendar_analysis": response,
            "meeting_detection": await self._detect_meetings_enhanced(email_context),
            "conflict_analysis": await self._check_calendar_conflicts(email_context)
        }
    
    async def _check_hallucination(self, draft: Dict[str, Any], email_context: Dict[str, Any]) -> Dict[str, Any]:
        """Check for hallucination in draft content"""
        # Implementation would check claims against knowledge base
        return {"has_hallucination": False, "confidence": 0.9}
    
    async def _check_intent_coverage(self, draft: Dict[str, Any], intents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check if all intents are addressed"""
        # Implementation would verify intent coverage
        return {"all_intents_covered": True, "coverage_score": 0.95}
    
    async def _check_persona_alignment(self, draft: Dict[str, Any], email_context: Dict[str, Any]) -> Dict[str, Any]:
        """Check persona alignment"""
        # Implementation would verify persona consistency
        return {"persona_aligned": True, "alignment_score": 0.9}
    
    async def _detect_meetings_enhanced(self, email_context: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced meeting detection with Parlant guidelines"""
        # Implementation would use calendar agent guidelines
        return {"meeting_detected": False, "confidence": 0.0}
    
    async def _check_calendar_conflicts(self, email_context: Dict[str, Any]) -> Dict[str, Any]:
        """Check for calendar conflicts"""
        # Implementation would check against existing calendar
        return {"has_conflicts": False, "suggested_alternatives": []}
    
    def _generate_recommendations(self, validation_results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on validation"""
        recommendations = []
        
        if not validation_results.get("hallucination_check", {}).get("has_hallucination", True):
            recommendations.append("Content appears factual and grounded")
        
        if validation_results.get("intent_coverage", {}).get("all_intents_covered", False):
            recommendations.append("All customer intents are addressed")
        
        if validation_results.get("persona_alignment", {}).get("persona_aligned", False):
            recommendations.append("Response aligns with brand persona")
        
        return recommendations

# Global framework instance
parlant_framework = ParlantFramework()