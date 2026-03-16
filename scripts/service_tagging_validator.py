#!/usr/bin/env python3
"""
Service tagging compliance validator for grv-api Datadog monitoring.
Ensures all services have proper tagging for effective monitoring and alerting.
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set

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


class ServiceTaggingValidator:
    """Validates and enforces service tagging compliance for grv-api."""
    
    def __init__(self):
        self.api_key = os.getenv('DD_API_KEY')
        self.app_key = os.getenv('DD_APP_KEY')
        self.service = os.getenv('DD_SERVICE', 'grv-api')
        self.env = os.getenv('DD_ENV', 'prod')
        
        # Required tags configuration
        self.required_tags = {
            'service': True,
            'env': True,
            'version': True,
            'team': True,
            'owner': True
        }
        
        # Expected tag values
        self.expected_values = {
            'service': [self.service],
            'env': ['prod', 'stg', 'dev'],
            'team': ['backend', 'frontend', 'devops'],
            'owner': ['grv-team']
        }
        
        # Initialize Datadog client
        if DATADOG_AVAILABLE and self.api_key and self.app_key:
            initialize(api_key=self.api_key, app_key=self.app_key)
            self.datadog_enabled = True
        else:
            self.datadog_enabled = False
            logger.warning("Datadog client not available or missing credentials")
    
    def get_service_metrics(self) -> Dict[str, Any]:
        """Get all metrics for the service to analyze tagging."""
        if not self.datadog_enabled:
            return {}
        
        try:
            from datetime import datetime, timedelta
            
            # Get metrics from the last hour
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=1)
            
            # Query for all metrics with service tag
            query = f"*{{service:{self.service},env:{self.env}}}"
            
            result = api.Metric.query(
                start=start_time,
                end=end_time,
                query=query
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get service metrics: {e}")
            return {}
    
    def extract_tags_from_metrics(self, metrics_data: Dict[str, Any]) -> Set[str]:
        """Extract all tags from metrics data."""
        tags = set()
        
        try:
            if 'series' in metrics_data:
                for series in metrics_data['series']:
                    if 'tags' in series:
                        tags.update(series['tags'])
                    
                    if 'scope' in series:
                        tags.update(series['scope'].split(','))
                    
                    if 'expression' in series:
                        # Extract tags from query expressions
                        import re
                        tag_matches = re.findall(r'(\w+):\w+', series['expression'])
                        tags.update([f"{match[0]}:{match[1]}" for match in tag_matches])
        
        except Exception as e:
            logger.error(f"Failed to extract tags: {e}")
        
        return tags
    
    def parse_tags(self, tags: Set[str]) -> Dict[str, Set[str]]:
        """Parse tags into key-value pairs."""
        parsed_tags = {}
        
        for tag in tags:
            if ':' in tag:
                key, value = tag.split(':', 1)
                if key not in parsed_tags:
                    parsed_tags[key] = set()
                parsed_tags[key].add(value)
            else:
                # Unkeyed tag
                if 'unkeyed' not in parsed_tags:
                    parsed_tags['unkeyed'] = set()
                parsed_tags['unkeyed'].add(tag)
        
        return parsed_tags
    
    def validate_required_tags(self, parsed_tags: Dict[str, Set[str]]) -> Dict[str, Any]:
        """Validate that all required tags are present."""
        validation_result = {
            'valid': True,
            'missing_tags': [],
            'invalid_values': {},
            'warnings': []
        }
        
        # Check required tags
        for required_tag in self.required_tags:
            if required_tag not in parsed_tags:
                validation_result['missing_tags'].append(required_tag)
                validation_result['valid'] = False
            elif not parsed_tags[required_tag]:
                validation_result['missing_tags'].append(f"{required_tag} (empty)")
                validation_result['valid'] = False
        
        # Check expected values
        for tag_key, expected_values in self.expected_values.items():
            if tag_key in parsed_tags:
                actual_values = parsed_tags[tag_key]
                invalid_values = actual_values - set(expected_values)
                if invalid_values:
                    validation_result['invalid_values'][tag_key] = list(invalid_values)
                    validation_result['valid'] = False
        
        # Check for deprecated or inconsistent tags
        if 'environment' in parsed_tags:
            validation_result['warnings'].append("Deprecated tag 'environment' found, use 'env' instead")
        
        if 'service_name' in parsed_tags:
            validation_result['warnings'].append("Deprecated tag 'service_name' found, use 'service' instead")
        
        return validation_result
    
    def check_tracing_coverage(self) -> Dict[str, Any]:
        """Check tracing coverage and tag consistency."""
        if not self.datadog_enabled:
            return {}
        
        try:
            from datetime import datetime, timedelta
            
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(minutes=15)
            
            # Check for traces without proper tags
            tracing_queries = {
                'missing_trace_id': f"sum:trace.django.request.hits{{service:{self.service},env:{self.env},!trace_id:*}}",
                'missing_parent_id': f"sum:trace.django.request.hits{{service:{self.service},env:{self.env},!parent_id:*}}",
                'missing_version': f"sum:trace.django.request.hits{{service:{self.service},env:{self.env},!version:*}}",
                'missing_team': f"sum:trace.django.request.hits{{service:{self.service},env:{self.env},!team:*}}",
                'missing_owner': f"sum:trace.django.request.hits{{service:{self.service},env:{self.env},!owner:*}}"
            }
            
            coverage_results = {}
            
            for query_name, query in tracing_queries.items():
                try:
                    result = api.Metric.query(
                        start=start_time,
                        end=end_time,
                        query=query
                    )
                    
                    if result['series']:
                        total_missing = sum(point[1] for series in result['series'] for point in series['pointlist'])
                        coverage_results[query_name] = total_missing
                    else:
                        coverage_results[query_name] = 0
                
                except Exception as e:
                    logger.error(f"Failed to query {query_name}: {e}")
                    coverage_results[query_name] = -1
            
            return coverage_results
            
        except Exception as e:
            logger.error(f"Failed to check tracing coverage: {e}")
            return {}
    
    def generate_compliance_report(self) -> Dict[str, Any]:
        """Generate comprehensive tagging compliance report."""
        logger.info("Generating tagging compliance report")
        
        # Get service metrics
        metrics_data = self.get_service_metrics()
        
        # Extract and parse tags
        tags = self.extract_tags_from_metrics(metrics_data)
        parsed_tags = self.parse_tags(tags)
        
        # Validate required tags
        validation_result = self.validate_required_tags(parsed_tags)
        
        # Check tracing coverage
        tracing_coverage = self.check_tracing_coverage()
        
        # Generate report
        report = {
            'service': self.service,
            'env': self.env,
            'timestamp': datetime.utcnow().isoformat(),
            'validation': validation_result,
            'tracing_coverage': tracing_coverage,
            'tag_summary': {
                'total_unique_tags': len(tags),
                'tag_keys': list(parsed_tags.keys()),
                'tags_by_key': {k: list(v) for k, v in parsed_tags.items()}
            },
            'recommendations': []
        }
        
        # Generate recommendations
        if validation_result['missing_tags']:
            report['recommendations'].append(f"Add missing required tags: {', '.join(validation_result['missing_tags'])}")
        
        if validation_result['invalid_values']:
            for tag, values in validation_result['invalid_values'].items():
                report['recommendations'].append(f"Fix invalid values for {tag}: {', '.join(values)}")
        
        if validation_result['warnings']:
            report['recommendations'].extend(validation_result['warnings'])
        
        # Tracing coverage recommendations
        for query_name, count in tracing_coverage.items():
            if count > 0:
                if 'missing_trace_id' in query_name:
                    report['recommendations'].append(f"Fix {count} traces missing trace_id")
                elif 'missing_parent_id' in query_name:
                    report['recommendations'].append(f"Fix {count} traces missing parent_id")
                elif 'missing_version' in query_name:
                    report['recommendations'].append(f"Add version tag to {count} traces")
                elif 'missing_team' in query_name:
                    report['recommendations'].append(f"Add team tag to {count} traces")
                elif 'missing_owner' in query_name:
                    report['recommendations'].append(f"Add owner tag to {count} traces")
        
        # Overall compliance score
        total_checks = len(self.required_tags) + len(tracing_coverage)
        passed_checks = (len(self.required_tags) - len(validation_result['missing_tags'])) + sum(1 for count in tracing_coverage.values() if count == 0)
        compliance_score = (passed_checks / total_checks) * 100 if total_checks > 0 else 0
        
        report['compliance_score'] = compliance_score
        report['compliance_grade'] = self._get_compliance_grade(compliance_score)
        
        return report
    
    def _get_compliance_grade(self, score: float) -> str:
        """Get compliance grade based on score."""
        if score >= 95:
            return 'A'
        elif score >= 85:
            return 'B'
        elif score >= 70:
            return 'C'
        elif score >= 50:
            return 'D'
        else:
            return 'F'
    
    def send_compliance_event(self, report: Dict[str, Any]) -> bool:
        """Send compliance report event to Datadog."""
        if not self.datadog_enabled:
            return False
        
        try:
            # Determine event type
            if report['validation']['valid'] and report['compliance_score'] >= 90:
                alert_type = 'success'
                event_title = f"Tagging Compliance: {report['compliance_grade']} - {self.service}"
            elif report['compliance_score'] >= 70:
                alert_type = 'warning'
                event_title = f"Tagging Compliance: {report['compliance_grade']} - {self.service}"
            else:
                alert_type = 'error'
                event_title = f"Tagging Compliance: {report['compliance_grade']} - {self.service} - ACTION REQUIRED"
            
            # Prepare event text
            event_text = f"""
Service: {self.service}
Environment: {self.env}
Compliance Score: {report['compliance_score']:.1f}%
Compliance Grade: {report['compliance_grade']}
Timestamp: {report['timestamp']}

Validation Status: {'PASS' if report['validation']['valid'] else 'FAIL'}
Missing Tags: {', '.join(report['validation']['missing_tags']) if report['validation']['missing_tags'] else 'None'}
Invalid Values: {json.dumps(report['validation']['invalid_values']) if report['validation']['invalid_values'] else 'None'}

Tracing Coverage Issues:
{chr(10).join([f"- {k}: {v}" for k, v in report['tracing_coverage'].items() if v > 0]) if any(v > 0 for v in report['tracing_coverage'].values()) else 'No issues detected'}

Recommendations:
{chr(10).join([f"- {rec}" for rec in report['recommendations']]) if report['recommendations'] else 'No recommendations'}

Tag Summary:
- Total Unique Tags: {report['tag_summary']['total_unique_tags']}
- Tag Keys: {', '.join(report['tag_summary']['tag_keys'])}

Compliance Dashboard: https://app.datadoghq.com/apm/services/{self.service}?env={self.env}
            """.strip()
            
            # Create event tags
            tags = [
                f"service:{self.service}",
                f"env:{self.env}",
                "source:compliance",
                "monitor_type:tagging",
                f"compliance_grade:{report['compliance_grade']}",
                f"compliance_score:{int(report['compliance_score'])}"
            ]
            
            # Send event
            api.Event.create(
                title=event_title,
                text=event_text,
                tags=tags,
                alert_type=alert_type
            )
            
            logger.info(f"Compliance event sent for {self.service}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send compliance event: {e}")
            return False
    
    def fix_tagging_issues(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """Generate fix suggestions for tagging issues."""
        fixes = {
            'code_changes': [],
            'configuration_changes': [],
            'deployment_changes': []
        }
        
        # Code changes
        if 'version' in report['validation']['missing_tags']:
            fixes['code_changes'].append({
                'file': 'settings.py',
                'change': 'Add DD_VERSION environment variable',
                'code': 'os.environ.setdefault("DD_VERSION", get_version())'
            })
        
        if 'team' in report['validation']['missing_tags']:
            fixes['code_changes'].append({
                'file': 'ddtrace configuration',
                'change': 'Add team tag to tracer configuration',
                'code': 'tracer.set_tags({"team": "backend"})'
            })
        
        if 'owner' in report['validation']['missing_tags']:
            fixes['code_changes'].append({
                'file': 'ddtrace configuration',
                'change': 'Add owner tag to tracer configuration',
                'code': 'tracer.set_tags({"owner": "grv-team"})'
            })
        
        # Configuration changes
        fixes['configuration_changes'].append({
            'file': '.env',
            'change': 'Add required environment variables',
            'variables': [
                'DD_SERVICE=grv-api',
                'DD_ENV=prod',
                'DD_VERSION=v1.0.0',
                'DD_TEAM=backend',
                'DD_OWNER=grv-team'
            ]
        })
        
        # Deployment changes
        fixes['deployment_changes'].append({
            'file': 'deployment script',
            'change': 'Add version tagging to deployment',
            'code': 'export DD_VERSION=$BUILD_VERSION'
        })
        
        return fixes
    
    def run_compliance_check(self, send_event: bool = True) -> Dict[str, Any]:
        """Run complete compliance check."""
        logger.info(f"Running tagging compliance check for {self.service}")
        
        # Generate compliance report
        report = self.generate_compliance_report()
        
        # Send compliance event
        if send_event:
            self.send_compliance_event(report)
        
        # Generate fixes
        report['fixes'] = self.fix_tagging_issues(report)
        
        return report


def main():
    """Main compliance validation function."""
    parser = argparse.ArgumentParser(description='Validate service tagging compliance')
    parser.add_argument('--service', type=str, help='Service name (default: from DD_SERVICE)')
    parser.add_argument('--env', type=str, help='Environment (default: from DD_ENV)')
    parser.add_argument('--no-event', action='store_true', help='Do not send compliance event')
    parser.add_argument('--output', type=str, help='Output report to file')
    
    args = parser.parse_args()
    
    # Initialize validator
    validator = ServiceTaggingValidator()
    
    # Override with command line arguments
    if args.service:
        validator.service = args.service
    if args.env:
        validator.env = args.env
    
    # Run compliance check
    report = validator.run_compliance_check(send_event=not args.no_event)
    
    # Output report
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"Report saved to {args.output}")
    else:
        print(json.dumps(report, indent=2))
    
    # Exit with appropriate code
    if not report['validation']['valid']:
        sys.exit(1)
    elif report['compliance_score'] < 70:
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
