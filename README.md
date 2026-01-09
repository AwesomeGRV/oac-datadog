# Production Datadog Observability Setup - grv-api

Complete production-level observability-as-code implementation for Datadog monitoring of `grv-api` service.

## Implementation Overview

### APM & Tracing
- **ddtrace for Django & Celery**: Request/DB/Redis traces, task spans
- **Service tagging**: `service=grv-api`, `env=prod|stg|dev`, `version=vX.Y.Z|sha`
- **Deploy annotations**: Automatic deploy events on each release
- **Key monitors**: P95 latency, error rate, request volume, Celery task failures/backlog

### Logs Management
- **Agent log collection**: Docker log tailing with proper parsing
- **JSON logging**: Structured logs in Django/Celery/Nginx with trace_id correlation
- **Log pipelines**: Parse levels, routing, and sensitive data masking
- **Key monitors**: ERROR spikes, exception fingerprints, Nginx 5xx surges

### Infrastructure & Integrations
- **Docker/Container monitoring**: OOM kills, restarts, CPU throttling
- **PostgreSQL integration**: Connections, locks, slow queries, replication
- **Redis integration**: Memory usage, evictions, hit/miss ratios, blocked clients
- **Nginx integration**: Requests, 4xx/5xx rates, upstream response times

## Project Structure

```
├── datadog/
│   ├── agent/                  # Datadog Agent configurations
│   │   ├── conf.d/            # Integration configs
│   │   └── checks.d/          # Custom checks
│   ├── monitors/               # Monitor definitions
│   │   ├── apm/               # APM monitors
│   │   ├── logs/              # Log monitors
│   │   └── infrastructure/    # Infrastructure monitors
│   ├── dashboards/             # Dashboard configurations
│   └── pipelines/              # Log processing pipelines
├── docker/                     # Docker configurations
│   ├── datadog-agent/         # Agent Docker setup
│   └── nginx/                 # Nginx logging config
├── examples/                   # Example implementations
│   ├── django/                # Django integration examples
│   ├── celery/                # Celery integration examples
│   └── logging/               # Logging configuration examples
├── scripts/                    # Deployment and utility scripts
├── kubernetes/                 # K8s manifests (if applicable)
└── docs/                       # Documentation
```

## Quick Start

### 1. Environment Setup
```bash
# Copy environment template
cp .env.example .env

# Edit with your Datadog credentials and service config
vim .env
```

### 2. Deploy Datadog Agent
```bash
# Using Docker Compose
docker-compose -f docker/docker-compose.yml up -d datadog-agent

# Or using Kubernetes
kubectl apply -f kubernetes/datadog-agent/
```

### 3. Configure Application Tracing
```bash
# Install dependencies
pip install -r requirements.txt

# Apply Django configuration
cp examples/django/settings.py.example your_project/settings.py

# Configure Celery
cp examples/celery/celery_app.py.example your_project/celery_app.py
```

### 4. Deploy Monitors and Dashboards
```bash
# Deploy all monitors
./scripts/deploy-monitors.sh

# Deploy dashboards
./scripts/deploy-dashboards.sh
```

### 5. Verify Setup
```bash
# Test tracing
python scripts/test-tracing.py

# Test logging
python scripts/test-logging.py

# Check agent status
docker exec datadog-agent agent status
```

## Configuration

### Environment Variables
```bash
# Datadog Configuration
DD_API_KEY=your_datadog_api_key
DD_APP_KEY=your_datadog_app_key
DD_SITE=datadoghq.com

# Service Configuration
DD_SERVICE=grv-api
DD_ENV=prod
DD_VERSION=v1.0.0

# Infrastructure
DD_POSTGRES_HOST=localhost
DD_REDIS_HOST=localhost
DD_NGINX_STATUS_URL=http://localhost:8080/nginx_status
```

### Service Tags
All telemetry automatically tagged with:
- `service: grv-api`
- `env: prod|stg|dev`
- `version: vX.Y.Z|git-sha`
- `team: backend`
- `owner: grv-team`

## Monitoring Coverage

### Application Performance Metrics
- **Request Latency**: P50, P90, P95, P99 by endpoint
- **Error Rates**: HTTP errors, exceptions, database errors
- **Request Volume**: RPS, concurrent requests, queue depth
- **Database Performance**: Query times, connection pools, slow queries
- **Celery Tasks**: Execution time, failure rates, queue backlog

### Infrastructure Health
- **Container Metrics**: CPU, memory, OOM kills, restarts
- **Database Health**: Connections, locks, replication lag
- **Redis Performance**: Memory usage, evictions, hit ratios
- **Web Server Metrics**: Request rates, response codes, upstream times

### Business Intelligence
- **User Activity**: Active users, session duration, feature usage
- **System Reliability**: Uptime, SLA compliance, error budgets
- **Performance Trends**: Latency trends, capacity planning

## Security & Compliance

- **Data Masking**: Automatic PII detection and redaction
- **Secure Credentials**: API keys in environment variables
- **Network Security**: TLS encryption, firewall rules
- **Audit Logging**: All configuration changes tracked
- **Data Retention**: Configurable retention policies

## Alerting Strategy

### Critical Alerts (5-minute SLA)
- Service downtime (>99.9% availability)
- Error rate > 5%
- P95 latency > 2s
- Database connection failures

### Warning Alerts (15-minute SLA)
- High memory usage (>85%)
- CPU throttling detected
- Redis memory pressure
- Nginx 5xx rate increase

### Info Alerts (1-hour SLA)
- Deploy events
- Configuration changes
- Performance trends

## Troubleshooting

### Common Issues
1. **Missing traces**: Check ddtrace configuration and service tagging
2. **Log parsing errors**: Validate JSON format and pipeline configuration
3. **Agent connectivity**: Verify API keys and network access
4. **High resource usage**: Adjust sampling rates and collection intervals

### Debug Commands
```bash
# Check agent status
docker exec datadog-agent agent status

# Test trace collection
curl -X POST http://localhost:8126/v0.4/traces

# View log processing
docker logs datadog-agent | grep "log_processing"

# Check monitor status
datadog-cli monitor list --status alert
```

## Additional Resources

- [Datadog APM Documentation](https://docs.datadoghq.com/tracing/)
- [Log Management Guide](https://docs.datadoghq.com/logs/)
- [Infrastructure Monitoring](https://docs.datadoghq.com/infrastructure/)
- [Best Practices](docs/best-practices.md)
- [Troubleshooting Guide](docs/troubleshooting.md)

## Support

For implementation support:
1. Check this documentation
2. Review troubleshooting guides
3. Contact the observability team
4. Create an issue in this repository
