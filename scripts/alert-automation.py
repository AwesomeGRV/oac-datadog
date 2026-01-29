#!/usr/bin/env python3
"""
Advanced alert automation and incident response for grv-api Datadog setup.
Provides intelligent alert routing, escalation, and automated remediation.
"""

import os
import sys
import json
import time
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import aiohttp

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class AlertSeverity(Enum):
    """Alert severity levels."""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class AlertStatus(Enum):
    """Alert status values."""
    TRIGGERED = "triggered"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


class IncidentPriority(Enum):
    """Incident priority levels."""
    P1 = "P1"  # Critical - Service down
    P2 = "P2"  # High - Service degraded
    P3 = "P3"  # Medium - Feature impacted
    P4 = "P4"  # Low - Minor issue


@dataclass
class Alert:
    """Alert data structure."""
    id: str
    name: str
    severity: AlertSeverity
    status: AlertStatus
    timestamp: datetime
    message: str
    tags: List[str]
    metric_query: str
    current_value: float
    threshold: float
    service: str = "grv-api"
    environment: str = "prod"
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Incident:
    """Incident data structure."""
    id: str
    title: str
    priority: IncidentPriority
    status: str
    created_at: datetime
    updated_at: datetime
    alerts: List[Alert] = field(default_factory=list)
    assigned_to: Optional[str] = None
    resolution_time: Optional[timedelta] = None
    root_cause: Optional[str] = None
    actions_taken: List[str] = field(default_factory=list)


class AlertAutomation:
    """Advanced alert automation and incident response."""
    
    def __init__(self):
        self.setup_logging()
        self.load_configuration()
        self.active_incidents = {}
        self.alert_rules = self.config.get('alert_rules', {})
        self.automation_rules = self.config.get('automation_rules', {})
        self.escalation_policies = self.config.get('escalation_policies', {})
        
    def setup_logging(self):
        """Setup structured logging for alert automation."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def load_configuration(self):
        """Load alert automation configuration."""
        config_file = os.path.join(
            os.path.dirname(__file__), 
            '..', 
            'config', 
            'alert-automation.json'
        )
        
        default_config = {
            "alert_rules": {
                "service_down": {
                    "conditions": ["error_rate > 50%", "latency_p95 > 5000ms", "availability < 99%"],
                    "auto_incident": True,
                    "priority": "P1",
                    "auto_escalation": True
                },
                "performance_degradation": {
                    "conditions": ["latency_p95 > 2000ms", "apdex_score < 0.8"],
                    "auto_incident": True,
                    "priority": "P2",
                    "auto_escalation": False
                },
                "resource_exhaustion": {
                    "conditions": ["cpu_usage > 90%", "memory_usage > 85%", "disk_space < 10%"],
                    "auto_incident": True,
                    "priority": "P2",
                    "auto_escalation": True
                }
            },
            "automation_rules": {
                "auto_restart_service": {
                    "trigger": "service_down",
                    "conditions": ["error_rate > 80%", "no_recent_deploys"],
                    "action": "restart_service",
                    "cooldown_minutes": 15
                },
                "auto_scale_up": {
                    "trigger": "resource_exhaustion",
                    "conditions": ["cpu_usage > 95%", "memory_usage > 90%"],
                    "action": "scale_horizontal",
                    "cooldown_minutes": 10
                },
                "auto_rollback": {
                    "trigger": "recent_deploy_issues",
                    "conditions": ["error_rate_spike > 50%", "within_30min_of_deploy"],
                    "action": "rollback_deployment",
                    "cooldown_minutes": 30
                }
            },
            "escalation_policies": {
                "P1": {
                    "levels": [
                        {"delay_minutes": 0, "notify": ["oncall_engineer", "team_lead"]},
                        {"delay_minutes": 5, "notify": ["engineering_manager"]},
                        {"delay_minutes": 15, "notify": ["vp_engineering", "cto"]},
                        {"delay_minutes": 30, "notify": ["executive_team"]}
                    ]
                },
                "P2": {
                    "levels": [
                        {"delay_minutes": 0, "notify": ["oncall_engineer"]},
                        {"delay_minutes": 15, "notify": ["team_lead"]},
                        {"delay_minutes": 60, "notify": ["engineering_manager"]}
                    ]
                }
            },
            "notification_channels": {
                "slack": {
                    "webhook_url": os.getenv("SLACK_WEBHOOK_URL"),
                    "channels": {
                        "critical": "#incidents-critical",
                        "warning": "#incidents-warning",
                        "info": "#incidents-info"
                    }
                },
                "pagerduty": {
                    "service_key": os.getenv("PAGERDUTY_SERVICE_KEY"),
                    "escalation_policy": os.getenv("PAGERDUTY_ESCALATION_POLICY")
                },
                "email": {
                    "smtp_server": os.getenv("SMTP_SERVER"),
                    "recipients": {
                        "critical": os.getenv("CRITICAL_EMAIL_RECIPIENTS", "").split(","),
                        "warning": os.getenv("WARNING_EMAIL_RECIPIENTS", "").split(",")
                    }
                }
            }
        }
        
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    self.config = json.load(f)
            else:
                self.config = default_config
                # Create default config file
                os.makedirs(os.path.dirname(config_file), exist_ok=True)
                with open(config_file, 'w') as f:
                    json.dump(default_config, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to load alert automation config: {e}")
            self.config = default_config
    
    def classify_alert(self, alert: Alert) -> Optional[str]:
        """Classify alert into incident type."""
        for rule_name, rule_config in self.alert_rules.items():
            conditions = rule_config.get('conditions', [])
            
            # Simple pattern matching (in real implementation, use more sophisticated logic)
            alert_text = f"{alert.name} {alert.message}".lower()
            
            if all(condition.lower() in alert_text for condition in conditions):
                return rule_name
        
        return None
    
    def create_incident(self, alert: Alert, incident_type: str) -> Incident:
        """Create incident from alert."""
        rule_config = self.alert_rules.get(incident_type, {})
        priority = IncidentPriority[rule_config.get('priority', 'P3')]
        
        incident_id = f"INC-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-{len(self.active_incidents)}"
        
        incident = Incident(
            id=incident_id,
            title=f"{incident_type.replace('_', ' ').title()} - {alert.name}",
            priority=priority,
            status="open",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            alerts=[alert]
        )
        
        self.active_incidents[incident_id] = incident
        self.logger.info(f"Created incident {incident_id} with priority {priority.value}")
        
        return incident
    
    def send_notification(self, incident: Incident, message: str, channels: List[str] = None):
        """Send notification through configured channels."""
        if channels is None:
            channels = ["slack", "pagerduty"]
        
        severity_map = {
            IncidentPriority.P1: "critical",
            IncidentPriority.P2: "warning", 
            IncidentPriority.P3: "warning",
            IncidentPriority.P4: "info"
        }
        
        severity = severity_map.get(incident.priority, "info")
        
        for channel in channels:
            try:
                if channel == "slack":
                    self.send_slack_notification(incident, message, severity)
                elif channel == "pagerduty":
                    self.send_pagerduty_alert(incident, message)
                elif channel == "email":
                    self.send_email_notification(incident, message, severity)
                
                self.logger.info(f"Sent {channel} notification for incident {incident.id}")
                
            except Exception as e:
                self.logger.error(f"Failed to send {channel} notification: {e}")
    
    def send_slack_notification(self, incident: Incident, message: str, severity: str):
        """Send Slack notification."""
        slack_config = self.config.get('notification_channels', {}).get('slack', {})
        webhook_url = slack_config.get('webhook_url')
        
        if not webhook_url:
            return
        
        channel = slack_config.get('channels', {}).get(severity, "#incidents")
        
        color_map = {
            "critical": "danger",
            "warning": "warning", 
            "info": "good"
        }
        
        payload = {
            "channel": channel,
            "username": "Incident Bot",
            "icon_emoji": ":warning:",
            "attachments": [{
                "color": color_map.get(severity, "warning"),
                "title": f"Incident {incident.id} - {incident.priority.value}",
                "text": message,
                "fields": [
                    {"title": "Service", "value": incident.alerts[0].service, "short": True},
                    {"title": "Environment", "value": incident.alerts[0].environment, "short": True},
                    {"title": "Created", "value": incident.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"), "short": True},
                    {"title": "Alerts", "value": str(len(incident.alerts)), "short": True}
                ],
                "footer": "Datadog Alert Automation",
                "ts": int(incident.created_at.timestamp())
            }]
        }
        
        response = requests.post(webhook_url, json=payload, timeout=10)
        if response.status_code != 200:
            raise Exception(f"Slack API error: {response.text}")
    
    def send_pagerduty_alert(self, incident: Incident, message: str):
        """Send PagerDuty alert."""
        pd_config = self.config.get('notification_channels', {}).get('pagerduty', {})
        service_key = pd_config.get('service_key')
        
        if not service_key:
            return
        
        severity_map = {
            IncidentPriority.P1: "critical",
            IncidentPriority.P2: "error",
            IncidentPriority.P3: "warning",
            IncidentPriority.P4: "info"
        }
        
        payload = {
            "routing_key": service_key,
            "event_action": "trigger",
            "payload": {
                "summary": f"Incident {incident.id}: {incident.title}",
                "source": "grv-api",
                "severity": severity_map.get(incident.priority, "warning"),
                "timestamp": incident.created_at.isoformat(),
                "component": "datadog-automation",
                "group": incident.priority.value,
                "class": "incident",
                "custom_details": {
                    "incident_id": incident.id,
                    "priority": incident.priority.value,
                    "alert_count": len(incident.alerts),
                    "message": message
                }
            }
        }
        
        response = requests.post("https://events.pagerduty.com/v2/enqueue", json=payload, timeout=10)
        if response.status_code != 202:
            raise Exception(f"PagerDuty API error: {response.text}")
    
    def send_email_notification(self, incident: Incident, message: str, severity: str):
        """Send email notification."""
        email_config = self.config.get('notification_channels', {}).get('email', {})
        recipients = email_config.get('recipients', {}).get(severity, [])
        
        if not recipients or not email_config.get('smtp_server'):
            return
        
        # Implementation depends on your email setup
        self.logger.info(f"Email notification sent to {recipients}")
    
    def execute_automation(self, incident: Incident, alert: Alert):
        """Execute automated remediation actions."""
        incident_type = self.classify_alert(alert)
        
        if not incident_type:
            return
        
        automation_rules = self.automation_rules.get(incident_type, {})
        
        for rule_name, rule_config in automation_rules.items():
            if self.should_execute_automation(rule_config, incident, alert):
                action = rule_config.get('action')
                
                try:
                    if action == "restart_service":
                        self.restart_service()
                    elif action == "scale_horizontal":
                        self.scale_horizontal()
                    elif action == "rollback_deployment":
                        self.rollback_deployment()
                    elif action == "clear_cache":
                        self.clear_cache()
                    
                    incident.actions_taken.append(f"Executed automation: {action}")
                    self.logger.info(f"Executed automation action: {action} for incident {incident.id}")
                    
                except Exception as e:
                    self.logger.error(f"Failed to execute automation {action}: {e}")
    
    def should_execute_automation(self, rule_config: Dict[str, Any], incident: Incident, alert: Alert) -> bool:
        """Check if automation should be executed."""
        # Check cooldown
        cooldown_minutes = rule_config.get('cooldown_minutes', 30)
        last_execution = self.get_last_execution_time(rule_config.get('action'))
        
        if last_execution and (datetime.utcnow() - last_execution).total_seconds() < cooldown_minutes * 60:
            return False
        
        # Check conditions (simplified)
        conditions = rule_config.get('conditions', [])
        
        for condition in conditions:
            if condition == "error_rate > 80%" and alert.current_value <= 80:
                return False
            elif condition == "no_recent_deploys" and self.has_recent_deploy():
                return False
        
        return True
    
    def restart_service(self):
        """Restart the grv-api service."""
        # Implementation depends on your deployment setup
        # Example for Docker/Kubernetes
        self.logger.info("Executing service restart automation")
        
        # Example: kubectl rollout restart deployment/grv-api
        # or: docker-compose restart grv-api
        pass
    
    def scale_horizontal(self):
        """Scale service horizontally."""
        self.logger.info("Executing horizontal scaling automation")
        # Implementation depends on your orchestration platform
        pass
    
    def rollback_deployment(self):
        """Rollback to previous deployment."""
        self.logger.info("Executing deployment rollback automation")
        # Implementation depends on your deployment system
        pass
    
    def clear_cache(self):
        """Clear application cache."""
        self.logger.info("Executing cache clear automation")
        # Implementation depends on your cache system
        pass
    
    def has_recent_deploy(self) -> bool:
        """Check if there was a recent deployment."""
        # Query deployment events from Datadog
        # Simplified implementation
        return False
    
    def get_last_execution_time(self, action: str) -> Optional[datetime]:
        """Get last execution time for an automation action."""
        # In real implementation, store execution history
        return None
    
    def process_alert(self, alert_data: Dict[str, Any]) -> Optional[Incident]:
        """Process incoming alert and create incident if needed."""
        alert = Alert(
            id=alert_data.get('id', ''),
            name=alert_data.get('name', ''),
            severity=AlertSeverity[alert_data.get('severity', 'warning').upper()],
            status=AlertStatus[alert_data.get('status', 'triggered').upper()],
            timestamp=datetime.fromisoformat(alert_data.get('timestamp', datetime.utcnow().isoformat())),
            message=alert_data.get('message', ''),
            tags=alert_data.get('tags', []),
            metric_query=alert_data.get('query', ''),
            current_value=alert_data.get('value', 0),
            threshold=alert_data.get('threshold', 0),
            metadata=alert_data.get('metadata', {})
        )
        
        # Classify alert
        incident_type = self.classify_alert(alert)
        
        if incident_type and self.alert_rules.get(incident_type, {}).get('auto_incident', False):
            incident = self.create_incident(alert, incident_type)
            
            # Send initial notification
            message = f"Incident created: {incident.title}\n\nAlert: {alert.name}\nMessage: {alert.message}"
            self.send_notification(incident, message)
            
            # Execute automation
            self.execute_automation(incident, alert)
            
            return incident
        
        return None
    
    def escalate_incident(self, incident: Incident):
        """Escalate incident based on time and priority."""
        escalation_policy = self.escalation_policies.get(incident.priority.value, {})
        levels = escalation_policy.get('levels', [])
        
        time_since_creation = datetime.utcnow() - incident.created_at
        
        for level in levels:
            delay = timedelta(minutes=level.get('delay_minutes', 0))
            
            if time_since_creation >= delay:
                notify_list = level.get('notify', [])
                
                # Check if already notified at this level
                level_key = f"escalated_level_{level.get('delay_minutes', 0)}"
                if level_key not in incident.actions_taken:
                    message = f"Incident {incident.id} escalated to {notify_list}"
                    self.send_notification(incident, message, channels=["slack", "pagerduty"])
                    incident.actions_taken.append(level_key)
                    self.logger.info(f"Escalated incident {incident.id} to level {level.get('delay_minutes', 0)}")
    
    def run_automation_cycle(self):
        """Run automation cycle for active incidents."""
        self.logger.info("Starting alert automation cycle")
        
        # Check for escalation
        for incident in self.active_incidents.values():
            if incident.status == "open":
                self.escalate_incident(incident)
        
        # In real implementation, you would:
        # 1. Query Datadog for new alerts
        # 2. Process each alert
        # 3. Create incidents if needed
        # 4. Execute automation
        # 5. Handle escalation
        
        # Example simulation
        sample_alert = {
            'id': 'alert-123',
            'name': '[GRV-API] High Error Rate Alert',
            'severity': 'critical',
            'status': 'triggered',
            'timestamp': datetime.utcnow().isoformat(),
            'message': 'High error rate detected for grv-api service',
            'tags': ['service:grv-api', 'env:prod'],
            'value': 85.5,
            'threshold': 5.0
        }
        
        incident = self.process_alert(sample_alert)
        if incident:
            self.logger.info(f"Processed alert and created incident {incident.id}")
    
    def generate_automation_report(self) -> Dict[str, Any]:
        """Generate automation performance report."""
        last_24h = datetime.utcnow() - timedelta(hours=24)
        
        active_incidents = [i for i in self.active_incidents.values() if i.created_at > last_24h]
        resolved_incidents = [i for i in active_incidents if i.status == "resolved"]
        
        automation_stats = {
            'total_incidents': len(active_incidents),
            'resolved_incidents': len(resolved_incidents),
            'resolution_rate': len(resolved_incidents) / len(active_incidents) if active_incidents else 0,
            'avg_resolution_time': self.calculate_avg_resolution_time(resolved_incidents),
            'automation_actions_executed': sum(len(i.actions_taken) for i in active_incidents),
            'incidents_by_priority': self.count_incidents_by_priority(active_incidents)
        }
        
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'period': '24h',
            'automation_stats': automation_stats,
            'active_incidents_count': len([i for i in self.active_incidents.values() if i.status == "open"]),
            'automation_rules_count': len(self.automation_rules),
            'escalation_policies_count': len(self.escalation_policies)
        }
    
    def calculate_avg_resolution_time(self, incidents: List[Incident]) -> Optional[float]:
        """Calculate average resolution time in minutes."""
        if not incidents:
            return None
        
        total_time = sum(
            (i.resolution_time.total_seconds() / 60) 
            for i in incidents 
            if i.resolution_time
        )
        
        return total_time / len(incidents)
    
    def count_incidents_by_priority(self, incidents: List[Incident]) -> Dict[str, int]:
        """Count incidents by priority."""
        counts = {priority.value: 0 for priority in IncidentPriority}
        
        for incident in incidents:
            counts[incident.priority.value] += 1
        
        return counts


def main():
    """Main function to run alert automation."""
    from dotenv import load_dotenv
    load_dotenv()
    
    automation = AlertAutomation()
    
    try:
        while True:
            automation.run_automation_cycle()
            time.sleep(30)  # Run every 30 seconds
    except KeyboardInterrupt:
        print("\nAlert automation stopped")
        
        # Generate final report
        report = automation.generate_automation_report()
        print("\nAutomation Report:")
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
