#!/usr/bin/env python3
"""
Cost optimization script for grv-api Datadog observability.
Provides automated cost control and optimization recommendations.
"""

import os
import sys
import json
import time
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class CostCategory(Enum):
    """Cost categories for optimization."""
    LOGS = "logs"
    METRICS = "metrics"
    TRACES = "traces"
    CUSTOM_METRICS = "custom_metrics"
    INFRASTRUCTURE = "infrastructure"


@dataclass
class CostMetric:
    """Cost metric data structure."""
    category: CostCategory
    name: str
    current_cost: float
    projected_monthly_cost: float
    usage_volume: int
    unit_cost: float
    optimization_potential: float
    recommendations: List[str]


@dataclass
class OptimizationAction:
    """Optimization action data structure."""
    name: str
    category: CostCategory
    description: str
    estimated_savings: float
    implementation_effort: str
    risk_level: str
    automated: bool


class CostOptimizer:
    """Advanced cost optimization for Datadog observability."""
    
    def __init__(self):
        self.setup_logging()
        self.load_configuration()
        self.cost_metrics = []
        self.optimization_actions = []
        
    def setup_logging(self):
        """Setup structured logging for cost optimization."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def load_configuration(self):
        """Load cost optimization configuration."""
        config_file = os.path.join(
            os.path.dirname(__file__), 
            '..', 
            'config', 
            'cost-optimization.json'
        )
        
        default_config = {
            "budget_limits": {
                "monthly_total": 10000.0,
                "logs": 3000.0,
                "metrics": 2000.0,
                "traces": 2500.0,
                "custom_metrics": 1500.0,
                "infrastructure": 1000.0
            },
            "optimization_rules": {
                "log_sampling": {
                    "enabled": True,
                    "high_volume_threshold": 1000000,  # logs per day
                    "target_sample_rate": 0.1
                },
                "metric_retention": {
                    "enabled": True,
                    "custom_metrics_retention_days": 15,
                    "infrastructure_metrics_retention_days": 30
                },
                "trace_sampling": {
                    "enabled": True,
                    "high_traffic_threshold": 10000,  # traces per minute
                    "adaptive_sampling": True
                },
                "custom_metrics": {
                    "enabled": True,
                    "max_custom_metrics": 500,
                    "unused_metric_threshold_days": 7
                }
            },
            "alerting": {
                "cost_threshold_percentage": 80.0,
                "daily_cost_report": True,
                "weekly_optimization_report": True
            },
            "automation": {
                "auto_optimize": True,
                "require_approval_for": ["log_sampling", "metric_deletion"],
                "optimization_window": {
                    "start_hour": 2,
                    "end_hour": 4,
                    "timezone": "UTC",
                    "weekends_only": False
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
            self.logger.error(f"Failed to load cost optimization config: {e}")
            self.config = default_config
    
    def get_current_usage_metrics(self) -> Dict[str, Any]:
        """Get current usage metrics from Datadog API."""
        try:
            # In a real implementation, query Datadog usage API
            # This is a simulation of the API response
            
            usage_data = {
                "logs": {
                    "indexed_events": 2500000,
                    "ingested_bytes": 1073741824,  # 1GB
                    "cost_per_gb": 0.50
                },
                "metrics": {
                    "custom_metrics": 350,
                    "infrastructure_metrics": 1500,
                    "cost_per_metric": 0.25
                },
                "traces": {
                    "indexed_spans": 500000,
                    "ingested_bytes": 536870912,  # 512MB
                    "cost_per_gb": 1.00
                },
                "infrastructure": {
                    "hosts": 20,
                    "containers": 100,
                    "cost_per_host": 5.00
                }
            }
            
            return usage_data
            
        except Exception as e:
            self.logger.error(f"Failed to get usage metrics: {e}")
            return {}
    
    def calculate_costs(self, usage_data: Dict[str, Any]) -> List[CostMetric]:
        """Calculate costs for each category."""
        cost_metrics = []
        
        # Logs cost calculation
        if 'logs' in usage_data:
            logs_data = usage_data['logs']
            daily_cost = (logs_data['ingested_bytes'] / (1024**3)) * logs_data['cost_per_gb']
            projected_monthly = daily_cost * 30
            
            cost_metrics.append(CostMetric(
                category=CostCategory.LOGS,
                name="Log Management",
                current_cost=daily_cost,
                projected_monthly_cost=projected_monthly,
                usage_volume=logs_data['indexed_events'],
                unit_cost=logs_data['cost_per_gb'],
                optimization_potential=self.calculate_optimization_potential(CostCategory.LOGS, projected_monthly),
                recommendations=self.get_log_recommendations(logs_data)
            ))
        
        # Metrics cost calculation
        if 'metrics' in usage_data:
            metrics_data = usage_data['metrics']
            total_metrics = metrics_data['custom_metrics'] + metrics_data['infrastructure_metrics']
            daily_cost = total_metrics * metrics_data['cost_per_metric']
            projected_monthly = daily_cost * 30
            
            cost_metrics.append(CostMetric(
                category=CostCategory.METRICS,
                name="Metrics Collection",
                current_cost=daily_cost,
                projected_monthly_cost=projected_monthly,
                usage_volume=total_metrics,
                unit_cost=metrics_data['cost_per_metric'],
                optimization_potential=self.calculate_optimization_potential(CostCategory.METRICS, projected_monthly),
                recommendations=self.get_metrics_recommendations(metrics_data)
            ))
        
        # Traces cost calculation
        if 'traces' in usage_data:
            traces_data = usage_data['traces']
            daily_cost = (traces_data['ingested_bytes'] / (1024**3)) * traces_data['cost_per_gb']
            projected_monthly = daily_cost * 30
            
            cost_metrics.append(CostMetric(
                category=CostCategory.TRACES,
                name="APM Tracing",
                current_cost=daily_cost,
                projected_monthly_cost=projected_monthly,
                usage_volume=traces_data['indexed_spans'],
                unit_cost=traces_data['cost_per_gb'],
                optimization_potential=self.calculate_optimization_potential(CostCategory.TRACES, projected_monthly),
                recommendations=self.get_trace_recommendations(traces_data)
            ))
        
        # Infrastructure cost calculation
        if 'infrastructure' in usage_data:
            infra_data = usage_data['infrastructure']
            total_infra_units = infra_data['hosts'] + (infra_data['containers'] / 10)  # 10 containers = 1 host equivalent
            daily_cost = total_infra_units * infra_data['cost_per_host']
            projected_monthly = daily_cost * 30
            
            cost_metrics.append(CostMetric(
                category=CostCategory.INFRASTRUCTURE,
                name="Infrastructure Monitoring",
                current_cost=daily_cost,
                projected_monthly_cost=projected_monthly,
                usage_volume=int(total_infra_units),
                unit_cost=infra_data['cost_per_host'],
                optimization_potential=self.calculate_optimization_potential(CostCategory.INFRASTRUCTURE, projected_monthly),
                recommendations=self.get_infrastructure_recommendations(infra_data)
            ))
        
        return cost_metrics
    
    def calculate_optimization_potential(self, category: CostCategory, current_cost: float) -> float:
        """Calculate optimization potential for a category."""
        budget_limit = self.config.get('budget_limits', {}).get(category.value, 1000.0)
        
        if current_cost > budget_limit:
            return min(current_cost * 0.3, current_cost - budget_limit)  # Up to 30% reduction
        else:
            return current_cost * 0.1  # 10% optimization target for under-budget categories
    
    def get_log_recommendations(self, logs_data: Dict[str, Any]) -> List[str]:
        """Get log optimization recommendations."""
        recommendations = []
        
        if logs_data['indexed_events'] > 1000000:  # > 1M logs/day
            recommendations.append("Implement log sampling to reduce volume by 80%")
            recommendations.append("Filter out DEBUG and TRACE level logs")
            recommendations.append("Exclude health check logs from collection")
        
        if logs_data['ingested_bytes'] > 2147483648:  # > 2GB/day
            recommendations.append("Enable log compression")
            recommendations.append("Reduce log verbosity in production")
            recommendations.append("Implement log aggregation at source")
        
        return recommendations
    
    def get_metrics_recommendations(self, metrics_data: Dict[str, Any]) -> List[str]:
        """Get metrics optimization recommendations."""
        recommendations = []
        
        if metrics_data['custom_metrics'] > 500:
            recommendations.append("Review and remove unused custom metrics")
            recommendations.append("Consolidate similar metrics using tags")
            recommendations.append("Implement metric rollups for high-cardinality data")
        
        if metrics_data['infrastructure_metrics'] > 2000:
            recommendations.append("Reduce infrastructure metric collection frequency")
            recommendations.append("Disable unnecessary system metrics")
            recommendations.append("Use metric filtering to exclude noise")
        
        return recommendations
    
    def get_trace_recommendations(self, traces_data: Dict[str, Any]) -> List[str]:
        """Get trace optimization recommendations."""
        recommendations = []
        
        if traces_data['indexed_spans'] > 1000000:  # > 1M spans/day
            recommendations.append("Implement adaptive trace sampling")
            recommendations.append("Reduce trace sampling rate for high-traffic endpoints")
            recommendations.append("Exclude health check and monitoring endpoints from tracing")
        
        if traces_data['ingested_bytes'] > 1073741824:  # > 1GB/day
            recommendations.append("Reduce span size by limiting metadata")
            recommendations.append("Implement trace filtering")
            recommendations.append("Use span sampling for resource-intensive operations")
        
        return recommendations
    
    def get_infrastructure_recommendations(self, infra_data: Dict[str, Any]) -> List[str]:
        """Get infrastructure monitoring recommendations."""
        recommendations = []
        
        if infra_data['hosts'] > 50:
            recommendations.append("Review host monitoring necessity")
            recommendations.append("Consolidate monitoring for similar hosts")
            recommendations.append("Use container-level monitoring where possible")
        
        if infra_data['containers'] > 200:
            recommendations.append("Implement container grouping")
            recommendations.append("Reduce container monitoring frequency")
            recommendations.append("Use service-level monitoring instead of container-level")
        
        return recommendations
    
    def generate_optimization_actions(self) -> List[OptimizationAction]:
        """Generate specific optimization actions."""
        actions = []
        
        # Log optimization actions
        actions.append(OptimizationAction(
            name="Implement Log Sampling",
            category=CostCategory.LOGS,
            description="Reduce log volume by implementing intelligent sampling",
            estimated_savings=150.0,
            implementation_effort="Low",
            risk_level="Low",
            automated=True
        ))
        
        actions.append(OptimizationAction(
            name="Filter Debug Logs",
            category=CostCategory.LOGS,
            description="Exclude DEBUG and TRACE level logs from production",
            estimated_savings=100.0,
            implementation_effort="Low",
            risk_level="Low",
            automated=True
        ))
        
        # Metrics optimization actions
        actions.append(OptimizationAction(
            name="Remove Unused Custom Metrics",
            category=CostCategory.METRICS,
            description="Identify and remove custom metrics with no recent activity",
            estimated_savings=200.0,
            implementation_effort="Medium",
            risk_level="Medium",
            automated=False
        ))
        
        actions.append(OptimizationAction(
            name="Reduce Metric Collection Frequency",
            category=CostCategory.METRICS,
            description="Decrease collection frequency for non-critical metrics",
            estimated_savings=80.0,
            implementation_effort="Low",
            risk_level="Low",
            automated=True
        ))
        
        # Trace optimization actions
        actions.append(OptimizationAction(
            name="Implement Adaptive Sampling",
            category=CostCategory.TRACES,
            description="Use intelligent sampling based on endpoint importance",
            estimated_savings=300.0,
            implementation_effort="Medium",
            risk_level="Medium",
            automated=True
        ))
        
        actions.append(OptimizationAction(
            name="Exclude Health Check Tracing",
            category=CostCategory.TRACES,
            description="Remove tracing from health check and monitoring endpoints",
            estimated_savings=50.0,
            implementation_effort="Low",
            risk_level="Low",
            automated=True
        ))
        
        # Infrastructure optimization actions
        actions.append(OptimizationAction(
            name="Optimize Container Monitoring",
            category=CostCategory.INFRASTRUCTURE,
            description="Consolidate container monitoring and reduce frequency",
            estimated_savings=120.0,
            implementation_effort="Medium",
            risk_level="Low",
            automated=True
        ))
        
        return actions
    
    def execute_optimization_action(self, action: OptimizationAction) -> bool:
        """Execute an optimization action."""
        if not action.automated:
            self.logger.info(f"Manual action required: {action.name}")
            return False
        
        try:
            if action.category == CostCategory.LOGS:
                return self.execute_log_optimization(action)
            elif action.category == CostCategory.METRICS:
                return self.execute_metrics_optimization(action)
            elif action.category == CostCategory.TRACES:
                return self.execute_trace_optimization(action)
            elif action.category == CostCategory.INFRASTRUCTURE:
                return self.execute_infrastructure_optimization(action)
            
        except Exception as e:
            self.logger.error(f"Failed to execute optimization action {action.name}: {e}")
            return False
        
        return False
    
    def execute_log_optimization(self, action: OptimizationAction) -> bool:
        """Execute log optimization action."""
        if "sampling" in action.name.lower():
            # Implement log sampling
            config = {
                "logs": [
                    {
                        "type": "file",
                        "path": "/var/log/app.log",
                        "sample_rate": 0.1
                    }
                ]
            }
            
            # Update Datadog agent configuration
            self.logger.info("Implementing log sampling with 10% rate")
            # In real implementation, update agent config files
            
        elif "filter" in action.name.lower():
            # Implement log filtering
            self.logger.info("Implementing log filtering to exclude DEBUG logs")
            # In real implementation, update log configuration
        
        return True
    
    def execute_metrics_optimization(self, action: OptimizationAction) -> bool:
        """Execute metrics optimization action."""
        if "unused" in action.name.lower():
            # Remove unused custom metrics
            self.logger.info("Identifying and removing unused custom metrics")
            # In real implementation, query Datadog API and delete unused metrics
            
        elif "frequency" in action.name.lower():
            # Reduce collection frequency
            self.logger.info("Reducing metric collection frequency")
            # In real implementation, update agent configuration
        
        return True
    
    def execute_trace_optimization(self, action: OptimizationAction) -> bool:
        """Execute trace optimization action."""
        if "sampling" in action.name.lower():
            # Implement adaptive sampling
            self.logger.info("Implementing adaptive trace sampling")
            # In real implementation, update tracing configuration
            
        elif "exclude" in action.name.lower():
            # Exclude health check tracing
            self.logger.info("Excluding health check endpoints from tracing")
            # In real implementation, update tracing configuration
        
        return True
    
    def execute_infrastructure_optimization(self, action: OptimizationAction) -> bool:
        """Execute infrastructure optimization action."""
        if "container" in action.name.lower():
            # Optimize container monitoring
            self.logger.info("Optimizing container monitoring configuration")
            # In real implementation, update infrastructure monitoring config
        
        return True
    
    def generate_cost_report(self) -> Dict[str, Any]:
        """Generate comprehensive cost optimization report."""
        usage_data = self.get_current_usage_metrics()
        cost_metrics = self.calculate_costs(usage_data)
        optimization_actions = self.generate_optimization_actions()
        
        total_current_cost = sum(m.current_cost for m in cost_metrics)
        total_projected_cost = sum(m.projected_monthly_cost for m in cost_metrics)
        total_optimization_potential = sum(m.optimization_potential for m in cost_metrics)
        total_action_savings = sum(a.estimated_savings for a in optimization_actions)
        
        budget_limits = self.config.get('budget_limits', {})
        total_budget = budget_limits.get('monthly_total', 10000.0)
        
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "current_daily_cost": total_current_cost,
                "projected_monthly_cost": total_projected_cost,
                "total_budget": total_budget,
                "budget_utilization": (total_projected_cost / total_budget) * 100,
                "optimization_potential": total_optimization_potential,
                "action_savings": total_action_savings,
                "final_projected_cost": total_projected_cost - total_action_savings
            },
            "cost_breakdown": [
                {
                    "category": m.category.value,
                    "name": m.name,
                    "current_cost": m.current_cost,
                    "projected_monthly_cost": m.projected_monthly_cost,
                    "usage_volume": m.usage_volume,
                    "optimization_potential": m.optimization_potential,
                    "recommendations": m.recommendations
                }
                for m in cost_metrics
            ],
            "optimization_actions": [
                {
                    "name": a.name,
                    "category": a.category.value,
                    "description": a.description,
                    "estimated_savings": a.estimated_savings,
                    "implementation_effort": a.implementation_effort,
                    "risk_level": a.risk_level,
                    "automated": a.automated
                }
                for a in optimization_actions
            ],
            "budget_status": {
                "within_budget": total_projected_cost <= total_budget,
                "over_budget_amount": max(0, total_projected_cost - total_budget),
                "savings_needed": max(0, total_projected_cost - total_budget)
            }
        }
        
        return report
    
    def send_cost_alert(self, report: Dict[str, Any]) -> bool:
        """Send cost alert if thresholds exceeded."""
        budget_utilization = report['summary']['budget_utilization']
        threshold = self.config.get('alerting', {}).get('cost_threshold_percentage', 80.0)
        
        if budget_utilization > threshold:
            try:
                # Send alert to configured channels
                webhook_url = os.getenv("COST_ALERT_WEBHOOK_URL")
                
                if webhook_url:
                    payload = {
                        "alert_type": "cost_warning",
                        "budget_utilization": budget_utilization,
                        "projected_cost": report['summary']['projected_monthly_cost'],
                        "budget": report['summary']['total_budget'],
                        "optimization_potential": report['summary']['optimization_potential']
                    }
                    
                    response = requests.post(webhook_url, json=payload, timeout=10)
                    if response.status_code == 200:
                        self.logger.info("Cost alert sent successfully")
                        return True
                    else:
                        self.logger.error(f"Failed to send cost alert: {response.text}")
                
            except Exception as e:
                self.logger.error(f"Error sending cost alert: {e}")
        
        return False
    
    def run_optimization_cycle(self) -> Dict[str, Any]:
        """Run a complete optimization cycle."""
        self.logger.info("Starting cost optimization cycle")
        
        # Generate cost report
        report = self.generate_cost_report()
        
        # Send alerts if needed
        self.send_cost_alert(report)
        
        # Execute automated optimizations
        if self.config.get('automation', {}).get('auto_optimize', True):
            optimization_actions = self.generate_optimization_actions()
            
            for action in optimization_actions:
                if action.automated and action.risk_level == "Low":
                    if self.execute_optimization_action(action):
                        self.logger.info(f"Executed optimization: {action.name}")
                        time.sleep(1)  # Rate limiting
        
        self.logger.info(f"Cost optimization cycle completed. Potential savings: ${report['summary']['action_savings']:.2f}/month")
        
        return report


def main():
    """Main function to run cost optimization."""
    from dotenv import load_dotenv
    load_dotenv()
    
    optimizer = CostOptimizer()
    
    try:
        while True:
            report = optimizer.run_optimization_cycle()
            
            # Save report to file
            report_file = f"cost_optimization_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
            
            print(f"\nCost optimization report saved to: {report_file}")
            print(f"Projected monthly cost: ${report['summary']['projected_monthly_cost']:.2f}")
            print(f"Optimization potential: ${report['summary']['optimization_potential']:.2f}")
            print(f"Action savings: ${report['summary']['action_savings']:.2f}")
            
            # Run daily
            time.sleep(86400)  # 24 hours
            
    except KeyboardInterrupt:
        print("\nCost optimization stopped")


if __name__ == "__main__":
    main()
