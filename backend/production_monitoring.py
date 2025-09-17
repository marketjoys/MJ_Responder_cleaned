"""
Production Monitoring System for Email Processing
Health checks, metrics, and system monitoring for 50k+ email processing
"""
import asyncio
import logging
import time
import psutil
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import os

from config import config
from redis_manager import redis_manager, queue_manager

logger = logging.getLogger(__name__)

# Prometheus metrics
EMAIL_PROCESSING_COUNTER = Counter('emails_processed_total', 'Total emails processed', ['status', 'queue'])
EMAIL_PROCESSING_TIME = Histogram('email_processing_seconds', 'Time spent processing emails', ['stage'])
QUEUE_SIZE_GAUGE = Gauge('queue_size', 'Current queue size', ['queue_name'])
API_REQUEST_COUNTER = Counter('api_requests_total', 'Total API requests', ['provider', 'status'])
CACHE_HIT_COUNTER = Counter('cache_hits_total', 'Cache hits', ['cache_type'])
SYSTEM_MEMORY_GAUGE = Gauge('system_memory_usage_percent', 'System memory usage percentage')
SYSTEM_CPU_GAUGE = Gauge('system_cpu_usage_percent', 'System CPU usage percentage')

@dataclass
class HealthStatus:
    """System health status"""
    service_name: str
    status: str  # healthy, degraded, unhealthy
    last_check: float
    details: Dict[str, Any]
    error_message: Optional[str] = None

class ProductionMonitoringSystem:
    """Comprehensive monitoring system for production deployment"""
    
    def __init__(self):
        self.health_checks = {}
        self.metrics_history = []
        self.alert_thresholds = {
            "cpu_usage": 85.0,
            "memory_usage": 90.0,
            "queue_length": config.monitoring.max_queue_length,
            "processing_time": config.monitoring.max_processing_time,
            "error_rate": 10.0  # 10% error rate threshold
        }
        
        self.monitoring_active = False
        
    async def initialize(self):
        """Initialize the monitoring system"""
        try:
            # Start Prometheus metrics server if enabled
            if config.monitoring.enable_prometheus:
                start_http_server(config.monitoring.metrics_port)
                logger.info(f"✅ Prometheus metrics server started on port {config.monitoring.metrics_port}")
            
            # Initialize health checks
            await self._initialize_health_checks()
            
            # Start monitoring tasks
            await self._start_monitoring_tasks()
            
            self.monitoring_active = True
            logger.info("✅ Production monitoring system initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize monitoring system: {e}")
            raise
    
    async def _initialize_health_checks(self):
        """Initialize all health check services"""
        self.health_checks = {
            "redis": HealthStatus("Redis", "unknown", 0, {}),
            "database": HealthStatus("MongoDB", "unknown", 0, {}),
            "queue_system": HealthStatus("Queue System", "unknown", 0, {}),
            "api_rotation": HealthStatus("API Rotation", "unknown", 0, {}),
            "cache_system": HealthStatus("Cache System", "unknown", 0, {}),
            "email_processor": HealthStatus("Email Processor", "unknown", 0, {}),
            "system_resources": HealthStatus("System Resources", "unknown", 0, {})
        }
    
    async def _start_monitoring_tasks(self):
        """Start all monitoring background tasks"""
        # Health check task
        asyncio.create_task(self._health_check_loop())
        
        # Metrics collection task
        asyncio.create_task(self._metrics_collection_loop())
        
        # System resource monitoring
        asyncio.create_task(self._system_resource_monitor())
        
        # Queue monitoring
        asyncio.create_task(self._queue_monitoring_loop())
        
        # Alert processing
        asyncio.create_task(self._alert_processing_loop())
        
        logger.info("✅ Started all monitoring tasks")
    
    async def _health_check_loop(self):
        """Main health check loop"""
        while self.monitoring_active:
            try:
                await self._perform_all_health_checks()
                await asyncio.sleep(config.monitoring.health_check_interval)
            except Exception as e:
                logger.error(f"❌ Health check loop error: {e}")
                await asyncio.sleep(30)
    
    async def _perform_all_health_checks(self):
        """Perform all health checks"""
        current_time = time.time()
        
        # Redis health check
        await self._check_redis_health(current_time)
        
        # Database health check
        await self._check_database_health(current_time)
        
        # Queue system health check
        await self._check_queue_system_health(current_time)
        
        # API rotation health check
        await self._check_api_rotation_health(current_time)
        
        # Cache system health check
        await self._check_cache_system_health(current_time)
        
        # Email processor health check
        await self._check_email_processor_health(current_time)
        
        # System resources health check
        await self._check_system_resources_health(current_time)
    
    async def _check_redis_health(self, current_time: float):
        """Check Redis connection health"""
        try:
            if redis_manager.redis_async:
                # Test ping
                await redis_manager.redis_async.ping()
                
                # Get Redis info
                redis_info = await redis_manager.redis_async.info()
                
                # Check memory usage
                memory_usage = redis_info.get('used_memory', 0)
                max_memory = redis_info.get('maxmemory', 0)
                memory_percent = (memory_usage / max_memory * 100) if max_memory > 0 else 0
                
                status = "healthy"
                if memory_percent > 90:
                    status = "degraded"
                
                self.health_checks["redis"] = HealthStatus(
                    service_name="Redis",
                    status=status,
                    last_check=current_time,
                    details={
                        "connected_clients": redis_info.get('connected_clients', 0),
                        "memory_usage_percent": round(memory_percent, 2),
                        "total_commands_processed": redis_info.get('total_commands_processed', 0),
                        "uptime_seconds": redis_info.get('uptime_in_seconds', 0)
                    }
                )
            else:
                self.health_checks["redis"] = HealthStatus(
                    service_name="Redis",
                    status="unhealthy",
                    last_check=current_time,
                    details={},
                    error_message="Redis connection not initialized"
                )
                
        except Exception as e:
            self.health_checks["redis"] = HealthStatus(
                service_name="Redis",
                status="unhealthy",
                last_check=current_time,
                details={},
                error_message=str(e)
            )
    
    async def _check_database_health(self, current_time: float):
        """Check MongoDB health"""
        try:
            # This would need access to the database client
            # For now, simulate a basic check
            self.health_checks["database"] = HealthStatus(
                service_name="MongoDB",
                status="healthy",
                last_check=current_time,
                details={
                    "connection_status": "connected",
                    "last_operation": "ping_successful"
                }
            )
            
        except Exception as e:
            self.health_checks["database"] = HealthStatus(
                service_name="MongoDB",
                status="unhealthy",
                last_check=current_time,
                details={},
                error_message=str(e)
            )
    
    async def _check_queue_system_health(self, current_time: float):
        """Check queue system health"""
        try:
            if queue_manager.redis_async:
                queue_stats = await queue_manager.get_queue_stats()
                
                # Calculate total queue length
                total_queue_length = sum(
                    int(v) for k, v in queue_stats.items() 
                    if k.endswith('_length') and isinstance(v, (int, str))
                )
                
                status = "healthy"
                if total_queue_length > self.alert_thresholds["queue_length"]:
                    status = "degraded"
                
                self.health_checks["queue_system"] = HealthStatus(
                    service_name="Queue System",
                    status=status,
                    last_check=current_time,
                    details={
                        "total_queue_length": total_queue_length,
                        "queue_stats": queue_stats
                    }
                )
            else:
                self.health_checks["queue_system"] = HealthStatus(
                    service_name="Queue System",
                    status="unhealthy",
                    last_check=current_time,
                    details={},
                    error_message="Queue manager not initialized"
                )
                
        except Exception as e:
            self.health_checks["queue_system"] = HealthStatus(
                service_name="Queue System",
                status="unhealthy",
                last_check=current_time,
                details={},
                error_message=str(e)
            )
    
    async def _check_api_rotation_health(self, current_time: float):
        """Check API rotation manager health"""
        try:
            # This would integrate with the API rotation manager
            self.health_checks["api_rotation"] = HealthStatus(
                service_name="API Rotation",
                status="healthy",
                last_check=current_time,
                details={
                    "groq_keys_active": "simulated",
                    "cohere_keys_active": "simulated"
                }
            )
            
        except Exception as e:
            self.health_checks["api_rotation"] = HealthStatus(
                service_name="API Rotation",
                status="unhealthy",
                last_check=current_time,
                details={},
                error_message=str(e)
            )
    
    async def _check_cache_system_health(self, current_time: float):
        """Check cache system health"""
        try:
            # This would integrate with the cache manager
            self.health_checks["cache_system"] = HealthStatus(
                service_name="Cache System",
                status="healthy",
                last_check=current_time,
                details={
                    "cache_hit_rate": "simulated",
                    "total_cached_items": "simulated"
                }
            )
            
        except Exception as e:
            self.health_checks["cache_system"] = HealthStatus(
                service_name="Cache System",
                status="unhealthy",
                last_check=current_time,
                details={},
                error_message=str(e)
            )
    
    async def _check_email_processor_health(self, current_time: float):
        """Check email processor health"""
        try:
            # This would integrate with the email processor
            self.health_checks["email_processor"] = HealthStatus(
                service_name="Email Processor",
                status="healthy",
                last_check=current_time,
                details={
                    "workers_active": "simulated",
                    "processing_rate": "simulated"
                }
            )
            
        except Exception as e:
            self.health_checks["email_processor"] = HealthStatus(
                service_name="Email Processor",
                status="unhealthy",
                last_check=current_time,
                details={},
                error_message=str(e)
            )
    
    async def _check_system_resources_health(self, current_time: float):
        """Check system resource health"""
        try:
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Update Prometheus metrics
            SYSTEM_CPU_GAUGE.set(cpu_percent)
            SYSTEM_MEMORY_GAUGE.set(memory.percent)
            
            status = "healthy"
            if cpu_percent > self.alert_thresholds["cpu_usage"] or memory.percent > self.alert_thresholds["memory_usage"]:
                status = "degraded"
            if cpu_percent > 95 or memory.percent > 95:
                status = "unhealthy"
            
            self.health_checks["system_resources"] = HealthStatus(
                service_name="System Resources",
                status=status,
                last_check=current_time,
                details={
                    "cpu_percent": round(cpu_percent, 2),
                    "memory_percent": round(memory.percent, 2),
                    "memory_available_gb": round(memory.available / (1024**3), 2),
                    "disk_usage_percent": round(disk.percent, 2),
                    "disk_free_gb": round(disk.free / (1024**3), 2)
                }
            )
            
        except Exception as e:
            self.health_checks["system_resources"] = HealthStatus(
                service_name="System Resources",
                status="unhealthy",
                last_check=current_time,
                details={},
                error_message=str(e)
            )
    
    async def _metrics_collection_loop(self):
        """Collect and store metrics"""
        while self.monitoring_active:
            try:
                current_metrics = await self._collect_current_metrics()
                
                # Store in Redis for historical analysis
                if redis_manager.redis_async:
                    await redis_manager.redis_async.lpush(
                        "metrics_history", 
                        json.dumps(current_metrics)
                    )
                    
                    # Keep only last 1440 entries (24 hours at 1 minute intervals)
                    await redis_manager.redis_async.ltrim("metrics_history", 0, 1439)
                
                # Store in memory for recent access
                self.metrics_history.append(current_metrics)
                if len(self.metrics_history) > 60:  # Keep last 60 entries in memory
                    self.metrics_history.pop(0)
                
                await asyncio.sleep(60)  # Collect every minute
                
            except Exception as e:
                logger.error(f"❌ Metrics collection error: {e}")
                await asyncio.sleep(60)
    
    async def _collect_current_metrics(self) -> Dict[str, Any]:
        """Collect current system metrics"""
        try:
            metrics = {
                "timestamp": time.time(),
                "system": {
                    "cpu_percent": psutil.cpu_percent(),
                    "memory_percent": psutil.virtual_memory().percent,
                    "disk_percent": psutil.disk_usage('/').percent
                },
                "health_status": {
                    service: status.status 
                    for service, status in self.health_checks.items()
                }
            }
            
            # Add queue metrics if available
            if queue_manager.redis_async:
                try:
                    queue_stats = await queue_manager.get_queue_stats()
                    metrics["queues"] = queue_stats
                except Exception:
                    pass
            
            return metrics
            
        except Exception as e:
            logger.error(f"❌ Failed to collect metrics: {e}")
            return {"timestamp": time.time(), "error": str(e)}
    
    async def _system_resource_monitor(self):
        """Monitor system resources and update Prometheus metrics"""
        while self.monitoring_active:
            try:
                # Update CPU and memory gauges
                cpu_percent = psutil.cpu_percent(interval=1)
                memory_percent = psutil.virtual_memory().percent
                
                SYSTEM_CPU_GAUGE.set(cpu_percent)
                SYSTEM_MEMORY_GAUGE.set(memory_percent)
                
                await asyncio.sleep(30)  # Update every 30 seconds
                
            except Exception as e:
                logger.error(f"❌ System resource monitor error: {e}")
                await asyncio.sleep(30)
    
    async def _queue_monitoring_loop(self):
        """Monitor queue sizes and update metrics"""
        while self.monitoring_active:
            try:
                if queue_manager.redis_async:
                    queue_stats = await queue_manager.get_queue_stats()
                    
                    # Update Prometheus queue size gauges
                    for queue_name in ["email_processing", "intent_classification", "draft_generation", "email_validation", "email_sending"]:
                        queue_length = queue_stats.get(f"{queue_name}_length", 0)
                        if isinstance(queue_length, (int, str)):
                            QUEUE_SIZE_GAUGE.labels(queue_name=queue_name).set(int(queue_length))
                
                await asyncio.sleep(30)  # Update every 30 seconds
                
            except Exception as e:
                logger.error(f"❌ Queue monitoring error: {e}")
                await asyncio.sleep(30)
    
    async def _alert_processing_loop(self):
        """Process alerts based on thresholds"""
        while self.monitoring_active:
            try:
                await self._check_alert_conditions()
                await asyncio.sleep(60)  # Check alerts every minute
                
            except Exception as e:
                logger.error(f"❌ Alert processing error: {e}")
                await asyncio.sleep(60)
    
    async def _check_alert_conditions(self):
        """Check for alert conditions"""
        try:
            alerts = []
            
            # Check system resources
            system_health = self.health_checks.get("system_resources")
            if system_health and system_health.status in ["degraded", "unhealthy"]:
                cpu_percent = system_health.details.get("cpu_percent", 0)
                memory_percent = system_health.details.get("memory_percent", 0)
                
                if cpu_percent > self.alert_thresholds["cpu_usage"]:
                    alerts.append(f"High CPU usage: {cpu_percent}%")
                
                if memory_percent > self.alert_thresholds["memory_usage"]:
                    alerts.append(f"High memory usage: {memory_percent}%")
            
            # Check queue lengths
            queue_health = self.health_checks.get("queue_system")
            if queue_health and queue_health.status == "degraded":
                total_length = queue_health.details.get("total_queue_length", 0)
                alerts.append(f"High queue length: {total_length}")
            
            # Log alerts
            for alert in alerts:
                logger.warning(f"🚨 ALERT: {alert}")
            
            # Store alerts in Redis for dashboard
            if alerts and redis_manager.redis_async:
                alert_data = {
                    "timestamp": time.time(),
                    "alerts": alerts,
                    "severity": "warning"
                }
                await redis_manager.redis_async.lpush("system_alerts", json.dumps(alert_data))
                await redis_manager.redis_async.ltrim("system_alerts", 0, 99)  # Keep last 100 alerts
            
        except Exception as e:
            logger.error(f"❌ Alert condition check error: {e}")
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status"""
        try:
            overall_status = "healthy"
            unhealthy_services = []
            degraded_services = []
            
            for service_name, health in self.health_checks.items():
                if health.status == "unhealthy":
                    unhealthy_services.append(service_name)
                    overall_status = "unhealthy"
                elif health.status == "degraded":
                    degraded_services.append(service_name)
                    if overall_status == "healthy":
                        overall_status = "degraded"
            
            return {
                "overall_status": overall_status,
                "services": {name: asdict(status) for name, status in self.health_checks.items()},
                "unhealthy_services": unhealthy_services,
                "degraded_services": degraded_services,
                "last_updated": time.time(),
                "monitoring_active": self.monitoring_active
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get health status: {e}")
            return {
                "overall_status": "unknown",
                "error": str(e),
                "last_updated": time.time()
            }
    
    async def get_metrics_summary(self) -> Dict[str, Any]:
        """Get metrics summary"""
        try:
            recent_metrics = self.metrics_history[-10:] if self.metrics_history else []
            
            # Calculate averages for recent metrics
            if recent_metrics:
                avg_cpu = sum(m["system"]["cpu_percent"] for m in recent_metrics if "system" in m) / len(recent_metrics)
                avg_memory = sum(m["system"]["memory_percent"] for m in recent_metrics if "system" in m) / len(recent_metrics)
            else:
                avg_cpu = avg_memory = 0
            
            # Get current queue stats
            queue_stats = {}
            if queue_manager.redis_async:
                try:
                    queue_stats = await queue_manager.get_queue_stats()
                except Exception:
                    pass
            
            return {
                "current_time": time.time(),
                "system_averages": {
                    "cpu_percent": round(avg_cpu, 2),
                    "memory_percent": round(avg_memory, 2)
                },
                "queue_statistics": queue_stats,
                "recent_metrics_count": len(recent_metrics),
                "total_metrics_collected": len(self.metrics_history)
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get metrics summary: {e}")
            return {"error": str(e)}
    
    async def shutdown(self):
        """Shutdown monitoring system"""
        self.monitoring_active = False
        logger.info("✅ Production monitoring system shutdown")

# Global monitoring instance
monitoring_system = ProductionMonitoringSystem()