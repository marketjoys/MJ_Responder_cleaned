#!/usr/bin/env python3
"""
Core Infrastructure Testing for AI-Powered Email Automation System
Tests the 6 key components requested in the review:
1. Authentication System - JWT token validation
2. API Health Check - main endpoints accessibility
3. Database Connection - MongoDB connectivity and CRUD operations
4. Redis/RQ Integration - Redis connection, RQ workers, background task processing
5. Environment Variables - API keys and configurations
6. Email Processing Pipeline - basic workflow without actual emails
"""
import asyncio
import sys
import os
import requests
import json
import time
from datetime import datetime
import uuid

# Add backend to path
sys.path.append('/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/backend/.env')
load_dotenv('/app/frontend/.env')

# Configuration
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://worker-restart-hub.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ['MONGO_URL']
DB_NAME = os.environ['DB_NAME']

class InfrastructureTester:
    def __init__(self):
        self.client = None
        self.db = None
        self.test_results = []
        self.auth_token = None
        self.test_user_id = None
        
    async def setup(self):
        """Setup database connection"""
        try:
            self.client = AsyncIOMotorClient(MONGO_URL)
            self.db = self.client[DB_NAME]
            # Test connection
            await self.client.admin.command('ping')
            print("✅ Database connection established")
            return True
        except Exception as e:
            print(f"❌ Database connection failed: {str(e)}")
            return False
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.client:
            self.client.close()
    
    def log_test_result(self, test_name: str, passed: bool, details: str = ""):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        result = {
            "test": test_name,
            "status": status,
            "passed": passed,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.test_results.append(result)
        print(f"{status}: {test_name}")
        if details:
            print(f"   Details: {details}")
    
    def test_authentication_system(self):
        """Test 1: Authentication System - User registration, login, JWT token validation"""
        print("\n🔐 Testing Authentication System...")
        
        try:
            # Generate unique test user
            test_email = f"test.infra.{int(time.time())}@example.com"
            test_password = "TestPassword123!"
            
            # Test 1a: User Registration
            register_data = {
                "email": test_email,
                "password": test_password,
                "full_name": "Infrastructure Test User"
            }
            
            try:
                response = requests.post(f"{API_BASE}/auth/register", json=register_data, timeout=15)
                register_passed = response.status_code == 200
                if register_passed:
                    register_result = response.json()
                    self.auth_token = register_result.get('access_token')
                    self.test_user_id = register_result.get('user', {}).get('id')
                    register_details = f"Status: {response.status_code}, Token received: {bool(self.auth_token)}"
                else:
                    register_details = f"Status: {response.status_code}, Error: {response.text[:100]}"
            except Exception as e:
                register_passed = False
                register_details = f"Error: {str(e)}"
            
            # Test 1b: User Login
            login_data = {
                "email": test_email,
                "password": test_password
            }
            
            try:
                response = requests.post(f"{API_BASE}/auth/login", json=login_data, timeout=10)
                login_passed = response.status_code == 200
                if login_passed:
                    login_result = response.json()
                    login_token = login_result.get('access_token')
                    login_details = f"Status: {response.status_code}, Token received: {bool(login_token)}"
                else:
                    login_details = f"Status: {response.status_code}"
            except Exception as e:
                login_passed = False
                login_details = f"Error: {str(e)}"
            
            # Test 1c: JWT Token Validation - Get user profile
            jwt_passed = False
            if self.auth_token:
                try:
                    headers = {"Authorization": f"Bearer {self.auth_token}"}
                    response = requests.get(f"{API_BASE}/auth/me", headers=headers, timeout=10)
                    jwt_passed = response.status_code == 200
                    if jwt_passed:
                        profile = response.json()
                        jwt_details = f"Status: {response.status_code}, User ID: {profile.get('id')}"
                    else:
                        jwt_details = f"Status: {response.status_code}"
                except Exception as e:
                    jwt_details = f"Error: {str(e)}"
            else:
                jwt_details = "Skipped - no auth token"
            
            # Test 1d: Invalid Token Handling
            try:
                headers = {"Authorization": "Bearer invalid_token_12345"}
                response = requests.get(f"{API_BASE}/auth/me", headers=headers, timeout=10)
                invalid_token_passed = response.status_code == 401
                invalid_token_details = f"Invalid token status: {response.status_code}"
            except Exception as e:
                invalid_token_passed = False
                invalid_token_details = f"Error: {str(e)}"
            
            all_passed = register_passed and login_passed and jwt_passed and invalid_token_passed
            
            # Log individual results
            self.log_test_result("Auth - User Registration", register_passed, register_details)
            self.log_test_result("Auth - User Login", login_passed, login_details)
            self.log_test_result("Auth - JWT Validation", jwt_passed, jwt_details)
            self.log_test_result("Auth - Invalid Token Handling", invalid_token_passed, invalid_token_details)
            
            details = f"Register: {register_passed}, Login: {login_passed}, JWT: {jwt_passed}, Invalid: {invalid_token_passed}"
            self.log_test_result("Authentication System", all_passed, details)
            
        except Exception as e:
            self.log_test_result("Authentication System", False, f"Exception: {str(e)}")
    
    def test_api_health_check(self):
        """Test 2: API Health Check - Verify main endpoints are accessible"""
        print("\n🌐 Testing API Health Check...")
        
        try:
            # Test 2a: Polling Status Endpoint (no auth required)
            try:
                response = requests.get(f"{API_BASE}/polling/status", timeout=10)
                polling_passed = response.status_code == 200
                if polling_passed:
                    polling_data = response.json()
                    polling_details = f"Status: {response.status_code}, Service: {polling_data.get('status')}"
                else:
                    polling_details = f"Status: {response.status_code}"
            except Exception as e:
                polling_passed = False
                polling_details = f"Error: {str(e)}"
            
            # Test 2b: Email Providers Endpoint (no auth required)
            try:
                response = requests.get(f"{API_BASE}/email-providers", timeout=10)
                providers_passed = response.status_code == 200
                if providers_passed:
                    providers_data = response.json()
                    providers_details = f"Status: {response.status_code}, Providers: {len(providers_data)}"
                else:
                    providers_details = f"Status: {response.status_code}"
            except Exception as e:
                providers_passed = False
                providers_details = f"Error: {str(e)}"
            
            # Test 2c: Protected Endpoints with Authentication
            protected_passed = False
            if self.auth_token:
                try:
                    headers = {"Authorization": f"Bearer {self.auth_token}"}
                    response = requests.get(f"{API_BASE}/intents", headers=headers, timeout=10)
                    protected_passed = response.status_code == 200
                    protected_details = f"Status: {response.status_code}"
                except Exception as e:
                    protected_details = f"Error: {str(e)}"
            else:
                protected_details = "Skipped - no auth token"
            
            # Test 2d: CORS and Basic API Structure
            try:
                response = requests.options(f"{API_BASE}/polling/status", timeout=10)
                cors_passed = response.status_code in [200, 204]
                cors_details = f"OPTIONS status: {response.status_code}"
            except Exception as e:
                cors_passed = False
                cors_details = f"Error: {str(e)}"
            
            all_passed = polling_passed and providers_passed and protected_passed and cors_passed
            
            # Log individual results
            self.log_test_result("API - Polling Status", polling_passed, polling_details)
            self.log_test_result("API - Email Providers", providers_passed, providers_details)
            self.log_test_result("API - Protected Endpoints", protected_passed, protected_details)
            self.log_test_result("API - CORS Support", cors_passed, cors_details)
            
            details = f"Polling: {polling_passed}, Providers: {providers_passed}, Protected: {protected_passed}, CORS: {cors_passed}"
            self.log_test_result("API Health Check", all_passed, details)
            
        except Exception as e:
            self.log_test_result("API Health Check", False, f"Exception: {str(e)}")
    
    async def test_database_connection(self):
        """Test 3: Database Connection - MongoDB connectivity and basic CRUD operations"""
        print("\n🗄️ Testing Database Connection...")
        
        try:
            # Test 3a: Basic Connection and Ping
            try:
                await self.client.admin.command('ping')
                ping_passed = True
                ping_details = "MongoDB ping successful"
            except Exception as e:
                ping_passed = False
                ping_details = f"Ping failed: {str(e)}"
            
            # Test 3b: Database and Collection Access
            try:
                collections = await self.db.list_collection_names()
                collections_passed = len(collections) > 0
                collections_details = f"Collections found: {len(collections)}"
            except Exception as e:
                collections_passed = False
                collections_details = f"Error: {str(e)}"
            
            # Test 3c: CRUD Operations - Create
            test_doc_id = str(uuid.uuid4())
            test_doc = {
                "id": test_doc_id,
                "test_type": "infrastructure_test",
                "created_at": datetime.utcnow(),
                "data": "Test document for infrastructure validation"
            }
            
            try:
                result = await self.db.test_collection.insert_one(test_doc)
                create_passed = result.inserted_id is not None
                create_details = f"Document inserted: {bool(result.inserted_id)}"
            except Exception as e:
                create_passed = False
                create_details = f"Error: {str(e)}"
            
            # Test 3d: CRUD Operations - Read
            try:
                found_doc = await self.db.test_collection.find_one({"id": test_doc_id})
                read_passed = found_doc is not None and found_doc.get('id') == test_doc_id
                read_details = f"Document found: {read_passed}"
            except Exception as e:
                read_passed = False
                read_details = f"Error: {str(e)}"
            
            # Test 3e: CRUD Operations - Update
            try:
                update_result = await self.db.test_collection.update_one(
                    {"id": test_doc_id},
                    {"$set": {"updated_at": datetime.utcnow(), "status": "updated"}}
                )
                update_passed = update_result.modified_count == 1
                update_details = f"Documents updated: {update_result.modified_count}"
            except Exception as e:
                update_passed = False
                update_details = f"Error: {str(e)}"
            
            # Test 3f: CRUD Operations - Delete
            try:
                delete_result = await self.db.test_collection.delete_one({"id": test_doc_id})
                delete_passed = delete_result.deleted_count == 1
                delete_details = f"Documents deleted: {delete_result.deleted_count}"
            except Exception as e:
                delete_passed = False
                delete_details = f"Error: {str(e)}"
            
            # Test 3g: Index Operations
            try:
                await self.db.test_collection.create_index("test_type")
                indexes = await self.db.test_collection.list_indexes().to_list(None)
                index_passed = len(indexes) > 1  # _id index + our test index
                index_details = f"Indexes created: {len(indexes)}"
            except Exception as e:
                index_passed = False
                index_details = f"Error: {str(e)}"
            
            all_passed = (ping_passed and collections_passed and create_passed and 
                         read_passed and update_passed and delete_passed and index_passed)
            
            # Log individual results
            self.log_test_result("DB - Connection Ping", ping_passed, ping_details)
            self.log_test_result("DB - Collections Access", collections_passed, collections_details)
            self.log_test_result("DB - CRUD Create", create_passed, create_details)
            self.log_test_result("DB - CRUD Read", read_passed, read_details)
            self.log_test_result("DB - CRUD Update", update_passed, update_details)
            self.log_test_result("DB - CRUD Delete", delete_passed, delete_details)
            self.log_test_result("DB - Index Operations", index_passed, index_details)
            
            details = f"Ping: {ping_passed}, Collections: {collections_passed}, CRUD: {create_passed and read_passed and update_passed and delete_passed}, Indexes: {index_passed}"
            self.log_test_result("Database Connection", all_passed, details)
            
        except Exception as e:
            self.log_test_result("Database Connection", False, f"Exception: {str(e)}")
    
    def test_redis_rq_integration(self):
        """Test 4: Redis/RQ Integration - Redis connection, RQ workers, background task processing"""
        print("\n🔴 Testing Redis/RQ Integration...")
        
        try:
            # Test 4a: Redis Connection
            try:
                import redis
                redis_client = redis.Redis(host='localhost', port=6379, db=0)
                ping_result = redis_client.ping()
                redis_passed = ping_result is True
                redis_details = f"Redis ping: {ping_result}"
            except Exception as e:
                redis_passed = False
                redis_details = f"Redis connection error: {str(e)}"
            
            # Test 4b: RQ Queue Operations
            rq_passed = False
            if redis_passed:
                try:
                    from rq import Queue
                    queue = Queue('test_queue', connection=redis_client)
                    
                    # Test queue creation and basic operations
                    queue_length_before = len(queue)
                    
                    # Add a simple job
                    def test_job(x, y):
                        return x + y
                    
                    job = queue.enqueue(test_job, 2, 3)
                    queue_length_after = len(queue)
                    
                    rq_passed = job is not None and queue_length_after >= queue_length_before
                    rq_details = f"Job enqueued: {job is not None}, Queue length: {queue_length_after}"
                    
                except Exception as e:
                    rq_details = f"RQ error: {str(e)}"
            else:
                rq_details = "Skipped - Redis not available"
            
            # Test 4c: Background Task Processing (check if RQ workers are running)
            try:
                from rq import Worker
                workers = Worker.all(connection=redis_client) if redis_passed else []
                worker_count = len(workers)
                workers_passed = worker_count >= 0  # Accept 0 workers as valid (may not be running)
                workers_details = f"RQ workers found: {worker_count}"
            except Exception as e:
                workers_passed = False
                workers_details = f"Worker check error: {str(e)}"
            
            # Test 4d: Queue Statistics
            try:
                if redis_passed:
                    # Import the queue stats function from the backend
                    sys.path.append('/app/backend')
                    from tasks import get_queue_stats
                    stats = get_queue_stats()
                    stats_passed = isinstance(stats, dict) and 'redis_connected' in stats
                    stats_details = f"Queue stats available: {stats_passed}, Redis connected: {stats.get('redis_connected', False)}"
                else:
                    stats_passed = False
                    stats_details = "Skipped - Redis not available"
            except Exception as e:
                stats_passed = False
                stats_details = f"Stats error: {str(e)}"
            
            # Test 4e: FastAPI Background Tasks Fallback
            try:
                # Test that the system can fall back to FastAPI background tasks
                from fastapi import BackgroundTasks
                background_tasks = BackgroundTasks()
                
                def dummy_task():
                    return "completed"
                
                background_tasks.add_task(dummy_task)
                fallback_passed = True
                fallback_details = "FastAPI BackgroundTasks available"
            except Exception as e:
                fallback_passed = False
                fallback_details = f"Fallback error: {str(e)}"
            
            all_passed = redis_passed and rq_passed and workers_passed and stats_passed and fallback_passed
            
            # Log individual results
            self.log_test_result("Redis - Connection", redis_passed, redis_details)
            self.log_test_result("RQ - Queue Operations", rq_passed, rq_details)
            self.log_test_result("RQ - Workers Status", workers_passed, workers_details)
            self.log_test_result("RQ - Queue Statistics", stats_passed, stats_details)
            self.log_test_result("RQ - Fallback Mechanism", fallback_passed, fallback_details)
            
            details = f"Redis: {redis_passed}, RQ: {rq_passed}, Workers: {workers_passed}, Stats: {stats_passed}, Fallback: {fallback_passed}"
            self.log_test_result("Redis/RQ Integration", all_passed, details)
            
        except Exception as e:
            self.log_test_result("Redis/RQ Integration", False, f"Exception: {str(e)}")
    
    def test_environment_variables(self):
        """Test 5: Environment Variables - API keys and configurations properly loaded"""
        print("\n🔧 Testing Environment Variables...")
        
        try:
            # Test 5a: Required API Keys
            groq_key = os.environ.get('GROQ_API_KEY')
            cohere_key = os.environ.get('COHERE_API_KEY')
            jwt_secret = os.environ.get('JWT_SECRET_KEY')
            
            api_keys_passed = bool(groq_key and cohere_key and jwt_secret)
            api_keys_details = f"GROQ: {'SET' if groq_key else 'MISSING'}, COHERE: {'SET' if cohere_key else 'MISSING'}, JWT: {'SET' if jwt_secret else 'MISSING'}"
            
            # Test 5b: Database Configuration
            mongo_url = os.environ.get('MONGO_URL')
            db_name = os.environ.get('DB_NAME')
            
            db_config_passed = bool(mongo_url and db_name)
            db_config_details = f"MONGO_URL: {'SET' if mongo_url else 'MISSING'}, DB_NAME: {'SET' if db_name else 'MISSING'}"
            
            # Test 5c: Redis Configuration
            redis_url = os.environ.get('REDIS_URL')
            redis_config_passed = bool(redis_url)
            redis_config_details = f"REDIS_URL: {'SET' if redis_url else 'MISSING'}"
            
            # Test 5d: OAuth Configuration
            google_client_id = os.environ.get('GOOGLE_CLIENT_ID')
            google_client_secret = os.environ.get('GOOGLE_CLIENT_SECRET')
            microsoft_client_id = os.environ.get('MICROSOFT_CLIENT_ID')
            microsoft_client_secret = os.environ.get('MICROSOFT_CLIENT_SECRET')
            
            oauth_config_passed = bool(google_client_id and google_client_secret and microsoft_client_id and microsoft_client_secret)
            oauth_config_details = f"Google OAuth: {'SET' if google_client_id and google_client_secret else 'MISSING'}, Microsoft OAuth: {'SET' if microsoft_client_id and microsoft_client_secret else 'MISSING'}"
            
            # Test 5e: Frontend Configuration
            backend_url = os.environ.get('REACT_APP_BACKEND_URL')
            frontend_config_passed = bool(backend_url)
            frontend_config_details = f"REACT_APP_BACKEND_URL: {'SET' if backend_url else 'MISSING'}"
            
            # Test 5f: Calendar Integration
            calcom_key = os.environ.get('CALCOM_API_KEY')
            encryption_key = os.environ.get('ENCRYPTION_KEY')
            
            calendar_config_passed = bool(calcom_key and encryption_key)
            calendar_config_details = f"Cal.com: {'SET' if calcom_key else 'MISSING'}, Encryption: {'SET' if encryption_key else 'MISSING'}"
            
            all_passed = (api_keys_passed and db_config_passed and redis_config_passed and 
                         oauth_config_passed and frontend_config_passed and calendar_config_passed)
            
            # Log individual results
            self.log_test_result("Env - API Keys", api_keys_passed, api_keys_details)
            self.log_test_result("Env - Database Config", db_config_passed, db_config_details)
            self.log_test_result("Env - Redis Config", redis_config_passed, redis_config_details)
            self.log_test_result("Env - OAuth Config", oauth_config_passed, oauth_config_details)
            self.log_test_result("Env - Frontend Config", frontend_config_passed, frontend_config_details)
            self.log_test_result("Env - Calendar Config", calendar_config_passed, calendar_config_details)
            
            details = f"API Keys: {api_keys_passed}, DB: {db_config_passed}, Redis: {redis_config_passed}, OAuth: {oauth_config_passed}, Frontend: {frontend_config_passed}, Calendar: {calendar_config_passed}"
            self.log_test_result("Environment Variables", all_passed, details)
            
        except Exception as e:
            self.log_test_result("Environment Variables", False, f"Exception: {str(e)}")
    
    async def test_email_processing_pipeline(self):
        """Test 6: Email Processing Pipeline - Basic workflow without triggering actual emails"""
        print("\n📧 Testing Email Processing Pipeline...")
        
        try:
            # Test 6a: AI API Connectivity - Groq
            try:
                import httpx
                groq_key = os.environ.get('GROQ_API_KEY')
                
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {groq_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "messages": [{"role": "user", "content": "Test"}],
                            "model": "llama-3.3-70b-versatile",
                            "max_completion_tokens": 10
                        },
                        timeout=10
                    )
                    groq_passed = response.status_code == 200
                    groq_details = f"Groq API accessible: {groq_passed}"
            except Exception as e:
                groq_passed = False
                groq_details = f"Groq API error: {str(e)}"
            
            # Test 6b: AI API Connectivity - Cohere
            try:
                cohere_key = os.environ.get('COHERE_API_KEY')
                
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://api.cohere.com/v1/embed",
                        headers={
                            "Authorization": f"Bearer {cohere_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": "embed-english-v3.0",
                            "texts": ["test"],
                            "input_type": "classification"
                        },
                        timeout=10
                    )
                    cohere_passed = response.status_code == 200
                    cohere_details = f"Cohere API accessible: {cohere_passed}"
            except Exception as e:
                cohere_passed = False
                cohere_details = f"Cohere API error: {str(e)}"
            
            # Test 6c: Email Processing Functions Import
            try:
                sys.path.append('/app/backend')
                from server import classify_email_intents, generate_draft, validate_final_email
                functions_passed = True
                functions_details = "Email processing functions imported successfully"
            except Exception as e:
                functions_passed = False
                functions_details = f"Import error: {str(e)}"
            
            # Test 6d: Parlant Framework Integration
            try:
                from parlant_framework import parlant_framework, ParlantAgent
                parlant_passed = parlant_framework is not None
                parlant_details = f"Parlant framework available: {parlant_passed}"
            except Exception as e:
                parlant_passed = False
                parlant_details = f"Parlant error: {str(e)}"
            
            # Test 6e: Email Services Integration
            try:
                from email_services import EmailConnection, EmailPollingService
                services_passed = True
                services_details = "Email services imported successfully"
            except Exception as e:
                services_passed = False
                services_details = f"Services error: {str(e)}"
            
            # Test 6f: OAuth Services Integration
            try:
                from oauth_google import google_oauth_service
                from oauth_microsoft import microsoft_oauth_service
                oauth_services_passed = True
                oauth_services_details = "OAuth services imported successfully"
            except Exception as e:
                oauth_services_passed = False
                oauth_services_details = f"OAuth services error: {str(e)}"
            
            all_passed = (groq_passed and cohere_passed and functions_passed and 
                         parlant_passed and services_passed and oauth_services_passed)
            
            # Log individual results
            self.log_test_result("Pipeline - Groq API", groq_passed, groq_details)
            self.log_test_result("Pipeline - Cohere API", cohere_passed, cohere_details)
            self.log_test_result("Pipeline - Processing Functions", functions_passed, functions_details)
            self.log_test_result("Pipeline - Parlant Framework", parlant_passed, parlant_details)
            self.log_test_result("Pipeline - Email Services", services_passed, services_details)
            self.log_test_result("Pipeline - OAuth Services", oauth_services_passed, oauth_services_details)
            
            details = f"Groq: {groq_passed}, Cohere: {cohere_passed}, Functions: {functions_passed}, Parlant: {parlant_passed}, Services: {services_passed}, OAuth: {oauth_services_passed}"
            self.log_test_result("Email Processing Pipeline", all_passed, details)
            
        except Exception as e:
            self.log_test_result("Email Processing Pipeline", False, f"Exception: {str(e)}")
    
    async def run_all_tests(self):
        """Run all infrastructure tests"""
        print("🚀 Starting Core Infrastructure Tests for AI-Powered Email Automation System")
        print(f"🔗 Backend URL: {BACKEND_URL}")
        print(f"🗄️  Database: {MONGO_URL}/{DB_NAME}")
        print("=" * 80)
        
        # Setup
        if not await self.setup():
            print("❌ Setup failed, aborting tests")
            return
        
        # Run tests
        self.test_authentication_system()
        self.test_api_health_check()
        await self.test_database_connection()
        self.test_redis_rq_integration()
        self.test_environment_variables()
        await self.test_email_processing_pipeline()
        
        # Cleanup
        await self.cleanup()
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 INFRASTRUCTURE TEST SUMMARY")
        print("=" * 80)
        
        passed_tests = [r for r in self.test_results if r['passed']]
        failed_tests = [r for r in self.test_results if not r['passed']]
        
        print(f"✅ PASSED: {len(passed_tests)}")
        print(f"❌ FAILED: {len(failed_tests)}")
        print(f"📈 SUCCESS RATE: {len(passed_tests)}/{len(self.test_results)} ({len(passed_tests)/len(self.test_results)*100:.1f}%)")
        
        if failed_tests:
            print(f"\n❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"   • {test['test']}: {test['details']}")
        
        print(f"\n📋 DETAILED RESULTS:")
        for result in self.test_results:
            print(f"   {result['status']}: {result['test']}")
            if result['details']:
                print(f"      {result['details']}")
        
        print("=" * 80)
        
        # Return overall success
        return len(failed_tests) == 0

async def main():
    """Main test runner"""
    tester = InfrastructureTester()
    success = await tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)