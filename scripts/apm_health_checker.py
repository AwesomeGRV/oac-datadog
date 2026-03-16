#!/usr/bin/env python3
"""
Comprehensive APM health checker for grv-api Datadog monitoring.
Validates the health and effectiveness of the entire APM monitoring setup.
"""

import os
import sys
import json
import logging
import argparse
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

# Datadog imports
try:
    from datadog import initialize, api
    DATADOG_AVAILABLE = True
except ImportError:
    DATADOG_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class APMHealthChecker:
    """Comprehensive APM health checker for grv-api."""
    
    def __init__(self):
        self.api_key = os.getenv('DD_API_KEY')
        self.app_key = os.getenv('DD_APP_KEY')
        self.service = os.getenv('DD_SERVICE', 'grv-api')
        self.env = os.getenv('DD_ENV', 'prod')
        
        # Health check thresholds
        self.thresholds = {
            'trace_rate_min': 10,  # traces per minute
            'error_rate_max': 5.0,  # percentage
            'latency_p95_max': 2000,  # milliseconds
            'apdex_min': 0.85,
            'trace_sampling_min': 10.0,  # percentage
            'monitor_coverage_min': 80.0  # percentage
        }
        
        # Initialize Datadog client
        if DATADOG_AVAILABLE and self.api_key and self.app_key:
            initialize(api_key=self.api_key, app_key=self.app_key)
            self.datadog_enabled = True
        else:
            self.datadog_enabled = False
            logger.warning("Datadog client not available or missing credentials")
    
    def check_service_health(self) -> Dict[str, Any]:
        """Check overall service health metrics."""
        if not self.datadog_enabled:
            return {'status': 'error', 'message': 'Datadog client not available'}
        
        try:
            from datetime import datetime, timedelta
            
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(minutes=15)
            
            health_metrics = {}
            
            # Check trace rate
            trace_query = f"sum:trace.django.request.hits{{service:{self.service},env:{self.env}}}"
            trace_result = api.Metric.query(start=start_time, end=end_time, query=trace_query)
            
            if trace_result['series']:
                trace_sum = sum(point[1] for series in trace_result['series'] for point in series['pointlist'])
                trace_rate = trace_sum / 15  # per minute
                health_metrics['trace_rate'] = trace_rate
                health_metrics['trace_rate_status'] = 'healthy' if trace_rate >= self.thresholds['trace_rate_min'] else 'warning'
            else:
                health_metrics['trace_rate'] = 0
                health_metrics['trace_rate_status'] = 'critical'
            
            # Check error rate
            error_query = f"sum:trace.django.request.errors{{service:{self.service},env:{self.env}}}"
            hits_query = f"sum:trace.django.request.hits{{service:{self.service},env:{self.env}}}"
            
            error_result = api.Metric.query(start=start_time, end=end_time, query=error_query)
            hits_result = api.Metric.query(start=start_time, end=end_time, query=hits_query)
            
            if error_result['series'] and hits_result['series']:
                error_sum = sum(point[1] for series in error_result['series'] for point in series['pointlist'])
                hits_sum = sum(point[1] for series in hits_result['series'] for point in series['pointlist'])
                
                if hits_sum > 0:
                    error_rate = (error_sum / hits_sum) * 100
                    health_metrics['error_rate'] = error_rate
                    health_metrics['error_rate_status'] = 'healthy' if error_rate <= self.thresholds['error_rate_max'] else 'critical'
                else:
                    health_metrics['error_rate'] = 0
                    health_metrics['error_rate_status'] = 'warning'
            else:
                health_metrics['error_rate'] = 0
                health_metrics['error_rate_status'] = 'unknown'
            
            # Check latency
            latency_query = f"avg:trace.django.request.duration{{service:{self.service},env:{self.env}}}.p95(95)"
            latency_result = api.Metric.query(start=start_time, end=end_time, query=latency_query)
            
            if latency_result['series']:
                latency_values = [point[1] for series in latency_result['series'] for point in series['pointlist'] if point[1] is not None]
                if latency_values:
                    avg_latency = sum(latency_values) / len(latency_values)
                    health_metrics['p95_latency'] = avg_latency
                    health_metrics['p95_latency_status'] = 'healthy' if avg_latency <= self.thresholds['latency_p95_max'] else 'warning'
                else:
                    health_metrics['p95_latency'] = 0
                    health_metrics['p95_latency_status'] = 'unknown'
            else:
                health_metrics['p95_latency'] = 0
                health_metrics['p95_latency_status'] = 'unknown'
            
            # Check Apdex score
            apdex_query = f"apdex:trace.django.request{{service:{self.service},env:{self.env}}}"
            apdex_result = api.Metric.query(start=start_time, end=end_time, query=apdex_query)
            
            if apdex_result['series']:
                apdex_values = [point[1] for series in apdex_result['series'] for point in series['pointlist'] if point[1] is not None]
                if apdex_values:
                    avg_apdex = sum(apdex_values) / len(apdex_values)
                    health_metrics['apdex_score'] = avg_apdex
                    health_metrics['apdex_status'] = 'healthy' if avg_apdex >= self.thresholds['apdex_min'] else 'warning'
                else:
                    health_metrics['apdex_score'] = 0
                    health_metrics['apdex_status'] = 'unknown'
            else:
                health_metrics['apdex_score'] = 0
                health_metrics['apdex_status'] = 'unknown'
            
            # Overall health status
            status_counts = {
                'healthy': list(health_metrics.values()).count('healthy'),
                'warning': list(health_metrics.values()).count('warning'),
                'critical': list(health_metrics.values()).count('critical'),
                'unknown': list(health_metrics.values()).count('unknown')
            }
            
            if status_counts['critical'] > 0:
                overall_status = 'critical'
            elif status_counts['warning'] > 0:
                overall_status = 'warning'
            elif status_counts['unknown'] > 0:
                overall_status = 'unknown'
            else:
                overall_status = 'healthy'
            
            return {
                'status': overall_status,
                'metrics': health_metrics,
                'thresholds': self.thresholds,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to check service health: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def check_monitor_coverage(self) -> Dict[str, Any]:
        """Check monitor coverage for the service."""
        if not self.datadog_enabled:
            return {'status': 'error', 'message': 'Datadog client not available'}
        
        try:
            # Get all monitors for the service
            monitors = api.Monitor.get_all()
            
            service_monitors = []
            monitor_types = {}
            
            for monitor in monitors:
                if f"service:{self.service}" in str(monitor.get('tags', [])):
                    service_monitors.append(monitor)
                    
                    # Categorize by type
                    monitor_type = 'unknown'
                    for tag in monitor.get('tags', []):
                        if tag.startswith('monitor_type:'):
                            monitor_type = tag.split(':')[1]
                            break
                    
                    if monitor_type not in monitor_types:
                        monitor_types[monitor_type] = 0
                    monitor_types[monitor_type] += 1
            
            # Expected monitor types for comprehensive coverage
            expected_types = [
                'apm', 'infrastructure', 'database', 'redis', 'celery', 
                'nginx', 'security', 'deployment', 'compliance'
            ]
            
            coverage_score = (len(monitor_types) / len(expected_types)) * 100
            
            return {
                'status': 'healthy' if coverage_score >= self.thresholds['monitor_coverage_min'] else 'warning',
                'total_monitors': len(service_monitors),
                'monitor_types': monitor_types,
                'expected_types': expected_types,
                'coverage_score': coverage_score,
                'missing_types': [t for t in expected_types if t not in monitor_types],
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to check monitor coverage: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def check_tracing_configuration(self) -> Dict[str, Any]:
        """Check tracing configuration and health."""
        if not self.datadog_enabled:
            return {'status': 'error', 'message': 'Datadog client not available'}
        
        try:
            from datetime import datetime, timedelta
            
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(minutes=10)
            
            tracing_checks = {}
            
            # Check trace sampling rate
            total_traces_query = f"sum:trace.django.request.hits{{service:{self.service},env:{self.env}}}"
            nginx_requests_query = f"sum:nginx.http.requests.count{{service:{self.service},env:{self.env}}}"
            
            try:
                traces_result = api.Metric.query(start=start_time, end=end_time, query=total_traces_query)
                nginx_result = api.Metric.query(start=start_time, end=end_time, query=nginx_requests_query)
                
                traces_sum = sum(point[1] for series in traces_result['series'] for point in series['pointlist']) if traces_result['series'] else 0
                nginx_sum = sum(point[1] for series in nginx_result['series'] for point in series['pointlist']) if nginx_result['series'] else 0
                
                if nginx_sum > 0:
                    sampling_rate = (traces_sum / nginx_sum) * 100
                    tracing_checks['sampling_rate'] = sampling_rate
                    tracing_checks['sampling_status'] = 'healthy' if sampling_rate >= self.thresholds['trace_sampling_min'] else 'warning'
                else:
                    tracing_checks['sampling_rate'] = 0
                    tracing_checks['sampling_status'] = 'unknown'
            
            except Exception:
                tracing_checks['sampling_rate'] = 0
                tracing_checks['sampling_status'] = 'unknown'
            
            # Check for missing trace IDs
            missing_trace_query = f"sum:trace.django.request.hits{{service:{self.service},env:{self.env},!trace_id:*}}"
            missing_trace_result = api.Metric.query(start=start_time, end=end_time, query=missing_trace_query)
            
            missing_traces = sum(point[1] for series in missing_trace_result['series'] for point in series['pointlist']) if missing_trace_result['series'] else 0
            tracing_checks['missing_trace_ids'] = missing_traces
            tracing_checks['trace_id_status'] = 'healthy' if missing_traces == 0 else 'warning'
            
            # Check for missing parent IDs
            missing_parent_query = f"sum:trace.django.request.hits{{service:{self.service},env:{self.env},!parent_id:*}}"
            missing_parent_result = api.Metric.query(start=start_time, end=end_time, query=missing_parent_query)
            
            missing_parents = sum(point[1] for series in missing_parent_result['series'] for point in series['pointlist']) if missing_parent_result['series'] else 0
            tracing_checks['missing_parent_ids'] = missing_parents
            tracing_checks['parent_id_status'] = 'healthy' if missing_parents == 0 else 'warning'
            
            # Overall tracing status
            tracing_status = 'healthy'
            if any(status == 'warning' for status in tracing_checks.values() if isinstance(status, str) and 'status' in status):
                tracing_status = 'warning'
            elif any(status == 'unknown' for status in tracing_checks.values() if isinstance(status, str) and 'status' in status):
                tracing_status = 'unknown'
            
            return {
                'status': tracing_status,
                'checks': tracing_checks,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to check tracing configuration: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def check_celery_health(self) -> Dict[str, Any]:
        """Check Celery background job health."""
        if not self.datadog_enabled:
            return {'status': 'error', 'message': 'Datadog client not available'}
        
        try:
            from datetime import datetime, timedelta
            
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(minutes=15)
            
            celery_metrics = {}
            
            # Check task execution rate
            task_hits_query = f"sum:trace.celery.task.hits{{service:{self.service},env:{self.env}}}"
            task_hits_result = api.Metric.query(start=start_time, end=end_time, query=task_hits_query)
            
            if task_hits_result['series']:
                task_sum = sum(point[1] for series in task_hits_result['series'] for point in series['pointlist'])
                task_rate = task_sum / 15  # per minute
                celery_metrics['task_rate'] = task_rate
                celery_metrics['task_rate_status'] = 'healthy' if task_rate > 0 else 'warning'
            else:
                celery_metrics['task_rate'] = 0
                celery_metrics['task_rate_status'] = 'unknown'
            
            # Check task failure rate
            task_errors_query = f"sum:trace.celery.task.errors{{service:{self.service},env:{self.env}}}"
            task_errors_result = api.Metric.query(start=start_time, end=end_time, query=task_errors_query)
            
            if task_hits_result['series'] and task_errors_result['series']:
                task_sum = sum(point[1] for series in task_hits_result['series'] for point in series['pointlist'])
                error_sum = sum(point[1] for series in task_errors_result['series'] for point in series['pointlist'])
                
                if task_sum > 0:
                    failure_rate = (error_sum / task_sum) * 100
                    celery_metrics['failure_rate'] = failure_rate
                    celery_metrics['failure_rate_status'] = 'healthy' if failure_rate <= 10 else 'warning'
                else:
                    celery_metrics['failure_rate'] = 0
                    celery_metrics['failure_rate_status'] = 'unknown'
            else:
                celery_metrics['failure_rate'] = 0
                celery_metrics['failure_rate_status'] = 'unknown'
            
            # Check queue depth
            queue_query = f"avg:celery.queue.length{{service:{self.service},env:{self.env}}}"
            queue_result = api.Metric.query(start=start_time, end=end_time, query=queue_query)
            
            if queue_result['series']:
                queue_values = [point[1] for series in queue_result['series'] for point in series['pointlist'] if point[1] is not None]
                if queue_values:
                    avg_queue_depth = sum(queue_values) / len(queue_values)
                    celery_metrics['queue_depth'] = avg_queue_depth
                    celery_metrics['queue_status'] = 'healthy' if avg_queue_depth < 100 else 'warning'
                else:
                    celery_metrics['queue_depth'] = 0
                    celery_metrics['queue_status'] = 'unknown'
            else:
                celery_metrics['queue_depth'] = 0
                celery_metrics['queue_status'] = 'unknown'
            
            # Overall Celery status
            celery_status = 'healthy'
            if any(status == 'warning' for status in celery_metrics.values() if isinstance(status, str) and 'status' in status):
                celery_status = 'warning'
            elif any(status == 'unknown' for status in celery_metrics.values() if isinstance(status, str) and 'status' in status):
                celery_status = 'unknown'
            
            return {
                'status': celery_status,
                'metrics': celery_metrics,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to check Celery health: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def run_comprehensive_health_check(self) -> Dict[str, Any]:
        """Run comprehensive APM health check."""
        logger.info(f"Running comprehensive APM health check for {self.service}")
        
        health_check = {
            'service': self.service,
            'env': self.env,
            'timestamp': datetime.utcnow().isoformat(),
            'checks': {}
        }
        
        # Run all health checks
        health_check['checks']['service_health'] = self.check_service_health()
        health_check['checks']['monitor_coverage'] = self.check_monitor_coverage()
        health_check['checks']['tracing_configuration'] = self.check_tracing_configuration()
        health_check['checks']['celery_health'] = self.check_celery_health()
        
        # Calculate overall health score
        check_statuses = [check['status'] for check in health_check['checks'].values() if 'status' in check]
        
        if 'critical' in check_statuses or 'error' in check_statuses:
            overall_status = 'critical'
            health_score = 0
        elif 'warning' in check_statuses:
            overall_status = 'warning'
            health_score = 70
        elif 'unknown' in check_statuses:
            overall_status = 'unknown'
            health_score = 50
        else:
            overall_status = 'healthy'
            health_score = 100
        
        health_check['overall_status'] = overall_status
        health_check['health_score'] = health_score
        
        # Generate recommendations
        recommendations = []
        
        # Service health recommendations
        service_health = health_check['checks']['service_health']
        if service_health.get('status') == 'critical':
            recommendations.append("Service health is critical - immediate investigation required")
        elif service_health.get('status') == 'warning':
            if service_health.get('metrics', {}).get('trace_rate', 0) < self.thresholds['trace_rate_min']:
                recommendations.append("Trace rate is low - check ddtrace configuration")
            if service_health.get('metrics', {}).get('error_rate', 0) > self.thresholds['error_rate_max']:
                recommendations.append("Error rate is high - review application logs")
            if service_health.get('metrics', {}).get('p95_latency', 0) > self.thresholds['latency_p95_max']:
                recommendations.append("Latency is high - optimize database queries or scale resources")
        
        # Monitor coverage recommendations
        monitor_coverage = health_check['checks']['monitor_coverage']
        if monitor_coverage.get('status') == 'warning':
            missing_types = monitor_coverage.get('missing_types', [])
            if missing_types:
                recommendations.append(f"Missing monitor types: {', '.join(missing_types)}")
        
        # Tracing configuration recommendations
        tracing_config = health_check['checks']['tracing_configuration']
        if tracing_config.get('status') == 'warning':
            checks = tracing_config.get('checks', {})
            if checks.get('sampling_status') == 'warning':
                recommendations.append("Trace sampling rate is low - consider increasing DD_TRACE_SAMPLE_RATE")
            if checks.get('trace_id_status') == 'warning':
                recommendations.append("Missing trace IDs detected - check ddtrace configuration")
        
        # Celery health recommendations
        celery_health = health_check['checks']['celery_health']
        if celery_health.get('status') == 'warning':
            metrics = celery_health.get('metrics', {})
            if metrics.get('failure_rate_status') == 'warning':
                recommendations.append("Celery task failure rate is high - review task implementation")
            if metrics.get('queue_status') == 'warning':
                recommendations.append("Celery queue depth is high - consider scaling workers")
        
        health_check['recommendations'] = recommendations
        
        return health_check
    
    def send_health_event(self, health_check: Dict[str, Any]) -> bool:
        """Send health check event to Datadog."""
        if not self.datadog_enabled:
            return False
        
        try:
            # Determine event type
            overall_status = health_check['overall_status']
            if overall_status == 'healthy':
                alert_type = 'success'
                event_title = f"APM Health: {overall_status.upper()} - {self.service}"
            elif overall_status == 'warning':
                alert_type = 'warning'
                event_title = f"APM Health: {overall_status.upper()} - {self.service}"
            else:
                alert_type = 'error'
                event_title = f"APM Health: {overall_status.upper()} - {self.service} - ACTION REQUIRED"
            
            # Prepare event text
            event_text = f"""
Service: {self.service}
Environment: {self.env}
Overall Status: {overall_status.upper()}
Health Score: {health_check['health_score']}%
Timestamp: {health_check['timestamp']}

Health Check Results:
{chr(10).join([f"- {name}: {check.get('status', 'unknown').upper()}" for name, check in health_check['checks'].items()])}

Service Health Metrics:
- Trace Rate: {health_check['checks']['service_health'].get('metrics', {}).get('trace_rate', 0):.1f} traces/min
- Error Rate: {health_check['checks']['service_health'].get('metrics', {}).get('error_rate', 0):.2f}%
- P95 Latency: {health_check['checks']['service_health'].get('metrics', {}).get('p95_latency', 0):.1f}ms
- Apdex Score: {health_check['checks']['service_health'].get('metrics', {}).get('apdex_score', 0):.3f}

Monitor Coverage: {health_check['checks']['monitor_coverage'].get('coverage_score', 0):.1f}%
Tracing Status: {health_check['checks']['tracing_configuration'].get('status', 'unknown')}
Celery Status: {health_check['checks']['celery_health'].get('status', 'unknown')}

Recommendations:
{chr(10).join([f"- {rec}" for rec in health_check['recommendations']]) if health_check['recommendations'] else 'No recommendations - all systems healthy'}

APM Dashboard: https://app.datadoghq.com/apm/services/{self.service}?env={self.env}
            """.strip()
            
            # Create event tags
            tags = [
                f"service:{self.service}",
                f"env:{self.env}",
                "source:health_check",
                "monitor_type:apm_health",
                f"overall_status:{overall_status}",
                f"health_score:{health_check['health_score']}"
            ]
            
            # Send event
            api.Event.create(
                title=event_title,
                text=event_text,
                tags=tags,
                alert_type=alert_type
            )
            
            logger.info(f"APM health event sent for {self.service}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send APM health event: {e}")
            return False


def main():
    """Main health check function."""
    parser = argparse.ArgumentParser(description='Run comprehensive APM health check')
    parser.add_argument('--service', type=str, help='Service name (default: from DD_SERVICE)')
    parser.add_argument('--env', type=str, help='Environment (default: from DD_ENV)')
    parser.add_argument('--no-event', action='store_true', help='Do not send health event')
    parser.add_argument('--output', type=str, help='Output report to file')
    parser.add_argument('--thresholds', type=str, help='JSON file with custom thresholds')
    
    args = parser.parse_args()
    
    # Initialize health checker
    checker = APMHealthChecker()
    
    # Override with command line arguments
    if args.service:
        checker.service = args.service
    if args.env:
        checker.env = args.env
    
    # Load custom thresholds
    if args.thresholds:
        try:
            with open(args.thresholds, 'r') as f:
                custom_thresholds = json.load(f)
                checker.thresholds.update(custom_thresholds)
        except Exception as e:
            logger.error(f"Failed to load custom thresholds: {e}")
    
    # Run health check
    health_check = checker.run_comprehensive_health_check()
    
    # Send health event
    if not args.no_event:
        checker.send_health_event(health_check)
    
    # Output report
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(health_check, f, indent=2)
        print(f"Health check report saved to {args.output}")
    else:
        print(json.dumps(health_check, indent=2))
    
    # Exit with appropriate code
    if health_check['overall_status'] in ['critical', 'error']:
        sys.exit(1)
    elif health_check['overall_status'] == 'warning':
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
