#!/usr/bin/env python3
"""
Enhanced deployment event script for grv-api with comprehensive monitoring.
Provides automated deployment event creation and rollback detection.
"""

import os
import sys
import json
import logging
import argparse
import subprocess
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

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


class GRVDeploymentTracker:
    """Enhanced deployment tracking for grv-api service."""
    
    def __init__(self):
        self.api_key = os.getenv('DD_API_KEY')
        self.app_key = os.getenv('DD_APP_KEY')
        self.service = os.getenv('DD_SERVICE', 'grv-api')
        self.env = os.getenv('DD_ENV', 'prod')
        self.team = os.getenv('DD_TEAM', 'backend')
        self.owner = os.getenv('DD_OWNER', 'grv-team')
        
        # Deployment configuration
        self.deployment_window = int(os.getenv('DEPLOYMENT_MONITORING_WINDOW', 1800))  # 30 minutes
        self.rollback_threshold = float(os.getenv('ROLLBACK_THRESHOLD', '15.0'))
        self.latency_threshold = float(os.getenv('ROLLBACK_LATENCY_THRESHOLD', '3000'))
        
        # Initialize Datadog client
        if DATADOG_AVAILABLE and self.api_key and self.app_key:
            initialize(api_key=self.api_key, app_key=self.app_key)
            self.datadog_enabled = True
        else:
            self.datadog_enabled = False
            logger.warning("Datadog client not available or missing credentials")
    
    def get_git_info(self) -> Dict[str, str]:
        """Get git information for the deployment."""
        git_info = {}
        
        try:
            # Get current git SHA
            result = subprocess.run(['git', 'rev-parse', 'HEAD'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                git_info['sha'] = result.stdout.strip()
            
            # Get git branch
            result = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                git_info['branch'] = result.stdout.strip()
            
            # Get commit message
            result = subprocess.run(['git', 'log', '-1', '--pretty=%B'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                git_info['message'] = result.stdout.strip()
            
            # Get commit author
            result = subprocess.run(['git', 'log', '-1', '--pretty=%an'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                git_info['author'] = result.stdout.strip()
            
            # Get commit date
            result = subprocess.run(['git', 'log', '-1', '--pretty=%ai'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                git_info['date'] = result.stdout.strip()
                
        except Exception as e:
            logger.error(f"Failed to get git information: {e}")
        
        return git_info
    
    def send_deployment_event(self, version: str, git_info: Dict[str, str], 
                            deployer: str = None, notes: str = None) -> bool:
        """Send deployment event to Datadog."""
        if not self.datadog_enabled:
            logger.error("Datadog client not available")
            return False
        
        try:
            # Prepare event data
            event_title = f"Deployment: {self.service} v{version}"
            event_text = f"""
Service: {self.service}
Environment: {self.env}
Version: {version}
Deployer: {deployer or 'system'}
Deployment Time: {datetime.utcnow().isoformat()}

Git Information:
- SHA: {git_info.get('sha', 'unknown')}
- Branch: {git_info.get('branch', 'unknown')}
- Author: {git_info.get('author', 'unknown')}
- Message: {git_info.get('message', 'No message')[:200]}...

{f'Notes: {notes}' if notes else ''}

Monitoring:
- Error rate monitoring: Enabled
- Latency monitoring: Enabled
- Rollback detection: Enabled
- Performance regression: Enabled

Dashboard: https://app.datadoghq.com/apm/services/{self.service}?env={self.env}
            """.strip()
            
            # Create event tags
            tags = [
                f"service:{self.service}",
                f"env:{self.env}",
                "source:deploy",
                f"version:{version}",
                f"team:{self.team}",
                f"owner:{self.owner}",
            ]
            
            if git_info.get('sha'):
                tags.append(f"git.sha:{git_info['sha']}")
            
            if git_info.get('branch'):
                tags.append(f"git.branch:{git_info['branch']}")
            
            if deployer:
                tags.append(f"deployer:{deployer}")
            
            # Send event
            api.Event.create(
                title=event_title,
                text=event_text,
                tags=tags,
                alert_type='info'
            )
            
            logger.info(f"Deployment event sent for {self.service} v{version}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send deployment event: {e}")
            return False
    
    def create_deployment_monitor(self, version: str) -> bool:
        """Create temporary deployment monitoring monitor."""
        if not self.datadog_enabled:
            logger.error("Datadog client not available")
            return False
        
        try:
            # Monitor query for deployment rollback detection
            monitor_query = f"""
            sum(last_{self.deployment_window//60}m):sum:trace.django.request.errors{{service:{self.service},env:{self.env},version:{version}}} / sum(last_{self.deployment_window//60}m):sum:trace.django.request.hits{{service:{self.service},env:{self.env},version:{version}}} * 100 > {self.rollback_threshold} AND sum(last_{self.deployment_window//60}m):sum:trace.django.request.duration{{service:{self.service},env:{self.env},version:{version}}}.p95(95) > {self.latency_threshold}
            """.strip()
            
            monitor_message = f"""
            Potential deployment rollback detected for {self.service} service.
            
            Version: {version}
            Error Rate: {{{{value}}}}%
            P95 Latency: {{{{trace.django.request.duration.p95}}}}ms
            Environment: {self.env}
            Service: {self.service}
            
            Rollback Indicators:
            - High error rate post-deployment
            - Significant latency degradation
            - Performance regression detected
            
            Immediate Actions Required:
            1. Consider automatic rollback to previous version
            2. Check deployment logs for errors
            3. Review recent code changes
            4. Verify database migrations
            5. Monitor user impact and support tickets
            
            Rollback Decision:
            - If error rate > 20%: Immediate rollback recommended
            - If latency > 5s: Consider rollback
            - If both metrics degraded: Emergency rollback
            
            Deployment Dashboard: https://app.datadoghq.com/apm/services/{self.service}?env={self.env}&view=performance
            """.strip()
            
            # Create monitor
            monitor = api.Monitor.create(
                type="query alert",
                query=monitor_query,
                name=f"[{self.service.upper()}] Deployment Rollback Detection - v{version}",
                message=monitor_message,
                tags=[
                    f"service:{self.service}",
                    f"env:{self.env}",
                    f"version:{version}",
                    "monitor_type:deployment",
                    "severity:critical",
                    "event_type:rollback"
                ],
                options={
                    "notify_audit": False,
                    "locked": False,
                    "timeout_h": 0,
                    "silenced": {},
                    "include_tags": True,
                    "new_host_delay": 60,
                    "require_full_window": True,
                    "notify_no_data": False,
                    "renotify_interval": 15,
                    "escalation_message": "CRITICAL: Deployment performance severely degraded. Emergency rollback recommended immediately.",
                    "evaluation_delay": 60,
                    "thresholds": {
                        "critical": 25.0,
                        "warning": 15.0,
                        "critical_recovery": 5.0,
                        "warning_recovery": 2.0
                    }
                },
                priority=1
            )
            
            # Schedule monitor deletion after deployment window
            self._schedule_monitor_cleanup(monitor['id'])
            
            logger.info(f"Deployment monitor created: {monitor['id']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create deployment monitor: {e}")
            return False
    
    def _schedule_monitor_cleanup(self, monitor_id: int):
        """Schedule monitor cleanup after deployment window."""
        # This would typically be implemented with a background task
        # For now, we'll log the monitor ID for manual cleanup
        logger.info(f"Monitor {monitor_id} should be cleaned up after {self.deployment_window} seconds")
    
    def get_deployment_metrics(self, version: str, window_minutes: int = 30) -> Dict[str, Any]:
        """Get deployment performance metrics."""
        if not self.datadog_enabled:
            return {}
        
        try:
            from datetime import datetime, timedelta
            import time
            
            # Calculate time window
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(minutes=window_minutes)
            
            # Query metrics
            metrics = {}
            
            # Error rate
            error_query = f"sum:{self.service}.django.request.errors{{service:{self.service},env:{self.env},version:{version}}}"
            hits_query = f"sum:{self.service}.django.request.hits{{service:{self.service},env:{self.env},version:{version}}}"
            
            try:
                error_result = api.Metric.query(
                    start=start_time,
                    end=end_time,
                    query=error_query
                )
                
                hits_result = api.Metric.query(
                    start=start_time,
                    end=end_time,
                    query=hits_query
                )
                
                if error_result['series'] and hits_result['series']:
                    error_sum = sum(point[1] for series in error_result['series'] for point in series['pointlist'])
                    hits_sum = sum(point[1] for series in hits_result['series'] for point in series['pointlist'])
                    
                    if hits_sum > 0:
                        metrics['error_rate'] = (error_sum / hits_sum) * 100
                    else:
                        metrics['error_rate'] = 0
                
            except Exception as e:
                logger.error(f"Failed to query error metrics: {e}")
            
            # Latency
            latency_query = f"avg:{self.service}.django.request.duration{{service:{self.service},env:{self.env},version:{version}}}.p95(95)"
            
            try:
                latency_result = api.Metric.query(
                    start=start_time,
                    end=end_time,
                    query=latency_query
                )
                
                if latency_result['series']:
                    latency_values = [point[1] for series in latency_result['series'] for point in series['pointlist'] if point[1] is not None]
                    if latency_values:
                        metrics['p95_latency'] = sum(latency_values) / len(latency_values)
                
            except Exception as e:
                logger.error(f"Failed to query latency metrics: {e}")
            
            # Request volume
            try:
                volume_result = api.Metric.query(
                    start=start_time,
                    end=end_time,
                    query=hits_query
                )
                
                if volume_result['series']:
                    volume_sum = sum(point[1] for series in volume_result['series'] for point in series['pointlist'])
                    metrics['request_volume'] = volume_sum
                
            except Exception as e:
                logger.error(f"Failed to query volume metrics: {e}")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get deployment metrics: {e}")
            return {}
    
    def assess_deployment_health(self, version: str) -> Dict[str, Any]:
        """Assess deployment health and provide recommendations."""
        metrics = self.get_deployment_metrics(version)
        
        assessment = {
            'version': version,
            'timestamp': datetime.utcnow().isoformat(),
            'metrics': metrics,
            'health_status': 'unknown',
            'recommendations': [],
            'rollback_risk': 'low'
        }
        
        # Assess error rate
        error_rate = metrics.get('error_rate', 0)
        if error_rate > 20:
            assessment['health_status'] = 'critical'
            assessment['rollback_risk'] = 'high'
            assessment['recommendations'].append('Immediate rollback recommended - error rate too high')
        elif error_rate > 10:
            assessment['health_status'] = 'warning'
            assessment['rollback_risk'] = 'medium'
            assessment['recommendations'].append('Consider rollback - error rate elevated')
        elif error_rate > 5:
            assessment['health_status'] = 'warning'
            assessment['rollback_risk'] = 'low'
            assessment['recommendations'].append('Monitor closely - error rate elevated')
        else:
            assessment['health_status'] = 'healthy'
        
        # Assess latency
        p95_latency = metrics.get('p95_latency', 0)
        if p95_latency > 5000:
            assessment['health_status'] = 'critical'
            assessment['rollback_risk'] = 'high'
            assessment['recommendations'].append('Immediate rollback recommended - latency too high')
        elif p95_latency > 3000:
            assessment['health_status'] = 'warning'
            assessment['rollback_risk'] = 'medium'
            assessment['recommendations'].append('Consider rollback - latency elevated')
        elif p95_latency > 2000:
            assessment['health_status'] = 'warning'
            assessment['rollback_risk'] = 'low'
            assessment['recommendations'].append('Monitor closely - latency elevated')
        
        # Assess request volume
        request_volume = metrics.get('request_volume', 0)
        if request_volume == 0:
            assessment['health_status'] = 'critical'
            assessment['rollback_risk'] = 'high'
            assessment['recommendations'].append('No requests detected - service may be down')
        
        return assessment
    
    def track_deployment(self, version: str, deployer: str = None, 
                        notes: str = None, auto_monitor: bool = True) -> Dict[str, Any]:
        """Track a complete deployment with monitoring."""
        logger.info(f"Tracking deployment for {self.service} v{version}")
        
        # Get git information
        git_info = self.get_git_info()
        
        # Send deployment event
        event_sent = self.send_deployment_event(version, git_info, deployer, notes)
        
        # Create deployment monitor
        monitor_created = False
        if auto_monitor:
            monitor_created = self.create_deployment_monitor(version)
        
        # Initial health assessment
        initial_health = self.assess_deployment_health(version)
        
        result = {
            'service': self.service,
            'env': self.env,
            'version': version,
            'deployer': deployer,
            'git_info': git_info,
            'event_sent': event_sent,
            'monitor_created': monitor_created,
            'initial_health': initial_health,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Deployment tracking completed: {json.dumps(result, indent=2)}")
        return result


def main():
    """Main deployment tracking function."""
    parser = argparse.ArgumentParser(description='Track grv-api deployment with enhanced monitoring')
    parser.add_argument('--version', type=str, required=True, help='Deployment version')
    parser.add_argument('--deployer', type=str, help='Deployer name')
    parser.add_argument('--notes', type=str, help='Deployment notes')
    parser.add_argument('--no-monitor', action='store_true', help='Disable automatic monitoring')
    parser.add_argument('--assess-health', action='store_true', help='Assess deployment health')
    
    args = parser.parse_args()
    
    # Initialize deployment tracker
    tracker = GRVDeploymentTracker()
    
    # Track deployment
    result = tracker.track_deployment(
        version=args.version,
        deployer=args.deployer,
        notes=args.notes,
        auto_monitor=not args.no_monitor
    )
    
    # Assess health if requested
    if args.assess_health:
        health = tracker.assess_deployment_health(args.version)
        result['current_health'] = health
    
    # Print result
    print(json.dumps(result, indent=2))
    
    # Exit with appropriate code
    if result['initial_health']['health_status'] == 'critical':
        sys.exit(1)
    elif result['initial_health']['health_status'] == 'warning':
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
