# Quick Start Guide - grv-api Datadog Observability

Get your grv-api service fully monitored with Datadog in under 15 minutes.

## 🚀 5-Minute Setup

### 1. Configure Environment
```bash
# Copy and edit environment variables
cp .env.example .env
vim .env

# Set your Datadog credentials
DD_API_KEY=your_api_key_here
DD_APP_KEY=your_app_key_here
DD_SERVICE=grv-api
DD_ENV=prod
DD_VERSION=v1.0.0
```

### 2. Deploy with Docker Compose
```bash
# Start all services
docker-compose -f docker/docker-compose.yml up -d

# Verify deployment
docker-compose -f docker/docker-compose.yml ps
```

### 3. Deploy Monitors
```bash
# Deploy all production monitors
chmod +x scripts/deploy-monitors.sh
./scripts/deploy-monitors.sh
```

### 4. Test Setup
```bash
# Run comprehensive tests
python scripts/test-observability.py

# Send test deployment event
python scripts/send-deploy-event.py \
    --api-key $DD_API_KEY \
    --app-key $DD_APP_KEY \
    --version v1.0.0 \
    --auto-git
```

## 📊 What You Get

### ✅ APM & Tracing
- Django request tracing with ddtrace
- Celery task monitoring
- Database query tracing
- Redis operation tracking
- Automatic service tagging

### ✅ Structured Logging
- JSON log format with trace correlation
- Automatic sensitive data masking
- Nginx access/error log parsing
- Centralized log collection

### ✅ Infrastructure Monitoring
- Docker container metrics
- PostgreSQL performance monitoring
- Redis memory and connection tracking
- Nginx web server metrics
- System resource monitoring

### ✅ Production Alerts
- High latency alerts (P95/P99)
- Error rate monitoring
- Resource usage alerts
- Database performance alerts
- Celery queue monitoring

## 🔧 Integration Steps

### Django Application
```python
# Add to settings.py
MIDDLEWARE = [
    'ddtrace.contrib.django.TraceMiddleware',
    # ... your existing middleware
]

# Configure Datadog
DATADOG_TRACE = {
    'enabled': True,
    'service': 'grv-api',
    'env': 'prod',
    'version': 'v1.0.0',
    'agent_host': 'datadog-agent',
    'log_injection': True,
}
```

### Celery Application
```python
# Add to celery_app.py
from ddtrace.contrib.celery import patch_service
app = Celery('grv-api')
patch_service(app)
```

### Nginx Configuration
```nginx
# Add to nginx.conf
log_format json_combined escape=json
    '{'
    '"timestamp": "$time_iso8601",'
    '"service": "grv-api",'
    '"dd.trace_id": "$http_x_datadog_trace_id",'
    '"dd.span_id": "$http_x_datadog_parent_id",'
    '"status": $status,'
    '"request_time": $request_time'
    '}';
```

## 📈 Key Metrics Available

### Application Performance
- Request latency (P50, P90, P95, P99)
- Error rates by endpoint
- Request volume and throughput
- Database query performance
- Background task execution

### Infrastructure Health
- Container CPU and memory usage
- Database connection health
- Redis memory utilization
- Web server response times
- System resource metrics

### Business Intelligence
- User activity patterns
- Feature usage analytics
- System reliability indicators
- Performance SLA compliance

## 🚨 Alert Configuration

### Critical Alerts (5-minute response)
- Service downtime
- Error rate > 5%
- P95 latency > 2s
- Database connection failures

### Warning Alerts (15-minute response)
- High memory usage > 85%
- CPU throttling detected
- Redis memory pressure
- Nginx 5xx rate increase

## 🛠️ Troubleshooting

### Common Issues
1. **Missing traces**: Check agent connectivity
2. **No logs**: Verify log collection configuration
3. **Alerts not firing**: Check monitor queries
4. **High resource usage**: Adjust sampling rates

### Debug Commands
```bash
# Check agent status
docker exec datadog-agent agent status

# Test trace collection
curl -X POST http://localhost:8126/v0.4/traces

# View logs
docker logs datadog-agent | grep "trace"
```

## 📚 Next Steps

1. **Customize Monitors**: Adjust thresholds for your specific needs
2. **Add Dashboards**: Create custom visualization dashboards
3. **Set Up SLIs/SLOs**: Define service level objectives
4. **Configure Retention**: Set appropriate data retention policies
5. **Team Training**: Ensure team knows how to use Datadog

## 🔗 Useful Links

- [Datadog APM Documentation](https://docs.datadoghq.com/tracing/)
- [Deployment Guide](docs/deployment-guide.md)
- [Best Practices](docs/best-practices.md)
- [Troubleshooting Guide](docs/troubleshooting.md)

## 🆘 Support

For issues:
1. Check the troubleshooting guide
2. Review the test results
3. Check Datadog agent logs
4. Contact the observability team

You're all set! Your grv-api service is now fully observable with Datadog. 🎉
