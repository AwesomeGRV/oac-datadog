# Deployment Guide for grv-api Datadog Observability

This guide provides step-by-step instructions for deploying the complete Datadog observability setup for the grv-api service.

## Prerequisites

### Infrastructure Requirements
- Docker and Docker Compose installed
- PostgreSQL database (version 12+)
- Redis server (version 6+)
- Nginx reverse proxy
- Sufficient disk space for logs (recommend 50GB+)

### Datadog Account
- Datadog API key
- Datadog Application key
- Appropriate permissions in your Datadog organization

### Application Requirements
- Django application (version 4.2+)
- Celery for background tasks
- Python 3.9+

## Quick Start

### 1. Environment Setup

```bash
# Clone the repository
git clone <repository-url>
cd oac-datadog

# Copy environment template
cp .env.example .env

# Edit environment variables
vim .env
```

### 2. Configure Datadog Credentials

Edit `.env` file with your Datadog credentials:

```bash
# Required
DD_API_KEY=your_datadog_api_key
DD_APP_KEY=your_datadog_app_key
DD_SITE=datadoghq.com

# Service configuration
DD_SERVICE=grv-api
DD_ENV=prod
DD_VERSION=v1.0.0
```

### 3. Deploy with Docker Compose

```bash
# Build and start all services
docker-compose -f docker/docker-compose.yml up -d

# Check service status
docker-compose -f docker/docker-compose.yml ps

# View logs
docker-compose -f docker/docker-compose.yml logs -f datadog-agent
```

### 4. Deploy Monitors

```bash
# Make deploy script executable
chmod +x scripts/deploy-monitors.sh

# Deploy all monitors
./scripts/deploy-monitors.sh
```

### 5. Test the Setup

```bash
# Run observability tests
python scripts/test-observability.py

# Send test deployment event
python scripts/send-deploy-event.py \
    --api-key $DD_API_KEY \
    --app-key $DD_APP_KEY \
    --version v1.0.0 \
    --auto-git
```

## Detailed Deployment

### Step 1: Application Integration

#### Django Settings

Copy the example Django settings to your project:

```bash
cp examples/django/settings.py.example your_project/settings.py
```

Key configurations in `settings.py`:

```python
# Datadog tracing
DATADOG_TRACE = {
    'enabled': True,
    'service': os.getenv('DD_SERVICE', 'grv-api'),
    'env': os.getenv('DD_ENV', 'prod'),
    'version': os.getenv('DD_VERSION', 'v1.0.0'),
    'agent_host': os.getenv('DD_AGENT_HOST', 'localhost'),
    'agent_port': int(os.getenv('DD_TRACE_AGENT_PORT', '8126')),
    'trace_sample_rate': float(os.getenv('DD_TRACE_SAMPLE_RATE', '1.0')),
    'log_injection': True,
}

# Middleware for enhanced tracing
MIDDLEWARE = [
    'ddtrace.contrib.django.TraceMiddleware',
    'grv.core.middleware.RequestIDMiddleware',
    'grv.core.middleware.LoggingMiddleware',
    # ... other middleware
]
```

#### Celery Configuration

Copy the Celery configuration:

```bash
cp examples/celery/celery_app.py.example your_project/celery_app.py
```

#### Logging Configuration

Set up JSON logging:

```python
from examples.logging.json_formatter import setup_logging

# Configure structured logging
setup_logging(
    service='grv-api',
    env='prod',
    version='v1.0.0',
    log_level='INFO',
    log_file='/app/logs/grv-api.log'
)
```

### Step 2: Nginx Configuration

Configure Nginx for JSON logging and trace propagation:

```bash
# Copy Nginx configuration
cp docker/nginx/nginx.conf /etc/nginx/nginx.conf

# Test configuration
nginx -t

# Reload Nginx
systemctl reload nginx
```

### Step 3: Datadog Agent Deployment

#### Docker Deployment (Recommended)

```bash
# Build custom agent image
cd docker/datadog-agent
docker build -t grv-datadog-agent .

# Run with Docker Compose
docker-compose -f docker/docker-compose.yml up -d datadog-agent
```

#### Kubernetes Deployment

```bash
# Apply Kubernetes manifests
kubectl apply -f kubernetes/datadog-agent/

# Verify deployment
kubectl get pods -n datadog
kubectl logs -n datadog -l app=datadog-agent
```

### Step 4: Monitor Deployment

#### Automated Deployment

```bash
# Deploy all monitors
./scripts/deploy-monitors.sh

# Verify monitors in Datadog UI
# https://app.datadoghq.com/monitors
```

#### Manual Monitor Creation

Individual monitors can be deployed manually:

```bash
# Deploy specific monitor
curl -X POST "https://api.datadoghq.com/api/v1/monitor" \
    -H "Content-Type: application/json" \
    -H "DD-API-KEY: $DD_API_KEY" \
    -H "DD-APPLICATION-KEY: $DD_APP_KEY" \
    -d @datadog/monitors/apm/latency_monitor.json
```

### Step 5: Deployment Events

#### Integration with CI/CD

Add to your deployment pipeline:

```bash
# Send deployment event
python scripts/send-deploy-event.py \
    --api-key $DD_API_KEY \
    --app-key $DD_APP_KEY \
    --version $BUILD_VERSION \
    --git-commit $GIT_COMMIT \
    --build-number $BUILD_NUMBER \
    --deployer $DEPLOYER \
    --auto-git
```

#### GitHub Actions Example

```yaml
- name: Send Deployment Event
  run: |
    python scripts/send-deploy-event.py \
      --api-key ${{ secrets.DD_API_KEY }} \
      --app-key ${{ secrets.DD_APP_KEY }} \
      --version ${{ github.sha }} \
      --git-commit ${{ github.sha }} \
      --build-number ${{ github.run_number }} \
      --deployer ${{ github.actor }} \
      --auto-git
```

## Configuration Reference

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DD_API_KEY` | Yes | - | Datadog API key |
| `DD_APP_KEY` | Yes | - | Datadog application key |
| `DD_SERVICE` | No | grv-api | Service name |
| `DD_ENV` | No | prod | Environment |
| `DD_VERSION` | No | v1.0.0 | Application version |
| `DD_AGENT_HOST` | No | localhost | Datadog agent host |
| `DD_TRACE_AGENT_PORT` | No | 8126 | Trace agent port |

### Monitoring Thresholds

| Threshold | Default | Description |
|----------|---------|-------------|
| `ERROR_RATE_THRESHOLD` | 5.0 | Error rate percentage |
| `LATENCY_P95_THRESHOLD` | 2000 | P95 latency in ms |
| `CPU_THRESHOLD` | 80.0 | CPU usage percentage |
| `MEMORY_THRESHOLD` | 85.0 | Memory usage percentage |
| `CELERY_QUEUE_BACKLOG_THRESHOLD` | 100 | Queue backlog count |

## Verification

### Health Checks

```bash
# Check Datadog agent status
docker exec datadog-agent agent status

# Check Nginx status
curl http://localhost:8080/nginx_status

# Test application tracing
curl -H "X-Datadog-Trace-ID: 12345" http://localhost:8000/api/health
```

### Log Verification

```bash
# View application logs
docker logs grv-api

# View Nginx logs
docker logs nginx

# Check Datadog log processing
docker logs datadog-agent | grep "log_processing"
```

### Metric Verification

```bash
# Send test metrics
python scripts/test-observability.py

# Check metrics in Datadog
# https://app.datadoghq.com/metrics/explorer
```

## Troubleshooting

### Common Issues

#### Agent Not Receiving Traces

```bash
# Check agent connectivity
docker exec datadog-agent agent status

# Verify network access
telnet localhost 8126

# Check agent logs
docker logs datadog-agent | grep "trace"
```

#### Missing Logs

```bash
# Check log collection configuration
docker exec datadog-agent agent config

# Verify log file paths
docker exec datadog-agent ls -la /var/log/

# Check log processing
docker logs datadog-agent | grep "log"
```

#### Monitor Alerts Not Firing

```bash
# Test monitor query
curl -X GET "https://api.datadoghq.com/api/v1/query" \
    -H "DD-API-KEY: $DD_API_KEY" \
    -H "DD-APPLICATION-KEY: $DD_APP_KEY" \
    -d "query=avg:trace.flask.request.duration{service:grv-api}"

# Check monitor status
curl -X GET "https://api.datadoghq.com/api/v1/monitor" \
    -H "DD-API-KEY: $DD_API_KEY" \
    -H "DD-APPLICATION-KEY: $DD_APP_KEY"
```

### Performance Tuning

#### Sampling Configuration

```python
# Adjust trace sampling rate
DATADOG_TRACE = {
    'trace_sample_rate': 0.1,  # Sample 10% of traces
}
```

#### Log Filtering

```yaml
# Filter logs in agent configuration
logs:
  - type: file
    path: /var/log/app.log
    include_patterns:
      - "ERROR"
      - "WARNING"
    exclude_patterns:
      - "DEBUG"
```

## Security Considerations

### API Key Management

- Store API keys in secure environment variables
- Use different keys for different environments
- Rotate keys regularly
- Monitor key usage

### Network Security

- Restrict access to Datadog agent ports
- Use TLS for all communications
- Implement firewall rules
- Monitor network traffic

### Data Privacy

- Configure sensitive data masking
- Implement log retention policies
- Review data collection practices
- Ensure compliance with regulations

## Maintenance

### Regular Tasks

- Update Datadog agent regularly
- Review and adjust monitor thresholds
- Clean up old monitors and dashboards
- Monitor agent resource usage

### Backup and Recovery

- Export monitor configurations
- Document custom integrations
- Test disaster recovery procedures
- Maintain configuration in version control

## Support

### Documentation

- [Datadog APM Documentation](https://docs.datadoghq.com/tracing/)
- [Log Management Guide](https://docs.datadoghq.com/logs/)
- [Infrastructure Monitoring](https://docs.datadoghq.com/infrastructure/)

### Contact

- Internal observability team
- Datadog support (if applicable)
- Create issues in this repository

### Escalation

For critical issues:
1. Check the troubleshooting guide
2. Review system logs
3. Contact the on-call engineer
4. Escalate to management if needed
