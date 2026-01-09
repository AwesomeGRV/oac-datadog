"""
JSON logging formatter with Datadog trace correlation and sensitive data masking.
"""

import json
import logging
import re
import time
from datetime import datetime
from typing import Any, Dict, Optional
import ddtrace
from ddtrace import tracer


class DatadogJSONFormatter(logging.Formatter):
    """
    JSON formatter that includes Datadog trace context and masks sensitive data.
    """
    
    # Patterns for sensitive data masking
    SENSITIVE_PATTERNS = [
        (r'password["\s]*[:=]["\s]*[^"\s,}]+', 'password": "***"'),
        (r'token["\s]*[:=]["\s]*[^"\s,}]+', 'token": "***"'),
        (r'api_key["\s]*[:=]["\s]*[^"\s,}]+', 'api_key": "***"'),
        (r'secret["\s]*[:=]["\s]*[^"\s,}]+', 'secret": "***"'),
        (r'authorization["\s]*[:=]["\s]*[^"\s,}]+', 'authorization": "***"'),
        (r'credit_card["\s]*[:=]["\s]*[^"\s,}]+', 'credit_card": "***"'),
        (r'ssn["\s]*[:=]["\s]*[^"\s,}]+', 'ssn": "***"'),
        (r'email["\s]*[:=]["\s]*[^@\s]+@[^@\s]+\.[^@\s]+', 'email": "***@***.***"'),
    ]
    
    # Email pattern for masking
    EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    # IP pattern for masking (optional)
    IP_PATTERN = re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b')
    
    def __init__(
        self,
        service: str = "grv-api",
        env: str = "prod",
        version: str = "v1.0.0",
        mask_sensitive: bool = True,
        include_trace: bool = True,
    ):
        super().__init__()
        self.service = service
        self.env = env
        self.version = version
        self.mask_sensitive = mask_sensitive
        self.include_trace = include_trace
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON with Datadog context."""
        
        # Base log data
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "process_id": record.process,
            "thread_id": record.thread,
            "service": self.service,
            "env": self.env,
            "version": self.version,
        }
        
        # Add Datadog trace context
        if self.include_trace:
            span = tracer.current_span()
            if span:
                log_data.update({
                    "dd.trace_id": f"{span.trace_id:032x}",
                    "dd.span_id": f"{span.span_id:016x}",
                    "dd.service": self.service,
                    "dd.env": self.env,
                    "dd.version": self.version,
                })
            else:
                # Add placeholder if no span
                log_data.update({
                    "dd.trace_id": "0",
                    "dd.span_id": "0",
                    "dd.service": self.service,
                    "dd.env": self.env,
                    "dd.version": self.version,
                })
        
        # Add exception information if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "stack_trace": self.formatException(record.exc_info),
            }
        
        # Add extra fields from record
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in {
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                'filename', 'module', 'lineno', 'funcName', 'created',
                'msecs', 'relativeCreated', 'thread', 'threadName',
                'processName', 'process', 'getMessage', 'exc_info',
                'exc_text', 'stack_info'
            }:
                extra_fields[key] = value
        
        if extra_fields:
            log_data["extra"] = extra_fields
        
        # Mask sensitive data
        if self.mask_sensitive:
            log_data = self._mask_sensitive_data(log_data)
        
        # Convert to JSON
        try:
            return json.dumps(log_data, default=self._json_serializer, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            # Fallback to simple format if JSON serialization fails
            fallback_data = {
                "timestamp": log_data["timestamp"],
                "level": log_data["level"],
                "message": log_data["message"],
                "service": self.service,
                "env": self.env,
                "json_error": str(e)
            }
            return json.dumps(fallback_data, ensure_ascii=False)
    
    def _mask_sensitive_data(self, data: Any) -> Any:
        """Recursively mask sensitive data in log entries."""
        
        if isinstance(data, str):
            # Apply masking patterns
            masked_data = data
            for pattern, replacement in self.SENSITIVE_PATTERNS:
                masked_data = re.sub(pattern, replacement, masked_data, flags=re.IGNORECASE)
            
            # Mask emails
            masked_data = self.EMAIL_PATTERN.sub('***@***.***', masked_data)
            
            return masked_data
        
        elif isinstance(data, dict):
            # Recursively mask dictionary values
            masked_dict = {}
            for key, value in data.items():
                if any(sensitive in key.lower() for sensitive in ['password', 'token', 'secret', 'key', 'auth']):
                    masked_dict[key] = "***"
                else:
                    masked_dict[key] = self._mask_sensitive_data(value)
            return masked_dict
        
        elif isinstance(data, list):
            # Recursively mask list items
            return [self._mask_sensitive_data(item) for item in data]
        
        else:
            return data
    
    def _json_serializer(self, obj: Any) -> str:
        """Custom JSON serializer for non-serializable objects."""
        if hasattr(obj, 'isoformat'):  # datetime objects
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):  # custom objects
            return str(obj)
        else:
            return str(obj)


class StructuredLogger:
    """
    Helper class for structured logging with automatic context.
    """
    
    def __init__(self, name: str, service: str = "grv-api", env: str = "prod"):
        self.logger = logging.getLogger(name)
        self.service = service
        self.env = env
    
    def _log_with_context(self, level: int, message: str, **kwargs):
        """Log message with automatic context."""
        extra = {
            'service': self.service,
            'env': self.env,
            **kwargs
        }
        
        # Add trace context if available
        span = tracer.current_span()
        if span:
            extra.update({
                'dd.trace_id': f"{span.trace_id:032x}",
                'dd.span_id': f"{span.span_id:016x}",
            })
        
        self.logger.log(level, message, extra=extra)
    
    def info(self, message: str, **kwargs):
        """Log info message with context."""
        self._log_with_context(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with context."""
        self._log_with_context(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message with context."""
        self._log_with_context(logging.ERROR, message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with context."""
        self._log_with_context(logging.DEBUG, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message with context."""
        self._log_with_context(logging.CRITICAL, message, **kwargs)


class RequestContextFilter(logging.Filter):
    """
    Filter that adds request context to log records.
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add request context to log record."""
        # Try to get request from thread local storage
        try:
            from django.utils.deprecation import MiddlewareMixin
            # This would be set by middleware
            if hasattr(record, 'request'):
                request = record.request
                record.request_id = getattr(request, 'request_id', None)
                record.user_id = getattr(request, 'user', {}).id if hasattr(request, 'user') and request.user.is_authenticated else None
                record.method = getattr(request, 'method', None)
                record.path = getattr(request, 'path', None)
        except ImportError:
            pass
        
        return True


class PerformanceFilter(logging.Filter):
    """
    Filter that adds performance metrics to log records.
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add performance context to log record."""
        record.timestamp_ms = int(time.time() * 1000)
        
        # Add memory usage if available
        try:
            import psutil
            process = psutil.Process()
            record.memory_mb = process.memory_info().rss / 1024 / 1024
            record.cpu_percent = process.cpu_percent()
        except ImportError:
            pass
        
        return True


def setup_logging(
    service: str = "grv-api",
    env: str = "prod",
    version: str = "v1.0.0",
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    mask_sensitive: bool = True,
) -> None:
    """
    Set up JSON logging with Datadog integration.
    """
    
    # Create formatters
    json_formatter = DatadogJSONFormatter(
        service=service,
        env=env,
        version=version,
        mask_sensitive=mask_sensitive,
    )
    
    # Create handlers
    handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(json_formatter)
    console_handler.addFilter(RequestContextFilter())
    console_handler.addFilter(PerformanceFilter())
    handlers.append(console_handler)
    
    # File handler (if specified)
    if log_file:
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=100 * 1024 * 1024,  # 100MB
            backupCount=5,
        )
        file_handler.setFormatter(json_formatter)
        file_handler.addFilter(RequestContextFilter())
        file_handler.addFilter(PerformanceFilter())
        handlers.append(file_handler)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add new handlers
    for handler in handlers:
        root_logger.addHandler(handler)
    
    # Configure specific loggers
    loggers_to_configure = [
        'django',
        'grv',
        'celery',
        'ddtrace',
    ]
    
    for logger_name in loggers_to_configure:
        logger = logging.getLogger(logger_name)
        logger.setLevel(getattr(logging, log_level.upper()))
        
        # Remove existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # Add handlers
        for handler in handlers:
            logger.addHandler(handler)
