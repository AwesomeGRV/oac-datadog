#!/usr/bin/env python3
"""
Enhanced Celery ddtrace integration for grv-api.
Provides comprehensive background job tracing with proper service tagging.
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
from ddtrace.contrib.celery import patch as celery_patch
from ddtrace.contrib.psycopg import patch as psycopg_patch
from ddtrace.contrib.redis import patch as redis_patch

# Celery imports
from celery import Celery
from celery.signals import task_prerun, task_postrun, task_failure, task_success

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GRVCeleryTracingConfig:
    """Enhanced Celery tracing configuration for grv-api background jobs."""
    
    def __init__(self):
        self.service_name = os.getenv('DD_SERVICE', 'grv-api')
        self.env = os.getenv('DD_ENV', 'prod')
        self.version = os.getenv('DD_VERSION', self._get_version())
        self.team = os.getenv('DD_TEAM', 'backend')
        self.owner = os.getenv('DD_OWNER', 'grv-team')
        
        # Celery-specific configuration
        self.celery_service = f"{self.service_name}-celery"
        self.enabled = os.getenv('DD_TRACE_ENABLED', 'true').lower() == 'true'
        self.debug = os.getenv('DD_TRACE_DEBUG', 'false').lower() == 'true'
        self.sample_rate = float(os.getenv('DD_TRACE_SAMPLE_RATE', '0.1'))
        
        # Service tags for Celery
        self.service_tags = {
            'service': self.celery_service,
            'env': self.env,
            'version': self.version,
            'team': self.team,
            'owner': self.owner,
            'language': 'python',
            'framework': 'celery',
            'tracer_version': ddtrace.__version__,
            'component': 'background_jobs'
        }
    
    def _get_version(self) -> str:
        """Get application version from environment or git."""
        version = os.getenv('APP_VERSION')
        if version:
            return version
        
        try:
            import subprocess
            result = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        
        return datetime.now().strftime('%Y%m%d-%H%M%S')
    
    def configure_celery_tracer(self):
        """Configure the Datadog tracer for Celery."""
        if not self.enabled:
            logger.info("DD_TRACE_ENABLED is false, Celery tracing disabled")
            return
        
        # Configure Celery-specific tracer settings
        tracer.configure(
            hostname=os.getenv('DD_AGENT_HOST', 'localhost'),
            port=int(os.getenv('DD_TRACE_AGENT_PORT', '8126')),
            enabled=self.enabled,
            debug=self.debug,
            sample_rate=self.sample_rate,
            env=self.env,
            service=self.celery_service,
            version=self.version,
            tags=self.service_tags
        )
        
        # Set global tags for Celery
        for key, value in self.service_tags.items():
            tracer.set_tags({key: value})
        
        logger.info(f"Configured Celery tracer for {self.celery_service}")
    
    def patch_celery_enhanced(self):
        """Patch Celery with enhanced tracing configuration."""
        if not self.enabled:
            return
        
        # Patch Celery with custom configuration
        celery_patch(
            service=self.celery_service,
            tracer=tracer,
            distributed_tracing=True,
            analytics_enabled=True,
            default_tags=self.service_tags,
            worker_service_name=self.celery_service,
            propagate_traces=True
        )
        
        # Patch additional libraries used by Celery
        psycopg_patch(
            service=f"{self.celery_service}-postgres",
            tracer=tracer,
            analytics_enabled=True
        )
        
        redis_patch(
            service=f"{self.celery_service}-redis",
            tracer=tracer,
            analytics_enabled=True
        )
        
        logger.info("Enhanced Celery tracing patched successfully")
    
    def setup_celery_signals(self):
        """Setup Celery signal handlers for enhanced tracing."""
        if not self.enabled:
            return
        
        @task_prerun.connect
        def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
            """Handle task pre-run signal for tracing."""
            try:
                # Create a span for the task
                span = tracer.trace(
                    name=f"celery.task.{task.name}",
                    service=self.celery_service,
                    resource=task.name,
                    span_type="worker"
                )
                
                # Set standard tags
                span.set_tags(self.service_tags)
                span.set_tag('celery.task_id', task_id)
                span.set_tag('celery.task_name', task.name)
                span.set_tag('celery.args_count', len(args) if args else 0)
                span.set_tag('celery.kwargs_count', len(kwargs) if kwargs else 0)
                span.set_tag('celery.queue', task.queue if hasattr(task, 'queue') else 'default')
                span.set_tag('celery.routing_key', task.routing_key if hasattr(task, 'routing_key') else 'default')
                
                # Store span in task context
                task._dd_span = span
                
            except Exception as e:
                logger.error(f"Failed to handle task_prerun signal: {e}")
        
        @task_postrun.connect
        def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kwds):
            """Handle task post-run signal for tracing."""
            try:
                # Close the span if it exists
                if hasattr(task, '_dd_span') and task._dd_span:
                    span = task._dd_span
                    span.set_tag('celery.state', state)
                    span.set_tag('celery.success', state == 'SUCCESS')
                    
                    if retval is not None:
                        span.set_tag('celery.return_type', type(retval).__name__)
                        if hasattr(retval, '__len__'):
                            span.set_tag('celery.result_size', len(retval))
                    
                    span.finish()
                    delattr(task, '_dd_span')
                
            except Exception as e:
                logger.error(f"Failed to handle task_postrun signal: {e}")
        
        @task_failure.connect
        def task_failure_handler(sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwds):
            """Handle task failure signal for tracing."""
            try:
                # Add error information to span
                if hasattr(sender, '_dd_span') and sender._dd_span:
                    span = sender._dd_span
                    span.set_tag('celery.state', 'FAILURE')
                    span.set_tag('celery.success', False)
                    span.set_tag('error', True)
                    span.set_tag('error.type', type(exception).__name__)
                    span.set_tag('error.message', str(exception))
                    span.set_tag('error.stack', str(traceback))
                
                # Create error event
                tracer.current_span().set_exc_info(type(exception), exception, traceback)
                
            except Exception as e:
                logger.error(f"Failed to handle task_failure signal: {e}")
        
        @task_success.connect
        def task_success_handler(sender=None, result=None, **kwds):
            """Handle task success signal for tracing."""
            try:
                # Add success information to span
                if hasattr(sender, '_dd_span') and sender._dd_span:
                    span = sender._dd_span
                    span.set_tag('celery.state', 'SUCCESS')
                    span.set_tag('celery.success', True)
                    span.set_tag('celery.result_type', type(result).__name__)
                    
                    if hasattr(result, '__len__'):
                        span.set_tag('celery.result_size', len(result))
                
            except Exception as e:
                logger.error(f"Failed to handle task_success signal: {e}")
        
        logger.info("Celery signal handlers configured successfully")
    
    def setup_queue_monitoring(self):
        """Setup enhanced queue monitoring."""
        if not self.enabled:
            return
        
        def monitor_queue_depth():
            """Monitor Celery queue depth and create metrics."""
            try:
                from celery import current_app
                
                # Get queue information
                inspect = current_app.control.inspect()
                active_queues = inspect.active_queues()
                
                if active_queues:
                    for worker, queues in active_queues.items():
                        for queue_info in queues:
                            queue_name = queue_info.get('name', 'default')
                            
                            # Create a span for queue monitoring
                            with tracer.trace(
                                name="celery.queue.monitor",
                                service=self.celery_service,
                                resource=queue_name,
                                span_type="custom"
                            ) as span:
                                span.set_tags(self.service_tags)
                                span.set_tag('celery.queue_name', queue_name)
                                span.set_tag('celery.worker', worker)
                                span.set_tag('monitoring.type', 'queue_depth')
                                
            except Exception as e:
                logger.error(f"Failed to monitor queue depth: {e}")
        
        # Add to module for periodic execution
        sys.modules[__name__].monitor_queue_depth = monitor_queue_depth
        
        logger.info("Queue monitoring configured")
    
    def setup_task_performance_tracking(self):
        """Setup enhanced task performance tracking."""
        if not self.enabled:
            return
        
        def track_task_performance(task_name: str, duration: float, success: bool):
            """Track task performance metrics."""
            try:
                with tracer.trace(
                    name="celery.performance.track",
                    service=self.celery_service,
                    resource=task_name,
                    span_type="custom"
                ) as span:
                    span.set_tags(self.service_tags)
                    span.set_tag('celery.task_name', task_name)
                    span.set_tag('celery.duration_ms', duration * 1000)
                    span.set_tag('celery.success', success)
                    span.set_tag('monitoring.type', 'performance')
                    
                    # Performance classification
                    if duration > 300:  # 5 minutes
                        span.set_tag('performance.classification', 'slow')
                    elif duration > 60:  # 1 minute
                        span.set_tag('performance.classification', 'medium')
                    else:
                        span.set_tag('performance.classification', 'fast')
                
            except Exception as e:
                logger.error(f"Failed to track task performance: {e}")
        
        # Add to module for use in tasks
        sys.modules[__name__].track_task_performance = track_task_performance
        
        logger.info("Task performance tracking configured")
    
    def setup_custom_task_decorator(self):
        """Setup custom task decorator with enhanced tracing."""
        if not self.enabled:
            return
        
        def traced_task(name: str = None, queue: str = None, priority: int = None):
            """Enhanced task decorator with comprehensive tracing."""
            def decorator(func):
                # Create Celery task with enhanced configuration
                task = current_app.task(
                    name=name,
                    queue=queue,
                    priority=priority,
                    bind=True
                )(func)
                
                # Wrap with enhanced tracing
                def wrapper(self, *args, **kwargs):
                    start_time = datetime.now()
                    
                    try:
                        # Execute the task
                        result = func(self, *args, **kwargs)
                        
                        # Track performance
                        duration = (datetime.now() - start_time).total_seconds()
                        track_task_performance(task.name, duration, True)
                        
                        return result
                        
                    except Exception as e:
                        # Track failure
                        duration = (datetime.now() - start_time).total_seconds()
                        track_task_performance(task.name, duration, False)
                        raise
                
                return wrapper
            return decorator
        
        # Add to module for use in application
        sys.modules[__name__].traced_task = traced_task
        
        logger.info("Custom task decorator configured")
    
    def initialize_celery_tracing(self):
        """Initialize comprehensive Celery tracing for grv-api."""
        logger.info("Initializing enhanced Celery tracing for grv-api")
        
        # Configure tracer
        self.configure_celery_tracer()
        
        # Patch Celery and dependencies
        self.patch_celery_enhanced()
        
        # Setup enhanced features
        self.setup_celery_signals()
        self.setup_queue_monitoring()
        self.setup_task_performance_tracking()
        self.setup_custom_task_decorator()
        
        logger.info(f"Enhanced Celery tracing initialized for {self.celery_service}")


# Initialize Celery tracing when module is imported
def initialize_grv_celery_tracing():
    """Initialize grv-api Celery tracing with enhanced configuration."""
    config = GRVCeleryTracingConfig()
    config.initialize_celery_tracing()
    return config


# Auto-initialize if this is imported in Celery app
if 'celery' in sys.modules:
    try:
        config = initialize_grv_celery_tracing()
        logger.info("Auto-initialized grv-api Celery tracing")
    except Exception as e:
        logger.error(f"Failed to auto-initialize Celery tracing: {e}")


# Export configuration for manual initialization
__all__ = [
    'GRVCeleryTracingConfig',
    'initialize_grv_celery_tracing',
    'tracer',
    'traced_task',
    'monitor_queue_depth',
    'track_task_performance'
]
