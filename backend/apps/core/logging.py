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
            pass  # Don't break logging if filtering fails
        return True