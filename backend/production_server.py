"""
Production-Ready Email Assistant Server
Redesigned for handling 50k+ emails with queue-based architecture,
API key rotation, intelligent caching, and comprehensive monitoring
"""

from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json
import uuid
import time

# Import production components
from config import config
from redis_manager import redis_manager, queue_manager, QueueNames, QueueTask
from cache_manager import cache_manager
from api_rotation_manager import api_rotation_manager
from enhanced_email_processor import EnhancedEmailProcessor
from production_email_services import get_production_polling_service
from production_monitoring import monitoring_system

# Import existing modules (keeping compatibility)
from auth import (
    User, UserCreate, UserLogin, Token, get_current_active_user, 
    authenticate_user, create_access_token, get_password_hash,
    get_user_by_email, check_email_quota, increment_email_usage,
    get_user_quota_info, update_user_quota
)
from calendar_models import (
    CalendarProviderCreate, CalendarProviderResponse, CalendarInfo,
    EventCreate, EventUpdate, EventResponse, MeetingDetectionRequest,
    MeetingDetectionResponse, QuotaInfo, UserProfile
)
from calendar_services import calendar_service, credential_manager
from calendar_agent import calendar_agent
from oauth_google import google_oauth_service
from google_services import get_google_gmail_service, get_google_calendar_service

# Import existing models and functions we'll keep
from server import (
    Intent, IntentCreate, EmailAccount, EmailAccountCreate, KnowledgeBase, KnowledgeBaseCreate,
    EmailMessage, EmailTestRequest, DraftRequest, SendEmailRequest, PollingControlRequest,
    AccountPollingStatus, EMAIL_PROVIDERS, is_bounce_or_delivery_error,
    cosine_similarity
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).parent
from dotenv import load_dotenv
load_dotenv(ROOT_DIR / '.env')

# Create the main app
app = FastAPI(
    title="Production Email Assistant API",
    description="High-performance email processing system for 50k+ emails",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create router with /api prefix
api_router = APIRouter(prefix="/api")

# Global instances
db = None
enhanced_email_processor = None
production_polling_service = None

@app.on_event("startup")
async def startup_event():
    """Initialize all production components on startup"""
    global db, enhanced_email_processor, production_polling_service
    
    try:
        logger.info("🚀 Starting production email assistant server...")
        
        # Initialize database connection with optimized settings
        client = AsyncIOMotorClient(
            config.database.mongo_url,
            maxPoolSize=config.database.max_pool_size,
            minPoolSize=config.database.min_pool_size,
            maxIdleTimeMS=config.database.max_idle_time_ms
        )
        db = client[config.database.db_name]
        
        # Test database connection
        await db.admin.command('ping')
        logger.info("✅ Database connection established")
        
        # Initialize Redis and queue system
        await redis_manager.initialize()
        await queue_manager.initialize()
        logger.info("✅ Redis and queue system initialized")
        
        # Initialize cache manager
        await cache_manager.initialize()
        logger.info("✅ Cache manager initialized")
        
        # Initialize API rotation manager
        await api_rotation_manager.initialize()
        logger.info("✅ API rotation manager initialized")
        
        # Initialize enhanced email processor
        enhanced_email_processor = EnhancedEmailProcessor(db)
        await enhanced_email_processor.initialize()
        logger.info("✅ Enhanced email processor initialized")
        
        # Initialize production polling service
        production_polling_service = get_production_polling_service(
            config.database.mongo_url, 
            config.database.db_name
        )
        await production_polling_service.initialize()
        logger.info("✅ Production polling service initialized")
        
        # Initialize monitoring system
        await monitoring_system.initialize()
        logger.info("✅ Monitoring system initialized")
        
        # Start polling service
        asyncio.create_task(production_polling_service.start_polling())
        logger.info("🟢 Email polling service started")
        
        logger.info("🎉 Production email assistant server fully initialized!")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize server: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global production_polling_service
    
    try:
        logger.info("🛑 Shutting down production email assistant server...")
        
        # Stop polling service
        if production_polling_service:
            production_polling_service.stop_polling()
        
        # Shutdown monitoring
        await monitoring_system.shutdown()
        
        # Close API rotation manager
        await api_rotation_manager.close()
        
        # Close Redis connections
        await redis_manager.close()
        
        logger.info("✅ Server shutdown complete")
        
    except Exception as e:
        logger.error(f"❌ Error during shutdown: {e}")

# ============================================================================
# PRODUCTION HEALTH AND MONITORING ENDPOINTS
# ============================================================================

@api_router.get("/health")
async def health_check():
    """Comprehensive health check endpoint"""
    try:
        health_status = await monitoring_system.get_health_status()
        
        # Add additional health checks
        health_status["components"] = {
            "database": "healthy" if db else "unhealthy",
            "enhanced_processor": "healthy" if enhanced_email_processor else "unhealthy",
            "polling_service": "healthy" if production_polling_service and production_polling_service.is_running else "unhealthy"
        }
        
        # Determine overall status
        unhealthy_components = [
            name for name, status in health_status["components"].items() 
            if status == "unhealthy"
        ]
        
        if unhealthy_components:
            health_status["overall_status"] = "unhealthy"
        
        return health_status
        
    except Exception as e:
        return {
            "overall_status": "unhealthy",
            "error": str(e),
            "timestamp": time.time()
        }

@api_router.get("/metrics")
async def get_system_metrics():
    """Get comprehensive system metrics"""
    try:
        metrics = {}
        
        # Get processing stats
        if enhanced_email_processor:
            metrics["processing"] = await enhanced_email_processor.get_processing_stats()
        
        # Get polling stats
        if production_polling_service:
            metrics["polling"] = production_polling_service.get_polling_stats()
        
        # Get queue stats
        metrics["queues"] = await queue_manager.get_queue_stats()
        
        # Get cache stats
        metrics["cache"] = await cache_manager.get_cache_stats()
        
        # Get API stats
        metrics["api"] = await api_rotation_manager.get_api_stats()
        
        # Get monitoring metrics
        metrics["monitoring"] = await monitoring_system.get_metrics_summary()
        
        metrics["timestamp"] = time.time()
        
        return metrics
        
    except Exception as e:
        logger.error(f"❌ Failed to get metrics: {e}")
        return {"error": str(e), "timestamp": time.time()}

@api_router.get("/status")
async def get_system_status():
    """Get system status overview"""
    try:
        return {
            "service": "Production Email Assistant",
            "version": "2.0.0",
            "status": "running",
            "components": {
                "redis": "connected" if redis_manager.redis_async else "disconnected",
                "database": "connected" if db else "disconnected",
                "queue_system": "active" if queue_manager else "inactive",
                "cache_system": "active" if cache_manager else "inactive",
                "api_rotation": "active" if api_rotation_manager else "inactive",
                "email_processor": "active" if enhanced_email_processor else "inactive",
                "polling_service": "running" if production_polling_service and production_polling_service.is_running else "stopped",
                "monitoring": "active" if monitoring_system.monitoring_active else "inactive"
            },
            "uptime": time.time(),
            "timestamp": time.time()
        }
        
    except Exception as e:
        return {"error": str(e), "timestamp": time.time()}

# ============================================================================
# ENHANCED EMAIL PROCESSING ENDPOINTS
# ============================================================================

@api_router.post("/emails/batch-process")
async def batch_process_emails(email_batch: List[Dict[str, Any]]):
    """Process a batch of emails efficiently"""
    try:
        if not enhanced_email_processor:
            raise HTTPException(status_code=503, detail="Email processor not available")
        
        result = await enhanced_email_processor.process_email_batch(email_batch)
        
        return {
            "batch_id": str(uuid.uuid4()),
            "processed_count": result.processed_count,
            "successful_count": result.successful_count,
            "failed_count": result.failed_count,
            "cached_count": result.cached_count,
            "processing_time": result.processing_time,
            "errors": result.errors,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"❌ Batch processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/emails/high-priority")
async def enqueue_high_priority_email(email_data: Dict[str, Any]):
    """Enqueue an email for high-priority processing"""
    try:
        task = QueueTask(
            id=str(uuid.uuid4()),
            queue_name=QueueNames.HIGH_PRIORITY.value,
            task_type="process_email",
            payload=email_data,
            priority=100  # Highest priority
        )
        
        success = await queue_manager.enqueue_task(task)
        
        if success:
            return {
                "task_id": task.id,
                "queue": task.queue_name,
                "status": "enqueued",
                "priority": task.priority,
                "timestamp": time.time()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to enqueue high-priority email")
            
    except Exception as e:
        logger.error(f"❌ High-priority email enqueue failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/queue-status")
async def get_queue_status():
    """Get detailed queue status"""
    try:
        stats = await queue_manager.get_queue_stats()
        
        # Add processing rates
        processing_stats = {}
        if enhanced_email_processor:
            processing_stats = enhanced_email_processor.processing_stats
        
        return {
            "queue_stats": stats,
            "processing_stats": processing_stats,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get queue status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# ENHANCED INTENT CLASSIFICATION WITH CACHING
# ============================================================================

async def enhanced_classify_email_intents(email_message: EmailMessage) -> List[Dict[str, Any]]:
    """Enhanced intent classification with caching and batch processing"""
    try:
        # Skip delivery error/bounce emails
        if is_bounce_or_delivery_error(email_message):
            logger.info(f"🚫 Skipping delivery error/bounce email: {email_message.subject}")
            return []
        
        # Check cache first
        cached_intents = await cache_manager.get_cached_intent_classification(
            email_message.body, 
            email_message.subject
        )
        
        if cached_intents:
            logger.debug(f"✅ Using cached intent classification")
            return cached_intents["intents"]
        
        # Get email embedding with caching
        email_embedding = await cache_manager.get_cached_embedding(email_message.body)
        
        if not email_embedding:
            # Get embedding using API rotation manager
            email_embedding = await api_rotation_manager.make_cohere_request(email_message.body)
            
            # Cache the embedding
            await cache_manager.cache_embedding(email_message.body, email_embedding)
        
        # Get all intents with embeddings
        intents = await db.intents.find({"embedding": {"$exists": True}}).to_list(1000)
        
        intent_scores = []
        for intent in intents:
            if "embedding" in intent:
                similarity = cosine_similarity(email_embedding, intent["embedding"])
                if similarity >= intent.get("confidence_threshold", 0.7):
                    intent_scores.append({
                        "intent_id": intent["id"],
                        "name": intent["name"],
                        "description": intent["description"],
                        "system_prompt": intent.get("system_prompt", ""),
                        "confidence": similarity,
                        "is_meeting_related": intent.get("is_meeting_related", False)
                    })
        
        # Return top 3 intents
        intent_scores.sort(key=lambda x: x["confidence"], reverse=True)
        final_intents = intent_scores[:3]
        
        # Cache the result
        await cache_manager.cache_intent_classification(
            email_message.body, 
            email_message.subject, 
            final_intents
        )
        
        return final_intents
        
    except Exception as e:
        logger.error(f"❌ Enhanced intent classification failed: {e}")
        return []

async def enhanced_generate_draft(email_message: EmailMessage, intents: List[Dict[str, Any]]) -> Dict[str, str]:
    """Enhanced draft generation with caching and API rotation"""
    try:
        # Skip generating draft for delivery errors
        if is_bounce_or_delivery_error(email_message):
            logger.info(f"🚫 Skipping draft generation for delivery error: {email_message.subject}")
            return {
                "plain_text": "",
                "html": "",
                "reasoning": "Skipped - delivery error/bounce email detected"
            }
        
        # Check cache first
        cached_draft = await cache_manager.get_cached_draft(email_message.body, intents)
        
        if cached_draft:
            logger.debug(f"✅ Using cached draft")
            return cached_draft
        
        # Get account info
        account = await db.email_accounts.find_one({"id": email_message.account_id})
        if not account:
            raise HTTPException(status_code=404, detail="Email account not found")
        
        # Get enhanced knowledge base context with caching
        kb_data = await get_enhanced_knowledge_context_cached(email_message.body, intents)
        
        # Build system prompt
        system_prompt = build_enhanced_system_prompt(email_message, intents, account, kb_data)
        
        # Create messages
        messages = [
            {"role": "user", "content": f"Generate a comprehensive email body response for: {email_message.body}"}
        ]
        
        # Generate draft using API rotation manager
        response = await api_rotation_manager.make_groq_request(messages, system_prompt)
        
        # Clean the response
        clean_response = clean_draft_response(response)
        
        # Generate HTML version
        html_version = generate_html_version(clean_response)
        
        draft_result = {
            "plain_text": clean_response,
            "html": html_version,
            "reasoning": f"Used KB items: {kb_data.get('items_count', 0)}, Intents: {', '.join([i['name'] for i in intents])}"
        }
        
        # Cache the result
        await cache_manager.cache_draft(email_message.body, intents, draft_result)
        
        return draft_result
        
    except Exception as e:
        logger.error(f"❌ Enhanced draft generation failed: {e}")
        raise

# Helper functions for draft generation
async def get_enhanced_knowledge_context_cached(email_body: str, intents: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Get enhanced knowledge base context with caching"""
    try:
        import hashlib
        
        # Create cache key from email body and intents
        context_hash = hashlib.md5(f"{email_body}_{json.dumps(intents, sort_keys=True)}".encode()).hexdigest()
        
        # Check cache first
        cached_context = await cache_manager.get_cached_knowledge_context(context_hash)
        if cached_context:
            return cached_context
        
        # Get email embedding with caching
        email_embedding = await cache_manager.get_cached_embedding(email_body)
        
        if not email_embedding:
            email_embedding = await api_rotation_manager.make_cohere_request(email_body)
            await cache_manager.cache_embedding(email_body, email_embedding)
        
        # Get knowledge base items
        kb_items = await db.knowledge_base.find({"embedding": {"$exists": True}}).to_list(1000)
        
        relevant_items = []
        for item in kb_items:
            if "embedding" in item:
                similarity = cosine_similarity(email_embedding, item["embedding"])
                if similarity >= 0.5:
                    relevant_items.append({
                        "title": item["title"],
                        "content": item["content"],
                        "tags": item.get("tags", []),
                        "similarity": similarity
                    })
        
        # Sort by similarity and take top 5
        relevant_items.sort(key=lambda x: x["similarity"], reverse=True)
        relevant_items = relevant_items[:5]
        
        # Build context
        if relevant_items:
            context = "RELEVANT KNOWLEDGE BASE INFORMATION:\n"
            for item in relevant_items:
                context += f"- {item['title']}: {item['content']}\n"
            context += f"\nTags: {', '.join(set([tag for item in relevant_items for tag in item.get('tags', [])]))}\n"
            
            context_data = {
                "context": context,
                "items_count": len(relevant_items),
                "has_relevant_info": True
            }
        else:
            context_data = {
                "context": "No highly relevant knowledge base items found. Use general professional tone.",
                "items_count": 0,
                "has_relevant_info": False
            }
        
        # Cache the result
        await cache_manager.cache_knowledge_context(context_hash, context_data)
        
        return context_data
        
    except Exception as e:
        logger.error(f"❌ Failed to get enhanced knowledge context: {e}")
        return {
            "context": "Error retrieving knowledge base information. Use general professional tone.",
            "items_count": 0,
            "has_relevant_info": False
        }

def build_enhanced_system_prompt(email_message: EmailMessage, intents: List[Dict], account: Dict, kb_data: Dict) -> str:
    """Build enhanced system prompt for draft generation"""
    intent_descriptions = [f"- {intent['name']}: {intent['description']} (confidence: {intent['confidence']:.2f})" 
                         for intent in intents]
    
    system_prompt = f"""You are Agent A - an email draft generator. Generate ONLY the email body content for a professional reply.

ACCOUNT PERSONA: {account.get('persona', 'Professional and helpful')}

EMAIL CONTEXT:
- Original Subject: {email_message.subject}
- From: {email_message.sender}
- Body: {email_message.body}

IDENTIFIED INTENTS:
{chr(10).join(intent_descriptions) if intent_descriptions else "No specific intents identified"}

{kb_data.get("context", "")}

CRITICAL INSTRUCTIONS:
1. Generate ONLY the email body content - no subject lines, no signatures, no placeholders
2. MUST use information from the knowledge base when relevant
3. Keep response comprehensive but professional (200-400 words when detailed info is needed)
4. Address all identified intents directly using knowledge base information
5. Maintain a {account.get('persona', 'professional')} tone
6. Include actionable next steps where appropriate
7. Start directly with the email content (e.g., "Thank you for your inquiry...")

Generate the email body content now:"""

    return system_prompt

def clean_draft_response(response: str) -> str:
    """Clean the draft response"""
    import re
    
    clean_response = response.strip()
    
    # Remove any <think> tags or reasoning content
    clean_response = re.sub(r'<think>.*?</think>', '', clean_response, flags=re.DOTALL)
    clean_response = re.sub(r'PLAIN_TEXT:|HTML:|Subject:|Re:.*?\n', '', clean_response)
    clean_response = re.sub(r'^-+|^=+', '', clean_response, flags=re.MULTILINE)
    clean_response = clean_response.strip()
    
    return clean_response

def generate_html_version(plain_text: str) -> str:
    """Generate HTML version from plain text"""
    import re
    
    html_version = plain_text.replace('\n\n', '</p><p>').replace('\n', '<br>')
    if html_version and not html_version.startswith('<p>'):
        html_version = f"<p>{html_version}</p>"
    
    # Make links clickable
    url_pattern = r'(https?://[^\s<>"{}|\\^`[\]]+)'
    html_version = re.sub(url_pattern, r'<a href="\1" target="_blank">\1</a>', html_version)
    
    return html_version

# ============================================================================
# KEEP ALL EXISTING ENDPOINTS (Authentication, Calendar, CRUD operations)
# ============================================================================

# Authentication Routes (keeping existing)
@api_router.post("/auth/register", response_model=Token)
async def register_user(user_data: UserCreate):
    """Register a new user"""
    # Check if user already exists
    existing_user = await get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    user_id = str(uuid.uuid4())
    hashed_password = get_password_hash(user_data.password)
    
    # Set quota reset date to next month
    next_month = datetime.utcnow().replace(day=1) + timedelta(days=32)
    next_month = next_month.replace(day=1)
    
    new_user = {
        "id": user_id,
        "email": user_data.email,
        "full_name": user_data.full_name or "",
        "hashed_password": hashed_password,
        "is_active": True,
        "email_quota": 100,  # Default monthly quota
        "emails_used": 0,
        "quota_reset_date": next_month,
        "timezone": "UTC",
        "created_at": datetime.utcnow()
    }
    
    await db.users.insert_one(new_user)
    
    # Create access token
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user_data.email}, expires_delta=access_token_expires
    )
    
    user_response = User(**new_user)
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=user_response
    )

@api_router.post("/auth/login", response_model=Token)
async def login_user(user_credentials: UserLogin):
    """Login user and return JWT token"""
    user = await authenticate_user(user_credentials.email, user_credentials.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user["email"]}, expires_delta=access_token_expires
    )
    
    user_response = User(**user)
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=user_response
    )

@api_router.get("/auth/me", response_model=UserProfile)
async def get_current_user_profile(current_user: User = Depends(get_current_active_user)):
    """Get current user's profile"""
    quota_info = await get_user_quota_info(current_user.id)
    
    return UserProfile(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        timezone=current_user.timezone,
        email_quota=current_user.email_quota,
        emails_used=current_user.emails_used,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        quota_info=QuotaInfo(**quota_info)
    )

# Add all the existing routes from the original server
# (I'll include the key ones here, but in practice you'd include all of them)

# Include the router in the app
app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)