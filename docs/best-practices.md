# Datadog Observability Best Practices for grv-api

This document outlines best practices for implementing and maintaining Datadog observability for the grv-api service.

## APM & Tracing Best Practices

### Service Naming and Tagging

#### Consistent Service Naming
```python
# Use consistent service naming
DD_SERVICE=grv-api

# Include environment in all telemetry
DD_ENV=prod|stg|dev

# Always include version
DD_VERSION=v1.0.0
```

#### Standard Tags
Always include these tags in all telemetry:
- `service:grv-api`
- `env:prod|stg|dev`
- `version:vX.Y.Z`
- `team:backend`
- `owner:grv-team`

#### Resource Naming
```python
# Use clear, consistent resource names
@tracer.wrap(resource="user.create", service="grv-api")
def create_user():
    pass

# Include HTTP method and path
resource = f"{request.method} {request.path}"
```

### Trace Sampling

#### Environment-Specific Sampling
```python
# Production: Lower sampling rate
DD_TRACE_SAMPLE_RATE=0.1  # 10%

# Staging: Higher sampling rate
DD_TRACE_SAMPLE_RATE=0.5  # 50%

# Development: Full sampling
DD_TRACE_SAMPLE_RATE=1.0  # 100%
```

#### Intelligent Sampling
```python
# Sample based on importance
@tracer.wrap(sample_rate=1.0)  # Always sample critical operations
def process_payment():
    pass

@tracer.wrap(sample_rate=0.01)  # Low sample rate for health checks
def health_check():
    pass
```

### Span Best Practices

#### Proper Span Naming
```python
# Good: Descriptive and specific
@tracer.wrap(resource="user.profile.update", service="grv-api")
def update_user_profile():
    pass

# Bad: Too generic
@tracer.wrap(resource="api_call", service="grv-api")
def update_user_profile():
    pass
```

#### Span Tags
```python
with tracer.trace("database.query", service="grv-api-db") as span:
    span.set_tag("db.operation", "SELECT")
    span.set_tag("db.table", "users")
    span.set_tag("db.statement", "SELECT * FROM users WHERE id = %s")
    span.set_tag("user.id", user_id)
```

#### Error Handling
```python
try:
    with tracer.trace("external.api.call", service="grv-api") as span:
        response = requests.get(url, timeout=30)
        span.set_tag("http.status_code", response.status_code)
        return response.json()
except requests.RequestException as e:
    span.set_tag("error", True)
    span.set_tag("error.message", str(e))
    span.set_tag("error.type", type(e).__name__)
    raise
```

## Logging Best Practices

### Structured Logging

#### JSON Format
```python
# Use structured logging with consistent fields
logger.info(
    "User login successful",
    extra={
        "user_id": user.id,
        "user_email": user.email,
        "login_method": "password",
        "ip_address": request.META.get('REMOTE_ADDR'),
        "trace_id": trace_id,
        "span_id": span_id
    }
)
```

#### Log Levels
- **DEBUG**: Detailed debugging information
- **INFO**: General information about application flow
- **WARNING**: Unexpected behavior that doesn't stop the application
- **ERROR**: Error conditions that should be investigated
- **CRITICAL**: Serious errors that may cause the application to stop

#### Correlation IDs
```python
# Always include correlation IDs
logger.info(
    "Processing request",
    extra={
        "request_id": request.request_id,
        "trace_id": trace_id,
        "span_id": span_id,
        "user_id": user.id
    }
)
```

### Sensitive Data Handling

#### Data Masking
```python
# Implement automatic sensitive data masking
class SensitiveDataFilter(logging.Filter):
    SENSITIVE_PATTERNS = [
        (r'password["\s]*[:=]["\s]*[^"\s,}]+', 'password": "***"'),
        (r'token["\s]*[:=]["\s]*[^"\s,}]+', 'token": "***"'),
        (r'secret["\s]*[:=]["\s]*[^"\s,}]+', 'secret": "***"'),
    ]
    
    def filter(self, record):
        for pattern, replacement in self.SENSITIVE_PATTERNS:
            record.msg = re.sub(pattern, replacement, str(record.msg))
        return True
```

#### PII Redaction
```python
# Redact personally identifiable information
def mask_pii(data):
    if isinstance(data, str):
        # Mask emails
        data = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '***@***.***', data)
        # Mask phone numbers
        data = re.sub(r'\b\d{3}-\d{3}-\d{4}\b', '***-***-****', data)
        # Mask SSN
        data = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '***-**-****', data)
    return data
```

### Log Retention and Rotation

#### Configuration
```python
# Configure log rotation
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    '/app/logs/grv-api.log',
    maxBytes=100 * 1024 * 1024,  # 100MB
    backupCount=5
)
```

#### Retention Policies
- **Error logs**: 30 days
- **Access logs**: 7 days
- **Debug logs**: 1 day (development only)
- **Audit logs**: 1 year

## Infrastructure Monitoring Best Practices

### Container Monitoring

#### Resource Limits
```yaml
# Set appropriate resource limits
services:
  grv-api:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
```

#### Health Checks
```yaml
# Implement proper health checks
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

### Database Monitoring

#### Connection Pooling
```python
# Configure connection pooling
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'OPTIONS': {
            'MAX_CONNS': 20,
            'MIN_CONNS': 5,
            'CONN_MAX_AGE': 300,
        }
    }
}
```

#### Query Optimization
```python
# Monitor slow queries
@tracer.wrap(resource="database.query", service="grv-api-db")
def get_user_data(user_id):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT id, email, created_at FROM users WHERE id = %s",
            [user_id]
        )
        return cursor.fetchone()
```

### Redis Monitoring

#### Memory Management
```python
# Monitor Redis memory usage
def check_redis_memory():
    r = redis.Redis()
    info = r.info('memory')
    used_memory = info['used_memory']
    max_memory = info['maxmemory']
    
    if max_memory > 0:
        usage_percent = (used_memory / max_memory) * 100
        statsd.gauge('redis.memory.usage_percent', usage_percent)
```

#### Key Expiration
```python
# Set appropriate TTL for cache keys
def cache_user_data(user_id, data, ttl=3600):
    r.setex(f"user:{user_id}", ttl, json.dumps(data))
```

## Monitor and Alert Best Practices

### Monitor Design

#### Meaningful Names
```json
{
  "name": "[GRV-API] High P95 Latency Alert",
  "message": "High P95 latency detected for grv-api service"
}
```

#### Appropriate Thresholds
- **Latency**: P95 < 2s, P99 < 5s
- **Error Rate**: < 5% for 5xx errors
- **CPU Usage**: < 80% average
- **Memory Usage**: < 85% average
- **Disk Usage**: < 90%

#### Alert Severity
- **Critical**: Service down, data loss, security breach
- **Warning**: Performance degradation, high resource usage
- **Info**: Deployments, configuration changes

### Alert Fatigue Prevention

#### Alert Grouping
```python
# Group related alerts
tags = [
    "service:grv-api",
    "env:prod",
    "component:database",
    "severity:warning"
]
```

#### Escalation Policies
- **Level 1**: 5 minutes - On-call engineer
- **Level 2**: 15 minutes - Team lead
- **Level 3**: 30 minutes - Engineering manager

#### Alert Suppression
```python
# Suppress alerts during maintenance windows
if is_maintenance_window():
    return "suppressed_maintenance"
```

## Performance Optimization

### Sampling Strategies

#### Adaptive Sampling
```python
def get_sample_rate(endpoint, method):
    # Higher sampling for critical endpoints
    if endpoint in ['/api/v1/payments', '/api/v1/auth']:
        return 1.0
    # Lower sampling for health checks
    elif endpoint == '/health':
        return 0.01
    # Default sampling
    else:
        return 0.1
```

#### Head-Based Sampling
```python
# Sample based on trace ID
def should_sample(trace_id):
    return int(trace_id[:8], 16) % 100 < 10  # 10% sampling
```

### Metric Optimization

#### Cardinality Control
```python
# Avoid high cardinality tags
# Bad: user_id as tag
statsd.increment('api.requests', tags=[f'user_id:{user_id}'])

# Good: user_id as field
statsd.increment('api.requests', tags=['endpoint:users'])
statsd.histogram('api.user_requests', 1, tags=[f'user_tier:{user_tier}'])
```

#### Metric Aggregation
```python
# Pre-aggregate metrics where possible
def aggregate_metrics():
    # Instead of sending individual request times
    # Send aggregated statistics
    statsd.histogram('api.request.duration', avg_duration)
    statsd.histogram('api.request.duration.p95', p95_duration)
    statsd.histogram('api.request.duration.p99', p99_duration)
```

## Security Best Practices

### API Key Management

#### Environment Variables
```bash
# Use environment variables for credentials
export DD_API_KEY="your_api_key_here"
export DD_APP_KEY="your_app_key_here"
```

#### Key Rotation
```python
# Implement key rotation
def rotate_datadog_keys():
    old_key = os.getenv('DD_API_KEY')
    new_key = generate_new_api_key()
    
    # Test new key
    if test_api_key(new_key):
        os.environ['DD_API_KEY'] = new_key
        deactivate_key(old_key)
```

### Network Security

#### TLS Configuration
```python
# Use TLS for all communications
DD_AGENT_HOST=datadog-agent.example.com
DD_AGENT_PORT=8126
DD_TRACE_AGENT_URL=https://datadog-agent.example.com:8126
```

#### Firewall Rules
```bash
# Restrict access to Datadog agent
ufw allow from 10.0.0.0/8 to any port 8126
ufw allow from 172.16.0.0/12 to any port 8126
ufw allow from 192.168.0.0/16 to any port 8126
```

### Data Privacy

#### GDPR Compliance
```python
# Implement data retention policies
def delete_user_data(user_id):
    # Delete user traces older than 30 days
    delete_traces(user_id, older_than=30)
    
    # Anonymize logs
    anonymize_logs(user_id)
    
    # Clear cache
    clear_user_cache(user_id)
```

## Troubleshooting Best Practices

### Debugging Methodology

#### Systematic Approach
1. **Check agent status**
2. **Verify network connectivity**
3. **Review configuration**
4. **Examine logs**
5. **Test with simple cases**

#### Debug Tools
```bash
# Check agent status
agent status

# Test trace collection
curl -X POST http://localhost:8126/v0.4/traces

# Verify log processing
agent config
```

### Performance Issues

#### Bottleneck Identification
```python
# Profile slow operations
@tracer.wrap(resource="slow.operation")
def slow_operation():
    with tracer.trace("database.query") as span:
        # Database operation
        pass
    
    with tracer.trace("external.api") as span:
        # External API call
        pass
```

#### Resource Analysis
```python
# Monitor resource usage
def monitor_resources():
    import psutil
    
    cpu_percent = psutil.cpu_percent(interval=1)
    memory_percent = psutil.virtual_memory().percent
    
    statsd.gauge('system.cpu.percent', cpu_percent)
    statsd.gauge('system.memory.percent', memory_percent)
```

## Documentation and Knowledge Sharing

### Documentation Standards

#### Runbooks
```markdown
# High Latency Incident Runbook

## Symptoms
- P95 latency > 2s
- User complaints about slow response times

## Diagnosis
1. Check Datadog APM traces
2. Review database query performance
3. Examine external API response times

## Resolution
1. Identify slow queries
2. Add database indexes
3. Implement caching
4. Scale resources if needed
```

#### Architecture Diagrams
- Document service dependencies
- Include monitoring integration points
- Show data flow and trace propagation

### Team Training

#### Knowledge Sharing
- Regular observability workshops
- Incident review meetings
- Best practice documentation updates
- Cross-team collaboration

#### Onboarding
- Observability setup checklist
- Monitor configuration guidelines
- Alert response procedures
- Troubleshooting common issues

## Continuous Improvement

### Review Processes

#### Monthly Reviews
- Monitor effectiveness analysis
- Alert fatigue assessment
- Performance trend analysis
- Cost optimization opportunities

#### Quarterly Reviews
- Architecture evaluation
- Tooling assessment
- Team skill gaps
- Process improvements

### Metrics for Success

#### Observability Maturity
- **Level 1**: Basic metrics and logs
- **Level 2**: APM and distributed tracing
- **Level 3**: Proactive monitoring and alerting
- **Level 4**: Automated remediation
- **Level 5**: Predictive analytics

#### KPIs
- **MTTD** (Mean Time to Detect): < 5 minutes
- **MTTR** (Mean Time to Resolve): < 30 minutes
- **Alert Fatigue**: < 10 alerts per day
- **Coverage**: > 95% of services monitored

This comprehensive best practices guide ensures that your grv-api service maintains high observability standards while optimizing performance, security, and operational efficiency.
