from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Union, Dict, Any
import uuid
from datetime import datetime, timedelta
import json
import asyncio
import httpx
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import imaplib
import email
import re
from email.header import decode_header
import time

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="Automated Email Assistant API")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# API Keys from environment
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
COHERE_API_KEY = os.environ.get('COHERE_API_KEY')

# Email provider configurations
EMAIL_PROVIDERS = {
    "gmail": {
        "name": "Gmail",
        "imap_server": "imap.gmail.com",
        "imap_port": 993,
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "requires_app_password": True
    },
    "outlook": {
        "name": "Outlook/Hotmail",
        "imap_server": "outlook.office365.com",
        "imap_port": 993,
        "smtp_server": "smtp-mail.outlook.com",
        "smtp_port": 587,
        "requires_app_password": False
    },
    "yahoo": {
        "name": "Yahoo Mail",
        "imap_server": "imap.mail.yahoo.com",
        "imap_port": 993,
        "smtp_server": "smtp.mail.yahoo.com",
        "smtp_port": 587,
        "requires_app_password": True
    },
    "custom": {
        "name": "Custom IMAP/SMTP",
        "imap_server": "",
        "imap_port": 993,
        "smtp_server": "",
        "smtp_port": 587,
        "requires_app_password": False
    }
}

# Models
class Intent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    examples: List[str] = []
    system_prompt: str = ""
    confidence_threshold: float = 0.7
    follow_up_hours: int = 24
    is_meeting_related: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

class IntentCreate(BaseModel):
    name: str
    description: str
    examples: List[str] = []
    system_prompt: str = ""
    confidence_threshold: float = 0.7
    follow_up_hours: int = 24
    is_meeting_related: bool = False

class EmailAccount(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: str
    provider: str
    imap_server: str
    imap_port: int
    smtp_server: str
    smtp_port: int
    username: str
    password: str  # In production, this should be encrypted
    is_active: bool = True
    persona: str = ""
    signature: str = ""
    last_uid: int = 0
    uidvalidity: Optional[str] = None
    last_polled: Optional[datetime] = None
    auto_send: bool = True  # Auto-send approved replies
    created_at: datetime = Field(default_factory=datetime.utcnow)

class EmailAccountCreate(BaseModel):
    name: str
    email: str
    provider: str
    imap_server: Optional[str] = None
    imap_port: Optional[int] = None
    smtp_server: Optional[str] = None
    smtp_port: Optional[int] = None
    username: str
    password: str
    persona: str = ""
    signature: str = ""
    auto_send: bool = True

class KnowledgeBase(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    content: str
    tags: List[str] = []
    embedding: Optional[List[float]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class KnowledgeBaseCreate(BaseModel):
    title: str
    content: str
    tags: List[str] = []

class EmailTestRequest(BaseModel):
    subject: str
    body: str
    sender: str
    account_id: str

class DraftRequest(BaseModel):
    email_id: str
    force_redraft: bool = False

class SendEmailRequest(BaseModel):
    email_id: str
    manual_override: bool = False

class PollingControlRequest(BaseModel):
    action: str  # start, stop, status

# Import email services and model
from email_services import get_polling_service, EmailConnection, EmailMessage

# Global polling service
polling_service = None

# Helper Functions
async def get_cohere_embedding(text: str) -> List[float]:
    """Get embedding from Cohere API"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.cohere.com/v1/embed",
            headers={
                "Authorization": f"Bearer {COHERE_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "embed-english-v3.0",
                "texts": [text],
                "input_type": "classification",
                "truncate": "NONE"
            }
        )
        if response.status_code == 200:
            result = response.json()
            return result["embeddings"][0]
        else:
            raise HTTPException(status_code=500, detail=f"Cohere API error: {response.text}")

async def groq_chat_completion(messages: List[Dict], system_prompt: str = "") -> str:
    """Get completion from Groq API"""
    if system_prompt:
        messages = [{"role": "system", "content": system_prompt}] + messages
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "messages": messages,
                "model": "deepseek-r1-distill-llama-70b",
                "temperature": 0.6,
                "max_completion_tokens": 4096,
                "top_p": 0.95,
                "stream": False
            }
        )
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            raise HTTPException(status_code=500, detail=f"Groq API error: {response.text}")

def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Calculate cosine similarity between two embeddings"""
    import math
    dot_product = sum(x * y for x, y in zip(a, b))
    magnitude_a = math.sqrt(sum(x * x for x in a))
    magnitude_b = math.sqrt(sum(x * x for x in b))
    if magnitude_a == 0 or magnitude_b == 0:
        return 0
    return dot_product / (magnitude_a * magnitude_b)

# Intent Management Routes
@api_router.post("/intents", response_model=Intent)
async def create_intent(intent: IntentCreate):
    intent_dict = intent.dict()
    intent_obj = Intent(**intent_dict)
    
    # Create embedding for intent description + examples
    text_for_embedding = f"{intent_obj.description} {' '.join(intent_obj.examples)}"
    embedding = await get_cohere_embedding(text_for_embedding)
    
    # Store with embedding
    doc = intent_obj.dict()
    doc["embedding"] = embedding
    await db.intents.insert_one(doc)
    return intent_obj

@api_router.get("/intents", response_model=List[Intent])
async def get_intents():
    intents = await db.intents.find().to_list(1000)
    return [Intent(**intent) for intent in intents]

@api_router.delete("/intents/{intent_id}")
async def delete_intent(intent_id: str):
    result = await db.intents.delete_one({"id": intent_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Intent not found")
    return {"message": "Intent deleted successfully"}

# Email Account Management Routes
@api_router.get("/email-providers")
async def get_email_providers():
    return EMAIL_PROVIDERS

@api_router.post("/email-accounts", response_model=EmailAccount)
async def create_email_account(account: EmailAccountCreate):
    account_dict = account.dict()
    
    # Auto-fill provider settings if not custom
    if account.provider != "custom" and account.provider in EMAIL_PROVIDERS:
        provider_config = EMAIL_PROVIDERS[account.provider]
        account_dict["imap_server"] = provider_config["imap_server"]
        account_dict["imap_port"] = provider_config["imap_port"]
        account_dict["smtp_server"] = provider_config["smtp_server"]
        account_dict["smtp_port"] = provider_config["smtp_port"]
    
    account_obj = EmailAccount(**account_dict)
    await db.email_accounts.insert_one(account_obj.dict())
    return account_obj

@api_router.get("/email-accounts", response_model=List[EmailAccount])
async def get_email_accounts():
    accounts = await db.email_accounts.find().to_list(1000)
    # Don't return passwords in response
    for account in accounts:
        account["password"] = "***"
    return [EmailAccount(**account) for account in accounts]

@api_router.delete("/email-accounts/{account_id}")
async def delete_email_account(account_id: str):
    result = await db.email_accounts.delete_one({"id": account_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Email account not found")
    return {"message": "Email account deleted successfully"}

@api_router.put("/email-accounts/{account_id}/toggle")
async def toggle_email_account(account_id: str):
    """Toggle email account active status"""
    account = await db.email_accounts.find_one({"id": account_id})
    if not account:
        raise HTTPException(status_code=404, detail="Email account not found")
    
    new_status = not account.get("is_active", True)
    await db.email_accounts.update_one(
        {"id": account_id},
        {"$set": {"is_active": new_status}}
    )
    
    return {"message": f"Account {'activated' if new_status else 'deactivated'} successfully"}

# Knowledge Base Routes
@api_router.post("/knowledge-base", response_model=KnowledgeBase)
async def create_knowledge_base(kb: KnowledgeBaseCreate):
    kb_dict = kb.dict()
    kb_obj = KnowledgeBase(**kb_dict)
    
    # Create embedding for content
    embedding = await get_cohere_embedding(kb_obj.content)
    
    # Store with embedding
    doc = kb_obj.dict()
    doc["embedding"] = embedding
    await db.knowledge_base.insert_one(doc)
    return kb_obj

@api_router.get("/knowledge-base", response_model=List[KnowledgeBase])
async def get_knowledge_base():
    kb_items = await db.knowledge_base.find().to_list(1000)
    return [KnowledgeBase(**kb) for kb in kb_items]

@api_router.delete("/knowledge-base/{kb_id}")
async def delete_knowledge_base(kb_id: str):
    result = await db.knowledge_base.delete_one({"id": kb_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Knowledge base item not found")
    return {"message": "Knowledge base item deleted successfully"}

# Email Processing Routes
@api_router.post("/emails/test")
async def test_email_processing(request: EmailTestRequest):
    """Test email processing with manual input"""
    # Create a test email message
    email_obj = EmailMessage(
        account_id=request.account_id,
        message_id=f"test-{uuid.uuid4()}",
        thread_id=f"thread-{uuid.uuid4()}",
        subject=request.subject,
        sender=request.sender,
        recipient="test@example.com",
        body=request.body,
        received_at=datetime.utcnow(),
        status="processing"
    )
    
    # Store in database
    await db.emails.insert_one(email_obj.dict())
    
    # Process the email
    await process_email_async(email_obj.id)
    
    # Return processed email
    processed_email = await db.emails.find_one({"id": email_obj.id})
    return EmailMessage(**processed_email)

@api_router.post("/emails/{email_id}/send")
async def send_email_reply(email_id: str, request: SendEmailRequest):
    """Send email reply"""
    email_doc = await db.emails.find_one({"id": email_id})
    if not email_doc:
        raise HTTPException(status_code=404, detail="Email not found")
    
    if email_doc['status'] not in ['ready_to_send', 'needs_redraft'] and not request.manual_override:
        raise HTTPException(status_code=400, detail="Email not ready to send")
    
    # Get account
    account_doc = await db.email_accounts.find_one({"id": email_doc['account_id']})
    if not account_doc:
        raise HTTPException(status_code=404, detail="Email account not found")
    
    # Create connection and send
    connection = EmailConnection(account_doc)
    
    # Extract sender email
    sender_email = email_doc['sender']
    if '<' in sender_email:
        sender_email = sender_email.split('<')[1].split('>')[0]
    
    # Prepare reply subject
    subject = email_doc['subject']
    if not subject.lower().startswith('re:'):
        subject = f"Re: {subject}"
    
    # Send email
    success = connection.send_email(
        to_email=sender_email,
        subject=subject,
        body=email_doc['draft'],
        body_html=email_doc['draft_html'],
        message_id_to_reply=email_doc['message_id'],
        references=email_doc.get('references', '')
    )
    
    if success:
        # Update status to sent
        await db.emails.update_one(
            {"id": email_id},
            {"$set": {
                "status": "sent",
                "sent_at": datetime.utcnow()
            }}
        )
        return {"message": "Email sent successfully"}
    else:
        # Mark as failed to send
        await db.emails.update_one(
            {"id": email_id},
            {"$set": {"status": "send_failed"}}
        )
        raise HTTPException(status_code=500, detail="Failed to send email")

# Email Polling Control Routes
@api_router.post("/polling/control")
async def control_email_polling(request: PollingControlRequest):
    """Control email polling service"""
    global polling_service
    
    if request.action == "start":
        if polling_service and polling_service.is_running:
            return {"message": "Email polling is already running"}
        
        polling_service = get_polling_service(mongo_url, os.environ['DB_NAME'])
        # Start polling in background
        asyncio.create_task(polling_service.start_polling())
        return {"message": "Email polling started"}
    
    elif request.action == "stop":
        if polling_service:
            polling_service.stop_polling()
            return {"message": "Email polling stopped"}
        return {"message": "Email polling was not running"}
    
    elif request.action == "status":
        if polling_service and polling_service.is_running:
            return {
                "status": "running",
                "active_connections": len(polling_service.connections)
            }
        return {"status": "stopped"}
    
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'start', 'stop', or 'status'")

@api_router.get("/polling/status")
async def get_polling_status():
    """Get polling service status"""
    global polling_service
    if polling_service and polling_service.is_running:
        return {
            "status": "running",
            "active_connections": len(polling_service.connections)
        }
    return {"status": "stopped"}

async def classify_email_intents(email_body: str) -> List[Dict[str, Any]]:
    """Classify email intents using Cohere embeddings"""
    # Get email embedding
    email_embedding = await get_cohere_embedding(email_body)
    
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
    return intent_scores[:3]

async def generate_draft(email_message: EmailMessage, intents: List[Dict[str, Any]]) -> Dict[str, str]:
    """Generate email draft using Agent A (Groq API) - ONLY EMAIL BODY CONTENT"""
    # Get account info
    account = await db.email_accounts.find_one({"id": email_message.account_id})
    if not account:
        raise HTTPException(status_code=404, detail="Email account not found")
    
    # Get relevant knowledge base items
    kb_context = await get_knowledge_context(email_message.body)
    
    # Build context
    intent_descriptions = []
    system_prompts = []
    for intent in intents:
        intent_descriptions.append(f"- {intent['name']}: {intent['description']} (confidence: {intent['confidence']:.2f})")
        if intent.get('system_prompt'):
            system_prompts.append(intent['system_prompt'])
    
    system_prompt = f"""You are Agent A - an email draft generator. Generate ONLY the email body content for a professional reply.

ACCOUNT PERSONA: {account.get('persona', 'Professional and helpful')}

EMAIL CONTEXT:
- Original Subject: {email_message.subject}
- From: {email_message.sender}
- Body: {email_message.body}

IDENTIFIED INTENTS:
{chr(10).join(intent_descriptions) if intent_descriptions else "No specific intents identified"}

ADDITIONAL GUIDANCE:
{chr(10).join(system_prompts) if system_prompts else ""}

KNOWLEDGE BASE CONTEXT:
{kb_context}

CRITICAL INSTRUCTIONS:
1. Generate ONLY the email body content - no subject lines, no signatures, no placeholders
2. Do not include any reasoning, thinking, or meta-content
3. Keep response concise (150-250 words unless more detail is needed)
4. Address all identified intents directly
5. Maintain a {account.get('persona', 'professional')} tone
6. Include actionable next steps where appropriate
7. Do not make commitments about pricing or timelines unless specified in knowledge base
8. Start directly with the email content (e.g., "Thank you for your inquiry...")

Generate the email body content now:"""

    messages = [
        {"role": "user", "content": f"Generate only the email body content for replying to: {email_message.body}"}
    ]
    
    response = await groq_chat_completion(messages, system_prompt)
    
    # Clean the response to remove any unwanted content
    clean_response = response.strip()
    
    # Remove any <think> tags or reasoning content
    import re
    clean_response = re.sub(r'<think>.*?</think>', '', clean_response, flags=re.DOTALL)
    clean_response = re.sub(r'PLAIN_TEXT:|HTML:|Subject:|Re:.*?\n', '', clean_response)
    clean_response = re.sub(r'\*+.*?\*+', '', clean_response)  # Remove asterisk formatting
    clean_response = re.sub(r'^-+|^=+', '', clean_response, flags=re.MULTILINE)  # Remove separator lines
    clean_response = clean_response.strip()
    
    # Generate simple HTML version from plain text
    html_version = clean_response.replace('\n\n', '</p><p>').replace('\n', '<br>')
    if html_version and not html_version.startswith('<p>'):
        html_version = f"<p>{html_version}</p>"
    
    return {
        "plain_text": clean_response,
        "html": html_version,
        "reasoning": f"Addressed intents: {', '.join([i['name'] for i in intents])}"
    }

async def validate_draft(email_message: EmailMessage, draft: Dict[str, str], intents: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Validate draft using Agent B (Groq API)"""
    intent_descriptions = [f"- {intent['name']}: {intent['description']}" for intent in intents]
    
    system_prompt = f"""You are Agent B - an email draft validator. Check if the draft correctly addresses the email and intents.

ORIGINAL EMAIL:
Subject: {email_message.subject}
From: {email_message.sender}
Body: {email_message.body}

IDENTIFIED INTENTS TO ADDRESS:
{chr(10).join(intent_descriptions) if intent_descriptions else "No specific intents"}

DRAFT TO VALIDATE:
{draft['plain_text']}

VALIDATION CRITERIA:
1. Does the draft address each identified intent?
2. Are the facts consistent and accurate?
3. Is the tone appropriate and professional?
4. Are actionable next steps provided where needed?
5. Is the response length appropriate?

IMPORTANT: Start your response with either "PASS:" or "FAIL:" followed by your explanation.

Example responses:
"PASS: The draft addresses all intents professionally and includes actionable next steps."
"FAIL: The draft does not address the pricing inquiry and lacks specific next steps."

Validate the draft now:"""

    messages = [
        {"role": "user", "content": "Please validate this draft response and start with PASS: or FAIL:"}
    ]
    
    validation_response = await groq_chat_completion(messages, system_prompt)
    
    # Clean and properly parse the validation response
    validation_response = validation_response.strip()
    
    # Remove any thinking tags if present
    import re
    validation_response = re.sub(r'<think>.*?</think>', '', validation_response, flags=re.DOTALL).strip()
    
    # Determine if it's a pass or fail - check the entire response
    is_pass = "PASS:" in validation_response.upper() or validation_response.upper().startswith("PASS")
    
    # Extract just the feedback without the PASS:/FAIL: prefix
    feedback = validation_response
    if validation_response.startswith("PASS:"):
        feedback = validation_response[5:].strip()
    elif validation_response.startswith("FAIL:"):
        feedback = validation_response[5:].strip()
    
    return {
        "status": "PASS" if is_pass else "FAIL",
        "feedback": feedback,
        "coverage_report": validation_response
    }

async def get_knowledge_context(email_body: str) -> str:
    """Get relevant knowledge base context using embeddings"""
    # Get email embedding
    email_embedding = await get_cohere_embedding(email_body)
    
    # Get all knowledge base items with embeddings
    kb_items = await db.knowledge_base.find({"embedding": {"$exists": True}}).to_list(1000)
    
    relevant_items = []
    for item in kb_items:
        if "embedding" in item:
            similarity = cosine_similarity(email_embedding, item["embedding"])
            if similarity >= 0.6:  # Threshold for relevance
                relevant_items.append({
                    "title": item["title"],
                    "content": item["content"],
                    "similarity": similarity
                })
    
    # Sort by similarity and take top 3
    relevant_items.sort(key=lambda x: x["similarity"], reverse=True)
    relevant_items = relevant_items[:3]
    
    if relevant_items:
        context = "RELEVANT KNOWLEDGE:\n"
        for item in relevant_items:
            context += f"- {item['title']}: {item['content']}\n"
        return context
    else:
        return "No relevant knowledge base items found."

async def process_email_async(email_id: str):
    """Background task to process email through AI workflow"""
    try:
        # Get email
        email_doc = await db.emails.find_one({"id": email_id})
        if not email_doc:
            return
        
        email_message = EmailMessage(**email_doc)
        
        # Step 1: Classify intents
        intents = await classify_email_intents(email_message.body)
        
        # Update email with intents
        await db.emails.update_one(
            {"id": email_id},
            {"$set": {"intents": intents, "status": "classifying"}}
        )
        
        # Step 2: Generate draft
        draft = await generate_draft(email_message, intents)
        
        # Update email with draft
        await db.emails.update_one(
            {"id": email_id},
            {"$set": {
                "draft": draft["plain_text"],
                "draft_html": draft["html"],
                "status": "drafting"
            }}
        )
        
        # Step 3: Validate draft
        validation = await validate_draft(email_message, draft, intents)
        
        # Update email with validation
        final_status = "ready_to_send" if validation["status"] == "PASS" else "needs_redraft"
        await db.emails.update_one(
            {"id": email_id},
            {"$set": {
                "validation_result": validation,
                "status": final_status,
                "processed_at": datetime.utcnow()
            }}
        )
        
    except Exception as e:
        # Update email with error status
        await db.emails.update_one(
            {"id": email_id},
            {"$set": {"status": "error", "error": str(e)}}
        )

@api_router.post("/emails/{email_id}/redraft")
async def redraft_email(email_id: str):
    """Request a redraft of an email"""
    email_doc = await db.emails.find_one({"id": email_id})
    if not email_doc:
        raise HTTPException(status_code=404, detail="Email not found")
    
    email_message = EmailMessage(**email_doc)
    
    # Get previous validation feedback for improvement
    previous_feedback = email_message.validation_result.get("feedback", "") if email_message.validation_result else ""
    
    # Re-generate draft with feedback
    intents = email_message.intents
    draft = await generate_draft(email_message, intents)
    
    # Add improvement instruction based on previous feedback
    if previous_feedback:
        improvement_prompt = f"Previous draft had these issues: {previous_feedback}. Please address these in the new draft."
        # Here you could enhance the draft generation with the feedback
    
    # Validate new draft
    validation = await validate_draft(email_message, draft, intents)
    
    # Update email
    final_status = "ready_to_send" if validation["status"] == "PASS" else "escalate"
    await db.emails.update_one(
        {"id": email_id},
        {"$set": {
            "draft": draft["plain_text"],
            "draft_html": draft["html"],
            "validation_result": validation,
            "status": final_status,
            "processed_at": datetime.utcnow()
        }}
    )
    
    updated_email = await db.emails.find_one({"id": email_id})
    return EmailMessage(**updated_email)

@api_router.get("/emails", response_model=List[EmailMessage])
async def get_emails():
    emails = await db.emails.find().sort("received_at", -1).to_list(100)
    return [EmailMessage(**email) for email in emails]

@api_router.get("/emails/{email_id}", response_model=EmailMessage)
async def get_email(email_id: str):
    email_doc = await db.emails.find_one({"id": email_id})
    if not email_doc:
        raise HTTPException(status_code=404, detail="Email not found")
    return EmailMessage(**email_doc)

# Dashboard/Stats Routes
@api_router.get("/dashboard/stats")
async def get_dashboard_stats():
    total_emails = await db.emails.count_documents({})
    processed_emails = await db.emails.count_documents({"status": {"$in": ["ready_to_send", "sent"]}})
    escalated_emails = await db.emails.count_documents({"status": "escalate"})
    sent_emails = await db.emails.count_documents({"status": "sent"})
    total_intents = await db.intents.count_documents({})
    total_accounts = await db.email_accounts.count_documents({})
    active_accounts = await db.email_accounts.count_documents({"is_active": True})
    
    # Polling status
    global polling_service
    polling_status = "running" if polling_service and polling_service.is_running else "stopped"
    
    return {
        "total_emails": total_emails,
        "processed_emails": processed_emails,
        "sent_emails": sent_emails,
        "escalated_emails": escalated_emails,
        "total_intents": total_intents,
        "total_accounts": total_accounts,
        "active_accounts": active_accounts,
        "polling_status": polling_status,
        "processing_rate": processed_emails / total_emails * 100 if total_emails > 0 else 0
    }

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    global polling_service
    if polling_service:
        polling_service.stop_polling()
    client.close()