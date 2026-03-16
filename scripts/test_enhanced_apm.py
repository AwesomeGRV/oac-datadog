#!/usr/bin/env python3
"""
Comprehensive test suite for enhanced APM monitoring setup.
Validates all monitors, tracing configuration, and health checks.
"""

import os
import sys
import json
import logging
import time
import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestEnhancedAPMMonitoring(unittest.TestCase):
    """Test suite for enhanced APM monitoring setup."""
    
    def setUp(self):
        """Set up test environment."""
        self.service = 'grv-api'
        self.env = 'test'
        
        # Mock environment variables
        os.environ['DD_SERVICE'] = self.service
        os.environ['DD_ENV'] = self.env
        os.environ['DD_API_KEY'] = 'test-api-key'
        os.environ['DD_APP_KEY'] = 'test-app-key'
        os.environ['DD_VERSION'] = 'v1.0.0-test'
        os.environ['DD_TEAM'] = 'backend'
        os.environ['DD_OWNER'] = 'grv-team'
    
    def test_monitor_file_structure(self):
        """Test that all monitor files have correct structure."""
        monitor_dir = os.path.join(
            os.path.dirname(__file__),
            '..', 'datadog', 'monitors', 'apm'
        )
        
        required_fields = ['name', 'type', 'query', 'message', 'tags', 'options']
        
        for filename in os.listdir(monitor_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(monitor_dir, filename)
                
                with open(filepath, 'r') as f:
                    monitor_data = json.load(f)
                
                # Check required fields
                for field in required_fields:
                    self.assertIn(field, monitor_data, f"Monitor {filename} missing required field: {field}")
                
                # Check service tagging
                tags = monitor_data.get('tags', [])
                self.assertIn(f'service:{self.service}', tags, f"Monitor {filename} missing service tag")
                self.assertIn(f'env:{self.env}', tags, f"Monitor {filename} missing env tag")
                
                # Check monitor type tagging
                monitor_type_tags = [tag for tag in tags if tag.startswith('monitor_type:')]
                self.assertGreater(len(monitor_type_tags), 0, f"Monitor {filename} missing monitor_type tag")
    
    def test_enhanced_django_tracing_config(self):
        """Test enhanced Django tracing configuration."""
        try:
            from examples.django.enhanced_ddtrace_integration import GRVAPITracingConfig
            
            config = GRVAPITracingConfig()
            
            # Test configuration values
            self.assertEqual(config.service_name, self.service)
            self.assertEqual(config.env, self.env)
            self.assertEqual(config.team, 'backend')
            self.assertEqual(config.owner, 'grv-team')
            
            # Test service tags
            expected_tags = {
                'service': self.service,
                'env': self.env,
                'team': 'backend',
                'owner': 'grv-team',
                'language': 'python',
                'framework': 'django'
            }
            
            for key, value in expected_tags.items():
                self.assertIn(key, config.service_tags)
                self.assertEqual(config.service_tags[key], value)
            
            # Test version detection
            version = config._get_version()
            self.assertIsNotNone(version)
            self.assertIsInstance(version, str)
            self.assertGreater(len(version), 0)
            
        except ImportError as e:
            self.skipTest(f"Enhanced Django tracing not available: {e}")
    
    def test_enhanced_celery_tracing_config(self):
        """Test enhanced Celery tracing configuration."""
        try:
            from examples.celery.enhanced_celery_tracing import GRVCeleryTracingConfig
            
            config = GRVCeleryTracingConfig()
            
            # Test configuration values
            self.assertEqual(config.service_name, self.service)
            self.assertEqual(config.env, self.env)
            self.assertEqual(config.celery_service, f'{self.service}-celery')
            
            # Test service tags
            expected_tags = {
                'service': f'{self.service}-celery',
                'env': self.env,
                'team': 'backend',
                'owner': 'grv-team',
                'language': 'python',
                'framework': 'celery',
                'component': 'background_jobs'
            }
            
            for key, value in expected_tags.items():
                self.assertIn(key, config.service_tags)
                self.assertEqual(config.service_tags[key], value)
            
        except ImportError as e:
            self.skipTest(f"Enhanced Celery tracing not available: {e}")
    
    @patch('datadog.api.Metric.query')
    def test_apm_health_checker(self, mock_metric_query):
        """Test APM health checker functionality."""
        try:
            from scripts.apm_health_checker import APMHealthChecker
            
            # Mock metric query responses
            mock_metric_query.return_value = {
                'series': [
                    {
                        'pointlist': [[1234567890, 100], [1234567950, 150]]
                    }
                ]
            }
            
            checker = APMHealthChecker()
            
            # Test service health check
            health_result = checker.check_service_health()
            
            self.assertIn('status', health_result)
            self.assertIn('metrics', health_result)
            self.assertIn('timestamp', health_result)
            
            # Test monitor coverage check
            with patch('datadog.api.Monitor.get_all') as mock_monitors:
                mock_monitors.return_value = [
                    Mock(tags=[f'service:{self.service}', 'monitor_type:apm']),
                    Mock(tags=[f'service:{self.service}', 'monitor_type:infrastructure'])
                ]
                
                coverage_result = checker.check_monitor_coverage()
                
                self.assertIn('status', coverage_result)
                self.assertIn('total_monitors', coverage_result)
                self.assertIn('coverage_score', coverage_result)
            
            # Test comprehensive health check
            with patch('datadog.api.Monitor.get_all') as mock_monitors:
                mock_monitors.return_value = []
                
                health_check = checker.run_comprehensive_health_check()
                
                self.assertIn('overall_status', health_check)
                self.assertIn('health_score', health_check)
                self.assertIn('checks', health_check)
                self.assertIn('recommendations', health_check)
            
        except ImportError as e:
            self.skipTest(f"APM health checker not available: {e}")
    
    @patch('datadog.api.Metric.query')
    def test_service_tagging_validator(self, mock_metric_query):
        """Test service tagging validator functionality."""
        try:
            from scripts.service_tagging_validator import ServiceTaggingValidator
            
            # Mock metric query with proper tagging
            mock_metric_query.return_value = {
                'series': [
                    {
                        'tags': [f'service:{self.service}', f'env:{self.env}', 'version:v1.0.0', 'team:backend', 'owner:grv-team'],
                        'scope': f'service:{self.service},env:{self.env}',
                        'expression': f'sum:trace.django.request.hits{{service:{self.service},env:{self.env}}}'
                    }
                ]
            }
            
            validator = ServiceTaggingValidator()
            
            # Test compliance report generation
            report = validator.generate_compliance_report()
            
            self.assertIn('service', report)
            self.assertIn('env', report)
            self.assertIn('validation', report)
            self.assertIn('compliance_score', report)
            self.assertIn('compliance_grade', report)
            self.assertIn('recommendations', report)
            
            # Test validation logic
            self.assertTrue(report['validation']['valid'])
            self.assertGreaterEqual(report['compliance_score'], 0)
            self.assertLessEqual(report['compliance_score'], 100)
            
        except ImportError as e:
            self.skipTest(f"Service tagging validator not available: {e}")
    
    def test_enhanced_deployment_tracker(self):
        """Test enhanced deployment tracker functionality."""
        try:
            from scripts.enhanced_deployment_tracker import GRVDeploymentTracker
            
            tracker = GRVDeploymentTracker()
            
            # Test git information extraction
            git_info = tracker.get_git_info()
            
            self.assertIsInstance(git_info, dict)
            # Git info might be empty in test environment
            
            # Test deployment health assessment
            health_assessment = tracker.assess_deployment_health('v1.0.0')
            
            self.assertIn('version', health_assessment)
            self.assertIn('health_status', health_assessment)
            self.assertIn('recommendations', health_assessment)
            self.assertIn('rollback_risk', health_assessment)
            
            self.assertIn(health_assessment['health_status'], ['healthy', 'warning', 'critical', 'unknown'])
            self.assertIn(health_assessment['rollback_risk'], ['low', 'medium', 'high'])
            
        except ImportError as e:
            self.skipTest(f"Enhanced deployment tracker not available: {e}")
    
    def test_monitor_query_validation(self):
        """Test that monitor queries are syntactically valid."""
        monitor_dir = os.path.join(
            os.path.dirname(__file__),
            '..', 'datadog', 'monitors', 'apm'
        )
        
        # Common query patterns to validate
        valid_query_patterns = [
            'sum(', 'avg(', 'max(', 'min(',
            '.rollup(', '.by(', '.p95(', '.p99(',
            '{service:', 'env:', 'version:',
            '>', '<', '>=', '<=', '==', '!=',
            'AND', 'OR', 'NOT'
        ]
        
        for filename in os.listdir(monitor_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(monitor_dir, filename)
                
                with open(filepath, 'r') as f:
                    monitor_data = json.load(f)
                
                query = monitor_data.get('query', '')
                
                # Check for basic query structure
                self.assertGreater(len(query), 0, f"Monitor {filename} has empty query")
                
                # Check for valid service and env references
                self.assertIn(f'service:{self.service}', query, f"Monitor {filename} query missing service reference")
                self.assertIn(f'env:{self.env}', query, f"Monitor {filename} query missing env reference")
                
                # Check for valid metric patterns
                has_valid_metric = any(pattern in query for pattern in ['trace.django.request', 'trace.celery.task', 'nginx.http.requests'])
                self.assertTrue(has_valid_metric, f"Monitor {filename} query doesn't contain valid metrics")
    
    def test_monitor_message_templates(self):
        """Test that monitor messages contain proper template variables."""
        monitor_dir = os.path.join(
            os.path.dirname(__file__),
            '..', 'datadog', 'monitors', 'apm'
        )
        
        for filename in os.listdir(monitor_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(monitor_dir, filename)
                
                with open(filepath, 'r') as f:
                    monitor_data = json.load(f)
                
                message = monitor_data.get('message', '')
                
                # Check for basic template variables
                self.assertIn('{{service}}', message, f"Monitor {filename} message missing {{service}} template")
                self.assertIn('{{env}}', message, f"Monitor {filename} message missing {{env}} template")
                self.assertIn('{{value}}', message, f"Monitor {filename} message missing {{value}} template")
                
                # Check for investigation steps or dashboard links
                has_investigation = 'investigate' in message.lower() or 'dashboard' in message.lower()
                self.assertTrue(has_investigation, f"Monitor {filename} message missing investigation guidance")
    
    def test_monitor_tag_compliance(self):
        """Test that all monitors have proper tagging compliance."""
        monitor_dir = os.path.join(
            os.path.dirname(__file__),
            '..', 'datadog', 'monitors', 'apm'
        )
        
        required_tags = [
            f'service:{self.service}',
            f'env:{self.env}',
            'team:backend',
            'owner:grv-team',
            'monitor_type:'
        ]
        
        for filename in os.listdir(monitor_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(monitor_dir, filename)
                
                with open(filepath, 'r') as f:
                    monitor_data = json.load(f)
                
                tags = monitor_data.get('tags', [])
                
                # Check for all required tags
                for required_tag in required_tags:
                    if required_tag.endswith(':'):
                        # Check for tag prefix
                        has_tag_prefix = any(tag.startswith(required_tag) for tag in tags)
                        self.assertTrue(has_tag_prefix, f"Monitor {filename} missing tag with prefix {required_tag}")
                    else:
                        # Check for exact tag match
                        self.assertIn(required_tag, tags, f"Monitor {filename} missing required tag {required_tag}")
                
                # Check for severity tag
                severity_tags = [tag for tag in tags if tag.startswith('severity:')]
                self.assertGreater(len(severity_tags), 0, f"Monitor {filename} missing severity tag")
                
                valid_severities = ['critical', 'warning', 'info']
                for severity_tag in severity_tags:
                    severity_value = severity_tag.split(':')[1]
                    self.assertIn(severity_value, valid_severities, 
                                f"Monitor {filename} has invalid severity: {severity_value}")
    
    def test_environment_variable_handling(self):
        """Test that all scripts handle environment variables properly."""
        scripts_to_test = [
            'scripts/apm_health_checker.py',
            'scripts/service_tagging_validator.py',
            'scripts/enhanced_deployment_tracker.py'
        ]
        
        for script in scripts_to_test:
            script_path = os.path.join(os.path.dirname(__file__), '..', script)
            
            if os.path.exists(script_path):
                # Check that script imports and handles environment variables
                with open(script_path, 'r') as f:
                    content = f.read()
                
                # Should import os module
                self.assertIn('import os', content, f"Script {script} doesn't import os module")
                
                # Should use os.getenv for environment variables
                self.assertIn('os.getenv', content, f"Script {script} doesn't use os.getenv")
                
                # Should have default values for required environment variables
                self.assertIn('default=', content, f"Script {script} doesn't provide default values for environment variables")


class TestIntegrationScenarios(unittest.TestCase):
    """Integration tests for enhanced APM monitoring scenarios."""
    
    def setUp(self):
        """Set up integration test environment."""
        self.service = 'grv-api'
        self.env = 'test'
        
        # Mock environment variables
        os.environ['DD_SERVICE'] = self.service
        os.environ['DD_ENV'] = self.env
        os.environ['DD_API_KEY'] = 'test-api-key'
        os.environ['DD_APP_KEY'] = 'test-app-key'
    
    @patch('datadog.api.Event.create')
    @patch('datadog.api.Monitor.create')
    @patch('datadog.api.Metric.query')
    def test_deployment_tracking_flow(self, mock_metric_query, mock_monitor_create, mock_event_create):
        """Test complete deployment tracking flow."""
        try:
            from scripts.enhanced_deployment_tracker import GRVDeploymentTracker
            
            # Mock successful responses
            mock_metric_query.return_value = {'series': []}
            mock_monitor_create.return_value = {'id': 12345}
            mock_event_create.return_value = {'id': 'event-123'}
            
            tracker = GRVDeploymentTracker()
            
            # Test deployment tracking
            result = tracker.track_deployment(
                version='v1.0.0',
                deployer='test-user',
                notes='Test deployment'
            )
            
            # Verify result structure
            self.assertIn('service', result)
            self.assertIn('version', result)
            self.assertIn('event_sent', result)
            self.assertIn('monitor_created', result)
            self.assertIn('initial_health', result)
            
            # Verify API calls were made
            self.assertTrue(mock_event_create.called)
            self.assertTrue(mock_monitor_create.called)
            
        except ImportError as e:
            self.skipTest(f"Enhanced deployment tracker not available: {e}")
    
    @patch('datadog.api.Event.create')
    @patch('datadog.api.Metric.query')
    def test_health_check_flow(self, mock_metric_query, mock_event_create):
        """Test complete health check flow."""
        try:
            from scripts.apm_health_checker import APMHealthChecker
            
            # Mock healthy responses
            mock_metric_query.return_value = {
                'series': [
                    {
                        'pointlist': [[1234567890, 100], [1234567950, 150]]
                    }
                ]
            }
            mock_event_create.return_value = {'id': 'event-123'}
            
            checker = APMHealthChecker()
            
            # Test comprehensive health check
            health_check = checker.run_comprehensive_health_check()
            
            # Verify result structure
            self.assertIn('overall_status', health_check)
            self.assertIn('health_score', health_check)
            self.assertIn('checks', health_check)
            self.assertIn('recommendations', health_check)
            
            # Test event sending
            event_sent = checker.send_health_event(health_check)
            self.assertTrue(mock_event_create.called)
            
        except ImportError as e:
            self.skipTest(f"APM health checker not available: {e}")


def run_performance_tests():
    """Run performance tests for monitoring setup."""
    logger.info("Running performance tests...")
    
    # Test monitor loading performance
    start_time = time.time()
    monitor_dir = os.path.join(
        os.path.dirname(__file__),
        '..', 'datadog', 'monitors', 'apm'
    )
    
    monitor_count = 0
    for filename in os.listdir(monitor_dir):
        if filename.endswith('.json'):
            with open(os.path.join(monitor_dir, filename), 'r') as f:
                json.load(f)
            monitor_count += 1
    
    load_time = time.time() - start_time
    logger.info(f"Loaded {monitor_count} monitors in {load_time:.3f} seconds")
    
    # Test configuration loading performance
    start_time = time.time()
    
    try:
        from examples.django.enhanced_ddtrace_integration import GRVAPITracingConfig
        config = GRVAPITracingConfig()
        config_time = time.time() - start_time
        logger.info(f"Loaded Django tracing config in {config_time:.3f} seconds")
    except ImportError:
        logger.warning("Django tracing config not available for performance testing")
    
    try:
        from examples.celery.enhanced_celery_tracing import GRVCeleryTracingConfig
        config = GRVCeleryTracingConfig()
        celery_time = time.time() - start_time
        logger.info(f"Loaded Celery tracing config in {celery_time:.3f} seconds")
    except ImportError:
        logger.warning("Celery tracing config not available for performance testing")


def main():
    """Main test runner."""
    logger.info("Starting enhanced APM monitoring test suite")
    
    # Run unit tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestEnhancedAPMMonitoring))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegrationScenarios))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Run performance tests
    run_performance_tests()
    
    # Return exit code based on test results
    if result.wasSuccessful():
        logger.info("All tests passed successfully!")
        return 0
    else:
        logger.error(f"Tests failed: {len(result.failures)} failures, {len(result.errors)} errors")
        return 1


if __name__ == '__main__':
    sys.exit(main())
