#!/usr/bin/env python3
"""
Test script to validate Datadog observability setup for grv-api.
This script generates test traces, logs, and metrics to verify the monitoring setup.
"""

import os
import sys
import time
import json
import random
import logging
import requests
from datetime import datetime
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class ObservabilityTester:
    """Test suite for Datadog observability setup."""
    
    def __init__(self):
        self.setup_logging()
        self.test_results = []
    
    def setup_logging(self):
        """Setup structured logging for test output."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def log_test_result(self, test_name: str, success: bool, message: str = ""):
        """Log test result."""
        status = "✓" if success else "✗"
        self.logger.info(f"{status} {test_name}: {message}")
        self.test_results.append({
            "test": test_name,
            "success": success,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def test_ddtrace_import(self) -> bool:
        """Test ddtrace import and basic functionality."""
        try:
            import ddtrace
            from ddtrace import tracer, Span
            
            # Test tracer configuration
            tracer.configure(
                hostname=os.getenv("DD_AGENT_HOST", "localhost"),
                port=int(os.getenv("DD_TRACE_AGENT_PORT", "8126")),
                enabled=True
            )
            
            # Test span creation
            with tracer.trace("test.span", service="grv-api-test") as span:
                span.set_tag("test.type", "validation")
                span.set_tag("service", "grv-api")
                span.set_tag("env", "test")
            
            self.log_test_result("ddtrace Import", True, "ddtrace imported and configured successfully")
            return True
        
        except Exception as e:
            self.log_test_result("ddtrace Import", False, f"Failed to import or configure ddtrace: {e}")
            return False
    
    def test_django_integration(self) -> bool:
        """Test Django integration with ddtrace."""
        try:
            # Test Django settings import
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'grv.settings.prod')
            
            try:
                import django
                from django.conf import settings
                
                # Configure Django
                django.setup()
                
                # Test Datadog settings
                datadog_settings = getattr(settings, 'DATADOG_TRACE', {})
                if datadog_settings:
                    self.log_test_result("Django Integration", True, f"Django configured with Datadog: {datadog_settings.get('service', 'unknown')}")
                    return True
                else:
                    self.log_test_result("Django Integration", False, "DATADOG_TRACE settings not found")
                    return False
            
            except ImportError:
                self.log_test_result("Django Integration", False, "Django not available in test environment")
                return False
        
        except Exception as e:
            self.log_test_result("Django Integration", False, f"Django integration failed: {e}")
            return False
    
    def test_celery_integration(self) -> bool:
        """Test Celery integration with ddtrace."""
        try:
            from ddtrace.contrib.celery import patch_service
            import celery
            
            # Test Celery app creation
            app = celery.Celery('test-app')
            patch_service(app)
            
            # Test task creation
            @app.task
            def test_task(x):
                return x * 2
            
            # Execute test task
            result = test_task.apply_async(args=[5])
            
            self.log_test_result("Celery Integration", True, "Celery task created and executed successfully")
            return True
        
        except Exception as e:
            self.log_test_result("Celery Integration", False, f"Celery integration failed: {e}")
            return False
    
    def test_json_logging(self) -> bool:
        """Test JSON logging configuration."""
        try:
            # Import our custom formatter
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'examples', 'logging'))
            from json_formatter import DatadogJSONFormatter, StructuredLogger
            
            # Test formatter
            formatter = DatadogJSONFormatter(
                service="grv-api",
                env="test",
                version="v1.0.0-test"
            )
            
            # Create test log record
            record = logging.LogRecord(
                name="test.logger",
                level=logging.INFO,
                pathname="test.py",
                lineno=123,
                msg="Test log message",
                args=(),
                exc_info=None
            )
            
            # Format log record
            formatted = formatter.format(record)
            log_data = json.loads(formatted)
            
            # Validate required fields
            required_fields = ["timestamp", "level", "service", "env", "version", "message"]
            missing_fields = [field for field in required_fields if field not in log_data]
            
            if missing_fields:
                self.log_test_result("JSON Logging", False, f"Missing required fields: {missing_fields}")
                return False
            
            # Test structured logger
            structured_logger = StructuredLogger("test-logger")
            structured_logger.info("Test structured log", test_param="test_value")
            
            self.log_test_result("JSON Logging", True, "JSON logging configured and working")
            return True
        
        except Exception as e:
            self.log_test_result("JSON Logging", False, f"JSON logging test failed: {e}")
            return False
    
    def test_database_connectivity(self) -> bool:
        """Test database connectivity and monitoring."""
        try:
            import psycopg2
            from ddtrace import tracer
            
            # Test database connection with tracing
            with tracer.trace("database.test", service="grv-api-db") as span:
                conn = psycopg2.connect(
                    host=os.getenv("DD_POSTGRES_HOST", "localhost"),
                    port=int(os.getenv("DD_POSTGRES_PORT", "5432")),
                    database=os.getenv("DD_POSTGRES_DB", "grv_prod"),
                    user=os.getenv("DD_POSTGRES_USER", "grv_user"),
                    password=os.getenv("DD_POSTGRES_PASSWORD", ""),
                    connect_timeout=5
                )
                
                # Test query
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                cursor.close()
                conn.close()
                
                span.set_tag("db.name", "postgresql")
                span.set_tag("db.operation", "test")
            
            if result and result[0] == 1:
                self.log_test_result("Database Connectivity", True, "PostgreSQL connection successful")
                return True
            else:
                self.log_test_result("Database Connectivity", False, "Unexpected database result")
                return False
        
        except Exception as e:
            self.log_test_result("Database Connectivity", False, f"Database connection failed: {e}")
            return False
    
    def test_redis_connectivity(self) -> bool:
        """Test Redis connectivity and monitoring."""
        try:
            import redis
            from ddtrace import tracer
            
            # Test Redis connection with tracing
            with tracer.trace("redis.test", service="grv-api-redis") as span:
                r = redis.Redis(
                    host=os.getenv("DD_REDIS_HOST", "localhost"),
                    port=int(os.getenv("DD_REDIS_PORT", "6379")),
                    db=int(os.getenv("DD_REDIS_DB", "0")),
                    password=os.getenv("DD_REDIS_PASSWORD"),
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                
                # Test operations
                test_key = "test:observability"
                r.set(test_key, "test_value", ex=60)
                value = r.get(test_key)
                r.delete(test_key)
                
                span.set_tag("redis.command", "test_operations")
            
            if value and value.decode() == "test_value":
                self.log_test_result("Redis Connectivity", True, "Redis connection successful")
                return True
            else:
                self.log_test_result("Redis Connectivity", False, "Unexpected Redis result")
                return False
        
        except Exception as e:
            self.log_test_result("Redis Connectivity", False, f"Redis connection failed: {e}")
            return False
    
    def test_nginx_status(self) -> bool:
        """Test Nginx status endpoint."""
        try:
            nginx_status_url = os.getenv("DD_NGINX_STATUS_URL", "http://localhost:8080/nginx_status")
            
            response = requests.get(nginx_status_url, timeout=5)
            
            if response.status_code == 200:
                # Check if response contains expected Nginx status format
                content = response.text
                if "Active connections" in content and "server accepts" in content:
                    self.log_test_result("Nginx Status", True, "Nginx status endpoint accessible")
                    return True
                else:
                    self.log_test_result("Nginx Status", False, "Nginx status response format unexpected")
                    return False
            else:
                self.log_test_result("Nginx Status", False, f"Nginx status returned {response.status_code}")
                return False
        
        except Exception as e:
            self.log_test_result("Nginx Status", False, f"Nginx status check failed: {e}")
            return False
    
    def test_datadog_agent(self) -> bool:
        """Test Datadog agent connectivity."""
        try:
            # Test agent status endpoint
            agent_url = f"http://{os.getenv('DD_AGENT_HOST', 'localhost')}:8126/info"
            
            response = requests.get(agent_url, timeout=5)
            
            if response.status_code == 200:
                agent_info = response.json()
                if "config" in agent_info:
                    self.log_test_result("Datadog Agent", True, "Datadog agent is accessible")
                    return True
                else:
                    self.log_test_result("Datadog Agent", False, "Datadog agent response format unexpected")
                    return False
            else:
                self.log_test_result("Datadog Agent", False, f"Datadog agent returned {response.status_code}")
                return False
        
        except Exception as e:
            self.log_test_result("Datadog Agent", False, f"Datadog agent check failed: {e}")
            return False
    
    def generate_test_metrics(self) -> bool:
        """Generate test metrics to verify collection."""
        try:
            from datadog import statsd
            
            # Generate various test metrics
            statsd.increment('test.requests.count', tags=['service:grv-api', 'env:test'])
            statsd.gauge('test.response_time', random.randint(100, 500), tags=['service:grv-api', 'env:test'])
            statsd.histogram('test.latency', random.randint(50, 200), tags=['service:grv-api', 'env:test'])
            statsd.timer('test.timer', tags=['service:grv-api', 'env:test'])
            
            self.log_test_result("Test Metrics", True, "Test metrics sent to Datadog")
            return True
        
        except Exception as e:
            self.log_test_result("Test Metrics", False, f"Failed to send test metrics: {e}")
            return False
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all observability tests."""
        self.logger.info("Starting observability tests for grv-api...")
        
        # Core tracing tests
        self.test_ddtrace_import()
        self.test_django_integration()
        self.test_celery_integration()
        
        # Logging tests
        self.test_json_logging()
        
        # Infrastructure tests
        self.test_database_connectivity()
        self.test_redis_connectivity()
        self.test_nginx_status()
        self.test_datadog_agent()
        
        # Metrics tests
        self.generate_test_metrics()
        
        # Generate summary
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        summary = {
            "total_tests": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "success_rate": (passed_tests / total_tests) * 100 if total_tests > 0 else 0,
            "results": self.test_results,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.logger.info(f"\nTest Summary: {passed_tests}/{total_tests} tests passed ({summary['success_rate']:.1f}%)")
        
        if failed_tests > 0:
            self.logger.warning("Some tests failed. Please check the configuration.")
        
        return summary


def main():
    """Main function to run observability tests."""
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Run tests
    tester = ObservabilityTester()
    results = tester.run_all_tests()
    
    # Save results to file
    results_file = f"observability_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nDetailed results saved to: {results_file}")
    
    # Exit with appropriate code
    sys.exit(0 if results["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
