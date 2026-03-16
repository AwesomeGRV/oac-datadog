#!/usr/bin/env python3
"""
Enhanced Django and Celery ddtrace integration for grv-api.
Provides comprehensive tracing configuration with proper service tagging and deployment events.
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

# ddtrace imports
import ddtrace
from ddtrace import tracer, patch
from ddtrace.contrib.django import patch as django_patch
from ddtrace.contrib.celery import patch as celery_patch
from ddtrace.contrib.psycopg import patch as psycopg_patch
from ddtrace.contrib.redis import patch as redis_patch
from ddtrace.contrib.requests import patch as requests_patch

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GRVAPITracingConfig:
    """Enhanced tracing configuration for grv-api service."""
    
    def __init__(self):
        self.service_name = os.getenv('DD_SERVICE', 'grv-api')
        self.env = os.getenv('DD_ENV', 'prod')
        self.version = os.getenv('DD_VERSION', self._get_version())
        self.team = os.getenv('DD_TEAM', 'backend')
        self.owner = os.getenv('DD_OWNER', 'grv-team')
        
        # Tracing configuration
        self.enabled = os.getenv('DD_TRACE_ENABLED', 'true').lower() == 'true'
        self.debug = os.getenv('DD_TRACE_DEBUG', 'false').lower() == 'true'
        self.sample_rate = float(os.getenv('DD_TRACE_SAMPLE_RATE', '0.1'))
        self.agent_host = os.getenv('DD_AGENT_HOST', 'localhost')
        self.agent_port = int(os.getenv('DD_TRACE_AGENT_PORT', '8126'))
        
        # Service tags
        self.service_tags = {
            'service': self.service_name,
            'env': self.env,
            'version': self.version,
            'team': self.team,
            'owner': self.owner,
            'language': 'python',
            'framework': 'django',
            'tracer_version': ddtrace.__version__
        }
    
    def _get_version(self) -> str:
        """Get application version from environment or git."""
        # Try environment variable first
        version = os.getenv('APP_VERSION')
        if version:
            return version
        
        # Try git SHA
        try:
            import subprocess
            result = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        
        # Fallback to timestamp
        return datetime.now().strftime('%Y%m%d-%H%M%S')
    
    def configure_tracer(self):
        """Configure the Datadog tracer with enhanced settings."""
        if not self.enabled:
            logger.info("DD_TRACE_ENABLED is false, tracing disabled")
            return
        
        # Configure global tracer settings
        tracer.configure(
            hostname=self.agent_host,
            port=self.agent_port,
            enabled=self.enabled,
            debug=self.debug,
            sample_rate=self.sample_rate,
            env=self.env,
            service=self.service_name,
            version=self.version,
            tags=self.service_tags
        )
        
        # Set global tags
        for key, value in self.service_tags.items():
            tracer.set_tags({key: value})
        
        logger.info(f"Configured tracer for {self.service_name} in {self.env}")
    
    def patch_django(self):
        """Patch Django with enhanced tracing."""
        if not self.enabled:
            return
        
        # Patch Django with custom configuration
        django_patch(
            service=self.service_name,
            tracer=tracer,
            distributed_tracing=True,
            trace_requests=True,
            trace_templates=True,
            include_user_info=True,
            analytics_enabled=True,
            default_tags=self.service_tags
        )
        
        # Configure Django-specific settings
        from django.conf import settings
        if hasattr(settings, 'DATADOG_TRACE'):
            settings.DATADOG_TRACE.update({
                'DEFAULT_SERVICE': self.service_name,
                'TAGS': self.service_tags,
                'ANALYTICS_ENABLED': True,
                'DISTRIBUTED_TRACING': True,
                'INCLUDE_USER_INFO': True,
                'TRACE_TEMPLATES': True
            })
        
        logger.info("Django tracing patched successfully")
    
    def patch_celery(self):
        """Patch Celery with enhanced tracing."""
        if not self.enabled:
            return
        
        # Patch Celery with custom configuration
        celery_patch(
            service=self.service_name,
            tracer=tracer,
            distributed_tracing=True,
            analytics_enabled=True,
            default_tags=self.service_tags
        )
        
        logger.info("Celery tracing patched successfully")
    
    def patch_libraries(self):
        """Patch additional libraries for comprehensive tracing."""
        if not self.enabled:
            return
        
        # Patch database libraries
        psycopg_patch(
            service=f"{self.service_name}-postgres",
            tracer=tracer,
            analytics_enabled=True
        )
        
        # Patch Redis
        redis_patch(
            service=f"{self.service_name}-redis",
            tracer=tracer,
            analytics_enabled=True
        )
        
        # Patch HTTP requests
        requests_patch(
            tracer=tracer,
            analytics_enabled=True
        )
        
        logger.info("Additional libraries patched successfully")
    
    def setup_deployment_events(self):
        """Setup deployment event tracking."""
        if not self.enabled:
            return
        
        # Create deployment event
        deployment_data = {
            'service': self.service_name,
            'env': self.env,
            'version': self.version,
            'git_sha': self._get_git_sha(),
            'deploy_time': datetime.utcnow().isoformat(),
            'deployer': os.getenv('USER', 'system'),
            'tags': self.service_tags
        }
        
        # Send deployment event to Datadog
        try:
            from datadog import initialize, api
            
            initialize(
                api_key=os.getenv('DD_API_KEY'),
                app_key=os.getenv('DD_APP_KEY')
            )
            
            api.Event.create(
                title=f"Deployment: {self.service_name} v{self.version}",
                text=f"Service {self.service_name} deployed to {self.env} with version {self.version}",
                tags=[f"service:{self.service_name}", f"env:{self.env}", "source:deploy"],
                alert_type='info'
            )
            
            logger.info("Deployment event sent successfully")
            
        except Exception as e:
            logger.error(f"Failed to send deployment event: {e}")
    
    def _get_git_sha(self) -> str:
        """Get current git SHA."""
        try:
            import subprocess
            result = subprocess.run(['git', 'rev-parse', 'HEAD'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return "unknown"
    
    def setup_custom_spans(self):
        """Setup custom span decorators for business logic."""
        if not self.enabled:
            return
        
        def trace_business_operation(operation_name: str):
            """Decorator for tracing business operations."""
            def decorator(func):
                def wrapper(*args, **kwargs):
                    with tracer.trace(
                        name=f"business.{operation_name}",
                        service=self.service_name,
                        resource=operation_name,
                        span_type="custom"
                    ) as span:
                        span.set_tags(self.service_tags)
                        span.set_tag('operation.name', operation_name)
                        span.set_tag('operation.type', 'business')
                        return func(*args, **kwargs)
                return wrapper
            return decorator
        
        # Add to module for use in application
        sys.modules[__name__].trace_business_operation = trace_business_operation
        
        logger.info("Custom span decorators configured")
    
    def setup_health_checks(self):
        """Setup tracing health checks."""
        if not self.enabled:
            return
        
        def check_tracing_health():
            """Check if tracing is working properly."""
            try:
                # Create a test span
                with tracer.trace(
                    name="health.check",
                    service=self.service_name,
                    resource="tracing_health"
                ) as span:
                    span.set_tags(self.service_tags)
                    span.set_tag('health.check', 'tracing')
                    return True
            except Exception as e:
                logger.error(f"Tracing health check failed: {e}")
                return False
        
        # Add to module for use in health endpoints
        sys.modules[__name__].check_tracing_health = check_tracing_health
        
        logger.info("Tracing health checks configured")
    
    def initialize_tracing(self):
        """Initialize comprehensive tracing for grv-api."""
        logger.info("Initializing enhanced tracing for grv-api")
        
        # Configure tracer
        self.configure_tracer()
        
        # Patch frameworks and libraries
        self.patch_django()
        self.patch_celery()
        self.patch_libraries()
        
        # Setup additional features
        self.setup_deployment_events()
        self.setup_custom_spans()
        self.setup_health_checks()
        
        logger.info(f"Enhanced tracing initialized for {self.service_name} v{self.version}")


# Initialize tracing when module is imported
def initialize_grv_tracing():
    """Initialize grv-api tracing with enhanced configuration."""
    config = GRVAPITracingConfig()
    config.initialize_tracing()
    return config


# Auto-initialize if this is imported in Django settings
if 'django' in sys.modules:
    try:
        config = initialize_grv_tracing()
        logger.info("Auto-initialized grv-api tracing")
    except Exception as e:
        logger.error(f"Failed to auto-initialize tracing: {e}")


# Export configuration for manual initialization
__all__ = [
    'GRVAPITracingConfig',
    'initialize_grv_tracing',
    'tracer'
]
