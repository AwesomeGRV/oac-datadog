#!/usr/bin/env python3
"""
Security monitoring script for grv-api Datadog setup.
Provides real-time security event detection and automated response capabilities.
"""

import os
import sys
import json
import time
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class SecurityEventType(Enum):
    """Security event types."""
    SQL_INJECTION = "sql_injection"
    XSS_ATTACK = "xss_attack"
    AUTHENTICATION_FAILURE = "auth_failure"
    AUTHORIZATION_FAILURE = "authz_failure"
    RATE_LIMIT_EXCEEDED = "rate_limit"
    SUSPICIOUS_IP = "suspicious_ip"
    DATA_EXFILTRATION = "data_exfiltration"
    BRUTE_FORCE = "brute_force"


@dataclass
class SecurityEvent:
    """Security event data structure."""
    event_type: SecurityEventType
    timestamp: datetime
    source_ip: str
    user_agent: str
    endpoint: str
    method: str
    status_code: int
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    details: Dict[str, Any] = None


class SecurityMonitor:
    """Advanced security monitoring for grv-api."""
    
    def __init__(self):
        self.setup_logging()
        self.load_configuration()
        self.blocked_ips = set()
        self.security_events = []
        self.thresholds = self.config.get('thresholds', {})
        
    def setup_logging(self):
        """Setup structured logging for security events."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def load_configuration(self):
        """Load security monitoring configuration."""
        config_file = os.path.join(
            os.path.dirname(__file__), 
            '..', 
            'config', 
            'security-config.json'
        )
        
        default_config = {
            "thresholds": {
                "failed_auth_attempts": 5,
                "rate_limit_requests": 100,
                "suspicious_ip_threshold": 10,
                "data_exfiltration_bytes": 104857600  # 100MB
            },
            "alerting": {
                "webhook_url": os.getenv("SECURITY_WEBHOOK_URL"),
                "slack_channel": os.getenv("SECURITY_SLACK_CHANNEL"),
                "email_recipients": os.getenv("SECURITY_EMAILS", "").split(",")
            },
            "auto_response": {
                "block_ip_duration": 3600,  # 1 hour
                "enable_auto_blocking": True,
                "notify_teams": True
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
            self.logger.error(f"Failed to load security config: {e}")
            self.config = default_config
    
    def detect_sql_injection(self, log_entry: Dict[str, Any]) -> Optional[SecurityEvent]:
        """Detect SQL injection attempts in log entries."""
        sql_patterns = [
            "union+select", "drop+table", "insert+into", 
            "delete+from", "update+set", "' OR 1=1", 
            '" OR 1=1', "' OR 'a'='a", '" OR "a"="a',
            "sleep(", "benchmark(", "pg_sleep(", "waitfor delay"
        ]
        
        request_data = log_entry.get('message', '').lower()
        user_agent = log_entry.get('user_agent', '').lower()
        query_string = log_entry.get('query_string', '').lower()
        
        for pattern in sql_patterns:
            if pattern in request_data or pattern in user_agent or pattern in query_string:
                return SecurityEvent(
                    event_type=SecurityEventType.SQL_INJECTION,
                    timestamp=datetime.fromisoformat(log_entry.get('timestamp', datetime.utcnow().isoformat())),
                    source_ip=log_entry.get('client_ip', 'unknown'),
                    user_agent=log_entry.get('user_agent', 'unknown'),
                    endpoint=log_entry.get('endpoint', 'unknown'),
                    method=log_entry.get('method', 'unknown'),
                    status_code=log_entry.get('status_code', 0),
                    details={'pattern': pattern, 'full_request': request_data}
                )
        
        return None
    
    def detect_brute_force(self, events: List[SecurityEvent]) -> List[SecurityEvent]:
        """Detect brute force attacks from failed authentication events."""
        auth_failures = [e for e in events if e.event_type == SecurityEventType.AUTHENTICATION_FAILURE]
        
        # Group by IP and time window
        ip_attempts = {}
        for event in auth_failures:
            ip = event.source_ip
            if ip not in ip_attempts:
                ip_attempts[ip] = []
            ip_attempts[ip].append(event)
        
        # Detect brute force patterns
        brute_force_events = []
        threshold = self.thresholds.get('failed_auth_attempts', 5)
        time_window = timedelta(minutes=15)
        
        for ip, attempts in ip_attempts.items():
            # Check for multiple attempts within time window
            attempts.sort(key=lambda x: x.timestamp)
            
            for i in range(len(attempts) - threshold + 1):
                window_start = attempts[i].timestamp
                window_end = window_start + time_window
                
                window_attempts = [a for a in attempts[i:] if a.timestamp <= window_end]
                
                if len(window_attempts) >= threshold:
                    brute_force_events.append(SecurityEvent(
                        event_type=SecurityEventType.BRUTE_FORCE,
                        timestamp=window_end,
                        source_ip=ip,
                        user_agent=attempts[i].user_agent,
                        endpoint=attempts[i].endpoint,
                        method=attempts[i].method,
                        status_code=401,
                        details={
                            'attempt_count': len(window_attempts),
                            'time_window': str(time_window),
                            'user_ids': list(set([a.user_id for a in window_attempts if a.user_id]))
                        }
                    ))
                    break
        
        return brute_force_events
    
    def detect_data_exfiltration(self, log_entry: Dict[str, Any]) -> Optional[SecurityEvent]:
        """Detect potential data exfiltration based on response sizes."""
        response_size = log_entry.get('response_size', 0)
        threshold = self.thresholds.get('data_exfiltration_bytes', 104857600)  # 100MB
        
        if response_size > threshold:
            return SecurityEvent(
                event_type=SecurityEventType.DATA_EXFILTRATION,
                timestamp=datetime.fromisoformat(log_entry.get('timestamp', datetime.utcnow().isoformat())),
                source_ip=log_entry.get('client_ip', 'unknown'),
                user_agent=log_entry.get('user_agent', 'unknown'),
                endpoint=log_entry.get('endpoint', 'unknown'),
                method=log_entry.get('method', 'unknown'),
                status_code=log_entry.get('status_code', 0),
                details={
                    'response_size': response_size,
                    'threshold': threshold,
                    'endpoint_type': self.classify_endpoint(log_entry.get('endpoint', ''))
                }
            )
        
        return None
    
    def classify_endpoint(self, endpoint: str) -> str:
        """Classify endpoint type for security analysis."""
        if '/api/v1/users' in endpoint or '/admin/users' in endpoint:
            return 'user_data'
        elif '/api/v1/export' in endpoint or '/download' in endpoint:
            return 'export'
        elif '/api/v1/reports' in endpoint:
            return 'reports'
        elif '/health' in endpoint or '/status' in endpoint:
            return 'health'
        else:
            return 'other'
    
    def block_ip(self, ip_address: str, duration: int = 3600) -> bool:
        """Block IP address using firewall or WAF."""
        if not self.config.get('auto_response', {}).get('enable_auto_blocking', True):
            return False
        
        try:
            # Implementation depends on your infrastructure
            # Example for cloud provider WAF or firewall API
            webhook_url = self.config.get('alerting', {}).get('webhook_url')
            
            if webhook_url:
                payload = {
                    'action': 'block_ip',
                    'ip_address': ip_address,
                    'duration': duration,
                    'reason': 'Automated security response',
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                response = requests.post(webhook_url, json=payload, timeout=10)
                if response.status_code == 200:
                    self.blocked_ips.add(ip_address)
                    self.logger.info(f"Successfully blocked IP: {ip_address}")
                    return True
                else:
                    self.logger.error(f"Failed to block IP {ip_address}: {response.text}")
                    return False
            
            # Fallback: log the blocking action
            self.logger.warning(f"IP blocking requested for {ip_address} (duration: {duration}s)")
            self.blocked_ips.add(ip_address)
            return True
            
        except Exception as e:
            self.logger.error(f"Error blocking IP {ip_address}: {e}")
            return False
    
    def send_security_alert(self, event: SecurityEvent) -> bool:
        """Send security alert to configured channels."""
        try:
            alert_data = {
                'alert_type': 'security',
                'event_type': event.event_type.value,
                'severity': 'critical' if event.event_type in [SecurityEventType.SQL_INJECTION, SecurityEventType.DATA_EXFILTRATION] else 'warning',
                'timestamp': event.timestamp.isoformat(),
                'source_ip': event.source_ip,
                'endpoint': event.endpoint,
                'method': event.method,
                'status_code': event.status_code,
                'details': event.details,
                'service': 'grv-api',
                'environment': 'prod'
            }
            
            # Send to webhook
            webhook_url = self.config.get('alerting', {}).get('webhook_url')
            if webhook_url:
                response = requests.post(webhook_url, json=alert_data, timeout=10)
                if response.status_code != 200:
                    self.logger.error(f"Failed to send webhook alert: {response.text}")
            
            # Send to Slack (if configured)
            slack_channel = self.config.get('alerting', {}).get('slack_channel')
            if slack_channel:
                slack_message = f"🚨 SECURITY ALERT: {event.event_type.value.upper()}\n"
                slack_message += f"IP: {event.source_ip}\n"
                slack_message += f"Endpoint: {event.method} {event.endpoint}\n"
                slack_message += f"Time: {event.timestamp}\n"
                if event.details:
                    slack_message += f"Details: {json.dumps(event.details, indent=2)}"
                
                # Implementation depends on your Slack integration
                self.logger.info(f"Slack alert sent to {slack_channel}")
            
            self.logger.info(f"Security alert sent for {event.event_type.value}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send security alert: {e}")
            return False
    
    def process_log_entry(self, log_entry: Dict[str, Any]) -> List[SecurityEvent]:
        """Process a single log entry and detect security events."""
        events = []
        
        # SQL Injection detection
        sql_event = self.detect_sql_injection(log_entry)
        if sql_event:
            events.append(sql_event)
        
        # Data exfiltration detection
        data_event = self.detect_data_exfiltration(log_entry)
        if data_event:
            events.append(data_event)
        
        # Authentication failure detection
        if log_entry.get('status_code') == 401:
            auth_event = SecurityEvent(
                event_type=SecurityEventType.AUTHENTICATION_FAILURE,
                timestamp=datetime.fromisoformat(log_entry.get('timestamp', datetime.utcnow().isoformat())),
                source_ip=log_entry.get('client_ip', 'unknown'),
                user_agent=log_entry.get('user_agent', 'unknown'),
                endpoint=log_entry.get('endpoint', 'unknown'),
                method=log_entry.get('method', 'unknown'),
                status_code=401,
                user_id=log_entry.get('user_id'),
                details={'reason': log_entry.get('error_message', 'Authentication failed')}
            )
            events.append(auth_event)
        
        # Authorization failure detection
        elif log_entry.get('status_code') == 403:
            authz_event = SecurityEvent(
                event_type=SecurityEventType.AUTHORIZATION_FAILURE,
                timestamp=datetime.fromisoformat(log_entry.get('timestamp', datetime.utcnow().isoformat())),
                source_ip=log_entry.get('client_ip', 'unknown'),
                user_agent=log_entry.get('user_agent', 'unknown'),
                endpoint=log_entry.get('endpoint', 'unknown'),
                method=log_entry.get('method', 'unknown'),
                status_code=403,
                user_id=log_entry.get('user_id'),
                details={'required_permission': log_entry.get('required_permission', 'unknown')}
            )
            events.append(authz_event)
        
        return events
    
    def run_monitoring_cycle(self):
        """Run a single monitoring cycle."""
        self.logger.info("Starting security monitoring cycle")
        
        # In a real implementation, you would:
        # 1. Query recent logs from Datadog
        # 2. Process each log entry for security events
        # 3. Detect patterns (brute force, etc.)
        # 4. Take automated actions
        # 5. Send alerts
        
        # Example simulation
        sample_logs = [
            {
                'timestamp': datetime.utcnow().isoformat(),
                'client_ip': '192.168.1.100',
                'user_agent': 'Mozilla/5.0...',
                'endpoint': '/api/v1/users',
                'method': 'GET',
                'status_code': 401,
                'user_id': 'test@example.com',
                'message': 'Authentication failed for user test@example.com'
            }
        ]
        
        all_events = []
        for log_entry in sample_logs:
            events = self.process_log_entry(log_entry)
            all_events.extend(events)
        
        # Detect brute force patterns
        brute_force_events = self.detect_brute_force(all_events)
        all_events.extend(brute_force_events)
        
        # Process events
        for event in all_events:
            self.security_events.append(event)
            
            # Send alert
            self.send_security_alert(event)
            
            # Auto-block IP for critical events
            if event.event_type in [SecurityEventType.SQL_INJECTION, SecurityEventType.BRUTE_FORCE]:
                self.block_ip(event.source_ip)
        
        self.logger.info(f"Processed {len(all_events)} security events")
    
    def generate_security_report(self) -> Dict[str, Any]:
        """Generate security monitoring report."""
        last_24h = datetime.utcnow() - timedelta(hours=24)
        recent_events = [e for e in self.security_events if e.timestamp > last_24h]
        
        event_counts = {}
        for event_type in SecurityEventType:
            event_counts[event_type.value] = len([e for e in recent_events if e.event_type == event_type])
        
        top_offender_ips = {}
        for event in recent_events:
            ip = event.source_ip
            top_offender_ips[ip] = top_offender_ips.get(ip, 0) + 1
        
        report = {
            'timestamp': datetime.utcnow().isoformat(),
            'period': '24h',
            'total_events': len(recent_events),
            'event_counts': event_counts,
            'top_offender_ips': dict(sorted(top_offender_ips.items(), key=lambda x: x[1], reverse=True)[:10]),
            'currently_blocked_ips': list(self.blocked_ips),
            'monitoring_status': 'active'
        }
        
        return report


def main():
    """Main function to run security monitoring."""
    from dotenv import load_dotenv
    load_dotenv()
    
    monitor = SecurityMonitor()
    
    try:
        while True:
            monitor.run_monitoring_cycle()
            time.sleep(60)  # Run every minute
    except KeyboardInterrupt:
        print("\nSecurity monitoring stopped")
        
        # Generate final report
        report = monitor.generate_security_report()
        print("\nSecurity Report:")
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
