import logging
import re

class SensitiveDataFilter(logging.Filter):
    """Redact sensitive information from logs"""
    SENSITIVE_PATTERNS = {
        r'(?i)password': '[REDACTED]',
        r'(?i)api[-_]?key': '[REDACTED]',
        r'(?i)token': '[REDACTED]',
        r'\d{4}-\d{4}-\d{4}-\d{4}': '[CREDIT CARD REDACTED]'  # Basic CC pattern
    }

    def filter(self, record):
        try:
            msg = str(record.msg)
            for pattern, replacement in self.SENSITIVE_PATTERNS.items():
                msg = re.sub(pattern, replacement, msg)
            record.msg = msg
        except Exception as e:
            pass  
        return True


# Standard LogRecord attributes — anything NOT in this set came from `extra`
_STANDARD_ATTRS = {
    'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename',
    'module', 'exc_info', 'exc_text', 'stack_info', 'lineno', 'funcName',
    'created', 'msecs', 'relativeCreated', 'thread', 'threadName',
    'processName', 'process', 'message', 'asctime', 'taskName',
}

class ExtraFieldsFormatter(logging.Formatter):
    """Appends any `extra={}` fields onto the formatted log line."""

    def format(self, record):
        base = super().format(record)
        extras = {
            k: v for k, v in record.__dict__.items()
            if k not in _STANDARD_ATTRS
        }
        if extras:
            extras_str = " ".join(f"{k}={v!r}" for k, v in extras.items())
            return f"{base} | {extras_str}"
        return base