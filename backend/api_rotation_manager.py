"""
API Key Rotation Manager with Circuit Breaker Pattern
Handles multiple API keys for Groq and Cohere with automatic failover
"""
import asyncio
import httpx
import logging
import time
import random
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json

from config import config
from redis_manager import redis_manager

logger = logging.getLogger(__name__)

class APIProvider(Enum):
    GROQ = "groq"
    COHERE = "cohere"

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit is open, failing fast
    HALF_OPEN = "half_open"  # Testing if service is back

@dataclass
class APIKeyInfo:
    """Information about an API key"""
    key: str
    provider: APIProvider
    is_active: bool = True
    failure_count: int = 0
    last_failure: Optional[float] = None
    rate_limit_reset: Optional[float] = None
    requests_made: int = 0
    success_count: int = 0
    circuit_state: CircuitState = CircuitState.CLOSED
    last_state_change: float = field(default_factory=time.time)
    
    @property
    def is_rate_limited(self) -> bool:
        """Check if key is currently rate limited"""
        if not self.rate_limit_reset:
            return False
        return time.time() < self.rate_limit_reset
    
    @property
    def should_circuit_open(self) -> bool:
        """Check if circuit should open based on failure rate"""
        if self.failure_count >= config.api_keys.failure_threshold:
            return True
        
        # Check failure rate in recent requests
        if self.requests_made > 0:
            failure_rate = self.failure_count / self.requests_made
            return failure_rate > 0.5  # 50% failure rate
        
        return False

class ProductionAPIRotationManager:
    """Production-ready API key rotation with circuit breaker pattern"""
    
    def __init__(self):
        self.groq_keys: List[APIKeyInfo] = []
        self.cohere_keys: List[APIKeyInfo] = []
        self.redis = None
        
        # Circuit breaker settings
        self.failure_threshold = config.api_keys.failure_threshold
        self.recovery_timeout = config.api_keys.recovery_timeout
        
        # Rate limiting
        self.groq_rate_limit = config.api_keys.groq_rate_limit_per_key
        self.cohere_rate_limit = config.api_keys.cohere_rate_limit_per_key
        
        # HTTP clients with connection pooling
        self.http_clients: Dict[APIProvider, httpx.AsyncClient] = {}
        
    async def initialize(self):
        """Initialize the API rotation manager"""
        try:
            self.redis = redis_manager.redis_async
            
            # Initialize API keys
            self._initialize_api_keys()
            
            # Initialize HTTP clients with optimized settings
            await self._initialize_http_clients()
            
            # Load persisted key states from Redis
            await self._load_key_states()
            
            # Start background tasks
            asyncio.create_task(self._circuit_breaker_monitor())
            asyncio.create_task(self._rate_limit_monitor())
            
            logger.info(f"✅ API Rotation Manager initialized with {len(self.groq_keys)} Groq keys and {len(self.cohere_keys)} Cohere keys")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize API rotation manager: {e}")
            raise
    
    def _initialize_api_keys(self):
        """Initialize API key objects"""
        # Initialize Groq keys
        for key in config.api_keys.groq_keys:
            if key:  # Skip empty keys
                self.groq_keys.append(APIKeyInfo(
                    key=key,
                    provider=APIProvider.GROQ
                ))
        
        # Initialize Cohere keys
        for key in config.api_keys.cohere_keys:
            if key:  # Skip empty keys
                self.cohere_keys.append(APIKeyInfo(
                    key=key,
                    provider=APIProvider.COHERE
                ))
        
        if not self.groq_keys:
            raise ValueError("No valid Groq API keys provided")
        if not self.cohere_keys:
            raise ValueError("No valid Cohere API keys provided")
    
    async def _initialize_http_clients(self):
        """Initialize HTTP clients with optimal settings for high concurrency"""
        
        # Groq client
        self.http_clients[APIProvider.GROQ] = httpx.AsyncClient(
            limits=httpx.Limits(
                max_keepalive_connections=50,
                max_connections=100,
                keepalive_expiry=60
            ),
            timeout=httpx.Timeout(30.0, connect=10.0),
            headers={"Content-Type": "application/json"}
        )
        
        # Cohere client
        self.http_clients[APIProvider.COHERE] = httpx.AsyncClient(
            limits=httpx.Limits(
                max_keepalive_connections=30,
                max_connections=60,
                keepalive_expiry=60
            ),
            timeout=httpx.Timeout(20.0, connect=10.0),
            headers={"Content-Type": "application/json"}
        )
    
    async def _load_key_states(self):
        """Load persisted API key states from Redis"""
        try:
            for key_info in self.groq_keys + self.cohere_keys:
                key_state = await self.redis.hget("api_key_states", key_info.key)
                if key_state:
                    state_data = json.loads(key_state)
                    key_info.failure_count = state_data.get("failure_count", 0)
                    key_info.success_count = state_data.get("success_count", 0)
                    key_info.requests_made = state_data.get("requests_made", 0)
                    key_info.last_failure = state_data.get("last_failure")
                    key_info.rate_limit_reset = state_data.get("rate_limit_reset")
                    key_info.circuit_state = CircuitState(state_data.get("circuit_state", "closed"))
                    key_info.is_active = state_data.get("is_active", True)
        
        except Exception as e:
            logger.warning(f"⚠️ Failed to load API key states: {e}")
    
    async def _save_key_state(self, key_info: APIKeyInfo):
        """Save API key state to Redis"""
        try:
            state_data = {
                "failure_count": key_info.failure_count,
                "success_count": key_info.success_count,
                "requests_made": key_info.requests_made,
                "last_failure": key_info.last_failure,
                "rate_limit_reset": key_info.rate_limit_reset,
                "circuit_state": key_info.circuit_state.value,
                "is_active": key_info.is_active,
                "last_updated": time.time()
            }
            
            await self.redis.hset("api_key_states", key_info.key, json.dumps(state_data))
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to save API key state: {e}")
    
    async def get_available_key(self, provider: APIProvider) -> Optional[APIKeyInfo]:
        """Get an available API key using intelligent selection"""
        keys = self.groq_keys if provider == APIProvider.GROQ else self.cohere_keys
        
        # Filter available keys
        available_keys = [
            key for key in keys 
            if key.is_active 
            and key.circuit_state != CircuitState.OPEN 
            and not key.is_rate_limited
        ]
        
        if not available_keys:
            # Try half-open keys as last resort
            half_open_keys = [
                key for key in keys 
                if key.circuit_state == CircuitState.HALF_OPEN
            ]
            if half_open_keys:
                return half_open_keys[0]
            
            logger.warning(f"⚠️ No available {provider.value} keys")
            return None
        
        # Select key using weighted round-robin based on success rate
        return self._select_best_key(available_keys)
    
    def _select_best_key(self, keys: List[APIKeyInfo]) -> APIKeyInfo:
        """Select the best key based on performance metrics"""
        if len(keys) == 1:
            return keys[0]
        
        # Calculate weights based on success rate and recent performance
        weighted_keys = []
        for key in keys:
            # Base weight
            weight = 1.0
            
            # Success rate weight
            if key.requests_made > 0:
                success_rate = key.success_count / key.requests_made
                weight *= (success_rate + 0.1)  # Add small base to avoid zero weight
            
            # Failure penalty
            if key.failure_count > 0:
                failure_penalty = max(0.1, 1.0 - (key.failure_count / 10))
                weight *= failure_penalty
            
            # Recent failure penalty
            if key.last_failure and (time.time() - key.last_failure) < 300:  # 5 minutes
                weight *= 0.5
            
            weighted_keys.append((key, weight))
        
        # Select using weighted random selection
        total_weight = sum(weight for _, weight in weighted_keys)
        if total_weight == 0:
            return random.choice(keys)
        
        rand_val = random.uniform(0, total_weight)
        current_weight = 0
        
        for key, weight in weighted_keys:
            current_weight += weight
            if rand_val <= current_weight:
                return key
        
        return keys[0]  # Fallback
    
    async def make_groq_request(self, messages: List[Dict], system_prompt: str = "", max_retries: int = 3) -> str:
        """Make a Groq API request with automatic key rotation and circuit breaker"""
        
        for attempt in range(max_retries):
            key_info = await self.get_available_key(APIProvider.GROQ)
            if not key_info:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                continue
            
            try:
                # Prepare request
                if system_prompt:
                    messages = [{"role": "system", "content": system_prompt}] + messages
                
                payload = {
                    "messages": messages,
                    "model": "deepseek-r1-distill-llama-70b",
                    "temperature": 0.6,
                    "max_completion_tokens": 2048,
                    "top_p": 0.95,
                    "stream": False
                }
                
                # Make request
                client = self.http_clients[APIProvider.GROQ]
                response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {key_info.key}"},
                    json=payload
                )
                
                key_info.requests_made += 1
                
                if response.status_code == 200:
                    # Success
                    key_info.success_count += 1
                    key_info.circuit_state = CircuitState.CLOSED
                    await self._save_key_state(key_info)
                    
                    result = response.json()
                    return result["choices"][0]["message"]["content"]
                
                elif response.status_code == 429:
                    # Rate limit
                    await self._handle_rate_limit(key_info, response)
                    
                elif response.status_code in [401, 403]:
                    # Invalid key
                    await self._handle_invalid_key(key_info)
                    
                else:
                    # Other error
                    await self._handle_api_error(key_info, response.status_code, response.text)
                
            except asyncio.TimeoutError:
                await self._handle_timeout(key_info)
                
            except Exception as e:
                await self._handle_general_error(key_info, str(e))
            
            # Wait before retry
            if attempt < max_retries - 1:
                await asyncio.sleep(min(2 ** attempt, 10))
        
        raise Exception("All Groq API requests failed after retries")
    
    async def make_cohere_request(self, text: str, max_retries: int = 3) -> List[float]:
        """Make a Cohere API request with automatic key rotation"""
        
        for attempt in range(max_retries):
            key_info = await self.get_available_key(APIProvider.COHERE)
            if not key_info:
                await asyncio.sleep(2 ** attempt)
                continue
            
            try:
                payload = {
                    "model": "embed-english-v3.0",
                    "texts": [text],
                    "input_type": "classification",
                    "truncate": "NONE"
                }
                
                client = self.http_clients[APIProvider.COHERE]
                response = await client.post(
                    "https://api.cohere.com/v1/embed",
                    headers={"Authorization": f"Bearer {key_info.key}"},
                    json=payload
                )
                
                key_info.requests_made += 1
                
                if response.status_code == 200:
                    # Success
                    key_info.success_count += 1
                    key_info.circuit_state = CircuitState.CLOSED
                    await self._save_key_state(key_info)
                    
                    result = response.json()
                    return result["embeddings"][0]
                
                elif response.status_code == 429:
                    await self._handle_rate_limit(key_info, response)
                    
                elif response.status_code in [401, 403]:
                    await self._handle_invalid_key(key_info)
                    
                else:
                    await self._handle_api_error(key_info, response.status_code, response.text)
                
            except asyncio.TimeoutError:
                await self._handle_timeout(key_info)
                
            except Exception as e:
                await self._handle_general_error(key_info, str(e))
            
            if attempt < max_retries - 1:
                await asyncio.sleep(min(2 ** attempt, 10))
        
        raise Exception("All Cohere API requests failed after retries")
    
    async def _handle_rate_limit(self, key_info: APIKeyInfo, response: httpx.Response):
        """Handle rate limit response"""
        key_info.failure_count += 1
        
        # Extract rate limit reset time from headers
        reset_time = response.headers.get("x-ratelimit-reset-requests")
        if reset_time:
            try:
                key_info.rate_limit_reset = float(reset_time)
            except:
                key_info.rate_limit_reset = time.time() + 60  # Default 1 minute
        else:
            key_info.rate_limit_reset = time.time() + 60
        
        logger.warning(f"🚦 Rate limit hit for {key_info.provider.value} key ending in ...{key_info.key[-4:]}")
        await self._save_key_state(key_info)
    
    async def _handle_invalid_key(self, key_info: APIKeyInfo):
        """Handle invalid API key"""
        key_info.is_active = False
        key_info.failure_count += 1
        key_info.last_failure = time.time()
        
        logger.error(f"❌ Invalid {key_info.provider.value} API key ending in ...{key_info.key[-4:]}")
        await self._save_key_state(key_info)
    
    async def _handle_api_error(self, key_info: APIKeyInfo, status_code: int, error_text: str):
        """Handle general API errors"""
        key_info.failure_count += 1
        key_info.last_failure = time.time()
        
        if key_info.should_circuit_open:
            key_info.circuit_state = CircuitState.OPEN
            key_info.last_state_change = time.time()
        
        logger.warning(f"⚠️ API error for {key_info.provider.value} key: {status_code} - {error_text[:100]}")
        await self._save_key_state(key_info)
    
    async def _handle_timeout(self, key_info: APIKeyInfo):
        """Handle request timeout"""
        key_info.failure_count += 1
        key_info.last_failure = time.time()
        
        if key_info.should_circuit_open:
            key_info.circuit_state = CircuitState.OPEN
            key_info.last_state_change = time.time()
        
        logger.warning(f"⏰ Timeout for {key_info.provider.value} key ending in ...{key_info.key[-4:]}")
        await self._save_key_state(key_info)
    
    async def _handle_general_error(self, key_info: APIKeyInfo, error_msg: str):
        """Handle general errors"""
        key_info.failure_count += 1
        key_info.last_failure = time.time()
        
        logger.warning(f"⚠️ General error for {key_info.provider.value} key: {error_msg[:100]}")
        await self._save_key_state(key_info)
    
    async def _circuit_breaker_monitor(self):
        """Background task to monitor and manage circuit breaker states"""
        while True:
            try:
                current_time = time.time()
                
                for key_info in self.groq_keys + self.cohere_keys:
                    if key_info.circuit_state == CircuitState.OPEN:
                        # Check if recovery timeout has passed
                        if current_time - key_info.last_state_change >= self.recovery_timeout:
                            key_info.circuit_state = CircuitState.HALF_OPEN
                            key_info.last_state_change = current_time
                            logger.info(f"🔄 Circuit breaker half-open for {key_info.provider.value} key")
                            await self._save_key_state(key_info)
                    
                    elif key_info.circuit_state == CircuitState.HALF_OPEN:
                        # Reset failure count for testing
                        if current_time - key_info.last_state_change >= 30:  # 30 seconds
                            key_info.failure_count = 0
                            await self._save_key_state(key_info)
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"❌ Circuit breaker monitor error: {e}")
                await asyncio.sleep(30)
    
    async def _rate_limit_monitor(self):
        """Background task to reset rate limits"""
        while True:
            try:
                current_time = time.time()
                
                for key_info in self.groq_keys + self.cohere_keys:
                    if key_info.rate_limit_reset and current_time >= key_info.rate_limit_reset:
                        key_info.rate_limit_reset = None
                        logger.info(f"✅ Rate limit reset for {key_info.provider.value} key")
                        await self._save_key_state(key_info)
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"❌ Rate limit monitor error: {e}")
                await asyncio.sleep(10)
    
    async def get_api_stats(self) -> Dict[str, Any]:
        """Get comprehensive API statistics"""
        try:
            stats = {
                "groq": {
                    "total_keys": len(self.groq_keys),
                    "active_keys": sum(1 for k in self.groq_keys if k.is_active),
                    "closed_circuit_keys": sum(1 for k in self.groq_keys if k.circuit_state == CircuitState.CLOSED),
                    "open_circuit_keys": sum(1 for k in self.groq_keys if k.circuit_state == CircuitState.OPEN),
                    "rate_limited_keys": sum(1 for k in self.groq_keys if k.is_rate_limited),
                    "total_requests": sum(k.requests_made for k in self.groq_keys),
                    "total_successes": sum(k.success_count for k in self.groq_keys),
                    "total_failures": sum(k.failure_count for k in self.groq_keys)
                },
                "cohere": {
                    "total_keys": len(self.cohere_keys),
                    "active_keys": sum(1 for k in self.cohere_keys if k.is_active),
                    "closed_circuit_keys": sum(1 for k in self.cohere_keys if k.circuit_state == CircuitState.CLOSED),
                    "open_circuit_keys": sum(1 for k in self.cohere_keys if k.circuit_state == CircuitState.OPEN),
                    "rate_limited_keys": sum(1 for k in self.cohere_keys if k.is_rate_limited),
                    "total_requests": sum(k.requests_made for k in self.cohere_keys),
                    "total_successes": sum(k.success_count for k in self.cohere_keys),
                    "total_failures": sum(k.failure_count for k in self.cohere_keys)
                }
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Failed to get API stats: {e}")
            return {}
    
    async def close(self):
        """Close HTTP clients"""
        for client in self.http_clients.values():
            await client.aclose()

# Global instance
api_rotation_manager = ProductionAPIRotationManager()