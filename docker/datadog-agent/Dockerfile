FROM datadog/agent:7.48.0

# Environment variables for Datadog Agent
ENV DD_API_KEY=""
ENV DD_APP_KEY=""
ENV DD_SITE="datadoghq.com"
ENV DD_HOSTNAME="auto"
ENV DD_TAGS="team:backend,owner:grv-team"
ENV DD_SERVICE="grv-api"
ENV DD_ENV="prod"
ENV DD_VERSION="v1.0.0"

# Core Agent Features
ENV DD_PROCESS_AGENT_ENABLED="true"
ENV DD_LOGS_ENABLED="true"
ENV DD_LOGS_CONFIG_CONTAINER_COLLECT_ALL="true"
ENV DD_CONTAINER_EXCLUDE="name:dd-agent"
ENV DD_AC_INCLUDE="true"
ENV DD_APM_ENABLED="true"
ENV DD_APM_NON_LOCAL_TRAFFIC="true"

# Performance and Reliability
ENV DD_TRACE_AGENT_PORT="8126"
ENV DD_DOGSTATSD_PORT="8125"
ENV DD_LOG_LEVEL="INFO"
ENV DD_EXPVAR_PORT="6062"

# Security
ENV DD_BIND_HOST="0.0.0.0"
ENV DD_CMD_PORT="6062"

# Copy custom configuration files
COPY conf.d/ /etc/datadog-agent/conf.d/
COPY checks.d/ /etc/datadog-agent/checks.d/

# Create log directories
RUN mkdir -p /var/log/datadog /etc/datadog-agent/conf.d/log

# Set proper permissions
RUN chown -R dd-agent:dd-agent /etc/datadog-agent/conf.d /etc/datadog-agent/checks.d /var/log/datadog

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD agent health || exit 1

# Expose ports for metrics and traces
EXPOSE 8125/udp 8126/tcp 6062/tcp

# Run as dd-agent user
USER dd-agent

# Start the agent
CMD ["agent", "run"]
