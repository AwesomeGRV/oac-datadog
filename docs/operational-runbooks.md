# Operational Runbooks - grv-api Datadog Observability

This document provides comprehensive operational runbooks for handling common incidents and operational tasks for the grv-api service.

## Table of Contents

- [Incident Response](#incident-response)
- [Service Outages](#service-outages)
- [Performance Issues](#performance-issues)
- [Security Incidents](#security-incidents)
- [Database Issues](#database-issues)
- [Infrastructure Problems](#infrastructure-problems)
- [Deployment Issues](#deployment-issues)
- [Monitoring & Alerting](#monitoring--alerting)

---

## Incident Response

### General Incident Response Process

1. **Acknowledge Alert** (within 5 minutes)
   - Go to Datadog Monitor: https://app.datadoghq.com/monitors
   - Acknowledge the alert with your name and initial assessment
   - Join the incident Slack channel: #incidents-critical

2. **Assess Impact** (within 10 minutes)
   - Check service status: https://status.grv-api.com
   - Review error rates: https://app.datadoghq.com/apm/services/grv-api?env=prod&view=errors
   - Check user impact via error tracking
   - Determine incident priority (P1-P4)

3. **Create Incident** (if auto-creation failed)
   ```bash
   # Create incident via Datadog API
   curl -X POST "https://api.datadoghq.com/api/v1/incidents" \
     -H "Content-Type: application/json" \
     -H "DD-API-KEY: $DD_API_KEY" \
     -H "DD-APPLICATION-KEY: $DD_APP_KEY" \
     -d '{
       "data": {
         "type": "incidents",
         "attributes": {
           "title": "Service Outage - grv-api",
           "customer_impacted": true,
           "priority": "P1"
         }
       }
     }'
   ```

4. **Communicate** (ongoing)
   - Update incident Slack channel every 15 minutes
   - Post status updates to internal communication channels
   - Update external status page if customer-facing

5. **Mitigate** (primary goal)
   - Follow specific runbook sections below
   - Document all actions taken
   - Consider automated remediation options

6. **Resolve & Recover**
   - Verify service is fully operational
   - Monitor for 30 minutes post-resolution
   - Close incident with resolution summary

---

## Service Outages

### P1 - Complete Service Outage

**Symptoms:**
- Error rate > 50%
- Availability < 99%
- No successful requests
- All monitors firing

**Immediate Actions:**
1. **Check Service Status**
   ```bash
   # Check if service is running
   kubectl get pods -l app=grv-api -n production
   docker-compose ps grv-api
   
   # Check service logs
   kubectl logs -l app=grv-api -n production --tail=100
   docker-compose logs grv-api --tail=100
   ```

2. **Quick Health Check**
   ```bash
   # Test service endpoints
   curl -f https://api.grv-api.com/health
   curl -f https://api.grv-api.com/status
   
   # Check database connectivity
   python scripts/test-database-connectivity.py
   ```

3. **Common Causes & Solutions**

   **Service Not Running:**
   ```bash
   # Restart service
   kubectl rollout restart deployment/grv-api -n production
   docker-compose restart grv-api
   
   # Check resource limits
   kubectl describe pod <pod-name> -n production
   ```

   **Database Connection Issues:**
   ```bash
   # Check database status
   kubectl exec -it postgres-pod -- pg_isready
   python scripts/test-database-connectivity.py
   
   # Restart database if needed
   kubectl rollout restart deployment/postgres -n production
   ```

   **Infrastructure Issues:**
   ```bash
   # Check cluster status
   kubectl get nodes
   kubectl top nodes
   
   # Check resource usage
   kubectl top pods -n production
   ```

4. **Automated Remediation**
   ```bash
   # Run automated recovery script
   python scripts/auto-recovery.py --incident-type=service_outage
   ```

5. **Escalation**
   - If not resolved in 15 minutes: escalate to Engineering Manager
   - If not resolved in 30 minutes: escalate to VP Engineering
   - If not resolved in 60 minutes: declare major incident

### P2 - Service Degradation

**Symptoms:**
- Error rate 10-50%
- Latency P95 > 2000ms
- Partial functionality issues

**Actions:**
1. **Identify Affected Components**
   - Check specific endpoints: https://app.datadoghq.com/apm/services/grv-api/resources
   - Review error patterns: https://app.datadoghq.com/logs?query=service:grv-api%20status:5xx

2. **Common Solutions**
   ```bash
   # Clear application cache
   python scripts/clear-cache.py
   
   # Scale up service
   kubectl scale deployment grv-api --replicas=10 -n production
   
   # Restart specific components
   kubectl rollout restart deployment/grv-api-worker -n production
   ```

---

## Performance Issues

### High Latency (P95 > 2000ms)

**Diagnosis:**
1. **Check APM Traces**
   - Go to: https://app.datadoghq.com/apm/services/grv-api?env=prod&view=performance
   - Identify slow endpoints and operations
   - Look for database query bottlenecks

2. **Database Performance**
   ```bash
   # Check slow queries
   python scripts/check-slow-queries.py
   
   # Analyze query performance
   kubectl exec postgres-pod -- psql -c "SELECT query, mean_time, calls FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"
   ```

3. **Resource Utilization**
   ```bash
   # Check CPU/Memory usage
   kubectl top pods -n production
   kubectl describe nodes
   
   # Check for throttling
   kubectl get events --field-selector reason=Throttling
   ```

**Solutions:**
1. **Database Optimization**
   ```bash
   # Add database indexes
   python scripts/add-missing-indexes.py
   
   # Update query statistics
   kubectl exec postgres-pod -- psql -c "ANALYZE;"
   ```

2. **Application Scaling**
   ```bash
   # Horizontal scaling
   kubectl scale deployment grv-api --replicas=15 -n production
   
   # Vertical scaling (if needed)
   kubectl patch deployment grv-api -p '{"spec":{"template":{"spec":{"containers":[{"name":"grv-api","resources":{"limits":{"cpu":"2000m","memory":"4Gi"}}}]}}}}' -n production
   ```

3. **Cache Optimization**
   ```bash
   # Warm up cache
   python scripts/warm-up-cache.py
   
   # Check cache hit rates
   python scripts/check-cache-performance.py
   ```

### Low Apdex Score (< 0.8)

**Diagnosis:**
1. **Review Apdex Breakdown**
   - Check: https://app.datadoghq.com/apm/services/grv-api?env=prod
   - Identify which endpoints are dragging down the score

2. **Set Appropriate Thresholds**
   ```bash
   # Update Apdex threshold if needed
   # Go to Datadog APM > Service > Settings > Apdex
   ```

**Solutions:**
1. **Optimize Critical Paths**
   - Focus on high-traffic endpoints
   - Implement async processing for long operations
   - Add request timeouts

2. **Frontend Optimization**
   - Implement client-side caching
   - Optimize API response sizes
   - Add CDN for static assets

---

## Security Incidents

### SQL Injection Attack Detected

**Immediate Actions:**
1. **Block Malicious IPs**
   ```bash
   # Run security monitoring script
   python scripts/security-monitoring.py --block-attacker
   
   # Manual IP blocking
   kubectl annotate netpolicy block-ip-<IP> "net.beta.kubernetes.io/network-policy={\"ingress\":{\"isolation\":\"DefaultDeny\"}}"
   ```

2. **Investigate Attack**
   ```bash
   # Check application logs for attack patterns
   kubectl logs -l app=grv-api -n production | grep "sql_injection"
   
   # Review database for unauthorized changes
   python scripts/audit-database-changes.py --since="1 hour ago"
   ```

3. **Security Hardening**
   ```bash
   # Update WAF rules
   python scripts/update-waf-rules.py --rule-type=sql_injection
   
   # Enable additional logging
   kubectl patch deployment grv-api -p '{"spec":{"template":{"spec":{"containers":[{"name":"grv-api","env":[{"name":"LOG_LEVEL","value":"DEBUG"}]}]}}}}' -n production
   ```

4. **Communication**
   - Notify security team immediately
   - Document all findings
   - Prepare incident report

### Brute Force Attack

**Actions:**
1. **Implement Rate Limiting**
   ```bash
   # Update rate limiting configuration
   python scripts/update-rate-limits.py --requests-per-minute=10
   
   # Enable account lockout
   python scripts/enable-account-lockout.py --failed-attempts=5
   ```

2. **Block Attacker IPs**
   ```bash
   # Auto-block malicious IPs
   python scripts/security-monitoring.py --auto-block
   
   # Update firewall rules
   python scripts/update-firewall-rules.py --block-list=attacker_ips.txt
   ```

3. **Strengthen Authentication**
   ```bash
   # Enable 2FA for all accounts
   python scripts/enable-2fa.py --all-users
   
   # Force password reset
   python scripts/force-password-reset.py --all-users
   ```

---

## Database Issues

### Connection Pool Exhaustion

**Symptoms:**
- Database connection errors
- High active connection count
- Application timeouts

**Diagnosis:**
```bash
# Check connection pool status
kubectl exec postgres-pod -- psql -c "SELECT count(*) as active_connections FROM pg_stat_activity WHERE state = 'active';"

# Check connection limits
kubectl exec postgres-pod -- psql -c "SHOW max_connections;"
```

**Solutions:**
1. **Increase Connection Pool**
   ```bash
   # Update application connection pool size
   kubectl patch deployment grv-api -p '{"spec":{"template":{"spec":{"containers":[{"name":"grv-api","env":[{"name":"DB_POOL_SIZE","value":"50"}]}]}}}}' -n production
   
   # Restart application
   kubectl rollout restart deployment/grv-api -n production
   ```

2. **Database Optimization**
   ```bash
   # Kill long-running queries
   kubectl exec postgres-pod -- psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'active' AND query_start < now() - interval '5 minutes';"
   
   # Optimize database configuration
   kubectl patch configmap postgres-config -p '{"data":{"max_connections":"200","shared_buffers":"256MB"}}'
   ```

### Slow Queries

**Actions:**
1. **Identify Slow Queries**
   ```bash
   # Enable slow query logging
   kubectl exec postgres-pod -- psql -c "ALTER SYSTEM SET log_min_duration_statement = 1000;"
   kubectl exec postgres-pod -- psql -c "SELECT pg_reload_conf();"
   
   # Analyze current slow queries
   python scripts/analyze-slow-queries.py
   ```

2. **Optimize Queries**
   ```bash
   # Add missing indexes
   python scripts/optimize-database-indexes.py
   
   # Update table statistics
   kubectl exec postgres-pod -- psql -c "ANALYZE;"
   ```

---

## Infrastructure Problems

### High CPU Usage (> 90%)

**Diagnosis:**
```bash
# Check CPU usage by pod
kubectl top pods -n production --sort-by=cpu

# Check CPU throttling
kubectl describe pod <pod-name> -n production | grep -i throttling
```

**Solutions:**
1. **Scale Up Resources**
   ```bash
   # Increase CPU limits
   kubectl patch deployment grv-api -p '{"spec":{"template":{"spec":{"containers":[{"name":"grv-api","resources":{"limits":{"cpu":"2000m"}}}]}}}}' -n production
   
   # Scale horizontally
   kubectl scale deployment grv-api --replicas=20 -n production
   ```

2. **Optimize Application**
   ```bash
   # Profile application performance
   python scripts/profile-application.py
   
   # Enable CPU profiling
   kubectl patch deployment grv-api -p '{"spec":{"template":{"spec":{"containers":[{"name":"grv-api","env":[{"name":"ENABLE_CPU_PROFILING","value":"true"}]}]}}}}' -n production
   ```

### Memory Leaks

**Diagnosis:**
```bash
# Check memory usage trends
kubectl top pods -n production --sort-by=memory

# Check for OOM kills
kubectl get events -n production --field-selector reason=OOMKilling
```

**Solutions:**
1. **Increase Memory Limits**
   ```bash
   kubectl patch deployment grv-api -p '{"spec":{"template":{"spec":{"containers":[{"name":"grv-api","resources":{"limits":{"memory":"4Gi"}}}]}}}}' -n production
   ```

2. **Investigate Memory Leaks**
   ```bash
   # Enable memory profiling
   kubectl patch deployment grv-api -p '{"spec":{"template":{"spec":{"containers":[{"name":"grv-api","env":[{"name":"ENABLE_MEMORY_PROFILING","value":"true"}]}]}}}}' -n production
   
   # Analyze memory dumps
   python scripts/analyze-memory-dumps.py
   ```

### Disk Space Issues

**Actions:**
1. **Clean Up Disk Space**
   ```bash
   # Clean old logs
   kubectl exec -it <pod-name> -- find /var/log -name "*.log" -mtime +7 -delete
   
   # Clean temporary files
   kubectl exec -it <pod-name> -- find /tmp -type f -mtime +1 -delete
   
   # Clean Docker images (if applicable)
   docker system prune -f
   ```

2. **Expand Disk Space**
   ```bash
   # Expand PVC (if using cloud storage)
   kubectl patch pvc grv-api-data -p '{"spec":{"resources":{"requests":{"storage":"200Gi"}}}}'
   ```

---

## Deployment Issues

### Rollback Needed

**When to Rollback:**
- Error rate spike > 50% after deployment
- Critical functionality broken
- Performance degradation > 100%

**Rollback Process:**
1. **Quick Rollback**
   ```bash
   # Kubernetes rollback
   kubectl rollout undo deployment/grv-api -n production
   
   # Docker Compose rollback
   docker-compose down
   docker-compose up -d --force-recreate
   ```

2. **Verify Rollback**
   ```bash
   # Check deployment status
   kubectl rollout status deployment/grv-api -n production
   
   # Test service functionality
   python scripts/test-service-functionality.py
   ```

3. **Investigate Issue**
   ```bash
   # Compare deployment versions
   python scripts/compare-deployments.py --previous=<version> --current=<version>
   
   # Review deployment logs
   kubectl logs -l app=grv-api -n production --since="1 hour ago"
   ```

### Deployment Stuck

**Actions:**
1. **Check Deployment Status**
   ```bash
   kubectl get deployment grv-api -n production -o wide
   kubectl describe deployment grv-api -n production
   ```

2. **Force Restart**
   ```bash
   # Cancel stuck deployment
   kubectl rollout undo deployment/grv-api -n production --to-revision=<previous-revision>
   
   # Force restart
   kubectl rollout restart deployment/grv-api -n production
   ```

---

## Monitoring & Alerting

### Monitor Not Firing When Expected

**Troubleshooting:**
1. **Check Monitor Configuration**
   ```bash
   # Test monitor query
   curl -X GET "https://api.datadoghq.com/api/v1/query" \
     -H "DD-API-KEY: $DD_API_KEY" \
     -H "DD-APPLICATION-KEY: $DD_APP_KEY" \
     -d "query=<monitor-query>"
   ```

2. **Check Data Ingestion**
   ```bash
   # Verify metrics are being sent
   python scripts/test-metrics-ingestion.py
   
   # Check agent status
   kubectl exec datadog-agent -- agent status
   ```

### False Positives

**Solutions:**
1. **Adjust Thresholds**
   - Go to Datadog Monitor settings
   - Update thresholds based on baseline metrics
   - Consider dynamic thresholds for variable workloads

2. **Add Conditions**
   ```bash
   # Update monitor with additional conditions
   python scripts/update-monitor.py --monitor-id=<id> --add-conditions
   ```

3. **Implement Alert Suppression**
   ```bash
   # Add maintenance windows
   python scripts/schedule-maintenance-window.py --start="<time>" --duration="<hours>"
   ```

---

## Post-Incident Procedures

### Postmortem Template

1. **Summary**
   - What happened?
   - What was the impact?
   - When did it occur?
   - How long did it last?

2. **Timeline**
   - Detection time
   - Response actions
   - Resolution time
   - Key decision points

3. **Root Cause Analysis**
   - Primary cause
   - Contributing factors
   - Why wasn't it prevented?

4. **Impact Assessment**
   - User impact
   - Business impact
   - Financial impact (if applicable)

5. **Lessons Learned**
   - What went well
   - What could be improved
   - Action items

6. **Action Items**
   - Prevention measures
   - Detection improvements
   - Response improvements
   - Follow-up assignments

### Follow-up Tasks

1. **Update Monitoring**
   ```bash
   # Add new monitors based on incident learnings
   python scripts/create-monitor-from-incident.py --incident-id=<id>
   ```

2. **Improve Automation**
   ```bash
   # Add new automation rules
   python scripts/update-automation-rules.py --based-on-incident=<id>
   ```

3. **Documentation Updates**
   - Update runbooks
   - Add new troubleshooting steps
   - Update architecture diagrams

---

## Emergency Contacts

| Role | Contact | Escalation Time |
|------|---------|-----------------|
| On-call Engineer | Slack: @oncall | Immediate |
| Team Lead | Slack: @team-lead | 15 minutes |
| Engineering Manager | Slack: @eng-manager | 30 minutes |
| VP Engineering | Slack: @vp-eng | 1 hour |
| CTO | Slack: @cto | 2 hours |

---

## Tools and Scripts Reference

### Monitoring Scripts
- `scripts/test-observability.py` - Comprehensive observability testing
- `scripts/security-monitoring.py` - Real-time security monitoring
- `scripts/alert-automation.py` - Advanced alert automation

### Recovery Scripts
- `scripts/auto-recovery.py` - Automated incident recovery
- `scripts/clear-cache.py` - Cache management
- `scripts/rollback-deployment.py` - Deployment rollback

### Analysis Scripts
- `scripts/analyze-slow-queries.py` - Database performance analysis
- `scripts/profile-application.py` - Application performance profiling
- `scripts/audit-database-changes.py` - Security audit

---

## Training and Drills

### Regular Drills
1. **Monthly Fire Drills** - Simulated service outages
2. **Quarterly Security Drills** - Simulated security incidents
3. **Bi-annual Major Incident Drills** - Complex multi-system failures

### Training Requirements
- All engineers must complete incident response training
- On-call engineers must complete advanced troubleshooting training
- Team leads must complete incident command training

---

This runbook should be reviewed and updated quarterly or after any major incident.
