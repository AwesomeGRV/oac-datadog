# Enhanced APM Monitoring Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying the enhanced APM monitoring setup for the grv-api service, including all monitors, tracing configurations, and health checks.

## Prerequisites

- Datadog API and App keys with appropriate permissions
- Python 3.8+ with required dependencies
- Django application with ddtrace integration
- Celery workers (if using background jobs)
- Access to Datadog Agent configuration

## Quick Start

### 1. Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Edit with your Datadog credentials
vim .env
```

Required environment variables:

```bash
# Datadog Configuration
DD_API_KEY=your_datadog_api_key
DD_APP_KEY=your_datadog_app_key
DD_SITE=datadoghq.com

# Service Configuration
DD_SERVICE=grv-api
DD_ENV=prod
DD_VERSION=v1.0.0
DD_TEAM=backend
DD_OWNER=grv-team

# Tracing Configuration
DD_TRACE_ENABLED=true
DD_TRACE_DEBUG=false
DD_TRACE_SAMPLE_RATE=0.1
DD_AGENT_HOST=localhost
DD_TRACE_AGENT_PORT=8126

# Monitoring Thresholds
LATENCY_P95_THRESHOLD=2000
ERROR_RATE_THRESHOLD=5.0
APDEX_THRESHOLD=0.85
AVAILABILITY_THRESHOLD=99.0
```

### 2. Install Dependencies

```bash
# Install Python dependencies
pip install ddtrace datadog django celery psycopg2 redis

# Install enhanced monitoring scripts
pip install -r requirements.txt
```

### 3. Deploy Monitors

```bash
# Deploy all APM monitors
./scripts/deploy-monitors.sh

# Deploy specific monitor categories
./scripts/deploy-monitors.sh --category apm
./scripts/deploy-monitors.sh --category deployment
```

### 4. Configure Application Tracing

#### Django Integration

Add to your Django `settings.py`:

```python
# Import enhanced tracing configuration
from examples.django.enhanced_ddtrace_integration import initialize_grv_tracing

# Initialize tracing
DATADOG_CONFIG = initialize_grv_tracing()

# Enhanced logging with trace correlation
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            'format': '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s", "trace_id": "%(dd.trace_id)s", "span_id": "%(dd.span_id)s"}',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
            'filters': ['trace_context'],
        },
    },
    'filters': {
        'trace_context': {
            '()': 'ddtrace.logging.TraceContextFilter',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

#### Celery Integration

Add to your Celery app configuration:

```python
# Import enhanced Celery tracing
from examples.celery.enhanced_celery_tracing import initialize_grv_celery_tracing

# Initialize Celery tracing
CELERY_CONFIG = initialize_grv_celery_tracing()

# Use traced task decorator
from examples.celery.enhanced_celery_tracing import traced_task

@traced_task(name="process_data", queue="default")
def process_data(data):
    # Your task logic here
    pass
```

### 5. Test Setup

```bash
# Run comprehensive health check
python scripts/apm_health_checker.py

# Validate service tagging
python scripts/service_tagging_validator.py

# Test deployment tracking
python scripts/enhanced_deployment_tracker.py --version v1.0.0 --test

# Send test deployment event
python scripts/send-deploy-event.py --version v1.0.0 --auto-git
```

## Monitor Categories

### 1. Core APM Monitors

#### Latency Monitoring
- **comprehensive_latency_monitor.json**: P95/P99 latency by endpoint
- **latency_anomaly_detection.json**: ML-based latency anomaly detection

#### Error Rate Monitoring
- **enhanced_error_rate_monitor.json**: Error rate with exception breakdown
- **critical_exception_spike.json**: Critical exception spike detection

#### Throughput Monitoring
- **detailed_throughput_monitor.json**: Request volume tracking
- **request_rate_anomaly.json**: Request rate anomaly detection

#### User Experience Monitoring
- **enhanced_apdex_monitor.json**: Apdex score with user satisfaction
- **user_frustration_monitor.json**: User frustration rate tracking

#### Availability Monitoring
- **service_availability_sla.json**: Service availability with SLA tracking
- **monthly_sla_compliance.json**: Monthly SLA compliance monitoring

### 2. Django-Specific Monitors

- **django_orm_performance.json**: Django ORM query performance
- **django_view_performance.json**: Django view response times
- **django_middleware_performance.json**: Middleware processing times

### 3. Celery Monitors

- **celery_task_performance.json**: Task execution performance
- **celery_queue_depth.json**: Queue depth monitoring
- **celery_task_failures.json**: Task failure rate tracking

### 4. Deployment Monitors

- **deployment_event_monitor.json**: Deployment event tracking
- **deployment_rollback_detection.json**: Automatic rollback detection
- **deployment_performance_regression.json**: Performance regression detection

### 5. Compliance and Health Monitors

- **service_tagging_compliance.json**: Service tagging validation
- **distributed_tracing_health.json**: Tracing health monitoring
- **trace_sampling_monitor.json**: Trace sampling rate monitoring

## Configuration Customization

### Monitor Thresholds

Create a custom thresholds file:

```json
{
  "latency": {
    "p95_critical": 3000,
    "p95_warning": 2000,
    "p99_critical": 5000,
    "p99_warning": 3000
  },
  "error_rate": {
    "critical": 10.0,
    "warning": 5.0
  },
  "apdex": {
    "critical": 0.70,
    "warning": 0.85
  },
  "availability": {
    "critical": 98.0,
    "warning": 99.0
  }
}
```

Use custom thresholds:

```bash
python scripts/apm_health_checker.py --thresholds custom_thresholds.json
```

### Service Tags

Ensure consistent tagging across all services:

```python
# Standard tags for all traces
SERVICE_TAGS = {
    'service': 'grv-api',
    'env': 'prod',
    'version': 'v1.0.0',
    'team': 'backend',
    'owner': 'grv-team',
    'language': 'python',
    'framework': 'django'
}
```

## Deployment Automation

### CI/CD Integration

Add to your deployment pipeline:

```yaml
# GitHub Actions example
- name: Send Deployment Event
  run: |
    python scripts/enhanced_deployment_tracker.py \
      --version ${{ github.sha }} \
      --deployer ${{ github.actor }} \
      --notes "Automated deployment via CI/CD"

- name: Validate Deployment Health
  run: |
    python scripts/apm_health_checker.py \
      --service grv-api \
      --env prod

- name: Check Service Tagging
  run: |
    python scripts/service_tagging_validator.py \
      --service grv-api \
      --env prod
```

### Rollback Automation

```bash
# Check for rollback conditions
python scripts/enhanced_deployment_tracker.py \
  --version $NEW_VERSION \
  --assess-health \
  --auto-rollback-threshold 20

# Automatic rollback script
if [ $? -eq 1 ]; then
  echo "Deployment health critical - initiating rollback"
  kubectl rollout undo deployment/grv-api
  python scripts/enhanced_deployment_tracker.py \
    --version $PREVIOUS_VERSION \
    --notes "Automatic rollback due to health issues"
fi
```

## Monitoring Dashboards

### APM Overview Dashboard

Create a comprehensive APM dashboard with:

1. **Service Health Overview**
   - Request rate and error rate
   - P95/P99 latency trends
   - Apdex score and user satisfaction
   - Service availability percentage

2. **Performance Metrics**
   - Latency percentiles by endpoint
   - Database query performance
   - External API response times
   - Cache hit/miss ratios

3. **Error Analysis**
   - Error rate by exception type
   - Error distribution by endpoint
   - Recent error traces
   - Error correlation with deployments

4. **User Experience**
   - User frustration rate
   - Session duration trends
   - Geographic performance
   - Device/browser performance

### Deployment Dashboard

Track deployment impact with:

1. **Deployment Timeline**
   - Recent deployment events
   - Version deployment history
   - Rollback events
   - Deployment frequency

2. **Performance Impact**
   - Pre/post deployment metrics
   - Performance regression detection
   - Error rate changes
   - Latency impact analysis

3. **Health Assessment**
   - Deployment health scores
   - Rollback recommendations
   - Risk assessment
   - Recovery time metrics

## Troubleshooting

### Common Issues

#### Missing Traces

```bash
# Check ddtrace configuration
python -c "import ddtrace; print(ddtrace.__version__)"

# Verify agent connectivity
curl -X POST http://localhost:8126/v0.4/traces

# Check trace sampling rate
python scripts/apm_health_checker.py --check tracing
```

#### Monitor Not Triggering

```bash
# Validate monitor query
datadog-cli monitor validate --query "sum:trace.django.request.hits{service:grv-api,env:prod}"

# Check monitor status
datadog-cli monitor list --status alert

# Test monitor manually
python scripts/test-monitors.py --monitor-id 123456
```

#### High Resource Usage

```bash
# Adjust sampling rate
export DD_TRACE_SAMPLE_RATE=0.05

# Enable debug mode
export DD_TRACE_DEBUG=true

# Check agent status
docker exec datadog-agent agent status
```

### Performance Optimization

#### Trace Sampling

```python
# Configure intelligent sampling
tracer.configure(
    sample_rate=0.1,
    priority_sampling=True,
    rules=[
        {
            'service': 'grv-api',
            'sample_rate': 0.1,
            'name': 'default'
        },
        {
            'service': 'grv-api',
            'sample_rate': 1.0,
            'name': 'critical-endpoints',
            'resource': ['api/v1/users', 'api/v1/auth']
        }
    ]
)
```

#### Metric Filtering

```python
# Filter out high-cardinality metrics
tracer.configure(
    statsd_host='localhost',
    statsd_port=8125,
    dogstatsd_tags=['env:prod', 'service:grv-api'],
    hostname=None,  # Don't include hostname in metrics
    exclude_agent_time=True
)
```

## Best Practices

### 1. Service Tagging
- Always include required tags: service, env, version, team, owner
- Use consistent naming conventions
- Tag all custom spans and metrics
- Validate tagging compliance regularly

### 2. Trace Sampling
- Use intelligent sampling for high-traffic services
- Sample critical endpoints at higher rates
- Monitor sampling rate effectiveness
- Adjust based on cost and performance needs

### 3. Monitor Configuration
- Set appropriate thresholds for your service SLAs
- Use multi-level alerting (critical, warning, info)
- Include actionable information in monitor messages
- Regularly review and update monitor queries

### 4. Deployment Monitoring
- Track all deployment events
- Monitor for performance regressions
- Implement automated rollback detection
- Assess deployment health post-deployment

### 5. Health Checking
- Run regular health checks on all components
- Monitor tracing configuration health
- Validate service tagging compliance
- Check monitor coverage and effectiveness

## Support and Maintenance

### Regular Tasks

- **Daily**: Review APM health dashboard
- **Weekly**: Validate service tagging compliance
- **Monthly**: Review and optimize monitor thresholds
- **Quarterly**: Assess monitoring coverage and add gaps

### Contact Support

For issues with the enhanced APM monitoring:

1. Check this documentation
2. Review troubleshooting guides
3. Validate configuration with health checker
4. Create issue in repository with details

### Contributing

To contribute to the monitoring setup:

1. Fork the repository
2. Add new monitors with proper tagging
3. Update documentation
4. Test with health checker
5. Submit pull request with description
