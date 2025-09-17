"""
Production Cache Manager for high-performance email processing
Handles intent classification caching, knowledge base caching, and result memoization
"""
import hashlib
import json
import logging
import time
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
import pickle
import asyncio

from redis_manager import redis_manager
from config import config

logger = logging.getLogger(__name__)

class ProductionCacheManager:
    """High-performance cache manager with intelligent invalidation and compression"""
    
    def __init__(self):
        self.redis = None
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0
        }
        
        # Cache key prefixes
        self.INTENT_CACHE_PREFIX = "intent_cache:"
        self.KNOWLEDGE_BASE_CACHE_PREFIX = "kb_cache:"
        self.EMBEDDING_CACHE_PREFIX = "embedding_cache:"
        self.DRAFT_CACHE_PREFIX = "draft_cache:"
        self.VALIDATION_CACHE_PREFIX = "validation_cache:"
        self.EMAIL_SIMILARITY_PREFIX = "email_sim:"
        
        # Cache TTLs (in seconds)
        self.INTENT_CACHE_TTL = config.email_processing.intent_cache_ttl
        self.KNOWLEDGE_BASE_CACHE_TTL = config.email_processing.knowledge_base_cache_ttl
        self.EMBEDDING_CACHE_TTL = 7200  # 2 hours
        self.DRAFT_CACHE_TTL = 1800      # 30 minutes
        self.VALIDATION_CACHE_TTL = 1800 # 30 minutes
        self.EMAIL_SIMILARITY_TTL = 3600 # 1 hour
    
    async def initialize(self):
        """Initialize the cache manager"""
        try:
            self.redis = redis_manager.redis_async
            
            # Warm up cache with frequently used data
            await self._warm_up_cache()
            
            # Start background cleanup task
            asyncio.create_task(self._cache_cleanup_task())
            
            logger.info("✅ Production cache manager initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize cache manager: {e}")
            raise
    
    def _generate_cache_key(self, prefix: str, data: Union[str, Dict, List]) -> str:
        """Generate a consistent cache key from data"""
        if isinstance(data, str):
            content = data
        else:
            content = json.dumps(data, sort_keys=True)
        
        # Create hash for consistent key generation
        hash_object = hashlib.sha256(content.encode())
        hash_hex = hash_object.hexdigest()[:16]  # Use first 16 chars for shorter keys
        
        return f"{prefix}{hash_hex}"
    
    async def _warm_up_cache(self):
        """Warm up cache with frequently used data"""
        try:
            # This could be enhanced to pre-load common intents, knowledge base items, etc.
            logger.info("🔥 Cache warm-up completed")
            
        except Exception as e:
            logger.warning(f"⚠️ Cache warm-up failed: {e}")
    
    # Intent Classification Caching
    async def get_cached_intent_classification(self, email_body: str, email_subject: str = "") -> Optional[List[Dict[str, Any]]]:
        """Get cached intent classification result"""
        try:
            cache_key = self._generate_cache_key(
                self.INTENT_CACHE_PREFIX, 
                {"body": email_body, "subject": email_subject}
            )
            
            cached_result = await self.redis.get(cache_key)
            if cached_result:
                self.cache_stats["hits"] += 1
                result = json.loads(cached_result)
                logger.debug(f"✅ Intent cache hit for key: {cache_key[:20]}...")
                return result
            
            self.cache_stats["misses"] += 1
            return None
            
        except Exception as e:
            self.cache_stats["errors"] += 1
            logger.warning(f"⚠️ Failed to get cached intent classification: {e}")
            return None
    
    async def cache_intent_classification(self, email_body: str, email_subject: str, intents: List[Dict[str, Any]]) -> bool:
        """Cache intent classification result"""
        try:
            cache_key = self._generate_cache_key(
                self.INTENT_CACHE_PREFIX, 
                {"body": email_body, "subject": email_subject}
            )
            
            # Add timestamp to cached data
            cached_data = {
                "intents": intents,
                "timestamp": time.time(),
                "email_hash": hashlib.md5(email_body.encode()).hexdigest()[:8]
            }
            
            await self.redis.setex(
                cache_key, 
                self.INTENT_CACHE_TTL, 
                json.dumps(cached_data)
            )
            
            self.cache_stats["sets"] += 1
            logger.debug(f"✅ Cached intent classification for key: {cache_key[:20]}...")
            return True
            
        except Exception as e:
            self.cache_stats["errors"] += 1
            logger.warning(f"⚠️ Failed to cache intent classification: {e}")
            return False
    
    # Embedding Caching
    async def get_cached_embedding(self, text: str) -> Optional[List[float]]:
        """Get cached embedding"""
        try:
            cache_key = self._generate_cache_key(self.EMBEDDING_CACHE_PREFIX, text)
            
            cached_result = await self.redis.get(cache_key)
            if cached_result:
                self.cache_stats["hits"] += 1
                # Embeddings are stored as pickled binary data for efficiency
                embedding = pickle.loads(cached_result.encode('latin1'))
                logger.debug(f"✅ Embedding cache hit for text length: {len(text)}")
                return embedding
            
            self.cache_stats["misses"] += 1
            return None
            
        except Exception as e:
            self.cache_stats["errors"] += 1
            logger.warning(f"⚠️ Failed to get cached embedding: {e}")
            return None
    
    async def cache_embedding(self, text: str, embedding: List[float]) -> bool:
        """Cache embedding result"""
        try:
            cache_key = self._generate_cache_key(self.EMBEDDING_CACHE_PREFIX, text)
            
            # Use pickle for efficient binary storage of embeddings
            binary_data = pickle.dumps(embedding).decode('latin1')
            
            await self.redis.setex(
                cache_key, 
                self.EMBEDDING_CACHE_TTL, 
                binary_data
            )
            
            self.cache_stats["sets"] += 1
            logger.debug(f"✅ Cached embedding for text length: {len(text)}")
            return True
            
        except Exception as e:
            self.cache_stats["errors"] += 1
            logger.warning(f"⚠️ Failed to cache embedding: {e}")
            return False
    
    # Knowledge Base Caching
    async def get_cached_knowledge_context(self, query_hash: str) -> Optional[Dict[str, Any]]:
        """Get cached knowledge base context"""
        try:
            cache_key = f"{self.KNOWLEDGE_BASE_CACHE_PREFIX}{query_hash}"
            
            cached_result = await self.redis.get(cache_key)
            if cached_result:
                self.cache_stats["hits"] += 1
                result = json.loads(cached_result)
                logger.debug(f"✅ Knowledge base cache hit")
                return result
            
            self.cache_stats["misses"] += 1
            return None
            
        except Exception as e:
            self.cache_stats["errors"] += 1
            logger.warning(f"⚠️ Failed to get cached knowledge base context: {e}")
            return None
    
    async def cache_knowledge_context(self, query_hash: str, context_data: Dict[str, Any]) -> bool:
        """Cache knowledge base context"""
        try:
            cache_key = f"{self.KNOWLEDGE_BASE_CACHE_PREFIX}{query_hash}"
            
            cached_data = {
                **context_data,
                "timestamp": time.time()
            }
            
            await self.redis.setex(
                cache_key, 
                self.KNOWLEDGE_BASE_CACHE_TTL, 
                json.dumps(cached_data)
            )
            
            self.cache_stats["sets"] += 1
            logger.debug(f"✅ Cached knowledge base context")
            return True
            
        except Exception as e:
            self.cache_stats["errors"] += 1
            logger.warning(f"⚠️ Failed to cache knowledge base context: {e}")
            return False
    
    # Draft Caching
    async def get_cached_draft(self, email_body: str, intents: List[Dict[str, Any]]) -> Optional[Dict[str, str]]:
        """Get cached draft result"""
        try:
            cache_data = {
                "email_body": email_body,
                "intents": [{"name": i["name"], "confidence": i["confidence"]} for i in intents]
            }
            cache_key = self._generate_cache_key(self.DRAFT_CACHE_PREFIX, cache_data)
            
            cached_result = await self.redis.get(cache_key)
            if cached_result:
                self.cache_stats["hits"] += 1
                result = json.loads(cached_result)
                logger.debug(f"✅ Draft cache hit")
                return result
            
            self.cache_stats["misses"] += 1
            return None
            
        except Exception as e:
            self.cache_stats["errors"] += 1
            logger.warning(f"⚠️ Failed to get cached draft: {e}")
            return None
    
    async def cache_draft(self, email_body: str, intents: List[Dict[str, Any]], draft_result: Dict[str, str]) -> bool:
        """Cache draft result"""
        try:
            cache_data = {
                "email_body": email_body,
                "intents": [{"name": i["name"], "confidence": i["confidence"]} for i in intents]
            }
            cache_key = self._generate_cache_key(self.DRAFT_CACHE_PREFIX, cache_data)
            
            cached_draft = {
                **draft_result,
                "timestamp": time.time()
            }
            
            await self.redis.setex(
                cache_key, 
                self.DRAFT_CACHE_TTL, 
                json.dumps(cached_draft)
            )
            
            self.cache_stats["sets"] += 1
            logger.debug(f"✅ Cached draft result")
            return True
            
        except Exception as e:
            self.cache_stats["errors"] += 1
            logger.warning(f"⚠️ Failed to cache draft: {e}")
            return False
    
    # Email Similarity Caching for Deduplication
    async def check_similar_email(self, email_body: str, threshold: float = 0.8) -> Optional[Dict[str, Any]]:
        """Check if a similar email has been processed recently"""
        try:
            # Generate hash for current email
            email_hash = hashlib.md5(email_body.encode()).hexdigest()
            
            # Look for similar emails in the last 24 hours
            pattern = f"{self.EMAIL_SIMILARITY_PREFIX}*"
            similar_keys = []
            
            async for key in self.redis.scan_iter(pattern):
                cached_data = await self.redis.get(key)
                if cached_data:
                    data = json.loads(cached_data)
                    # Simple similarity check - could be enhanced with more sophisticated algorithms
                    if self._calculate_text_similarity(email_body, data.get("body", "")) >= threshold:
                        similar_keys.append(data)
            
            if similar_keys:
                # Return the most recent similar email
                return max(similar_keys, key=lambda x: x.get("timestamp", 0))
            
            return None
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to check similar email: {e}")
            return None
    
    async def cache_email_similarity(self, email_body: str, processing_result: Dict[str, Any]) -> bool:
        """Cache email for similarity checking"""
        try:
            email_hash = hashlib.md5(email_body.encode()).hexdigest()
            cache_key = f"{self.EMAIL_SIMILARITY_PREFIX}{email_hash}"
            
            similarity_data = {
                "body": email_body[:500],  # Store first 500 chars for similarity checking
                "processing_result": processing_result,
                "timestamp": time.time()
            }
            
            await self.redis.setex(
                cache_key, 
                self.EMAIL_SIMILARITY_TTL, 
                json.dumps(similarity_data)
            )
            
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to cache email similarity: {e}")
            return False
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity (can be enhanced with more sophisticated algorithms)"""
        try:
            # Simple word-based similarity
            words1 = set(text1.lower().split())
            words2 = set(text2.lower().split())
            
            if not words1 or not words2:
                return 0.0
            
            intersection = words1.intersection(words2)
            union = words1.union(words2)
            
            return len(intersection) / len(union) if union else 0.0
            
        except Exception:
            return 0.0
    
    # Batch Operations for High Performance
    async def get_multiple_cached_embeddings(self, texts: List[str]) -> Dict[str, Optional[List[float]]]:
        """Get multiple cached embeddings in a single operation"""
        try:
            cache_keys = [self._generate_cache_key(self.EMBEDDING_CACHE_PREFIX, text) for text in texts]
            
            # Use pipeline for efficient batch operation
            pipe = self.redis.pipeline()
            for key in cache_keys:
                pipe.get(key)
            
            results = await pipe.execute()
            
            cached_embeddings = {}
            for i, (text, result) in enumerate(zip(texts, results)):
                if result:
                    try:
                        embedding = pickle.loads(result.encode('latin1'))
                        cached_embeddings[text] = embedding
                        self.cache_stats["hits"] += 1
                    except Exception:
                        cached_embeddings[text] = None
                        self.cache_stats["errors"] += 1
                else:
                    cached_embeddings[text] = None
                    self.cache_stats["misses"] += 1
            
            return cached_embeddings
            
        except Exception as e:
            self.cache_stats["errors"] += 1
            logger.warning(f"⚠️ Failed to get multiple cached embeddings: {e}")
            return {text: None for text in texts}
    
    async def cache_multiple_embeddings(self, text_embedding_pairs: Dict[str, List[float]]) -> int:
        """Cache multiple embeddings in a single operation"""
        try:
            pipe = self.redis.pipeline()
            cached_count = 0
            
            for text, embedding in text_embedding_pairs.items():
                cache_key = self._generate_cache_key(self.EMBEDDING_CACHE_PREFIX, text)
                binary_data = pickle.dumps(embedding).decode('latin1')
                pipe.setex(cache_key, self.EMBEDDING_CACHE_TTL, binary_data)
                cached_count += 1
            
            await pipe.execute()
            self.cache_stats["sets"] += cached_count
            
            logger.debug(f"✅ Cached {cached_count} embeddings in batch")
            return cached_count
            
        except Exception as e:
            self.cache_stats["errors"] += 1
            logger.warning(f"⚠️ Failed to cache multiple embeddings: {e}")
            return 0
    
    # Cache Management
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate cache entries matching a pattern"""
        try:
            deleted_count = 0
            async for key in self.redis.scan_iter(pattern):
                await self.redis.delete(key)
                deleted_count += 1
            
            self.cache_stats["deletes"] += deleted_count
            logger.info(f"✅ Invalidated {deleted_count} cache entries matching pattern: {pattern}")
            return deleted_count
            
        except Exception as e:
            self.cache_stats["errors"] += 1
            logger.warning(f"⚠️ Failed to invalidate cache pattern {pattern}: {e}")
            return 0
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        try:
            # Get Redis info
            redis_info = await self.redis.info()
            
            # Calculate hit rate
            total_requests = self.cache_stats["hits"] + self.cache_stats["misses"]
            hit_rate = (self.cache_stats["hits"] / total_requests * 100) if total_requests > 0 else 0
            
            stats = {
                **self.cache_stats,
                "hit_rate_percent": round(hit_rate, 2),
                "total_requests": total_requests,
                "redis_memory_used": redis_info.get("used_memory_human", "0B"),
                "redis_connected_clients": redis_info.get("connected_clients", 0),
                "redis_commands_processed": redis_info.get("total_commands_processed", 0)
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Failed to get cache stats: {e}")
            return self.cache_stats
    
    async def _cache_cleanup_task(self):
        """Background task to clean up expired cache entries"""
        while True:
            try:
                # This is handled automatically by Redis TTL, but we can add custom cleanup logic here
                await asyncio.sleep(300)  # Run every 5 minutes
                
                # Example: Clean up old similarity cache entries
                current_time = time.time()
                pattern = f"{self.EMAIL_SIMILARITY_PREFIX}*"
                
                cleaned = 0
                async for key in self.redis.scan_iter(pattern):
                    try:
                        cached_data = await self.redis.get(key)
                        if cached_data:
                            data = json.loads(cached_data)
                            if current_time - data.get("timestamp", 0) > self.EMAIL_SIMILARITY_TTL:
                                await self.redis.delete(key)
                                cleaned += 1
                    except Exception:
                        continue
                
                if cleaned > 0:
                    logger.info(f"🧹 Cleaned up {cleaned} expired cache entries")
                
            except Exception as e:
                logger.warning(f"⚠️ Cache cleanup task error: {e}")
                await asyncio.sleep(300)

# Global instance
cache_manager = ProductionCacheManager()