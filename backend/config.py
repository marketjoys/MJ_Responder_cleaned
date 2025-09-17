"""
Production-ready configuration management
"""
import os
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

class RedisConfig(BaseModel):
    """Redis configuration"""
    host: str = Field(default=os.getenv("REDIS_HOST", "localhost"))
    port: int = Field(default=int(os.getenv("REDIS_PORT", "6379")))
    password: str = Field(default=os.getenv("REDIS_PASSWORD", ""))
    db: int = Field(default=int(os.getenv("REDIS_DB", "0")))
    max_connections: int = Field(default=100)
    socket_keepalive: bool = Field(default=True)
    socket_keepalive_options: Dict[int, int] = Field(default={})
    
    @property
    def url(self) -> str:
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"

class APIKeyRotationConfig(BaseModel):
    """API key rotation configuration"""
    groq_keys: List[str] = Field(default_factory=lambda: [
        key.strip() for key in os.getenv("GROQ_API_KEYS", os.getenv("GROQ_API_KEY", "")).split(",") 
        if key.strip()
    ])
    cohere_keys: List[str] = Field(default_factory=lambda: [
        key.strip() for key in os.getenv("COHERE_API_KEYS", os.getenv("COHERE_API_KEY", "")).split(",") 
        if key.strip()
    ])
    
    # Rate limits per key per minute
    groq_rate_limit_per_key: int = Field(default=int(os.getenv("GROQ_RATE_LIMIT_PER_KEY", "6000")))
    cohere_rate_limit_per_key: int = Field(default=int(os.getenv("COHERE_RATE_LIMIT_PER_KEY", "1000")))
    
    # Circuit breaker settings
    failure_threshold: int = Field(default=5)
    recovery_timeout: int = Field(default=60)
    expected_exception: tuple = Field(default=(Exception,))

class EmailProcessingConfig(BaseModel):
    """Email processing configuration for high-volume handling"""
    
    # Queue settings
    max_queue_size: int = Field(default=10000)
    batch_size: int = Field(default=50)  # Process emails in batches
    max_workers: int = Field(default=int(os.getenv("MAX_WORKERS", "10")))
    
    # Processing timeouts
    intent_classification_timeout: int = Field(default=30)
    draft_generation_timeout: int = Field(default=45)
    validation_timeout: int = Field(default=20)
    
    # Retry settings
    max_retries: int = Field(default=3)
    retry_delay: int = Field(default=5)
    exponential_backoff: bool = Field(default=True)
    
    # Cache settings
    intent_cache_ttl: int = Field(default=3600)  # 1 hour
    knowledge_base_cache_ttl: int = Field(default=7200)  # 2 hours
    
    # Connection pooling
    imap_connection_pool_size: int = Field(default=20)
    smtp_connection_pool_size: int = Field(default=10)
    connection_max_age: int = Field(default=3600)  # 1 hour

class MonitoringConfig(BaseModel):
    """Monitoring and health check configuration"""
    
    # Health check intervals
    health_check_interval: int = Field(default=30)
    api_health_check_interval: int = Field(default=60)
    
    # Metrics
    enable_prometheus: bool = Field(default=True)
    metrics_port: int = Field(default=8090)
    
    # Performance thresholds
    max_processing_time: int = Field(default=300)  # 5 minutes
    max_queue_length: int = Field(default=5000)
    memory_threshold_mb: int = Field(default=1024)

class DatabaseConfig(BaseModel):
    """Database configuration for high concurrency"""
    
    mongo_url: str = Field(default=os.getenv("MONGO_URL", ""))
    db_name: str = Field(default=os.getenv("DB_NAME", "email_assistant"))
    
    # Connection pooling
    max_pool_size: int = Field(default=100)
    min_pool_size: int = Field(default=10)
    max_idle_time_ms: int = Field(default=30000)
    
    # Write concerns for high-volume
    write_concern: str = Field(default="majority")
    read_preference: str = Field(default="primary")

class ProductionConfig:
    """Main production configuration"""
    
    def __init__(self):
        self.redis = RedisConfig()
        self.api_keys = APIKeyRotationConfig()
        self.email_processing = EmailProcessingConfig()
        self.monitoring = MonitoringConfig()
        self.database = DatabaseConfig()
        
        # Validate configuration
        self._validate_config()
    
    def _validate_config(self):
        """Validate configuration for production readiness"""
        if not self.api_keys.groq_keys:
            raise ValueError("At least one Groq API key must be provided")
        
        if not self.api_keys.cohere_keys:
            raise ValueError("At least one Cohere API key must be provided")
        
        if not self.database.mongo_url:
            raise ValueError("MongoDB URL must be provided")

# Global configuration instance
config = ProductionConfig()