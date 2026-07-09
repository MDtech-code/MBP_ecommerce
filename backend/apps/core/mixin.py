# mixin.py
from .fields import CustomDateTimeField
class TimestampFieldsMixin:
    created_at = CustomDateTimeField()
    updated_at = CustomDateTimeField()
