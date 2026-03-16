# Enhanced Django Settings for grv-api with Comprehensive ddtrace Integration

# Add to your Django settings.py

# Datadog Configuration
DATADOG_TRACE = {
    'DEFAULT_SERVICE': os.getenv('DD_SERVICE', 'grv-api'),
    'TAGS': {
        'env': os.getenv('DD_ENV', 'prod'),
        'version': os.getenv('DD_VERSION', 'v1.0.0'),
        'team': os.getenv('DD_TEAM', 'backend'),
        'owner': os.getenv('DD_OWNER', 'grv-team'),
    },
    'ANALYTICS_ENABLED': True,
    'DISTRIBUTED_TRACING': True,
    'INCLUDE_USER_INFO': True,
    'TRACE_TEMPLATES': True,
    'TRACE_QUERY_STRING': True,
    'TRACE_CLIENT_IP': True,
    'AGENT_HOSTNAME': os.getenv('DD_AGENT_HOST', 'localhost'),
    'AGENT_PORT': int(os.getenv('DD_TRACE_AGENT_PORT', '8126')),
    'ENABLED': os.getenv('DD_TRACE_ENABLED', 'true').lower() == 'true',
    'DEBUG': os.getenv('DD_TRACE_DEBUG', 'false').lower() == 'true',
    'SAMPLE_RATE': float(os.getenv('DD_TRACE_SAMPLE_RATE', '0.1')),
}

# Enhanced Logging Configuration with Trace Correlation
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            'format': '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s", "trace_id": "%(dd.trace_id)s", "span_id": "%(dd.span_id)s"}',
            'style': '%',
        },
        'verbose': {
            'format': '[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s [trace_id=%(dd.trace_id)s span_id=%(dd.span_id)s]',
            'style': '%',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
            'filters': ['trace_context'],
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/grv-api/app.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
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
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'grv_api': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'celery': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'ddtrace': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
}

# Middleware Configuration with Enhanced Tracing
MIDDLEWARE = [
    'ddtrace.contrib.django.TraceMiddleware',  # Add at the beginning
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Database Configuration with Tracing
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'grv_api'),
        'USER': os.getenv('DB_USER', 'grv_user'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
        'OPTIONS': {
            'connect_timeout': 10,
            'application_name': 'grv-api',
        },
        'ATOMIC_REQUESTS': True,
    }
}

# Cache Configuration with Tracing
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f"redis://{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', '6379')}/1",
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
        },
        'KEY_PREFIX': 'grv_api',
        'TIMEOUT': 300,
    }
}

# Celery Configuration with Enhanced Tracing
CELERY_BROKER_URL = f"redis://{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', '6379')}/0"
CELERY_RESULT_BACKEND = f"redis://{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', '6379')}/0"

CELERY_CONFIG = {
    'broker_url': CELERY_BROKER_URL,
    'result_backend': CELERY_RESULT_BACKEND,
    'task_serializer': 'json',
    'accept_content': ['json'],
    'result_serializer': 'json',
    'timezone': 'UTC',
    'enable_utc': True,
    'task_track_started': True,
    'task_time_limit': 30 * 60,  # 30 minutes
    'task_soft_time_limit': 25 * 60,  # 25 minutes
    'worker_prefetch_multiplier': 1,
    'worker_max_tasks_per_child': 1000,
    'result_expires': 3600,  # 1 hour
    'result_backend_transport_options': {
        'master_name': 'mymaster',
        'visibility_timeout': 3600,
        'retry_policy': {
            'timeout': 5.0
        }
    },
}

# Enhanced Performance Monitoring
PERFORMANCE_MONITORING = {
    'ENABLE_QUERY_ANALYSIS': True,
    'SLOW_QUERY_THRESHOLD': 1.0,  # seconds
    'ENABLE_TEMPLATE_TIMING': True,
    'ENABLE_MIDDLEWARE_TIMING': True,
    'ENABLE_CACHE_HIT_TRACKING': True,
    'ENABLE_EXTERNAL_API_TRACKING': True,
}

# Service Health Configuration
HEALTH_CHECKS = {
    'database': True,
    'cache': True,
    'celery_broker': True,
    'external_apis': True,
    'disk_space': True,
    'memory_usage': True,
}

# Deployment Configuration
DEPLOYMENT_CONFIG = {
    'auto_deploy_events': True,
    'rollback_detection': True,
    'performance_regression_detection': True,
    'health_check_grace_period': 300,  # 5 minutes
    'deployment_monitoring_window': 1800,  # 30 minutes
}

# Application Initialization
def initialize_datadog_tracing():
    """Initialize enhanced Datadog tracing for Django."""
    try:
        # Import the enhanced tracing configuration
        from examples.django.enhanced_ddtrace_integration import initialize_grv_tracing
        
        # Initialize tracing
        config = initialize_grv_tracing()
        
        # Log initialization
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Enhanced Datadog tracing initialized for {config.service_name}")
        
        return config
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to initialize Datadog tracing: {e}")
        return None

# Initialize tracing on Django startup
try:
    DATADOG_CONFIG = initialize_datadog_tracing()
except Exception:
    DATADOG_CONFIG = None

# Custom Django management command for deployment events
class Command(BaseCommand):
    help = 'Send deployment event to Datadog'
    
    def add_arguments(self, parser):
        parser.add_argument('--version', type=str, required=True)
        parser.add_argument('--git-sha', type=str)
        parser.add_argument('--deployer', type=str)
    
    def handle(self, *args, **options):
        try:
            from datadog import initialize, api
            
            initialize(
                api_key=os.getenv('DD_API_KEY'),
                app_key=os.getenv('DD_APP_KEY')
            )
            
            api.Event.create(
                title=f"Deployment: grv-api v{options['version']}",
                text=f"Service grv-api deployed to {os.getenv('DD_ENV', 'prod')} with version {options['version']}",
                tags=[
                    f"service:grv-api",
                    f"env:{os.getenv('DD_ENV', 'prod')}",
                    "source:deploy",
                    f"version:{options['version']}",
                    f"deployer:{options.get('deployer', 'system')}",
                ],
                alert_type='info'
            )
            
            self.stdout.write(self.style.SUCCESS('Deployment event sent successfully'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to send deployment event: {e}'))

# Add to your Django settings.py or create a separate tracing settings module
